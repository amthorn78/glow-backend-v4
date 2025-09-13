"""
Redis Session Store Implementation for T3.1-R2
Feature-flagged Redis backend for enterprise session management
"""

import os
import json
import redis
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class SessionStore:
    """Abstract session store interface"""
    
    def create_session(self, user_id: int) -> Dict:
        """Create new session, return session metadata"""
        raise NotImplementedError
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data, return None if not found/expired"""
        raise NotImplementedError
    
    def touch_session(self, session_id: str) -> Dict:
        """Update last_seen, return renewal info"""
        raise NotImplementedError
    
    def destroy_session(self, session_id: str) -> None:
        """Destroy single session"""
        raise NotImplementedError
    
    def destroy_all_user_sessions(self, user_id: int) -> int:
        """Destroy all sessions for user, return count"""
        raise NotImplementedError
    
    def list_user_sessions(self, user_id: int) -> List[str]:
        """List all session IDs for user"""
        raise NotImplementedError


class FilesystemSessionStore(SessionStore):
    """Filesystem-based session store (fallback/development)"""
    
    def __init__(self):
        self.sessions = {}  # In-memory for simplicity
        logger.info("Initialized filesystem session store")
    
    def create_session(self, user_id: int) -> Dict:
        session_id = f"fs_{uuid.uuid4().hex}"
        now = datetime.utcnow()
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': now.isoformat() + 'Z',
            'last_seen': now.isoformat() + 'Z',
            'absolute_expires_at': (now + timedelta(hours=24)).isoformat() + 'Z'
        }
        
        self.sessions[session_id] = session_data
        logger.info(f"Session created: {session_id} for user {user_id}")
        return session_data
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        session_data = self.sessions.get(session_id)
        if not session_data:
            return None
        
        # Check absolute expiry
        now = datetime.utcnow()
        absolute_expires_at = datetime.fromisoformat(session_data['absolute_expires_at'].replace('Z', ''))
        
        if now > absolute_expires_at:
            self.destroy_session(session_id)
            logger.info(f"Session expired (absolute): {session_id}")
            return None
        
        # Check idle expiry
        last_seen = datetime.fromisoformat(session_data['last_seen'].replace('Z', ''))
        if now - last_seen > timedelta(minutes=30):
            self.destroy_session(session_id)
            logger.info(f"Session expired (idle): {session_id}")
            return None
        
        return session_data
    
    def touch_session(self, session_id: str) -> Dict:
        session_data = self.get_session(session_id)
        if not session_data:
            return {'renewed': False, 'idle_ttl_seconds': 0}
        
        now = datetime.utcnow()
        last_seen = datetime.fromisoformat(session_data['last_seen'].replace('Z', ''))
        
        # Calculate remaining idle time
        idle_expires_at = last_seen + timedelta(minutes=30)
        time_until_idle_expiry = idle_expires_at - now
        idle_ttl_seconds = max(0, int(time_until_idle_expiry.total_seconds()))
        
        # Check if renewal needed (within 10 minutes of expiry)
        renewed = idle_ttl_seconds <= 600  # 10 minutes
        
        if renewed:
            session_data['last_seen'] = now.isoformat() + 'Z'
            self.sessions[session_id] = session_data
            idle_ttl_seconds = 1800  # Reset to 30 minutes
            logger.info(f"Session renewed: {session_id}")
        
        return {
            'renewed': renewed,
            'idle_ttl_seconds': idle_ttl_seconds
        }
    
    def destroy_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            user_id = self.sessions[session_id].get('user_id')
            del self.sessions[session_id]
            logger.info(f"Session destroyed: {session_id} for user {user_id}")
    
    def destroy_all_user_sessions(self, user_id: int) -> int:
        sessions_to_remove = [
            sid for sid, data in self.sessions.items() 
            if data.get('user_id') == user_id
        ]
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
        
        count = len(sessions_to_remove)
        logger.info(f"Destroyed {count} sessions for user {user_id}")
        return count
    
    def list_user_sessions(self, user_id: int) -> List[str]:
        return [
            sid for sid, data in self.sessions.items() 
            if data.get('user_id') == user_id
        ]


class RedisSessionStore(SessionStore):
    """Redis-based session store for production"""
    
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.idle_minutes = int(os.environ.get('SESSION_IDLE_MINUTES', 30))
        self.absolute_minutes = int(os.environ.get('SESSION_ABSOLUTE_MINUTES', 1440))  # 24 hours
        self.renew_threshold_minutes = int(os.environ.get('SESSION_RENEW_THRESHOLD_MINUTES', 10))
        
        # Test connection
        self.redis_client.ping()
        logger.info(f"Initialized Redis session store: idle={self.idle_minutes}m, absolute={self.absolute_minutes}m")
    
    def create_session(self, user_id: int) -> Dict:
        session_id = f"redis_{uuid.uuid4().hex}"
        now = datetime.utcnow()
        
        session_data = {
            'user_id': str(user_id),
            'created_at': now.isoformat() + 'Z',
            'last_seen': now.isoformat() + 'Z',
            'absolute_expires_at': (now + timedelta(minutes=self.absolute_minutes)).isoformat() + 'Z'
        }
        
        # Store session hash with TTL
        session_key = f"sess:{session_id}"
        user_sessions_key = f"sess:user:{user_id}"
        
        pipe = self.redis_client.pipeline()
        pipe.hset(session_key, mapping=session_data)
        pipe.expire(session_key, self.idle_minutes * 60)
        pipe.sadd(user_sessions_key, session_id)
        pipe.expire(user_sessions_key, self.absolute_minutes * 60)
        pipe.execute()
        
        result = session_data.copy()
        result['session_id'] = session_id
        
        logger.info(f"Redis session created: {session_id} for user {user_id}")
        return result
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        session_key = f"sess:{session_id}"
        
        try:
            session_data = self.redis_client.hgetall(session_key)
            if not session_data:
                return None
            
            # Check absolute expiry
            now = datetime.utcnow()
            absolute_expires_at = datetime.fromisoformat(session_data['absolute_expires_at'].replace('Z', ''))
            
            if now > absolute_expires_at:
                self.destroy_session(session_id)
                logger.info(f"Redis session expired (absolute): {session_id}")
                return None
            
            # Convert user_id back to int
            session_data['user_id'] = int(session_data['user_id'])
            return session_data
            
        except (redis.RedisError, ValueError, KeyError) as e:
            logger.error(f"Redis session get error: {e}")
            return None
    
    def touch_session(self, session_id: str) -> Dict:
        session_data = self.get_session(session_id)
        if not session_data:
            return {'renewed': False, 'idle_ttl_seconds': 0}
        
        session_key = f"sess:{session_id}"
        
        try:
            # Get current TTL
            current_ttl = self.redis_client.ttl(session_key)
            if current_ttl <= 0:
                return {'renewed': False, 'idle_ttl_seconds': 0}
            
            # Check if renewal needed
            renew_threshold_seconds = self.renew_threshold_minutes * 60
            renewed = current_ttl <= renew_threshold_seconds
            
            if renewed:
                now = datetime.utcnow()
                new_ttl = self.idle_minutes * 60
                
                # Update last_seen and extend TTL
                pipe = self.redis_client.pipeline()
                pipe.hset(session_key, 'last_seen', now.isoformat() + 'Z')
                pipe.expire(session_key, new_ttl)
                pipe.execute()
                
                logger.info(f"Redis session renewed: {session_id}, TTL reset to {new_ttl}s")
                return {'renewed': True, 'idle_ttl_seconds': new_ttl}
            else:
                return {'renewed': False, 'idle_ttl_seconds': current_ttl}
                
        except redis.RedisError as e:
            logger.error(f"Redis session touch error: {e}")
            return {'renewed': False, 'idle_ttl_seconds': 0}
    
    def destroy_session(self, session_id: str) -> None:
        session_key = f"sess:{session_id}"
        
        try:
            # Get user_id before deletion for cleanup
            session_data = self.redis_client.hgetall(session_key)
            user_id = session_data.get('user_id')
            
            # Remove from session hash and user index
            pipe = self.redis_client.pipeline()
            pipe.delete(session_key)
            if user_id:
                pipe.srem(f"sess:user:{user_id}", session_id)
            pipe.execute()
            
            logger.info(f"Redis session destroyed: {session_id} for user {user_id}")
            
        except redis.RedisError as e:
            logger.error(f"Redis session destroy error: {e}")
    
    def destroy_all_user_sessions(self, user_id: int) -> int:
        user_sessions_key = f"sess:user:{user_id}"
        
        try:
            # Get all session IDs for user
            session_ids = self.redis_client.smembers(user_sessions_key)
            
            if not session_ids:
                return 0
            
            # Delete all sessions
            pipe = self.redis_client.pipeline()
            for session_id in session_ids:
                pipe.delete(f"sess:{session_id}")
            pipe.delete(user_sessions_key)
            pipe.execute()
            
            count = len(session_ids)
            logger.info(f"Redis destroyed {count} sessions for user {user_id}")
            return count
            
        except redis.RedisError as e:
            logger.error(f"Redis destroy all sessions error: {e}")
            return 0
    
    def list_user_sessions(self, user_id: int) -> List[str]:
        user_sessions_key = f"sess:user:{user_id}"
        
        try:
            return list(self.redis_client.smembers(user_sessions_key))
        except redis.RedisError as e:
            logger.error(f"Redis list sessions error: {e}")
            return []


def get_session_store() -> SessionStore:
    """Factory function to get session store based on configuration"""
    backend = os.environ.get('SESSION_BACKEND', 'filesystem').lower()
    
    if backend == 'redis':
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            logger.warning("SESSION_BACKEND=redis but REDIS_URL not set, falling back to filesystem")
            return FilesystemSessionStore()
        
        try:
            return RedisSessionStore(redis_url)
        except Exception as e:
            logger.error(f"Failed to initialize Redis session store: {e}")
            logger.warning("Falling back to filesystem session store")
            return FilesystemSessionStore()
    else:
        return FilesystemSessionStore()

