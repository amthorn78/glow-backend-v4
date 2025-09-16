"""
Centralized Cookie Management for GLOW Platform (BE-CKHLP-01)
Resolves circular import issues between app.py and csrf_protection.py
"""

import os
from flask import make_response

# ============================================================================
# COOKIE CONFIGURATION
# ============================================================================

# Environment-based cookie configuration
SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN", ".glowme.io")
SESSION_SAMESITE = os.getenv("SESSION_SAMESITE", "Lax")
SESSION_SECURE = os.getenv("SESSION_SECURE", "true").lower() == "true"

def get_cookie_options():
    """
    Get standardized cookie options for the GLOW platform
    
    Returns:
        dict: Cookie options with domain, path, security settings
    """
    return {
        'domain': SESSION_COOKIE_DOMAIN,
        'path': '/',
        'httponly': True,
        'secure': SESSION_SECURE,
        'samesite': SESSION_SAMESITE,
    }

def set_cookie(response, name, value, max_age=None, httponly=True):
    """
    Set a cookie with standardized GLOW platform options
    
    Args:
        response: Flask response object
        name (str): Cookie name
        value (str): Cookie value
        max_age (int, optional): Cookie max age in seconds
        httponly (bool): Whether cookie should be HttpOnly (default: True)
    
    Returns:
        Flask response object with cookie set
    """
    cookie_opts = get_cookie_options()
    
    # Override httponly if specified (needed for CSRF cookies)
    if not httponly:
        cookie_opts['httponly'] = False
    
    response.set_cookie(name, value, max_age=max_age, **cookie_opts)
    return response

def clear_cookie(response, name):
    """
    Clear a cookie by setting it to expire immediately
    
    Args:
        response: Flask response object
        name (str): Cookie name to clear
    
    Returns:
        Flask response object with cookie cleared
    """
    cookie_opts = get_cookie_options()
    response.set_cookie(name, "", max_age=0, expires=0, **cookie_opts)
    return response

def set_session_cookie(response, session_id, max_age=1800):
    """
    Set the main session cookie with proper security attributes
    
    Args:
        response: Flask response object
        session_id (str): Session identifier
        max_age (int): Cookie max age in seconds (default: 30 minutes)
    
    Returns:
        Flask response object with session cookie set
    """
    # Session cookies must be HttpOnly for security
    response.set_cookie(
        'glow_session',
        session_id,
        max_age=max_age,
        domain=SESSION_COOKIE_DOMAIN,
        path='/',
        httponly=True,      # Prevent JS access to session cookie
        secure=True,        # HTTPS only (always true in prod)
        samesite='Lax'      # CSRF protection while allowing navigation
    )
    return response

def set_csrf_cookie_with_fallback(response, csrf_token, max_age=1800):
    """
    Set CSRF cookie with domain fallback logic
    CSRF cookies must be JS-readable (HttpOnly=false) for double-submit pattern
    """
    from flask import request, has_request_context
    import logging
    
    configured_domain = SESSION_COOKIE_DOMAIN
    use_domain = configured_domain
    
    # Only do domain fallback logic if we're in a request context
    if has_request_context():
        host = request.host.split(':')[0]  # Strip port for comparison
        
        # Check if configured domain matches request host
        if configured_domain and configured_domain.startswith('.'):
            # For .glowme.io, check if request host ends with glowme.io
            if not host.endswith(configured_domain[1:]):
                # Domain mismatch - use host-only cookie for CSRF only
                logger = logging.getLogger(__name__)
                logger.info("csrf_issue stage=mint reason=domain_mismatch")
                use_domain = None
    
    # Set CSRF cookie with hardened security attributes
    response.set_cookie(
        'glow_csrf', 
        csrf_token,
        max_age=max_age,
        domain=use_domain,  # None for host-only when domain mismatch
        path='/',
        httponly=False,     # CSRF cookies must be JS-readable
        secure=True,        # HTTPS only (always true in prod)
        samesite='Lax'      # CSRF protection while allowing navigation
    )
    return response

def set_csrf_cookie(response, csrf_token, max_age=1800):
    """
    Set the CSRF cookie with domain fallback
    """
    return set_csrf_cookie_with_fallback(response, csrf_token, max_age)

def clear_session_cookie(response):
    """
    Clear the main session cookie
    
    Args:
        response: Flask response object
    
    Returns:
        Flask response object with session cookie cleared
    """
    return clear_cookie(response, 'glow_session')

def clear_csrf_cookie(response):
    """
    Clear the CSRF cookie
    
    Args:
        response: Flask response object
    
    Returns:
        Flask response object with CSRF cookie cleared
    """
    return clear_cookie(response, 'glow_csrf')

def clear_all_auth_cookies(response):
    """
    Clear all authentication-related cookies
    
    Args:
        response: Flask response object
    
    Returns:
        Flask response object with all auth cookies cleared
    """
    clear_session_cookie(response)
    clear_csrf_cookie(response)
    return response

# ============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# ============================================================================

def _cookie_opts():
    """
    Legacy compatibility function for existing code
    Deprecated: Use get_cookie_options() instead
    """
    return get_cookie_options()

def _set_cookie(resp, name, value, max_age=None):
    """
    Legacy compatibility function for existing code
    Deprecated: Use set_cookie() instead
    """
    return set_cookie(resp, name, value, max_age=max_age)

def _clear_cookie(resp, name):
    """
    Legacy compatibility function for existing code
    Deprecated: Use clear_cookie() instead
    """
    return clear_cookie(resp, name)

