"""
Test /api/auth/me response shape and contract
S1.1-5: Lock the auth/me response shape (no profile_version; includes birth_data fields)
"""
import os
import pytest

# Skip by default - only run when explicitly enabled
if os.getenv('RUN_E2E') != '1':
    pytest.skip('E2E contract tests disabled by default; set RUN_E2E=1 to enable.', allow_module_level=True)

import json

def test_auth_me_response_shape(admin_session):
    """Test that /api/auth/me returns correct response shape without profile_version"""
    response = admin_session.get('/api/auth/me')
    
    assert response.status_code == 200
    assert response.headers.get('Cache-Control') == 'no-store'
    
    data = response.get_json()
    
    # Top-level structure
    assert 'ok' in data
    assert 'user' in data
    assert 'contract_version' in data
    assert 'issued_at' in data
    assert data['ok'] is True
    
    user = data['user']
    
    # Required user fields
    assert 'id' in user
    assert 'email' in user
    assert 'first_name' in user
    assert 'last_name' in user
    assert 'status' in user
    assert 'is_admin' in user
    assert 'updated_at' in user
    
    # Profile data
    assert 'profile' in user
    profile = user['profile']
    assert 'display_name' in profile
    assert 'bio' in profile
    assert 'avatar_url' in profile
    assert 'profile_completion' in profile
    
    # Birth data structure (may be null)
    assert 'birth_data' in user
    # birth_data can be null or contain date/time/location fields
    
    # Session metadata
    assert 'session_meta' in user
    session_meta = user['session_meta']
    assert 'session_id' in session_meta
    assert 'last_seen' in session_meta
    assert 'idle_expires_at' in session_meta
    assert 'absolute_expires_at' in session_meta
    assert 'renewed' in session_meta

def test_auth_me_no_profile_version(admin_session):
    """Test that profile_version field is absent from response"""
    response = admin_session.get('/api/auth/me')
    
    assert response.status_code == 200
    data = response.get_json()
    
    # Ensure profile_version is not in the response anywhere
    response_str = json.dumps(data)
    assert 'profile_version' not in response_str
    
    # Specifically check user object doesn't have profile_version
    user = data['user']
    assert 'profile_version' not in user

def test_auth_me_security_headers(admin_session):
    """Test that auth/me includes required security headers"""
    response = admin_session.get('/api/auth/me')
    
    assert response.status_code == 200
    
    # Required security headers
    assert response.headers.get('Cache-Control') == 'no-store'
    assert 'Content-Security-Policy-Report-Only' in response.headers
    assert 'Cross-Origin-Opener-Policy' in response.headers
    assert 'Referrer-Policy' in response.headers
    assert 'X-Content-Type-Options' in response.headers
    assert 'X-Frame-Options' in response.headers

def test_auth_me_unauthorized(client):
    """Test that /api/auth/me returns 401 for unauthenticated requests"""
    response = client.get('/api/auth/me')
    
    assert response.status_code == 401
    data = response.get_json()
    
    assert 'ok' in data
    assert data['ok'] is False
    assert 'error' in data

