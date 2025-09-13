"""
CSRF Protection Implementation for T3.2
Double-submit token pattern with feature flag support
"""

import os
import secrets
import logging
from functools import wraps
from flask import request, jsonify, session, make_response

def generate_csrf_token():
    """Generate a cryptographically secure CSRF token (>=128 bits)"""
    return secrets.token_urlsafe(32)  # 256 bits, URL-safe base64

def get_csrf_enforcement():
    """Check if CSRF enforcement is enabled via feature flag"""
    return os.environ.get('CSRF_ENFORCE', 'false').lower() == 'true'

def set_csrf_cookie(response, csrf_token):
    """Set the glow_csrf cookie with proper attributes"""
    response.set_cookie(
        'glow_csrf',
        csrf_token,
        max_age=7200,  # 2 hours
        secure=True,
        httponly=False,  # Must be readable by JavaScript
        samesite='Lax',
        path='/'
    )
    return response

def validate_csrf_token(session_store, logger):
    """
    Validate CSRF token using double-submit pattern
    Returns (is_valid, error_code, error_message)
    """
    # Get CSRF token from header
    csrf_header = request.headers.get('X-CSRF-Token')
    if not csrf_header:
        return False, 'CSRF_MISSING', 'CSRF token missing'
    
    # Get CSRF token from cookie
    csrf_cookie = request.cookies.get('glow_csrf')
    if not csrf_cookie:
        return False, 'CSRF_COOKIE_MISSING', 'CSRF cookie missing'
    
    # Check if header matches cookie (first validation)
    if csrf_header != csrf_cookie:
        return False, 'CSRF_INVALID', 'CSRF validation failed'
    
    # Get session data to validate against stored CSRF
    session_id = session.get('session_id')
    if not session_id:
        return False, 'CSRF_INVALID', 'CSRF validation failed'
    
    session_data = session_store.get_session(session_id)
    if not session_data:
        return False, 'CSRF_INVALID', 'CSRF validation failed'
    
    # Check if token matches session-stored CSRF (second validation)
    stored_csrf = session_data.get('csrf')
    if not stored_csrf or csrf_header != stored_csrf:
        return False, 'CSRF_INVALID', 'CSRF validation failed'
    
    return True, None, None

def csrf_protect(session_store, validate_auth_session_func):
    """
    CSRF protection decorator for authenticated mutations
    Only applies to POST, PUT, PATCH, DELETE methods
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger = logging.getLogger(__name__)
            
            # Only apply CSRF protection to mutation methods
            if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
                return f(*args, **kwargs)
            
            # Check if user is authenticated first
            user_id, auth_error = validate_auth_session_func()
            if not user_id:
                # Not authenticated - return auth error, not CSRF error
                return f(*args, **kwargs)
            
            # Validate CSRF token
            is_valid, error_code, error_message = validate_csrf_token(session_store, logger)
            
            # Log CSRF validation attempt
            session_id = session.get('session_id', 'unknown')
            if is_valid:
                logger.info(f"csrf_validate: session_id={session_id}, ok=true")
            else:
                logger.warning(f"csrf_fail: session_id={session_id}, reason={error_code}")
            
            # Check enforcement flag
            enforce = get_csrf_enforcement()
            
            if not is_valid:
                if enforce:
                    # Enforcement enabled - block the request
                    response_data = {
                        'ok': False,
                        'code': error_code,
                        'error': error_message
                    }
                    response = jsonify(response_data)
                    response.headers['Content-Type'] = 'application/json; charset=utf-8'
                    response.headers['Cache-Control'] = 'no-store'
                    response.headers['Vary'] = 'Origin'
                    return response, 403
                else:
                    # Shadow mode - log but allow request
                    logger.info(f"csrf_shadow_mode: would_block=true, reason={error_code}, session_id={session_id}")
            
            # CSRF validation passed or enforcement disabled - proceed
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def create_csrf_endpoints(app, session_store, validate_auth_session):
    """Create CSRF-related endpoints"""
    
    @app.route('/api/auth/csrf', methods=['GET'])
    def get_csrf_token():
        """Endpoint to fetch/rotate CSRF token"""
        logger = app.logger
        
        try:
            # Validate authentication
            user_id, error_code = validate_auth_session()
            if not user_id:
                return jsonify({
                    'ok': False,
                    'error': 'Authentication required',
                    'code': error_code
                }), 401
            
            # Generate new CSRF token
            csrf_token = generate_csrf_token()
            
            # Store in session
            session_id = session.get('session_id')
            if session_id:
                session_data = session_store.get_session(session_id)
                if session_data:
                    session_data['csrf'] = csrf_token
                    # Update session with new CSRF token
                    session_store.update_session(session_id, session_data)
            
            # Create response with new token
            response_data = {
                'ok': True,
                'csrf': csrf_token
            }
            
            response = make_response(jsonify(response_data))
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Vary'] = 'Origin'
            
            # Set new CSRF cookie
            set_csrf_cookie(response, csrf_token)
            
            logger.info(f"csrf_rotate: user_id={user_id}, session_id={session_id}")
            
            return response, 200
            
        except Exception as e:
            logger.error(f"CSRF token rotation error: {e}")
            return jsonify({
                'ok': False,
                'error': 'CSRF token rotation failed',
                'code': 'INTERNAL_ERROR'
            }), 500

def add_csrf_to_login(session_data, response, logger):
    """
    Add CSRF token to login response
    Call this from the login endpoint after successful authentication
    """
    try:
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        
        # Add to session data
        session_data['csrf'] = csrf_token
        
        # Set CSRF cookie
        set_csrf_cookie(response, csrf_token)
        
        logger.info(f"csrf_issue: user_id={session_data.get('user_id')}, session_id={session_data.get('session_id')}")
        
        return session_data
        
    except Exception as e:
        logger.error(f"CSRF token issuance error: {e}")
        # Don't fail login if CSRF fails
        return session_data

def clear_csrf_on_logout(response):
    """Clear CSRF cookie on logout"""
    response.set_cookie(
        'glow_csrf',
        '',
        max_age=0,
        secure=True,
        httponly=False,
        samesite='Lax',
        path='/'
    )
    return response

# Test function for CSRF validation
def test_csrf_protection():
    """Test CSRF token generation and validation"""
    token1 = generate_csrf_token()
    token2 = generate_csrf_token()
    
    print(f"CSRF Token 1: {token1}")
    print(f"CSRF Token 2: {token2}")
    print(f"Tokens different: {token1 != token2}")
    print(f"Token length: {len(token1)} characters")
    print(f"Enforcement enabled: {get_csrf_enforcement()}")

if __name__ == "__main__":
    test_csrf_protection()

