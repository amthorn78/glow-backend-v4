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
    return set_cookie(response, 'glow_session', session_id, max_age=max_age)

def set_csrf_cookie(response, csrf_token, max_age=1800):
    """
    Set the CSRF cookie with proper security attributes
    Note: CSRF cookies must be readable by JavaScript (httponly=False)
    
    Args:
        response: Flask response object
        csrf_token (str): CSRF token value
        max_age (int): Cookie max age in seconds (default: 30 minutes)
    
    Returns:
        Flask response object with CSRF cookie set
    """
    return set_cookie(response, 'glow_csrf', csrf_token, max_age=max_age, httponly=False)

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

