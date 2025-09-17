"""
Test logout JSON contract and idempotent behavior
S1.1-5: Validate logout JSON contract (idempotent, no redirects)
"""
import os
import pytest

# Skip by default - only run when explicitly enabled
if os.getenv('RUN_E2E') != '1':
    pytest.skip('E2E contract tests disabled by default; set RUN_E2E=1 to enable.', allow_module_level=True)

def test_logout_with_active_session(admin_session):
    """Test logout with active session returns standardized JSON"""
    response = admin_session.post('/api/auth/logout')
    
    assert response.status_code == 200
    assert response.headers.get('Cache-Control') == 'no-store'
    
    # Check for no redirect headers
    assert 'Location' not in response.headers
    
    data = response.get_json()
    
    # Standardized logout JSON contract
    assert data == {
        'status': 'ok',
        'code': 'LOGOUT',
        'message': 'Logged out',
        'idempotent': True,
        'ok': True
    }

def test_logout_without_session(client):
    """Test logout without session returns same JSON schema"""
    response = client.post('/api/auth/logout')
    
    assert response.status_code == 200
    assert response.headers.get('Cache-Control') == 'no-store'
    
    # Check for no redirect headers
    assert 'Location' not in response.headers
    
    data = response.get_json()
    
    # Same schema but different message
    assert data == {
        'status': 'ok',
        'code': 'LOGOUT',
        'message': 'No active session',
        'idempotent': True,
        'ok': True
    }

def test_logout_idempotent_behavior(admin_session):
    """Test that multiple logout calls return consistent responses"""
    # First logout (with session)
    response1 = admin_session.post('/api/auth/logout')
    assert response1.status_code == 200
    data1 = response1.get_json()
    assert data1['message'] == 'Logged out'
    
    # Second logout (no session)
    response2 = admin_session.post('/api/auth/logout')
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert data2['message'] == 'No active session'
    
    # Both responses have same structure
    assert data1['status'] == data2['status'] == 'ok'
    assert data1['code'] == data2['code'] == 'LOGOUT'
    assert data1['idempotent'] == data2['idempotent'] is True
    assert data1['ok'] == data2['ok'] is True

def test_logout_security_headers(admin_session):
    """Test that logout includes required security headers"""
    response = admin_session.post('/api/auth/logout')
    
    assert response.status_code == 200
    
    # Required security headers
    assert response.headers.get('Cache-Control') == 'no-store'
    assert 'Content-Security-Policy-Report-Only' in response.headers
    assert 'Cross-Origin-Opener-Policy' in response.headers
    assert 'Referrer-Policy' in response.headers
    assert 'X-Content-Type-Options' in response.headers
    assert 'X-Frame-Options' in response.headers

def test_logout_clears_session(admin_session):
    """Test that logout actually clears the session"""
    # Verify session is active
    response = admin_session.get('/api/auth/me')
    assert response.status_code == 200
    
    # Logout
    logout_response = admin_session.post('/api/auth/logout')
    assert logout_response.status_code == 200
    
    # Verify session is cleared
    response = admin_session.get('/api/auth/me')
    assert response.status_code == 401

