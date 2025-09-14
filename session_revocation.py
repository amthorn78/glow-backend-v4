"""
Session Revocation Implementation for T-BE-003
Logout-all and password-change session invalidation
"""

import os
import logging
from flask import request, jsonify, session, make_response
from functools import wraps

def get_revocation_enabled():
    """Check if session revocation is enabled via feature flag"""
    return os.environ.get('REVOCATION_ENABLE', 'true').lower() == 'true'

def add_session_to_user_set(session_store, user_id, session_id):
    """Add session to user's session set for tracking"""
    try:
        if hasattr(session_store, 'redis_client') and session_store.redis_client:
            # Redis backend - use SET operations
            user_sessions_key = f"user:{user_id}:sessions"
            session_store.redis_client.sadd(user_sessions_key, session_id)
            # Set TTL on the user sessions set (24 hours + buffer)
            session_store.redis_client.expire(user_sessions_key, 86400 + 3600)
        else:
            # Filesystem backend - store in session data
            session_data = session_store.get_session(session_id)
            if session_data:
                session_data['user_sessions_tracking'] = True
                session_store.update_session(session_id, session_data)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to add session to user set: {e}")

def remove_session_from_user_set(session_store, user_id, session_id):
    """Remove session from user's session set"""
    try:
        if hasattr(session_store, 'redis_client') and session_store.redis_client:
            # Redis backend - use SET operations
            user_sessions_key = f"user:{user_id}:sessions"
            session_store.redis_client.srem(user_sessions_key, session_id)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to remove session from user set: {e}")

def get_user_sessions(session_store, user_id):
    """Get all session IDs for a user"""
    try:
        if hasattr(session_store, 'redis_client') and session_store.redis_client:
            # Redis backend - use SET operations
            user_sessions_key = f"user:{user_id}:sessions"
            session_ids = session_store.redis_client.smembers(user_sessions_key)
            return [sid.decode('utf-8') if isinstance(sid, bytes) else sid for sid in session_ids]
        else:
            # Filesystem backend - can't enumerate easily, return empty
            return []
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to get user sessions: {e}")
        return []

def revoke_user_sessions(session_store, user_id, exclude_session_id=None):
    """
    Revoke all sessions for a user
    Returns (revoked_count, errors)
    """
    logger = logging.getLogger(__name__)
    revoked_count = 0
    errors = []
    
    try:
        # Get all session IDs for the user
        session_ids = get_user_sessions(session_store, user_id)
        
        logger.info(f"Revoking sessions for user {user_id}: {len(session_ids)} sessions found")
        
        for session_id in session_ids:
            if exclude_session_id and session_id == exclude_session_id:
                continue
                
            try:
                # Delete the session
                session_store.delete_session(session_id)
                
                # Remove from user's session set
                remove_session_from_user_set(session_store, user_id, session_id)
                
                revoked_count += 1
                logger.info(f"Revoked session {session_id} for user {user_id}")
                
            except Exception as e:
                error_msg = f"Failed to revoke session {session_id}: {e}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        return revoked_count, errors
        
    except Exception as e:
        error_msg = f"Failed to revoke sessions for user {user_id}: {e}"
        errors.append(error_msg)
        logger.error(error_msg)
        return revoked_count, errors

def rotate_current_session(session_store, current_session_id, user_id):
    """
    Rotate current session ID for security
    Returns (new_session_id, success)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get current session data
        session_data = session_store.get_session(current_session_id)
        if not session_data:
            return None, False
        
        # Generate new session ID
        import secrets
        new_session_id = f"redis_{secrets.token_hex(16)}"
        
        # Create new session with same data
        session_store.create_session(new_session_id, session_data)
        
        # Add new session to user set
        add_session_to_user_set(session_store, user_id, new_session_id)
        
        # Delete old session
        session_store.delete_session(current_session_id)
        remove_session_from_user_set(session_store, user_id, current_session_id)
        
        logger.info(f"Rotated session for user {user_id}: {current_session_id} → {new_session_id}")
        
        return new_session_id, True
        
    except Exception as e:
        logger.error(f"Failed to rotate session for user {user_id}: {e}")
        return None, False

def create_revocation_endpoints(app, session_store, validate_auth_session, csrf_protect):
    """Create session revocation endpoints"""
    
    @app.route('/api/auth/logout-all', methods=['POST'])
    @csrf_protect(session_store, validate_auth_session)
    def logout_all():
        """Logout all sessions for current user"""
        logger = app.logger
        
        try:
            # Check feature flag
            if not get_revocation_enabled():
                return jsonify({
                    'ok': False,
                    'error': 'DISABLED',
                    'code': 'FEATURE_DISABLED'
                }), 503
            
            # Validate authentication
            user_id, error_code = validate_auth_session()
            if not user_id:
                return jsonify({
                    'ok': False,
                    'error': 'Authentication required',
                    'code': error_code or 'AUTH_REQUIRED'
                }), 401
            
            current_session_id = session.get('session_id')
            
            # Revoke all sessions (KILL_ALL mode - including current)
            revoked_count, errors = revoke_user_sessions(session_store, user_id)
            
            # Log revocation event
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            user_agent = request.headers.get('User-Agent', 'unknown')
            
            logger.info(f"auth_logout_all: user_id={user_id}, count_revoked={revoked_count}, "
                       f"self_revoked=true, ip={client_ip}, ua={user_agent[:50]}")
            
            # Create response
            response_data = {
                'ok': True,
                'revoked_count': revoked_count,
                'self_revoked': True
            }
            
            response = make_response(jsonify(response_data))
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            response.headers['Cache-Control'] = 'no-store'
            
            # Clear current session cookie (KILL_ALL mode)
            response.set_cookie(
                'glow_session',
                '',
                max_age=0,
                secure=True,
                httponly=True,
                samesite='Lax',
                path='/'
            )
            
            # Clear CSRF cookie
            response.set_cookie(
                'glow_csrf',
                '',
                max_age=0,
                secure=True,
                httponly=False,
                samesite='Lax',
                path='/'
            )
            
            return response, 200
            
        except Exception as e:
            logger.error(f"Logout-all error: {e}")
            return jsonify({
                'ok': False,
                'error': 'Logout-all failed',
                'code': 'INTERNAL_ERROR'
            }), 500
    
    @app.route('/api/auth/password', methods=['POST'])
    @csrf_protect(session_store, validate_auth_session)
    def change_password():
        """Change password and revoke other sessions"""
        logger = app.logger
        
        try:
            # Check feature flag
            if not get_revocation_enabled():
                return jsonify({
                    'ok': False,
                    'error': 'DISABLED',
                    'code': 'FEATURE_DISABLED'
                }), 503
            
            # Validate authentication
            user_id, error_code = validate_auth_session()
            if not user_id:
                return jsonify({
                    'ok': False,
                    'error': 'Authentication required',
                    'code': error_code or 'AUTH_REQUIRED'
                }), 401
            
            # Get request data
            data = request.get_json()
            if not data or not data.get('current_password') or not data.get('new_password'):
                return jsonify({
                    'ok': False,
                    'error': 'Current password and new password required',
                    'code': 'VALIDATION_ERROR'
                }), 400
            
            current_password = data['current_password']
            new_password = data['new_password']
            
            # TODO: Validate current password and update to new password
            # This would integrate with your user authentication system
            # For now, we'll simulate the password change
            
            current_session_id = session.get('session_id')
            
            # Revoke all OTHER sessions (exclude current)
            revoked_count, errors = revoke_user_sessions(session_store, user_id, exclude_session_id=current_session_id)
            
            # Rotate current session ID for security
            new_session_id, rotation_success = rotate_current_session(session_store, current_session_id, user_id)
            
            # Log password change event
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            logger.info(f"auth_password_change: user_id={user_id}, others_revoked={revoked_count}, "
                       f"session_rotated={rotation_success}, ip={client_ip}")
            
            # Create response
            response_data = {
                'ok': True,
                'others_revoked': revoked_count,
                'session_rotated': rotation_success
            }
            
            response = make_response(jsonify(response_data))
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            response.headers['Cache-Control'] = 'no-store'
            
            # Update session cookie if rotation succeeded
            if rotation_success and new_session_id:
                # Update Flask session
                session['session_id'] = new_session_id
                
                # Set new session cookie
                response.set_cookie(
                    'glow_session',
                    new_session_id,
                    max_age=1800,  # 30 minutes
                    secure=True,
                    httponly=True,
                    samesite='Lax',
                    path='/'
                )
            
            return response, 200
            
        except Exception as e:
            logger.error(f"Password change error: {e}")
            return jsonify({
                'ok': False,
                'error': 'Password change failed',
                'code': 'INTERNAL_ERROR'
            }), 500

# Helper function to integrate with existing login
def track_session_on_login(session_store, user_id, session_id):
    """Call this from login endpoint to track the new session"""
    add_session_to_user_set(session_store, user_id, session_id)

# Helper function to integrate with existing logout
def untrack_session_on_logout(session_store, user_id, session_id):
    """Call this from logout endpoint to untrack the session"""
    remove_session_from_user_set(session_store, user_id, session_id)

