"""
GLOW Railway-Optimized Backend
Complete dating app with Magic 10 compatibility matching, Human Design integration, and admin console
Single-file architecture optimized for Railway deployment
"""

# ============================================================================
# IMPORTS AND CONFIGURATION
# ============================================================================
import os
import json
import hashlib
import secrets
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# ============================================================================
# APPLICATION SETUP
# ============================================================================
app = Flask(__name__)

class Config:
    """Railway-optimized configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'glow-dev-secret-key-change-in-production'
    
    # Database configuration with Railway URL handling
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///glow_dev.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # External API configuration
    MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY')
    MAILGUN_DOMAIN = os.environ.get('MAILGUN_DOMAIN')
    MAILGUN_BASE_URL = os.environ.get('MAILGUN_BASE_URL', 'https://api.mailgun.net/v3')
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@glow.app')
    
    HD_API_KEY = os.environ.get('HD_API_KEY')
    GEO_API_KEY = os.environ.get('GEO_API_KEY')
    HD_API_BASE_URL = os.environ.get('HD_API_BASE_URL', 'https://api.humandesignapi.nl/v1')
    
    # Frontend integration
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,https://www.glowme.io,https://glowme.io,https://glow-frontend-new.vercel.app').split(',')

app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy()
db.init_app(app)

# Configure CORS with explicit settings
CORS(app, 
     origins=Config.CORS_ORIGINS,
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     supports_credentials=True)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(db.Model):
    """User model with Railway-optimized schema"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')  # pending, approved, suspended
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class UserPriorities(db.Model):
    """Magic 10 user priorities with Railway-optimized schema"""
    __tablename__ = 'user_priorities'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    love_priority = db.Column(db.SmallInteger, default=5)
    intimacy_priority = db.Column(db.SmallInteger, default=5)
    communication_priority = db.Column(db.SmallInteger, default=5)
    friendship_priority = db.Column(db.SmallInteger, default=5)
    collaboration_priority = db.Column(db.SmallInteger, default=5)
    lifestyle_priority = db.Column(db.SmallInteger, default=5)
    decisions_priority = db.Column(db.SmallInteger, default=5)
    support_priority = db.Column(db.SmallInteger, default=5)
    growth_priority = db.Column(db.SmallInteger, default=5)
    space_priority = db.Column(db.SmallInteger, default=5)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'love_priority': self.love_priority,
            'intimacy_priority': self.intimacy_priority,
            'communication_priority': self.communication_priority,
            'friendship_priority': self.friendship_priority,
            'collaboration_priority': self.collaboration_priority,
            'lifestyle_priority': self.lifestyle_priority,
            'decisions_priority': self.decisions_priority,
            'support_priority': self.support_priority,
            'growth_priority': self.growth_priority,
            'space_priority': self.space_priority
        }
    
    def get_priorities_array(self):
        return [
            self.love_priority, self.intimacy_priority, self.communication_priority,
            self.friendship_priority, self.collaboration_priority, self.lifestyle_priority,
            self.decisions_priority, self.support_priority, self.growth_priority, self.space_priority
        ]

class CompatibilityMatrix(db.Model):
    """Pre-calculated compatibility scores"""
    __tablename__ = 'compatibility_matrix'
    
    user_a_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    user_b_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    love_score = db.Column(db.SmallInteger)
    intimacy_score = db.Column(db.SmallInteger)
    communication_score = db.Column(db.SmallInteger)
    friendship_score = db.Column(db.SmallInteger)
    collaboration_score = db.Column(db.SmallInteger)
    lifestyle_score = db.Column(db.SmallInteger)
    decisions_score = db.Column(db.SmallInteger)
    support_score = db.Column(db.SmallInteger)
    growth_score = db.Column(db.SmallInteger)
    space_score = db.Column(db.SmallInteger)
    overall_score = db.Column(db.SmallInteger)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'user_a_id': self.user_a_id,
            'user_b_id': self.user_b_id,
            'scores': {
                'love': self.love_score,
                'intimacy': self.intimacy_score,
                'communication': self.communication_score,
                'friendship': self.friendship_score,
                'collaboration': self.collaboration_score,
                'lifestyle': self.lifestyle_score,
                'decisions': self.decisions_score,
                'support': self.support_score,
                'growth': self.growth_score,
                'space': self.space_score
            },
            'overall_score': self.overall_score,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }

class BirthData(db.Model):
    """Birth data for Human Design calculations"""
    __tablename__ = 'birth_data'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    birth_date = db.Column(db.Date)
    birth_time = db.Column(db.Time)
    birth_location = db.Column(db.String(255))
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    data_consent = db.Column(db.Boolean, default=False)
    sharing_consent = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'birth_time': self.birth_time.isoformat() if self.birth_time else None,
            'birth_location': self.birth_location,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'data_consent': self.data_consent,
            'sharing_consent': self.sharing_consent
        }

class HumanDesignData(db.Model):
    """Human Design chart data with Railway-optimized schema"""
    __tablename__ = 'human_design_data'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    chart_data = db.Column(db.Text)  # JSON as TEXT for Railway compatibility
    energy_type = db.Column(db.String(50))
    strategy = db.Column(db.String(100))
    authority = db.Column(db.String(100))
    profile = db.Column(db.String(20))
    api_response = db.Column(db.Text)  # Cached full API response
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_chart_data(self, data):
        self.chart_data = json.dumps(data) if data else None
    
    def get_chart_data(self):
        return json.loads(self.chart_data) if self.chart_data else {}
    
    def set_api_response(self, response):
        self.api_response = json.dumps(response) if response else None
    
    def get_api_response(self):
        return json.loads(self.api_response) if self.api_response else {}
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'chart_data': self.get_chart_data(),
            'energy_type': self.energy_type,
            'strategy': self.strategy,
            'authority': self.authority,
            'profile': self.profile,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }

class AdminActionLog(db.Model):
    """Admin action logging for audit trail"""
    __tablename__ = 'admin_action_log'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(50), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'admin_user_id': self.admin_user_id,
            'action': self.action,
            'target_user_id': self.target_user_id,
            'details': self.details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class EmailNotification(db.Model):
    """Email notification tracking"""
    __tablename__ = 'email_notifications'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    email_type = db.Column(db.String(50), nullable=False)
    recipient_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_status = db.Column(db.String(20), default='sent')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_type': self.email_type,
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivery_status': self.delivery_status
        }

class UserSession(db.Model):
    """Simple session management"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

# ============================================================================
# MAGIC 10 COMPATIBILITY ENGINE
# ============================================================================

MAGIC_10_DIMENSIONS = [
    'love', 'intimacy', 'communication', 'friendship',
    'collaboration', 'lifestyle', 'decisions', 'support',
    'growth', 'space'
]

def calculate_compatibility_score(user1_priorities, user2_priorities):
    """
    Core Magic 10 compatibility calculation algorithm
    Calculates weighted compatibility scores between two users based on their priorities
    """
    if len(user1_priorities) != 10 or len(user2_priorities) != 10:
        raise ValueError("Both users must have exactly 10 priority values")
    
    # Initialize scores
    dimension_scores = {}
    total_weighted_score = 0
    total_weight = 0
    
    # Calculate compatibility for each dimension
    for i, dimension in enumerate(MAGIC_10_DIMENSIONS):
        priority1 = user1_priorities[i]
        priority2 = user2_priorities[i]
        
        # Validate priority values (1-10 scale)
        if not (1 <= priority1 <= 10) or not (1 <= priority2 <= 10):
            raise ValueError(f"Priority values must be between 1 and 10")
        
        # Calculate base compatibility (inverse of difference)
        difference = abs(priority1 - priority2)
        base_score = max(0, 10 - difference)
        
        # Apply weighting based on average priority importance
        avg_priority = (priority1 + priority2) / 2
        weight = avg_priority / 10  # Normalize to 0-1
        
        # Calculate weighted score for this dimension
        weighted_score = base_score * weight
        dimension_scores[dimension] = int(round(base_score))
        
        total_weighted_score += weighted_score
        total_weight += weight
    
    # Calculate overall compatibility score
    if total_weight > 0:
        overall_score = int(round((total_weighted_score / total_weight)))
    else:
        overall_score = 0
    
    # Apply bonus for high mutual priorities
    high_priority_bonus = 0
    for i in range(10):
        if user1_priorities[i] >= 8 and user2_priorities[i] >= 8:
            high_priority_bonus += 1
    
    # Apply penalty for major mismatches
    mismatch_penalty = 0
    for i in range(10):
        if abs(user1_priorities[i] - user2_priorities[i]) >= 7:
            mismatch_penalty += 2
    
    # Final score adjustment
    final_score = max(0, min(100, overall_score + high_priority_bonus - mismatch_penalty))
    
    return {
        'dimension_scores': dimension_scores,
        'overall_score': final_score,
        'high_priority_matches': high_priority_bonus,
        'major_mismatches': mismatch_penalty // 2
    }

def calculate_mutual_compatibility(user1_id, user2_id):
    """Calculate bidirectional compatibility between two users"""
    try:
        user1_priorities = UserPriorities.query.get(user1_id)
        user2_priorities = UserPriorities.query.get(user2_id)
        
        if not user1_priorities or not user2_priorities:
            return None
        
        # Get priority arrays
        priorities1 = user1_priorities.get_priorities_array()
        priorities2 = user2_priorities.get_priorities_array()
        
        # Calculate compatibility
        compatibility = calculate_compatibility_score(priorities1, priorities2)
        
        return compatibility
    except Exception as e:
        print(f"Error calculating mutual compatibility: {e}")
        return None

def store_compatibility_result(user_a_id, user_b_id, compatibility_result):
    """Store compatibility calculation result in database"""
    try:
        # Check if result already exists
        existing = CompatibilityMatrix.query.filter_by(
            user_a_id=user_a_id, user_b_id=user_b_id
        ).first()
        
        if existing:
            # Update existing record
            compatibility_record = existing
        else:
            # Create new record
            compatibility_record = CompatibilityMatrix(
                user_a_id=user_a_id,
                user_b_id=user_b_id
            )
        
        # Update scores
        scores = compatibility_result['dimension_scores']
        compatibility_record.love_score = scores.get('love', 0)
        compatibility_record.intimacy_score = scores.get('intimacy', 0)
        compatibility_record.communication_score = scores.get('communication', 0)
        compatibility_record.friendship_score = scores.get('friendship', 0)
        compatibility_record.collaboration_score = scores.get('collaboration', 0)
        compatibility_record.lifestyle_score = scores.get('lifestyle', 0)
        compatibility_record.decisions_score = scores.get('decisions', 0)
        compatibility_record.support_score = scores.get('support', 0)
        compatibility_record.growth_score = scores.get('growth', 0)
        compatibility_record.space_score = scores.get('space', 0)
        compatibility_record.overall_score = compatibility_result['overall_score']
        compatibility_record.calculated_at = datetime.utcnow()
        
        if not existing:
            db.session.add(compatibility_record)
        
        db.session.commit()
        return compatibility_record
    except Exception as e:
        db.session.rollback()
        print(f"Error storing compatibility result: {e}")
        return None

def get_user_matches(user_id, limit=20, min_score=60):
    """Get top matches for a user based on compatibility scores"""
    try:
        matches = CompatibilityMatrix.query.filter(
            CompatibilityMatrix.user_a_id == user_id,
            CompatibilityMatrix.overall_score >= min_score
        ).order_by(CompatibilityMatrix.overall_score.desc()).limit(limit).all()
        
        return [match.to_dict() for match in matches]
    except Exception as e:
        print(f"Error getting user matches: {e}")
        return []

def recalculate_all_compatibility():
    """Recalculate compatibility matrix for all users (admin function)"""
    try:
        users_with_priorities = UserPriorities.query.all()
        user_ids = [up.user_id for up in users_with_priorities]
        
        calculation_count = 0
        
        # Calculate compatibility for all user pairs
        for i, user_a_id in enumerate(user_ids):
            for user_b_id in user_ids[i+1:]:
                compatibility = calculate_mutual_compatibility(user_a_id, user_b_id)
                if compatibility:
                    # Store both directions
                    store_compatibility_result(user_a_id, user_b_id, compatibility)
                    store_compatibility_result(user_b_id, user_a_id, compatibility)
                    calculation_count += 2
        
        return {
            'status': 'success',
            'calculations_performed': calculation_count,
            'users_processed': len(user_ids)
        }
    except Exception as e:
        print(f"Error recalculating compatibility matrix: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

# ============================================================================
# AUTHENTICATION SYSTEM
# ============================================================================

def hash_password(password):
    """Secure password hashing"""
    return generate_password_hash(password)

def verify_password(password, password_hash):
    """Verify password against hash"""
    return check_password_hash(password_hash, password)

def create_session_token(user_id):
    """Create session token for user"""
    try:
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        
        # Set expiration (24 hours from now)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Create session record
        session = UserSession(
            user_id=user_id,
            session_token=token,
            expires_at=expires_at
        )
        
        db.session.add(session)
        db.session.commit()
        
        return token
    except Exception as e:
        db.session.rollback()
        print(f"Error creating session token: {e}")
        return None

def verify_session_token(token):
    """Verify session token and return user ID"""
    try:
        session = UserSession.query.filter_by(session_token=token).first()
        
        if not session:
            return None
        
        if session.is_expired():
            # Clean up expired session
            db.session.delete(session)
            db.session.commit()
            return None
        
        return session.user_id
    except Exception as e:
        print(f"Error verifying session token: {e}")
        return None

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        user_id = verify_session_token(token)
        
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user_id to request context
        request.current_user_id = user_id
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_admin(f):
    """Decorator to require admin privileges"""
    def decorated_function(*args, **kwargs):
        # First check authentication
        auth_result = require_auth(lambda: None)()
        if auth_result:
            return auth_result
        
        # Check if user is admin (for now, any authenticated user can be admin)
        # In production, you'd check a specific admin role
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

# ============================================================================
# EXTERNAL API INTEGRATIONS
# ============================================================================

def send_email_via_mailgun(to_email, subject, content, content_type='text'):
    """Send email via Mailgun API with error handling"""
    try:
        if not app.config['MAILGUN_API_KEY'] or not app.config['MAILGUN_DOMAIN']:
            print("Mailgun not configured, skipping email")
            return {'status': 'skipped', 'message': 'Email service not configured'}
        
        url = f"{app.config['MAILGUN_BASE_URL']}/{app.config['MAILGUN_DOMAIN']}/messages"
        
        data = {
            'from': app.config['FROM_EMAIL'],
            'to': to_email,
            'subject': subject
        }
        
        if content_type == 'html':
            data['html'] = content
        else:
            data['text'] = content
        
        response = requests.post(
            url,
            auth=('api', app.config['MAILGUN_API_KEY']),
            data=data,
            timeout=10
        )
        
        if response.status_code == 200:
            return {'status': 'sent', 'message': 'Email sent successfully'}
        else:
            print(f"Mailgun error: {response.status_code} - {response.text}")
            return {'status': 'failed', 'message': 'Email delivery failed'}
    
    except requests.RequestException as e:
        print(f"Mailgun request error: {e}")
        return {'status': 'failed', 'message': 'Email service unavailable'}
    except Exception as e:
        print(f"Email sending error: {e}")
        return {'status': 'failed', 'message': 'Email sending failed'}

def send_welcome_email(user):
    """Send welcome email to new user"""
    subject = "Welcome to GLOW!"
    content = f"""
    Hi {user.first_name or 'there'}!
    
    Welcome to GLOW, where meaningful connections begin with compatibility.
    
    Your account has been created and is pending approval. You'll receive another email once your account is approved and you can start exploring matches.
    
    Best regards,
    The GLOW Team
    """
    
    result = send_email_via_mailgun(user.email, subject, content)
    
    # Log email notification
    try:
        notification = EmailNotification(
            user_id=user.id,
            email_type='welcome',
            recipient_email=user.email,
            subject=subject,
            delivery_status=result['status']
        )
        db.session.add(notification)
        db.session.commit()
    except Exception as e:
        print(f"Error logging email notification: {e}")
    
    return result

def send_match_notification(user, match_user, compatibility_score):
    """Send new match notification email"""
    subject = "New Match Found on GLOW!"
    content = f"""
    Hi {user.first_name or 'there'}!
    
    Great news! We found a new compatibility match for you on GLOW.
    
    Match: {match_user.first_name or 'Someone special'}
    Compatibility Score: {compatibility_score}%
    
    Log in to GLOW to learn more about your match and start a conversation.
    
    Happy matching!
    The GLOW Team
    """
    
    result = send_email_via_mailgun(user.email, subject, content)
    
    # Log email notification
    try:
        notification = EmailNotification(
            user_id=user.id,
            email_type='match_notification',
            recipient_email=user.email,
            subject=subject,
            delivery_status=result['status']
        )
        db.session.add(notification)
        db.session.commit()
    except Exception as e:
        print(f"Error logging email notification: {e}")
    
    return result

def call_human_design_api(birth_data):
    """Call Human Design API with birth data"""
    try:
        if not app.config['HD_API_KEY'] or not app.config['GEO_API_KEY']:
            return {'error': 'Human Design API not configured'}
        
        url = f"{app.config['HD_API_BASE_URL']}/bodygraphs"
        
        headers = {
            'Content-Type': 'application/json',
            'HD-Api-Key': app.config['HD_API_KEY'],
            'HD-Geocode-Key': app.config['GEO_API_KEY']
        }
        
        # Format birth data for API
        api_data = {
            'birthdate': birth_data['birth_date'],
            'birthtime': birth_data['birth_time'],
            'location': birth_data['birth_location']
        }
        
        response = requests.post(
            url,
            headers=headers,
            json=api_data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Human Design API error: {response.status_code} - {response.text}")
            return {'error': f'API request failed: {response.status_code}'}
    
    except requests.RequestException as e:
        print(f"Human Design API request error: {e}")
        return {'error': 'Human Design API unavailable'}
    except Exception as e:
        print(f"Human Design API error: {e}")
        return {'error': 'Human Design calculation failed'}

def geocode_location(location_string):
    """Geocode location using Google Places API"""
    try:
        if not app.config['GEO_API_KEY']:
            return None
        
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': location_string,
            'key': app.config['GEO_API_KEY']
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                location = data['results'][0]['geometry']['location']
                return {
                    'latitude': location['lat'],
                    'longitude': location['lng']
                }
        
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def ensure_database():
    """Ensure database is initialized (Railway-safe lazy initialization)"""
    if not hasattr(ensure_database, 'initialized'):
        try:
            with app.app_context():
                # Create all tables
                db.create_all()
                
                # Verify tables were created by checking if users table exists
                result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
                if not result.fetchone():
                    # If using PostgreSQL, use different query
                    try:
                        result = db.session.execute(text("SELECT tablename FROM pg_tables WHERE tablename='users'"))
                        if not result.fetchone():
                            raise Exception("Users table not found after creation")
                    except:
                        # Force table creation again
                        db.create_all()
                
                ensure_database.initialized = True
                print("Database initialized successfully - all tables created")
        except Exception as e:
            print(f"Database initialization error: {e}")
            # Don't raise the exception, let the app continue
            pass

def log_admin_action(admin_user_id, action, target_user_id=None, details=None):
    """Log admin action for audit trail"""
    try:
        log_entry = AdminActionLog(
            admin_user_id=admin_user_id,
            action=action,
            target_user_id=target_user_id,
            details=details
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry
    except Exception as e:
        db.session.rollback()
        print(f"Error logging admin action: {e}")
        return None

def validate_email(email):
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_priorities(priorities):
    """Validate Magic 10 priorities array"""
    if not isinstance(priorities, list) or len(priorities) != 10:
        return False
    
    for priority in priorities:
        if not isinstance(priority, int) or not (1 <= priority <= 10):
            return False
    
    return True

# ============================================================================
# API ROUTES - HEALTH CHECK AND MONITORING
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway monitoring"""
    try:
        ensure_database()
        
        # Test database connection
        db.session.execute(text('SELECT 1'))
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'features': {
                'magic_10_matching': True,
                'human_design_integration': bool(app.config['HD_API_KEY']),
                'email_notifications': bool(app.config['MAILGUN_API_KEY']),
                'admin_console': True
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/debug/env', methods=['GET'])
def debug_environment():
    """Debug endpoint to check environment variables (remove in production)"""
    return jsonify({
        'database_url_set': bool(app.config['SQLALCHEMY_DATABASE_URI']),
        'secret_key_set': bool(app.config['SECRET_KEY']),
        'mailgun_configured': bool(app.config['MAILGUN_API_KEY']),
        'human_design_configured': bool(app.config['HD_API_KEY']),
        'cors_origins': app.config['CORS_ORIGINS']
    })

@app.route('/api/debug/init-db', methods=['POST'])
def init_database():
    """Manual database initialization endpoint"""
    try:
        with app.app_context():
            # Force database creation
            db.create_all()
            
            # Check what tables were created
            if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
                result = db.session.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
                tables = [row[0] for row in result.fetchall()]
            else:
                result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result.fetchall()]
            
            return jsonify({
                'status': 'success',
                'message': 'Database tables created successfully',
                'tables_created': tables,
                'table_count': len(tables)
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Database initialization failed: {str(e)}'
        }), 500

# ============================================================================
# API ROUTES - AUTHENTICATION
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        ensure_database()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate email format
        if not validate_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'User already exists'}), 409
        
        # Create new user
        user = User(
            email=data['email'].lower().strip(),
            password_hash=hash_password(data['password']),
            first_name=data['first_name'].strip(),
            last_name=data.get('last_name', '').strip(),
            status='pending'
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Create default priorities
        priorities = UserPriorities(user_id=user.id)
        db.session.add(priorities)
        db.session.commit()
        
        # Send welcome email
        send_welcome_email(user)
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        ensure_database()
        
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        # Find user
        user = User.query.filter_by(email=data['email'].lower().strip()).first()
        if not user or not verify_password(data['password'], user.password_hash):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check user status
        if user.status != 'approved':
            return jsonify({'error': f'Account is {user.status}'}), 403
        
        # Create session token
        token = create_session_token(user.id)
        if not token:
            return jsonify({'error': 'Failed to create session'}), 500
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user.to_dict()
        })
    
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """User logout endpoint"""
    try:
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1]
        
        # Delete session
        session = UserSession.query.filter_by(session_token=token).first()
        if session:
            db.session.delete(session)
            db.session.commit()
        
        return jsonify({'message': 'Logged out successfully'})
    
    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user information"""
    try:
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()})
    
    except Exception as e:
        print(f"Get current user error: {e}")
        return jsonify({'error': 'Failed to get user information'}), 500

# ============================================================================
# API ROUTES - MAGIC 10 MATCHING
# ============================================================================

@app.route('/api/priorities', methods=['GET'])
@require_auth
def get_user_priorities():
    """Get user's Magic 10 priorities"""
    try:
        priorities = UserPriorities.query.get(request.current_user_id)
        if not priorities:
            # Create default priorities if they don't exist
            priorities = UserPriorities(user_id=request.current_user_id)
            db.session.add(priorities)
            db.session.commit()
        
        return jsonify({'priorities': priorities.to_dict()})
    
    except Exception as e:
        print(f"Get priorities error: {e}")
        return jsonify({'error': 'Failed to get priorities'}), 500

@app.route('/api/priorities', methods=['PUT'])
@require_auth
def update_user_priorities():
    """Update user's Magic 10 priorities"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate priorities
        priority_fields = [
            'love_priority', 'intimacy_priority', 'communication_priority',
            'friendship_priority', 'collaboration_priority', 'lifestyle_priority',
            'decisions_priority', 'support_priority', 'growth_priority', 'space_priority'
        ]
        
        for field in priority_fields:
            if field in data:
                value = data[field]
                if not isinstance(value, int) or not (1 <= value <= 10):
                    return jsonify({'error': f'{field} must be an integer between 1 and 10'}), 400
        
        # Get or create priorities record
        priorities = UserPriorities.query.get(request.current_user_id)
        if not priorities:
            priorities = UserPriorities(user_id=request.current_user_id)
            db.session.add(priorities)
        
        # Update priorities
        for field in priority_fields:
            if field in data:
                setattr(priorities, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Priorities updated successfully',
            'priorities': priorities.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Update priorities error: {e}")
        return jsonify({'error': 'Failed to update priorities'}), 500

@app.route('/api/compatibility/calculate', methods=['POST'])
@require_auth
def calculate_compatibility():
    """Calculate compatibility with another user"""
    try:
        data = request.get_json()
        if not data or not data.get('target_user_id'):
            return jsonify({'error': 'target_user_id required'}), 400
        
        target_user_id = data['target_user_id']
        
        # Check if target user exists
        target_user = User.query.get(target_user_id)
        if not target_user:
            return jsonify({'error': 'Target user not found'}), 404
        
        # Calculate compatibility
        compatibility = calculate_mutual_compatibility(request.current_user_id, target_user_id)
        if not compatibility:
            return jsonify({'error': 'Failed to calculate compatibility'}), 500
        
        # Store result
        store_compatibility_result(request.current_user_id, target_user_id, compatibility)
        
        return jsonify({
            'compatibility': compatibility,
            'target_user': target_user.to_dict()
        })
    
    except Exception as e:
        print(f"Calculate compatibility error: {e}")
        return jsonify({'error': 'Failed to calculate compatibility'}), 500

@app.route('/api/matches', methods=['GET'])
@require_auth
def get_matches():
    """Get user's matches based on compatibility"""
    try:
        limit = request.args.get('limit', 20, type=int)
        min_score = request.args.get('min_score', 60, type=int)
        
        matches = get_user_matches(request.current_user_id, limit, min_score)
        
        # Get user details for matches
        enriched_matches = []
        for match in matches:
            user = User.query.get(match['user_b_id'])
            if user and user.status == 'approved':
                match_data = match.copy()
                match_data['user'] = user.to_dict()
                enriched_matches.append(match_data)
        
        return jsonify({
            'matches': enriched_matches,
            'count': len(enriched_matches)
        })
    
    except Exception as e:
        print(f"Get matches error: {e}")
        return jsonify({'error': 'Failed to get matches'}), 500

# ============================================================================
# API ROUTES - HUMAN DESIGN INTEGRATION
# ============================================================================

@app.route('/api/birth-data', methods=['GET'])
@require_auth
def get_birth_data():
    """Get user's birth data"""
    try:
        birth_data = BirthData.query.get(request.current_user_id)
        if not birth_data:
            return jsonify({'birth_data': None})
        
        return jsonify({'birth_data': birth_data.to_dict()})
    
    except Exception as e:
        print(f"Get birth data error: {e}")
        return jsonify({'error': 'Failed to get birth data'}), 500

@app.route('/api/birth-data', methods=['POST'])
@require_auth
def save_birth_data():
    """Save user's birth data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['birth_date', 'birth_time', 'birth_location']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Geocode location
        coordinates = geocode_location(data['birth_location'])
        
        # Get or create birth data record
        birth_data = BirthData.query.get(request.current_user_id)
        if not birth_data:
            birth_data = BirthData(user_id=request.current_user_id)
            db.session.add(birth_data)
        
        # Update birth data
        from datetime import datetime
        birth_data.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
        birth_data.birth_time = datetime.strptime(data['birth_time'], '%H:%M').time()
        birth_data.birth_location = data['birth_location']
        birth_data.data_consent = data.get('data_consent', False)
        birth_data.sharing_consent = data.get('sharing_consent', False)
        
        if coordinates:
            birth_data.latitude = Decimal(str(coordinates['latitude']))
            birth_data.longitude = Decimal(str(coordinates['longitude']))
        
        db.session.commit()
        
        return jsonify({
            'message': 'Birth data saved successfully',
            'birth_data': birth_data.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Save birth data error: {e}")
        return jsonify({'error': 'Failed to save birth data'}), 500

@app.route('/api/human-design/calculate', methods=['POST'])
@require_auth
def calculate_human_design():
    """Calculate Human Design chart"""
    try:
        # Get user's birth data
        birth_data = BirthData.query.get(request.current_user_id)
        if not birth_data:
            return jsonify({'error': 'Birth data not found'}), 404
        
        if not birth_data.data_consent:
            return jsonify({'error': 'Data consent required'}), 403
        
        # Prepare data for API call
        api_data = {
            'birth_date': birth_data.birth_date.strftime('%d-%b-%y'),
            'birth_time': birth_data.birth_time.strftime('%H:%M'),
            'birth_location': birth_data.birth_location
        }
        
        # Call Human Design API
        api_response = call_human_design_api(api_data)
        if 'error' in api_response:
            return jsonify({'error': api_response['error']}), 500
        
        # Store Human Design data
        hd_data = HumanDesignData.query.get(request.current_user_id)
        if not hd_data:
            hd_data = HumanDesignData(user_id=request.current_user_id)
            db.session.add(hd_data)
        
        # Extract key information from API response
        hd_data.set_api_response(api_response)
        hd_data.set_chart_data(api_response.get('chart', {}))
        hd_data.energy_type = api_response.get('type', '')
        hd_data.strategy = api_response.get('strategy', '')
        hd_data.authority = api_response.get('authority', '')
        hd_data.profile = api_response.get('profile', '')
        hd_data.calculated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Human Design chart calculated successfully',
            'human_design': hd_data.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Calculate Human Design error: {e}")
        return jsonify({'error': 'Failed to calculate Human Design chart'}), 500

@app.route('/api/human-design/generate-bodygraph', methods=['POST'])
@require_auth
def generate_bodygraph():
    """Generate Human Design bodygraph for admin onboarding"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['birthdate', 'birthtime', 'location']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Call Human Design API directly with the provided data
        api_response = call_human_design_api({
            'birth_date': data['birthdate'],
            'birth_time': data['birthtime'], 
            'birth_location': data['location']
        })
        
        if 'error' in api_response:
            return jsonify({'error': api_response['error']}), 500
        
        # Store or update Human Design data for the user
        hd_data = HumanDesignData.query.get(request.current_user_id)
        if not hd_data:
            hd_data = HumanDesignData(user_id=request.current_user_id)
            db.session.add(hd_data)
        
        # Extract and store key information from API response
        hd_data.type = api_response.get('type')
        hd_data.strategy = api_response.get('strategy')
        hd_data.authority = api_response.get('authority')
        hd_data.profile = api_response.get('profile')
        hd_data.centers = json.dumps(api_response.get('centers', {}))
        hd_data.gates = json.dumps(api_response.get('gates', {}))
        hd_data.channels = json.dumps(api_response.get('channels', {}))
        hd_data.full_chart_data = json.dumps(api_response)
        hd_data.calculated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Human Design bodygraph generated successfully',
            'bodygraph': api_response,
            'human_design': hd_data.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Generate bodygraph error: {e}")
        return jsonify({'error': 'Failed to generate Human Design bodygraph'}), 500

@app.route('/api/human-design', methods=['GET'])
@require_auth
def get_human_design():
    """Get user's Human Design data"""
    try:
        hd_data = HumanDesignData.query.get(request.current_user_id)
        if not hd_data:
            return jsonify({'human_design': None})
        
        return jsonify({'human_design': hd_data.to_dict()})
    
    except Exception as e:
        print(f"Get Human Design error: {e}")
        return jsonify({'error': 'Failed to get Human Design data'}), 500

# ============================================================================
# API ROUTES - PROFILE MANAGEMENT
# ============================================================================

@app.route('/api/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get user profile"""
    try:
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user.to_dict())
    
    except Exception as e:
        print(f"Get profile error: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500

@app.route('/api/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        user = User.query.get(request.current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update allowed profile fields
        allowed_fields = ['name', 'bio', 'interests']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Update profile error: {e}")
        return jsonify({'error': 'Failed to update profile'}), 500

@app.route('/api/profile/update-birth-data', methods=['POST'])
@require_auth
def update_birth_data():
    """Update user birth data and recalculate compatibility"""
    try:
        data = request.get_json()
        birth_data_input = data.get('birth_data', {})
        
        # Validate required fields
        required_fields = ['birth_date', 'birth_time', 'birth_location']
        for field in required_fields:
            if not birth_data_input.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get or create birth data record
        birth_data = BirthData.query.get(request.current_user_id)
        if not birth_data:
            birth_data = BirthData(user_id=request.current_user_id)
            db.session.add(birth_data)
        
        # Update birth data
        birth_data.birth_date = datetime.strptime(birth_data_input['birth_date'], '%Y-%m-%d').date()
        birth_data.birth_time = datetime.strptime(birth_data_input['birth_time'], '%H:%M').time()
        birth_data.birth_location = birth_data_input['birth_location']
        birth_data.data_consent = True
        birth_data.updated_at = datetime.utcnow()
        
        # Store compatibility data if provided
        if 'compatibility_data' in birth_data_input:
            birth_data.set_chart_data(birth_data_input['compatibility_data'])
        
        # Mark onboarding as completed if specified
        if birth_data_input.get('onboarding_completed'):
            user = User.query.get(request.current_user_id)
            user.onboarding_completed = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Birth data updated successfully',
            'birth_data': birth_data.to_dict()
        })
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': f'Invalid date/time format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Update birth data error: {e}")
        return jsonify({'error': 'Failed to update birth data'}), 500

# ============================================================================
# API ROUTES - ADMIN CONSOLE
# ============================================================================

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_get_users():
    """Get all users for admin console"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        status_filter = request.args.get('status')
        
        query = User.query
        
        if status_filter:
            query = query.filter(User.status == status_filter)
        
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page,
            'per_page': per_page
        })
    
    except Exception as e:
        print(f"Admin get users error: {e}")
        return jsonify({'error': 'Failed to get users'}), 500

@app.route('/api/admin/users/<int:user_id>/status', methods=['PUT'])
@require_admin
def admin_update_user_status(user_id):
    """Update user status (approve, suspend, etc.)"""
    try:
        data = request.get_json()
        if not data or not data.get('status'):
            return jsonify({'error': 'Status required'}), 400
        
        new_status = data['status']
        if new_status not in ['pending', 'approved', 'suspended']:
            return jsonify({'error': 'Invalid status'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        old_status = user.status
        user.status = new_status
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log admin action
        log_admin_action(
            admin_user_id=request.current_user_id,
            action='status_update',
            target_user_id=user_id,
            details=f'Changed status from {old_status} to {new_status}'
        )
        
        return jsonify({
            'message': 'User status updated successfully',
            'user': user.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Admin update user status error: {e}")
        return jsonify({'error': 'Failed to update user status'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@require_admin
def admin_delete_user(user_id):
    """Delete user (admin only)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Log admin action before deletion
        log_admin_action(
            admin_user_id=request.current_user_id,
            action='user_deletion',
            target_user_id=user_id,
            details=f'Deleted user {user.email}'
        )
        
        # Delete related records (cascade should handle this, but being explicit)
        UserPriorities.query.filter_by(user_id=user_id).delete()
        CompatibilityMatrix.query.filter(
            (CompatibilityMatrix.user_a_id == user_id) |
            (CompatibilityMatrix.user_b_id == user_id)
        ).delete()
        BirthData.query.filter_by(user_id=user_id).delete()
        HumanDesignData.query.filter_by(user_id=user_id).delete()
        UserSession.query.filter_by(user_id=user_id).delete()
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'User deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Admin delete user error: {e}")
        return jsonify({'error': 'Failed to delete user'}), 500

@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_get_stats():
    """Get system statistics for admin dashboard"""
    try:
        stats = {
            'users': {
                'total': User.query.count(),
                'pending': User.query.filter_by(status='pending').count(),
                'approved': User.query.filter_by(status='approved').count(),
                'suspended': User.query.filter_by(status='suspended').count()
            },
            'compatibility': {
                'calculations': CompatibilityMatrix.query.count(),
                'users_with_priorities': UserPriorities.query.count()
            },
            'human_design': {
                'users_with_birth_data': BirthData.query.count(),
                'calculated_charts': HumanDesignData.query.count()
            },
            'emails': {
                'total_sent': EmailNotification.query.count(),
                'welcome_emails': EmailNotification.query.filter_by(email_type='welcome').count(),
                'match_notifications': EmailNotification.query.filter_by(email_type='match_notification').count()
            }
        }
        
        return jsonify({'stats': stats})
    
    except Exception as e:
        print(f"Admin get stats error: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@app.route('/api/admin/compatibility/recalculate', methods=['POST'])
@require_admin
def admin_recalculate_compatibility():
    """Recalculate compatibility matrix for all users"""
    try:
        result = recalculate_all_compatibility()
        
        # Log admin action
        log_admin_action(
            admin_user_id=request.current_user_id,
            action='compatibility_recalculation',
            details=f"Recalculated compatibility matrix: {result}"
        )
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Admin recalculate compatibility error: {e}")
        return jsonify({'error': 'Failed to recalculate compatibility'}), 500

@app.route('/api/admin/logs', methods=['GET'])
@require_admin
def admin_get_logs():
    """Get admin action logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        logs = AdminActionLog.query.order_by(AdminActionLog.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'logs': [log.to_dict() for log in logs.items],
            'total': logs.total,
            'pages': logs.pages,
            'current_page': page,
            'per_page': per_page
        })
    
    except Exception as e:
        print(f"Admin get logs error: {e}")
        return jsonify({'error': 'Failed to get logs'}), 500

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

# Initialize database on first request
with app.app_context():
    ensure_database()

# Railway deployment compatibility - no app.run() call
# Gunicorn imports 'app' object directly

if __name__ == '__main__':
    # Only for local development testing
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

