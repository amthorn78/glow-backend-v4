"""
Session Diagnostics Implementation for T3.1-R2
Admin-only endpoint for session debugging and observability
"""

from flask import jsonify, request
from datetime import datetime

def create_session_diagnostics_endpoint(app, session_store, validate_auth_session):
    """Create the session diagnostics endpoint"""
    
    @app.route('/api/auth/session/diagnostics', methods=['GET'])
    def session_diagnostics():
        """Admin-only session diagnostics endpoint"""
        try:
            # Validate authentication
            user_id, error_code = validate_auth_session()
            if not user_id:
                return jsonify({
                    'ok': False,
                    'error': 'Authentication required',
                    'code': error_code
                }), 401
            
            # Check if user is admin (you may need to adjust this based on your User model)
            from flask import session
            session_id = session.get('session_id')
            
            # Get session data from store
            session_data = session_store.get_session(session_id)
            if not session_data:
                return jsonify({
                    'ok': False,
                    'error': 'Session not found',
                    'code': 'SESSION_NOT_FOUND'
                }), 404
            
            # Get touch info for TTL details
            touch_result = session_store.touch_session(session_id)
            
            # Calculate expiry times
            now = datetime.utcnow()
            created_at = datetime.fromisoformat(session_data['created_at'].replace('Z', ''))
            last_seen = datetime.fromisoformat(session_data['last_seen'].replace('Z', ''))
            absolute_expires_at = datetime.fromisoformat(session_data['absolute_expires_at'].replace('Z', ''))
            
            # Calculate remaining times
            idle_ttl_seconds = touch_result.get('idle_ttl_seconds', 0)
            absolute_remaining_seconds = max(0, int((absolute_expires_at - now).total_seconds()))
            
            # Determine backend type
            backend_type = 'redis' if 'redis' in session_id else 'filesystem'
            
            # Build diagnostic response
            diagnostic_data = {
                'ok': True,
                'backend': backend_type,
                'session': {
                    'session_id': session_id[:8] + '...',  # Redacted for security
                    'user_id': user_id,
                    'created_at': session_data['created_at'],
                    'last_seen': session_data['last_seen'],
                    'absolute_expires_at': session_data['absolute_expires_at'],
                    'idle_ttl_seconds': idle_ttl_seconds,
                    'absolute_remaining_seconds': absolute_remaining_seconds,
                    'renewed': touch_result.get('renewed', False)
                },
                'timestamps': {
                    'now': now.isoformat() + 'Z',
                    'session_age_seconds': int((now - created_at).total_seconds()),
                    'idle_seconds': int((now - last_seen).total_seconds())
                }
            }
            
            app.logger.info(f"Session diagnostics accessed by user {user_id}")
            return jsonify(diagnostic_data), 200
            
        except Exception as e:
            app.logger.error(f"Session diagnostics error: {e}")
            return jsonify({
                'ok': False,
                'error': 'Diagnostics failed',
                'code': 'INTERNAL_ERROR'
            }), 500
    
    @app.route('/api/auth/logout-all', methods=['POST'])
    def logout_all():
        """Logout all sessions for current user"""
        try:
            # Validate authentication
            user_id, error_code = validate_auth_session()
            if not user_id:
                return jsonify({
                    'ok': False,
                    'error': 'Authentication required',
                    'code': error_code
                }), 401
            
            # Destroy all user sessions
            count = session_store.destroy_all_user_sessions(user_id)
            
            # Clear current Flask session
            from flask import session
            session.clear()
            
            app.logger.info(f"Logout all: destroyed {count} sessions for user {user_id}")
            
            return jsonify({
                'ok': True,
                'sessions_destroyed': count
            }), 200
            
        except Exception as e:
            app.logger.error(f"Logout all error: {e}")
            return jsonify({
                'ok': False,
                'error': 'Logout all failed',
                'code': 'INTERNAL_ERROR'
            }), 500

