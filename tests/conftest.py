"""
Test configuration for GLOW Intelligence App backend tests
"""
import os
import pytest
import tempfile
from app import app, db

# Environment configuration
BASE_URL = os.getenv('BASE_URL', 'https://www.glowme.io')
SMOKE_EMAIL = os.getenv('SMOKE_EMAIL', 'admin@glow.app')
SMOKE_PASSWORD = os.getenv('SMOKE_PASSWORD', 'admin123')

@pytest.fixture
def test_app():
    """Create test app with short session idle time for testing"""
    # Skip if required environment not set
    if os.getenv('RUN_E2E') != '1':
        pytest.skip('E2E tests disabled')
    
    # Configure test environment
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for easier testing
    app.config['SESSION_RENEWAL_ENABLED'] = '1'  # Enable session renewal for tests
    
    # Use configurable idle time or skip time-sensitive tests
    idle_min = os.getenv('SESSION_IDLE_MIN_FOR_TESTS', '2')
    app.config['SESSION_IDLE_MIN'] = idle_min
    
    # Use in-memory SQLite for tests
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(test_app):
    """Create test client"""
    return test_app.test_client()

@pytest.fixture
def admin_session(client):
    """Create authenticated admin session using dedicated test account"""
    # Create admin user (non-destructive - uses test account)
    from app import User, UserProfile, db
    from werkzeug.security import generate_password_hash
    
    admin_user = User(
        email=SMOKE_EMAIL,
        password_hash=generate_password_hash(SMOKE_PASSWORD),
        status='approved',
        is_admin=True
    )
    db.session.add(admin_user)
    db.session.commit()
    
    # Create admin profile
    admin_profile = UserProfile(
        user_id=admin_user.id,
        first_name='Test',
        last_name='Admin',
        display_name='Test Admin'
    )
    db.session.add(admin_profile)
    db.session.commit()
    
    # Login using test credentials
    response = client.post('/api/auth/login', json={
        'email': SMOKE_EMAIL,
        'password': SMOKE_PASSWORD
    })
    
    assert response.status_code == 200
    return client

