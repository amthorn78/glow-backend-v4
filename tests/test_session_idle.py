"""
Test sliding session renewal and idle expiry behavior
S1.1-5: Prove sliding session renewal: 30m idle expiry; ~15m rolling refresh
"""
import os
import pytest

# Skip by default - only run when explicitly enabled
if os.getenv('RUN_E2E') != '1':
    pytest.skip('E2E contract tests disabled by default; set RUN_E2E=1 to enable.', allow_module_level=True)

import time
from unittest.mock import patch
from datetime import datetime, timedelta

def test_session_renewal_enabled_config(test_app):
    """Test that session renewal is enabled in test configuration"""
    with test_app.app_context():
        assert test_app.config['SESSION_RENEWAL_ENABLED'] == '1'
        assert test_app.config['SESSION_IDLE_MIN'] == '2'  # 2 minutes for testing

def test_session_rolling_refresh(admin_session):
    """Test that session gets refreshed after half idle time"""
    # Initial request to establish baseline
    response1 = admin_session.get('/api/auth/me')
    assert response1.status_code == 200
    
    # Wait for more than half the idle time (>1 minute for 2-minute idle)
    # Using mock to avoid actual sleep in tests
    with patch('app.datetime') as mock_datetime:
        # Mock current time to be 70 seconds later (>half of 2min = 60s)
        mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(seconds=70)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        response2 = admin_session.get('/api/auth/me')
        assert response2.status_code == 200
        
        # Check if Set-Cookie header is present (indicating renewal)
        # Note: In test client, cookie handling is automatic
        data = response2.get_json()
        session_meta = data['user']['session_meta']
        
        # Session should still be valid and potentially renewed
        assert 'session_id' in session_meta
        assert 'last_seen' in session_meta

def test_session_idle_expiry(admin_session):
    """Test that session expires after full idle time"""
    # Initial request to establish session
    response1 = admin_session.get('/api/auth/me')
    assert response1.status_code == 200
    
    # Mock time to be past the idle timeout (>2 minutes)
    with patch('app.datetime') as mock_datetime:
        # Mock current time to be 130 seconds later (>2min = 120s)
        mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(seconds=130)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        response2 = admin_session.get('/api/auth/me')
        
        # Should return 401 with SESSION_EXPIRED
        assert response2.status_code == 401
        data = response2.get_json()
        
        assert data['ok'] is False
        assert data['error'] == 'session_expired'
        assert data['code'] == 'SESSION_EXPIRED'

def test_session_active_usage_no_expiry(admin_session):
    """Test that active usage prevents session expiry"""
    # Make requests within the idle window
    for i in range(3):
        response = admin_session.get('/api/auth/me')
        assert response.status_code == 200
        
        # Short delay between requests (well within idle time)
        time.sleep(0.1)
    
    # Final request should still be successful
    response = admin_session.get('/api/auth/me')
    assert response.status_code == 200

def test_session_renewal_preserves_user_data(admin_session):
    """Test that session renewal preserves user data"""
    # Get initial user data
    response1 = admin_session.get('/api/auth/me')
    assert response1.status_code == 200
    data1 = response1.get_json()
    user1 = data1['user']
    
    # Simulate renewal scenario
    with patch('app.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(seconds=70)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        response2 = admin_session.get('/api/auth/me')
        assert response2.status_code == 200
        data2 = response2.get_json()
        user2 = data2['user']
        
        # User data should be preserved
        assert user1['id'] == user2['id']
        assert user1['email'] == user2['email']
        assert user1['first_name'] == user2['first_name']
        assert user1['is_admin'] == user2['is_admin']

def test_session_expiry_json_format(admin_session):
    """Test that session expiry returns proper JSON format"""
    with patch('app.datetime') as mock_datetime:
        # Mock time past expiry
        mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(seconds=130)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        response = admin_session.get('/api/auth/me')
        
        assert response.status_code == 401
        assert response.headers.get('Cache-Control') == 'no-store'
        
        data = response.get_json()
        
        # Exact SESSION_EXPIRED format
        assert data == {
            'ok': False,
            'error': 'session_expired',
            'code': 'SESSION_EXPIRED'
        }

