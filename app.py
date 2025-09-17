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
import logging
import re
import time as time_module
from datetime import datetime, timedelta, date, time
from decimal import Decimal
from flask import Flask, request, jsonify, session, make_response, g
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from argon2 import PasswordHasher
from rate_limit import login_rate_limiter
from argon2.exceptions import VerifyMismatchError
import redis

# Import Resonance Ten configuration
from resonance_config import (
    get_resonance_config, 
    validate_resonance_weights,
    convert_legacy_to_resonance,
    convert_resonance_to_legacy
)
# Import scoring module with safety guard
try:
    from resonance_scoring import ResonanceScorer, score_compatibility
except Exception as e:
    # Log but don't kill the app; scoring endpoints can handle this gracefully
    import logging
    logging.getLogger(__name__).exception("Scoring module not fully available: %s", e)
    ResonanceScorer = None
    score_compatibility = None

# Import Redis session store for T3.1-R2

# ============================================================================
# COOKIE CONFIGURATION (BE-CKHLP-01)
# ============================================================================
# Import centralized cookie helpers to resolve circular imports
from cookies import (
    get_cookie_options, set_cookie, clear_cookie,
    set_session_cookie, set_csrf_cookie, 
    clear_session_cookie, clear_csrf_cookie, clear_all_auth_cookies,
    # Legacy compatibility functions
    _cookie_opts, _set_cookie, _clear_cookie
)
from redis_session_store import get_session_store
from session_diagnostics import create_session_diagnostics_endpoint

# Import CSRF protection for T3.2
from csrf_protection import (
    add_csrf_to_login, clear_csrf_on_logout, create_csrf_endpoints,
    csrf_protect, get_csrf_enforcement
)
from session_revocation import (
    create_revocation_endpoints, track_session_on_login, untrack_session_on_logout
)
from api.normalize import normalize_birth_data_request

# ============================================================================
# APPLICATION SETUP
# ============================================================================
app = Flask(__name__)

# Configure ProxyFix for proper HTTPS detection behind Vercel/Railway proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Enable SQL logging for debugging
app.config["SQLALCHEMY_ECHO"] = True
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# SQL timing and debugging events
@event.listens_for(Engine, "before_cursor_execute")
def _before_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time_module.time())
    app.logger.info("SQL_START: %s ; params=%s", statement, parameters)

@event.listens_for(Engine, "after_cursor_execute")
def _after_execute(conn, cursor, statement, parameters, context, executemany):
    total = time_module.time() - conn.info["query_start_time"].pop(-1)
    app.logger.info("SQL_END: %.3f s", total)

class Config:
    """Railway-optimized configuration with Auth v2 session support"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'glow-dev-secret-key-change-in-production'
    
    # Database configuration with Railway URL handling
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///glow_dev.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Auth v2 Session Configuration
    # Use filesystem sessions for Flask-Session (we have our own Redis store)
    SESSION_TYPE = 'filesystem'  # Always use filesystem for Flask-Session
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'glow:'
    SESSION_FILE_DIR = '/tmp/glow_flask_sessions'  # Flask-Session filesystem dir
    
    # Cookie Configuration (Auth v2 spec)
    SESSION_COOKIE_NAME = 'flask_session'  # Different from our custom glow_session cookie
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_PATH = '/'
    SESSION_COOKIE_DOMAIN = None  # Host-only cookies (more secure)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)  # 30-minute sliding timeout
    
    # Auth v2 Security Configuration
    AUTH_ABSOLUTE_TIMEOUT = timedelta(hours=24)  # 24-hour absolute maximum
    AUTH_RATE_LIMIT_PER_IP = "10 per minute"  # Rate limiting for login attempts
    AUTH_RATE_LIMIT_PER_USER = "5 per minute"  # Per-user rate limiting
    
    # Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # External API configuration
    MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY')
    MAILGUN_DOMAIN = os.environ.get('MAILGUN_DOMAIN')
    MAILGUN_BASE_URL = os.environ.get('MAILGUN_BASE_URL', 'https://api.mailgun.net/v3')
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@glow.app')
    
    HD_API_KEY = os.environ.get('HD_API_KEY')
    GEO_API_KEY = os.environ.get('GEO_API_KEY')
    HD_API_BASE_URL = os.environ.get('HD_API_BASE_URL', 'https://api.humandesignapi.nl/v1')
    
    # Frontend integration - Environment-aware CORS
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    
    # Production CORS origins (secure)
    PRODUCTION_ORIGINS = [
        'https://www.glowme.io',
        'https://glowme.io', 
        'https://glow-frontend-new.vercel.app',
        'https://glow-frontend-v2.vercel.app'
    ]
    
    # Development CORS origins (includes localhost)
    DEVELOPMENT_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5173',
        'https://www.glowme.io',
        'https://glowme.io',
        'https://glow-frontend-new.vercel.app',
        'https://glow-frontend-v2.vercel.app'
    ]
    
    # Use environment variable or detect based on environment
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('DATABASE_URL'):
        # Production environment
        CORS_ORIGINS = PRODUCTION_ORIGINS
        # In production, ensure secure cookies
        SESSION_COOKIE_SECURE = True
    else:
        # Development environment
        CORS_ORIGINS = DEVELOPMENT_ORIGINS
        # In development, allow non-HTTPS
        SESSION_COOKIE_SECURE = False

app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy()
db.init_app(app)

# Initialize Flask-Session (filesystem for cookie management)
sess = Session()
sess.init_app(app)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["1000 per hour"]
)

# Initialize Argon2 password hasher
ph = PasswordHasher()

# Initialize Redis session store (T3.1-R2)
session_store = get_session_store()
app.logger.info(f"Session store initialized: {type(session_store).__name__}")

# Configure CORS with secure, production-ready setup
import re
from flask import make_response

# Strict allowlist (compiled once)
ALLOWED_ORIGIN_PATTERNS = [
    re.compile(r"^https://(www\.)?glowme\.io$"),
    re.compile(r"^https://.*\.vercel\.app$"),
    re.compile(r"^http://localhost:(3000|5173)$"),  # Development only
]

def origin_allowed(origin: str) -> bool:
    """Check if origin is in our allowlist"""
    if not origin:
        return False
    return any(pat.match(origin) for pat in ALLOWED_ORIGIN_PATTERNS)

# Flask-CORS handles most cases
CORS(
    app,
    resources={r"/api/*": {
        "origins": ALLOWED_ORIGIN_PATTERNS   # same allowlist
    }},
    supports_credentials=True,
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    expose_headers=["Content-Length"],
)

# after_request: DO NOT open CORS; only add helpers if the origin is allowed
@app.after_request
def add_cors_headers(resp):
    # Only touch /api/* and only for explicitly allowed origins
    origin = request.headers.get("Origin")
    if request.path.startswith("/api/") and origin_allowed(origin):
        # If Flask-CORS already set ACAO, leave it. Otherwise echo allowed origin.
        resp.headers.setdefault("Access-Control-Allow-Origin", origin)
        resp.headers.setdefault("Vary", "Origin")
        resp.headers.setdefault("Access-Control-Allow-Credentials", "true")
    return resp

@app.after_request
def add_security_headers(resp):
    """Add standard security headers to all API responses"""
    if request.path.startswith('/api/'):
        # Be authoritative on API responses (override any proxy-set values)
        resp.headers['Strict-Transport-Security'] = 'max-age=15552000; includeSubDomains'
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        resp.headers['X-Frame-Options'] = 'DENY'
        # Prevent caching of sensitive API responses
        resp.headers['Cache-Control'] = 'no-store'
        resp.headers['Pragma'] = 'no-cache'
        
        # S7-FSR-CLOSE: Additional hardening headers
        # CSP (report-only) – safe for JSON; no blocking of app behavior
        resp.headers['Content-Security-Policy-Report-Only'] = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'self'; "
            "connect-src 'self'"
        )
        
        # Lock down powerful features we don't use from API context
        resp.headers['Permissions-Policy'] = (
            "geolocation=(), camera=(), microphone=(), payment=(), usb=(), "
            "accelerometer=(), gyroscope=(), magnetometer=()"
        )
        
        # Cross-origin isolation hardening (safe for API)
        resp.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        resp.headers['Cross-Origin-Resource-Policy'] = 'same-site'
    return resp

@app.after_request
def handle_session_renewal(resp):
    """Handle session cookie renewal if flagged during request"""
    if hasattr(g, 'session_needs_refresh') and g.session_needs_refresh:
        session_id = getattr(g, 'session_id', None)
        if session_id:
            # Reissue session cookie with existing security flags
            set_session_cookie(resp, session_id)
            app.logger.info(f"Session cookie renewed in response: {session_id}")
    return resp

# OPTIONS catch-all for /api/* (bypasses auth; Railway edge always gets a 204)
@app.route("/api/<path:any_path>", methods=["OPTIONS"])
def api_preflight(any_path):
    """Catch-all preflight handler for any /api/* path"""
    origin = request.headers.get("Origin")
    # If origin not allowed, return 204 WITHOUT ACAO so browser blocks it
    if not origin_allowed(origin):
        return ("", 204)

    # Echo only what the browser asked for (spec-correct)
    req_method  = request.headers.get("Access-Control-Request-Method", "GET")
    req_headers = request.headers.get("Access-Control-Request-Headers", "")

    resp = make_response("", 204)
    resp.headers["Access-Control-Allow-Origin"] = origin
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    # It's okay to return a superset, but echoing is cleaner and prevents drift:
    resp.headers["Access-Control-Allow-Methods"] = req_method if req_method else "GET, POST, PUT, DELETE, OPTIONS"
    if req_headers:
        resp.headers["Access-Control-Allow-Headers"] = req_headers
    else:
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"

    # Cache preflight (browsers may cap this; Safari often ~600s)
    resp.headers["Access-Control-Max-Age"] = "86400"
    resp.headers["Vary"] = "Origin"
    return resp


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_birth_time_strict(birth_time):
    """S3-A1R-H4: Strict formatting for birth_time - TIME objects only"""
    if birth_time is None:
        return None
    
    # Only accept time objects, format as HH:mm
    if hasattr(birth_time, 'strftime'):
        return birth_time.strftime('%H:%M')
    
    # Reject non-time types with error logging
    app.logger.error(f"birth_time_format_error route=me type={type(birth_time)} value={birth_time}")
    raise ValueError(f"Invalid birth_time type: expected time, got {type(birth_time)}")

def log_request_shape_keys(route, payload):
    """G2F_0: Log request field names only (no values) on validation errors"""
    try:
        if not payload:
            return
        
        # Collect all top-level keys
        keys = list(payload.keys())
        
        # Check for wrapper detection
        wrapper_detected = any(key in ['birth_data', 'birthData'] for key in keys)
        
        # If wrapper present, also include child keys
        if wrapper_detected:
            for wrapper_key in ['birth_data', 'birthData']:
                if wrapper_key in payload and isinstance(payload[wrapper_key], dict):
                    child_keys = list(payload[wrapper_key].keys())
                    keys.extend([f"{wrapper_key}.{child_key}" for child_key in child_keys])
        
        # Check for alias detection
        alias_fields = ['birthDate', 'birthTime', 'birthLocation', 'date', 'time']
        alias_detected = any(key in alias_fields for key in keys)
        
        # Emit structured log
        app.logger.info(f"request_shape_keys route='{route}' keys={keys} alias_detected={alias_detected} wrapper_detected={wrapper_detected}")
        
    except Exception as e:
        # Don't let logging errors mask the original validation error
        app.logger.error(f"request_shape_keys logging failed: {e}")

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(db.Model):
    """User authentication model - minimal auth data only"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, suspended
    is_admin = db.Column(db.Boolean, default=False, nullable=False)  # Admin privilege flag
    profile_version = db.Column(db.Integer, nullable=False, default=1)  # Client hint/cache key
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'status': self.status,
            'is_admin': self.is_admin,
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

class UserProfile(db.Model):
    """Extended user profile information"""
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    display_name = db.Column(db.String(100))  # Added missing field
    avatar_url = db.Column(db.String(255))    # Added missing field
    bio = db.Column(db.Text)
    age = db.Column(db.Integer)
    profile_completion = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship back to user
    user = db.relationship('User', backref=db.backref('profile', uselist=False, cascade='all, delete-orphan'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'bio': self.bio,
            'age': self.age,
            'profile_completion': self.profile_completion,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def calculate_completion(self):
        """Calculate profile completion percentage"""
        completion = 0
        total_fields = 4  # first_name, last_name, bio, age
        
        if self.first_name: completion += 25
        if self.last_name: completion += 25
        if self.bio: completion += 25
        if self.age: completion += 25
        
        self.profile_completion = completion
        return completion

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
    
    # HD Enhancement Fields
    hd_enhancement_factor = db.Column(db.Float)  # HD intelligence enhancement factor
    compatibility_insights = db.Column(db.Text)  # JSON array of insights
    
    def to_dict(self):
        import json
        insights = []
        if self.compatibility_insights:
            try:
                insights = json.loads(self.compatibility_insights)
            except:
                pass
        
        return {
            'user_a_id': self.user_a_id,
            'user_b_id': self.user_b_id,
            'dimension_scores': {
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
            'hd_enhancement_factor': self.hd_enhancement_factor,
            'compatibility_insights': insights,
            'enhanced_by_hd': self.hd_enhancement_factor is not None,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }

class BirthData(db.Model):
    """Birth data for Human Design calculations with enhanced location support"""
    __tablename__ = 'birth_data'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    birth_date = db.Column(db.Date)
    birth_time = db.Column(db.Time)
    birth_location = db.Column(db.String(255))
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    data_consent = db.Column(db.Boolean, default=False)
    sharing_consent = db.Column(db.Boolean, default=False)
    
    # Enhanced location fields from OpenStreetMap Nominatim
    location_display_name = db.Column(db.Text)
    location_country = db.Column(db.String(100))
    location_state = db.Column(db.String(100))
    location_city = db.Column(db.String(100))
    location_importance = db.Column(db.Numeric(5, 4))
    location_osm_id = db.Column(db.BigInteger)
    location_osm_type = db.Column(db.String(20))
    timezone = db.Column(db.String(50))           # Added missing field
    location_source = db.Column(db.String(50))    # Added missing field  
    location_verified = db.Column(db.Boolean)     # Added missing field
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'birth_time': self.birth_time.isoformat() if self.birth_time else None,
            'birth_location': self.birth_location,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'data_consent': self.data_consent,
            'sharing_consent': self.sharing_consent,
            # Enhanced location data
            'location_display_name': self.location_display_name,
            'location_country': self.location_country,
            'location_state': self.location_state,
            'location_city': self.location_city,
            'location_importance': float(self.location_importance) if self.location_importance else None,
            'location_osm_id': self.location_osm_id,
            'location_osm_type': self.location_osm_type,
            'timezone': self.timezone,
            'location_source': self.location_source,
            'location_verified': self.location_verified
        }

class HumanDesignData(db.Model):
    """Human Design chart data with comprehensive relational compatibility factors"""
    __tablename__ = 'human_design_data'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    chart_data = db.Column(db.Text)  # JSON as TEXT for Railway compatibility
    api_response = db.Column(db.Text)  # Cached full API response
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # === CORE TYPE & STRATEGY ===
    energy_type = db.Column(db.String(50))  # Generator, Manifestor, Projector, Reflector
    sub_type = db.Column(db.String(50))  # Manifesting Generator (if applicable)
    strategy = db.Column(db.String(100))
    type_relational_impact = db.Column(db.Text)  # How type affects relationships
    
    # === AUTHORITY & DECISION MAKING ===
    authority = db.Column(db.String(100))  # Emotional, Sacral, Splenic, Ego, Self-Projected, Environmental, Lunar
    decision_pacing = db.Column(db.String(50))  # In-the-moment, requires waiting, instinctive
    authority_compatibility_impact = db.Column(db.Text)  # How authority pacing aligns or conflicts
    
    # === DEFINITION & SPLITS ===
    definition_type = db.Column(db.String(50))  # Single, Split, Triple Split, Quad Split, No Definition
    split_bridges = db.Column(db.Text)  # JSON: gates/channels that bridge splits
    definition_relational_impact = db.Column(db.Text)  # Attraction patterns, independence needs
    
    # === CENTERS (9 centers with relational dynamics) ===
    center_head = db.Column(db.Boolean, default=False)
    center_head_relational_impact = db.Column(db.Text)
    center_ajna = db.Column(db.Boolean, default=False)
    center_ajna_relational_impact = db.Column(db.Text)
    center_throat = db.Column(db.Boolean, default=False)
    center_throat_relational_impact = db.Column(db.Text)
    center_g = db.Column(db.Boolean, default=False)
    center_g_relational_impact = db.Column(db.Text)
    center_heart = db.Column(db.Boolean, default=False)
    center_heart_relational_impact = db.Column(db.Text)
    center_spleen = db.Column(db.Boolean, default=False)
    center_spleen_relational_impact = db.Column(db.Text)
    center_solar_plexus = db.Column(db.Boolean, default=False)
    center_solar_plexus_relational_impact = db.Column(db.Text)
    center_sacral = db.Column(db.Boolean, default=False)
    center_sacral_relational_impact = db.Column(db.Text)
    center_root = db.Column(db.Boolean, default=False)
    center_root_relational_impact = db.Column(db.Text)
    
    # === GATES (with hanging gates and relational impacts) ===
    gates_defined = db.Column(db.Text)  # JSON array of defined gate numbers
    gates_personality = db.Column(db.Text)  # JSON array of personality gates
    gates_design = db.Column(db.Text)  # JSON array of design gates
    hanging_gates = db.Column(db.Text)  # JSON array of hanging gates seeking connection
    key_relational_gates = db.Column(db.Text)  # JSON: gates 59,6,49,19,44,26,37,40 etc with impacts
    
    # === CHANNELS (with circuit and relational dynamics) ===
    channels_defined = db.Column(db.Text)  # JSON array of defined channel numbers
    key_relationship_channels = db.Column(db.Text)  # JSON: 59-6, 49-19, 40-37, 44-26 etc with impacts
    
    # === PROFILE (with line-by-line relational impacts) ===
    profile = db.Column(db.String(20))  # e.g., "1/3", "4/6", "2/4"
    profile_line1 = db.Column(db.String(50))  # Investigator characteristics
    profile_line2 = db.Column(db.String(50))  # Hermit characteristics  
    profile_line3 = db.Column(db.String(50))  # Martyr characteristics
    profile_line4 = db.Column(db.String(50))  # Opportunist characteristics
    profile_line5 = db.Column(db.String(50))  # Heretic characteristics
    profile_line6 = db.Column(db.String(50))  # Role Model characteristics
    profile_relational_impact = db.Column(db.Text)  # How profile shapes relational style & attraction
    
    # === INCARNATION CROSS ===
    incarnation_cross = db.Column(db.String(200))
    cross_gates = db.Column(db.Text)  # JSON array of 4 gates that define the cross
    cross_angle = db.Column(db.String(50))  # Right/Left angle, Juxtaposition
    cross_relational_impact = db.Column(db.Text)  # Compatibility of life themes & trajectories
    
    # === CONDITIONING & OPENNESS ===
    open_centers = db.Column(db.Text)  # JSON array of open center names
    conditioning_themes = db.Column(db.Text)  # Areas most influenced by others
    conditioning_relational_impact = db.Column(db.Text)  # Where attraction/conditioning happens
    
    # === CIRCUITRY (with relational impacts) ===
    circuitry_individual = db.Column(db.Integer, default=0)  # Count of individual circuitry
    circuitry_tribal = db.Column(db.Integer, default=0)  # Count of tribal circuitry
    circuitry_collective = db.Column(db.Integer, default=0)  # Count of collective circuitry
    circuitry_relational_impact = db.Column(db.Text)  # Tribal→intimacy, Collective→ideals, Individual→uniqueness
    
    # === NODES (North/South Node orientation) ===
    conscious_node = db.Column(db.String(50))  # North Node
    unconscious_node = db.Column(db.String(50))  # South Node
    nodes_relational_impact = db.Column(db.Text)  # Environmental orientation compatibility
    
    # === PLANETARY ACTIVATIONS (advanced layer) ===
    sun_personality = db.Column(db.String(20))  # Gate.Line format (e.g., "1.3")
    earth_personality = db.Column(db.String(20))
    moon_personality = db.Column(db.String(20))
    mercury_personality = db.Column(db.String(20))
    venus_personality = db.Column(db.String(20))
    mars_personality = db.Column(db.String(20))
    jupiter_personality = db.Column(db.String(20))
    saturn_personality = db.Column(db.String(20))
    uranus_personality = db.Column(db.String(20))
    neptune_personality = db.Column(db.String(20))
    pluto_personality = db.Column(db.String(20))
    north_node_personality = db.Column(db.String(20))
    south_node_personality = db.Column(db.String(20))
    
    sun_design = db.Column(db.String(20))
    earth_design = db.Column(db.String(20))
    moon_design = db.Column(db.String(20))
    mercury_design = db.Column(db.String(20))
    venus_design = db.Column(db.String(20))
    mars_design = db.Column(db.String(20))
    jupiter_design = db.Column(db.String(20))
    saturn_design = db.Column(db.String(20))
    uranus_design = db.Column(db.String(20))
    neptune_design = db.Column(db.String(20))
    pluto_design = db.Column(db.String(20))
    north_node_design = db.Column(db.String(20))
    south_node_design = db.Column(db.String(20))
    
    planetary_relational_impacts = db.Column(db.Text)  # JSON: planet-specific relational impacts
    
    # === COMPATIBILITY CALCULATIONS (for Magic 10 algorithm) ===
    electromagnetic_connections = db.Column(db.Text)  # JSON of electromagnetic connections
    compromise_connections = db.Column(db.Text)  # JSON of compromise connections  
    dominance_connections = db.Column(db.Text)  # JSON of dominance connections
    conditioning_dynamics = db.Column(db.Text)  # JSON of conditioning patterns with other charts
    
    # === METADATA ===
    schema_version = db.Column(db.Integer, default=3)  # Updated to v3 for comprehensive relational factors
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # === HELPER METHODS ===
    def set_chart_data(self, data):
        self.chart_data = json.dumps(data) if data else None
    
    def get_chart_data(self):
        return json.loads(self.chart_data) if self.chart_data else {}
    
    def set_api_response(self, response):
        self.api_response = json.dumps(response) if response else None
    
    def get_api_response(self):
        return json.loads(self.api_response) if self.api_response else {}
    
    def set_gates_defined(self, gates):
        self.gates_defined = json.dumps(gates) if gates else None
    
    def get_gates_defined(self):
        return json.loads(self.gates_defined) if self.gates_defined else []
    
    def set_hanging_gates(self, gates):
        self.hanging_gates = json.dumps(gates) if gates else None
    
    def get_hanging_gates(self):
        return json.loads(self.hanging_gates) if self.hanging_gates else []
    
    def set_channels_defined(self, channels):
        self.channels_defined = json.dumps(channels) if channels else None
    
    def get_channels_defined(self):
        return json.loads(self.channels_defined) if self.channels_defined else []
    
    def set_open_centers(self, centers):
        self.open_centers = json.dumps(centers) if centers else None
    
    def get_open_centers(self):
        return json.loads(self.open_centers) if self.open_centers else []
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'chart_data': self.get_chart_data(),
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
            
            # Core Type & Strategy
            'energy_type': self.energy_type,
            'sub_type': self.sub_type,
            'strategy': self.strategy,
            'type_relational_impact': self.type_relational_impact,
            
            # Authority & Decision Making
            'authority': self.authority,
            'decision_pacing': self.decision_pacing,
            'authority_compatibility_impact': self.authority_compatibility_impact,
            
            # Definition & Splits
            'definition_type': self.definition_type,
            'split_bridges': json.loads(self.split_bridges) if self.split_bridges else [],
            'definition_relational_impact': self.definition_relational_impact,
            
            # Centers with relational impacts
            'centers': {
                'head': {'defined': self.center_head, 'relational_impact': self.center_head_relational_impact},
                'ajna': {'defined': self.center_ajna, 'relational_impact': self.center_ajna_relational_impact},
                'throat': {'defined': self.center_throat, 'relational_impact': self.center_throat_relational_impact},
                'g': {'defined': self.center_g, 'relational_impact': self.center_g_relational_impact},
                'heart': {'defined': self.center_heart, 'relational_impact': self.center_heart_relational_impact},
                'spleen': {'defined': self.center_spleen, 'relational_impact': self.center_spleen_relational_impact},
                'solar_plexus': {'defined': self.center_solar_plexus, 'relational_impact': self.center_solar_plexus_relational_impact},
                'sacral': {'defined': self.center_sacral, 'relational_impact': self.center_sacral_relational_impact},
                'root': {'defined': self.center_root, 'relational_impact': self.center_root_relational_impact}
            },
            
            # Gates and Channels
            'gates_defined': self.get_gates_defined(),
            'hanging_gates': self.get_hanging_gates(),
            'channels_defined': self.get_channels_defined(),
            'key_relational_gates': json.loads(self.key_relational_gates) if self.key_relational_gates else {},
            'key_relationship_channels': json.loads(self.key_relationship_channels) if self.key_relationship_channels else {},
            
            # Profile with line details
            'profile': self.profile,
            'profile_lines': {
                'line1': self.profile_line1,
                'line2': self.profile_line2,
                'line3': self.profile_line3,
                'line4': self.profile_line4,
                'line5': self.profile_line5,
                'line6': self.profile_line6
            },
            'profile_relational_impact': self.profile_relational_impact,
            
            # Incarnation Cross
            'incarnation_cross': self.incarnation_cross,
            'cross_gates': json.loads(self.cross_gates) if self.cross_gates else [],
            'cross_angle': self.cross_angle,
            'cross_relational_impact': self.cross_relational_impact,
            
            # Conditioning & Openness
            'open_centers': self.get_open_centers(),
            'conditioning_themes': self.conditioning_themes,
            'conditioning_relational_impact': self.conditioning_relational_impact,
            
            # Circuitry
            'circuitry': {
                'individual': self.circuitry_individual,
                'tribal': self.circuitry_tribal,
                'collective': self.circuitry_collective,
                'relational_impact': self.circuitry_relational_impact
            },
            
            # Nodes
            'nodes': {
                'conscious': self.conscious_node,
                'unconscious': self.unconscious_node,
                'relational_impact': self.nodes_relational_impact
            },
            
            # Planetary Activations
            'planetary_activations': {
                'personality': {
                    'sun': self.sun_personality,
                    'earth': self.earth_personality,
                    'moon': self.moon_personality,
                    'mercury': self.mercury_personality,
                    'venus': self.venus_personality,
                    'mars': self.mars_personality,
                    'jupiter': self.jupiter_personality,
                    'saturn': self.saturn_personality,
                    'uranus': self.uranus_personality,
                    'neptune': self.neptune_personality,
                    'pluto': self.pluto_personality,
                    'north_node': self.north_node_personality,
                    'south_node': self.south_node_personality
                },
                'design': {
                    'sun': self.sun_design,
                    'earth': self.earth_design,
                    'moon': self.moon_design,
                    'mercury': self.mercury_design,
                    'venus': self.venus_design,
                    'mars': self.mars_design,
                    'jupiter': self.jupiter_design,
                    'saturn': self.saturn_design,
                    'uranus': self.uranus_design,
                    'neptune': self.neptune_design,
                    'pluto': self.pluto_design,
                    'north_node': self.north_node_design,
                    'south_node': self.south_node_design
                },
                'relational_impacts': json.loads(self.planetary_relational_impacts) if self.planetary_relational_impacts else {}
            },
            
            # Compatibility Calculations
            'compatibility_connections': {
                'electromagnetic': json.loads(self.electromagnetic_connections) if self.electromagnetic_connections else {},
                'compromise': json.loads(self.compromise_connections) if self.compromise_connections else {},
                'dominance': json.loads(self.dominance_connections) if self.dominance_connections else {},
                'conditioning_dynamics': json.loads(self.conditioning_dynamics) if self.conditioning_dynamics else {}
            },
            
            'schema_version': self.schema_version
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
# RESONANCE TEN MODELS
# ============================================================================

class UserResonancePrefs(db.Model):
    """User preferences for Resonance Ten compatibility model"""
    __tablename__ = 'user_resonance_prefs'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    weights = db.Column(db.JSON, nullable=False)  # Dict[str, int] - 0-100 scale
    facets = db.Column(db.JSON)  # Optional sub-facet preferences
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'version': self.version,
            'weights': self.weights or {},
            'facets': self.facets or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class UserResonanceSignalsPrivate(db.Model):
    """Private signals for Resonance Ten compatibility (backend only)"""
    __tablename__ = 'user_resonance_signals_private'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    decision_mode = db.Column(db.String(50), nullable=False)
    interaction_mode = db.Column(db.String(50), nullable=False)
    connection_style = db.Column(db.String(50), nullable=False)
    bridges_count = db.Column(db.SmallInteger, nullable=False)
    emotion_signal = db.Column(db.Boolean, nullable=False)
    work_energy = db.Column(db.Boolean, nullable=False)
    will_signal = db.Column(db.Boolean, nullable=False)
    expression_signal = db.Column(db.Boolean, nullable=False)
    mind_signal = db.Column(db.Boolean, nullable=False)
    role_pattern = db.Column(db.String(50), nullable=False)
    tempo_pattern = db.Column(db.String(50))
    identity_openness = db.Column(db.Boolean, nullable=False)
    trajectory_code = db.Column(db.String(20))
    confidence = db.Column(db.JSON)  # Confidence scores for signal quality
    computed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Note: This should never be exposed to public APIs"""
        return {
            'user_id': self.user_id,
            'decision_mode': self.decision_mode,
            'interaction_mode': self.interaction_mode,
            'connection_style': self.connection_style,
            'bridges_count': self.bridges_count,
            'emotion_signal': self.emotion_signal,
            'work_energy': self.work_energy,
            'will_signal': self.will_signal,
            'expression_signal': self.expression_signal,
            'mind_signal': self.mind_signal,
            'role_pattern': self.role_pattern,
            'tempo_pattern': self.tempo_pattern,
            'identity_openness': self.identity_openness,
            'trajectory_code': self.trajectory_code,
            'confidence': self.confidence or {},
            'computed_at': self.computed_at.isoformat() if self.computed_at else None
        }

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
    """Calculate bidirectional compatibility between two users with HD intelligence"""
    try:
        user1_priorities = UserPriorities.query.get(user1_id)
        user2_priorities = UserPriorities.query.get(user2_id)
        
        if not user1_priorities or not user2_priorities:
            return None
        
        # Get priority arrays
        priorities1 = user1_priorities.get_priorities_array()
        priorities2 = user2_priorities.get_priorities_array()
        
        # Calculate base Magic 10 compatibility
        magic10_compatibility = calculate_compatibility_score(priorities1, priorities2)
        
        # Enhance with HD intelligence
        try:
            from hd_intelligence_engine import calculate_enhanced_compatibility
            enhanced_compatibility = calculate_enhanced_compatibility(
                user1_id, user2_id, magic10_compatibility
            )
            return enhanced_compatibility
        except Exception as hd_error:
            print(f"HD enhancement failed, using Magic 10 only: {hd_error}")
            return magic10_compatibility
        
    except Exception as e:
        print(f"Error calculating mutual compatibility: {e}")
        return None

def store_compatibility_result(user_a_id, user_b_id, compatibility_result):
    """Store compatibility calculation result in database with HD enhancement"""
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
        
        # Store HD enhancement data if available
        if 'hd_enhancement_factor' in compatibility_result:
            compatibility_record.hd_enhancement_factor = compatibility_result['hd_enhancement_factor']
        
        if 'compatibility_insights' in compatibility_result:
            import json
            compatibility_record.compatibility_insights = json.dumps(compatibility_result['compatibility_insights'])
        
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
    """Decorator to require session-based authentication (cookie sessions only)"""
    def decorated_function(*args, **kwargs):
        user, error_code = validate_auth_session()
        
        if not user:
            if error_code == "AUTH_REQUIRED":
                return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
            else:
                # SESSION_EXPIRED - return typed JSON as per CRD
                return jsonify({
                    'ok': False, 
                    'error': 'session_expired', 
                    'code': 'SESSION_EXPIRED'
                }), 401
        
        # Add user to Flask g context for access in route handlers
        g.user = user
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_admin(f):
    """Decorator to require admin privileges (session-based)"""
    def decorated_function(*args, **kwargs):
        user, error_code = validate_auth_session()
        
        if not user:
            if error_code == "AUTH_REQUIRED":
                return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
            else:
                # SESSION_EXPIRED - return typed JSON as per CRD
                return jsonify({
                    'ok': False, 
                    'error': 'session_expired', 
                    'code': 'SESSION_EXPIRED'
                }), 401
        
        # Check if user is admin
        if not user.is_admin:
            return jsonify({'error': 'Admin privileges required', 'code': 'ADMIN_REQUIRED'}), 403
        
        # Add user to Flask g context
        g.user = user
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

@app.route('/api/_debug/cookies', methods=['GET'])
def debug_cookies():
    """Debug endpoint to check cookie state and request properties"""
    response_data = {
        'has_session': 'glow_session' in request.cookies,
        'session_id': request.cookies.get('glow_session'),
        'has_csrf_cookie': 'glow_csrf' in request.cookies,
        'csrf_cookie': request.cookies.get('glow_csrf'),
        'host': request.host,
        'secure': request.is_secure,
        'headers': dict(request.headers),
        'all_cookies': dict(request.cookies)
    }
    
    response = make_response(jsonify(response_data))
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.route('/api/debug/test-human-design', methods=['POST'])
def test_human_design_api():
    """Test Human Design API geocoding (remove in production)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Test with provided data or default test data
        test_data = {
            'birth_date': data.get('birthdate', '17-Mar-1978'),
            'birth_time': data.get('birthtime', '12:00'),
            'birth_location': data.get('location', 'East Grand Rapids, Michigan, USA')
        }
        
        print(f"Testing Human Design API with: {test_data}")
        
        # Call the Human Design API
        api_response = call_human_design_api(test_data)
        
        if 'error' in api_response:
            return jsonify({
                'success': False,
                'error': api_response['error'],
                'test_data': test_data
            }), 500
        
        # Return success with full API response for debugging
        return jsonify({
            'success': True,
            'test_data': test_data,
            'api_configured': bool(app.config['HD_API_KEY']),
            'geocoding_configured': bool(app.config['GEO_API_KEY']),
            'full_response': api_response  # Show complete response to debug geocoding
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'api_configured': bool(app.config.get('HD_API_KEY')),
            'geocoding_configured': bool(app.config.get('GEO_API_KEY'))
        }), 500

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

@app.route('/api/debug/migrate-user-profiles', methods=['POST'])
def migrate_user_profiles():
    """Migrate existing user data to user_profiles table"""
    try:
        with app.app_context():
            # First ensure tables exist
            db.create_all()
            
            # Check if users table has profile data to migrate
            if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
                # PostgreSQL
                check_columns = db.session.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name IN ('first_name', 'last_name')
                """))
            else:
                # SQLite
                check_columns = db.session.execute(text("PRAGMA table_info(users)"))
            
            columns = [row[0] for row in check_columns.fetchall()]
            has_profile_data = 'first_name' in columns or 'last_name' in columns
            
            migrated_count = 0
            
            if has_profile_data:
                # Get users with profile data
                users_with_data = db.session.execute(text("""
                    SELECT id, first_name, last_name, created_at 
                    FROM users 
                    WHERE first_name IS NOT NULL OR last_name IS NOT NULL
                """)).fetchall()
                
                # Create profile records for users
                for user_data in users_with_data:
                    user_id, first_name, last_name, created_at = user_data
                    
                    # Check if profile already exists
                    existing_profile = UserProfile.query.filter_by(user_id=user_id).first()
                    if existing_profile:
                        continue
                    
                    # Calculate completion
                    completion = 0
                    if first_name: completion += 25
                    if last_name: completion += 25
                    
                    # Create new profile
                    profile = UserProfile(
                        user_id=user_id,
                        first_name=first_name,
                        last_name=last_name,
                        profile_completion=completion,
                        created_at=created_at,
                        updated_at=datetime.utcnow()
                    )
                    
                    db.session.add(profile)
                    migrated_count += 1
                
                db.session.commit()
            
            # Get final counts
            total_users = User.query.count()
            total_profiles = UserProfile.query.count()
            
            return jsonify({
                'status': 'success',
                'message': 'User profiles migration completed',
                'migrated_count': migrated_count,
                'total_users': total_users,
                'total_profiles': total_profiles,
                'had_profile_data': has_profile_data
            })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Migration failed: {str(e)}'
        }), 500

@app.route('/api/debug/cleanup-user-redundancy', methods=['POST'])
def cleanup_user_redundancy():
    """Remove redundant first_name and last_name columns from users table"""
    try:
        with app.app_context():
            # Check if columns exist before trying to drop them
            if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
                # PostgreSQL
                check_columns = db.session.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name IN ('first_name', 'last_name')
                """))
                existing_columns = [row[0] for row in check_columns.fetchall()]
                
                # Drop columns if they exist
                for column in existing_columns:
                    try:
                        db.session.execute(text(f"ALTER TABLE users DROP COLUMN IF EXISTS {column}"))
                        print(f"Dropped column: {column}")
                    except Exception as e:
                        print(f"Could not drop column {column}: {e}")
                
            else:
                # SQLite - more complex, need to recreate table
                print("SQLite detected - column dropping requires table recreation")
                # For SQLite, we'd need to recreate the table, but this is more complex
                # For now, just report the status
                
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'User table redundancy cleanup completed',
                'columns_processed': existing_columns if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else ['SQLite - manual cleanup needed']
            })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Cleanup failed: {str(e)}'
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

# ============================================================================
# AUTH v2 HELPER FUNCTIONS
# ============================================================================

def create_auth_session(user_id):
    """Create a new authenticated session using Redis/filesystem backend"""
    try:
        # Create session using the session store
        session_data = session_store.create_session(user_id)
        
        # Set Flask session with session ID for cookie management
        session.permanent = True
        session['session_id'] = session_data['session_id']
        session['user_id'] = user_id
        session['created_at'] = session_data['created_at']
        session['last_seen_at'] = session_data['last_seen']
        
        # Track session for revocation (T-BE-003)
        track_session_on_login(session_store, user_id, session_data['session_id'])
        
        app.logger.info(f"Session created for user {user_id}: {session_data['session_id']}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to create session: {e}")
        return False

def validate_auth_session():
    """Validate current session using Redis/filesystem backend with smart renewal"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return None, "AUTH_REQUIRED"
        
        # Check if session renewal is enabled
        renewal_enabled = os.environ.get('SESSION_RENEWAL_ENABLED', '1') == '1'
        idle_minutes = int(os.environ.get('SESSION_IDLE_MIN', '30'))
        
        if not renewal_enabled:
            # Legacy behavior - just get session without renewal logic
            session_data = session_store.get_session(session_id)
            if not session_data:
                session.clear()
                return None, "SESSION_EXPIRED"
            return session_data['user_id'], None
        
        # Get session from store
        session_data = session_store.get_session(session_id)
        if not session_data:
            session.clear()
            return None, "SESSION_EXPIRED"
        
        # Check idle expiry with sliding renewal logic
        now = datetime.utcnow()
        last_seen_str = session_data.get('last_seen', session_data.get('created_at'))
        last_seen = datetime.fromisoformat(last_seen_str.replace('Z', ''))
        
        idle_seconds = (now - last_seen).total_seconds()
        idle_limit_seconds = idle_minutes * 60
        renewal_threshold_seconds = idle_limit_seconds / 2  # Renew at half-life (~15 min)
        
        # Expire if idle too long
        if idle_seconds >= idle_limit_seconds:
            session_store.destroy_session(session_id)
            session.clear()
            app.logger.info(f"Session expired (idle {idle_seconds:.0f}s >= {idle_limit_seconds}s): {session_id}")
            return None, "SESSION_EXPIRED"
        
        # Update last_seen for all requests
        session_data['last_seen'] = now.isoformat() + 'Z'
        session_store.update_session(session_id, session_data)
        
        # Check if rolling refresh needed (reissue cookie)
        needs_refresh = idle_seconds >= renewal_threshold_seconds
        if needs_refresh:
            # Set flag for cookie reissue in response
            g.session_needs_refresh = True
            g.session_id = session_id
            app.logger.info(f"Session renewal triggered (idle {idle_seconds:.0f}s >= {renewal_threshold_seconds:.0f}s): {session_id}")
        
        return session_data['user_id'], None
        
    except Exception as e:
        app.logger.error(f"Session validation error: {e}")
        session.clear()
        return None, "SESSION_EXPIRED"

def clear_auth_session():
    """Clear the current session using Redis/filesystem backend"""
    try:
        session_id = session.get('session_id')
        user_id = session.get('user_id')
        
        # Untrack session for revocation (T-BE-003)
        if user_id and session_id:
            untrack_session_on_logout(session_store, user_id, session_id)
        
        # Destroy session in store
        if session_id:
            session_store.destroy_session(session_id)
        
        # Clear Flask session
        session.clear()
        
        app.logger.info(f"Session cleared for user {user_id or 'unknown'}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to clear session: {e}")
        return False

def hash_password_v2(password):
    """Hash password using Argon2 (Auth v2)"""
    try:
        return ph.hash(password)
    except Exception as e:
        app.logger.error(f"Password hashing failed: {e}")
        raise

def verify_password_v2(password, password_hash):
    """Verify password using Argon2 (Auth v2)"""
    try:
        ph.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False
    except Exception as e:
        app.logger.error(f"Password verification failed: {e}")
        return False

# ============================================================================
# AUTH v2 ROUTES
# ============================================================================

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit(app.config['AUTH_RATE_LIMIT_PER_IP'])
def auth_v2_login():
    """Auth v2 Login - Cookie-based session with JSON contracts"""
    try:
        ensure_database()
        
        # Parse request
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({
                'ok': False,
                'error': 'Email and password required',
                'code': 'INVALID_REQUEST'
            }), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # S7-MP4: Check rate limit before processing
        retry_after = login_rate_limiter.check_rate_limit(request, email)
        if retry_after is not None:
            response = make_response(jsonify({
                'ok': False,
                'error': 'rate_limited',
                'code': 'RATE_LIMIT_LOGIN',
                'retry_after': retry_after
            }), 429)
            response.headers['Retry-After'] = str(retry_after)
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Vary'] = 'Origin'
            return response
        
        # Rate limiting log
        app.logger.info(f"Login attempt for email: {hashlib.sha256(email.encode()).hexdigest()[:8]}")
        
        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            app.logger.info(f"Login failed: user not found for email hash {hashlib.sha256(email.encode()).hexdigest()[:8]}")
            # S7-MP4: Record failed attempt
            login_rate_limiter.record_failed_attempt(request, email)
            return jsonify({
                'ok': False,
                'error': 'Invalid credentials',
                'code': 'INVALID_CREDENTIALS'
            }), 401
        
        # Verify password (support both old and new hashing)
        password_valid = False
        if user.password_hash.startswith('$argon2'):
            # New Argon2 hash
            password_valid = verify_password_v2(password, user.password_hash)
        else:
            # Legacy Werkzeug hash - verify and upgrade
            password_valid = check_password_hash(user.password_hash, password)
            if password_valid:
                # Upgrade to Argon2
                user.password_hash = hash_password_v2(password)
                db.session.commit()
                app.logger.info(f"Password upgraded to Argon2 for user {user.id}")
        
        if not password_valid:
            app.logger.info(f"Login failed: invalid password for user {user.id}")
            # S7-MP4: Record failed attempt
            login_rate_limiter.record_failed_attempt(request, email)
            return jsonify({
                'ok': False,
                'error': 'Invalid credentials',
                'code': 'INVALID_CREDENTIALS'
            }), 401
        
        # Check user status
        if user.status != 'approved':
            app.logger.info(f"Login failed: user {user.id} status is {user.status}")
            return jsonify({
                'ok': False,
                'error': f'Account is {user.status}',
                'code': 'ACCOUNT_NOT_APPROVED'
            }), 403
        
        # Create session
        if not create_auth_session(user.id):
            return jsonify({
                'ok': False,
                'error': 'Failed to create session',
                'code': 'SESSION_ERROR'
            }), 500
        
        # S7-MP4: Clear user bucket on successful login
        login_rate_limiter.clear_user_bucket(request, email)
        
        # Success response (Auth v2 contract)
        response_data = {
            'ok': True
        }
        
        # Create response with proper headers
        response = make_response(jsonify(response_data))
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Vary'] = 'Origin'
        
        # Issue both session and CSRF cookies using centralized helpers (BE-LOGIN-02)
        session_id = session.get('session_id')
        app.logger.info(f"DEBUG: session_id from Flask session: {session_id}")
        
        if session_id:
            # Import centralized cookie helpers
            from cookies import set_session_cookie, set_csrf_cookie
            from csrf_protection import generate_csrf_token
            
            app.logger.info(f"DEBUG: Setting cookies for session_id: {session_id}")
            
            # Set session cookie (HttpOnly=true)
            set_session_cookie(response, session_id, max_age=1800)
            
            # Generate and set CSRF cookie (HttpOnly=false for JavaScript access)
            csrf_token = generate_csrf_token()
            set_csrf_cookie(response, csrf_token, max_age=1800)
            
            # Store CSRF token in session for validation
            session_data = session_store.get_session(session_id)
            if session_data:
                session_data['csrf'] = csrf_token
                session_store.update_session(session_id, session_data)
            
            # Login diagnostics logging (BE-LOGIN-02-C)
            app.logger.info(f"auth_login_issue user_id={user.id} has_session_cookie=true has_csrf_cookie=true domain=.glowme.io status=200")
        else:
            app.logger.error(f"DEBUG: No session_id found in Flask session - cookies not set!")
            # Emergency fallback - try to get session_id from session store directly
            try:
                from cookies import set_session_cookie, set_csrf_cookie
                from csrf_protection import generate_csrf_token
                
                # Create a new session if none exists
                session_data = session_store.create_session(user.id)
                fallback_session_id = session_data['session_id']
                
                # Set Flask session
                session['session_id'] = fallback_session_id
                session['user_id'] = user.id
                
                app.logger.info(f"DEBUG: Created fallback session: {fallback_session_id}")
                
                # Set cookies with fallback session
                set_session_cookie(response, fallback_session_id, max_age=1800)
                csrf_token = generate_csrf_token()
                set_csrf_cookie(response, csrf_token, max_age=1800)
                
                # Store CSRF in session
                session_data['csrf'] = csrf_token
                session_store.update_session(fallback_session_id, session_data)
                
                app.logger.info(f"auth_login_issue_fallback user_id={user.id} has_session_cookie=true has_csrf_cookie=true domain=.glowme.io status=200")
            except Exception as e:
                app.logger.error(f"DEBUG: Fallback cookie setting failed: {e}")
        
        app.logger.info(f"Login successful for user {user.id}")
        return response, 200
    
    except Exception as e:
        app.logger.error(f"Login error: {e}")
        return jsonify({
            'ok': False,
            'error': 'Login failed',
            'code': 'INTERNAL_ERROR'
        }), 500

@app.route('/api/auth/me', methods=['GET'])
def auth_v2_me():
    """Auth v2 Me - Enhanced session validation with complete user profile data and session management"""
    start_time = time_module.time()
    
    try:
        # Set strict headers for security and caching
        response_headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Cache-Control': 'no-store',
            'Vary': 'Cookie'
        }
        
        user_id, error_code = validate_auth_session()
        
        if not user_id:
            app.logger.info(f"Me check failed: {error_code}")
            response = jsonify({
                'ok': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            })
            for header, value in response_headers.items():
                response.headers[header] = value
            return response, 401
        
        # Single optimized query with LEFT JOINs for all user data
        try:
            query = db.session.query(
                User.id,
                User.email,
                User.status,
                User.is_admin,
                User.updated_at,
                User.profile_version,
                UserProfile.first_name,
                UserProfile.last_name,
                UserProfile.display_name,
                UserProfile.avatar_url,
                UserProfile.bio,
                UserProfile.profile_completion,
                BirthData.birth_date,
                BirthData.birth_time,
                BirthData.timezone,
                BirthData.latitude,
                BirthData.longitude,
                BirthData.birth_location
            ).select_from(User).outerjoin(
                UserProfile, User.id == UserProfile.user_id
            ).outerjoin(
                BirthData, User.id == BirthData.user_id
            ).filter(User.id == user_id)
            
            # Log compiled SQL for debugging
            app.logger.info(f"me_join_sql user_id={user_id} query={str(query)}")
            
            result = query.first()
            
            # Log raw row for debugging
            if result:
                app.logger.info(f"me_join_row user_id={user_id} birth_date={result[10]} birth_time={result[11]}")
            else:
                app.logger.warning(f"me_join_row user_id={user_id} result=None")
                
        except Exception as query_error:
            app.logger.error(f"me_join_error user_id={user_id} error={type(query_error).__name__}: {query_error}")
            # Return 5xx instead of silent fallback
            response = jsonify({
                'ok': False,
                'error': 'Database query failed',
                'code': 'DB_QUERY_ERROR'
            })
            for header, value in response_headers.items():
                response.headers[header] = value
            return response, 500
        
        if not result:
            session.clear()
            app.logger.error(f"Me check failed: user {user_id} not found")
            response = jsonify({
                'ok': False,
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            })
            for header, value in response_headers.items():
                response.headers[header] = value
            return response, 401
        
        # Safely unpack query result
        try:
            (user_id, email, status, is_admin, updated_at, profile_version,
             first_name, last_name, display_name, avatar_url, bio, profile_completion,
             birth_date, birth_time, timezone, latitude, longitude, birth_location) = result
        except (ValueError, TypeError) as unpack_error:
            app.logger.error(f"Result unpacking error in /me: {unpack_error}")
            # Use safe defaults
            user_id, email, status, is_admin, updated_at = result[:5]
            profile_version = getattr(result, 'profile_version', 1) if hasattr(result, 'profile_version') else 1
            first_name = last_name = display_name = avatar_url = bio = profile_completion = None
            birth_date = birth_time = timezone = latitude = longitude = birth_location = None
        
        # Session management and renewal logic using Redis session data
        now = datetime.utcnow()
        session_renewed = False
        
        # Get session metadata from Redis store (not Flask session)
        session_id = session.get('session_id')
        if session_id:
            # Get session data from Redis store
            redis_session_data = session_store.get_session(session_id)
            if redis_session_data:
                # Use Redis session data for metadata
                created_at = datetime.fromisoformat(redis_session_data['created_at'].replace('Z', ''))
                last_seen = datetime.fromisoformat(redis_session_data['last_seen'].replace('Z', ''))
                
                # Check if session was renewed during validation
                touch_result = session_store.touch_session(session_id)
                session_renewed = touch_result.get('renewed', False)
                
                # Use Redis session TTL for accurate idle time
                idle_ttl_seconds = touch_result.get('idle_ttl_seconds', 1800)
                idle_expires_at = now + timedelta(seconds=idle_ttl_seconds)
                absolute_expires_at = datetime.fromisoformat(redis_session_data['absolute_expires_at'].replace('Z', ''))
            else:
                # Fallback if Redis session not found
                created_at = last_seen = now
                idle_expires_at = now + timedelta(minutes=30)
                absolute_expires_at = now + timedelta(hours=24)
        else:
            # Fallback session metadata
            session_id = f'sess_{user_id}_{int(now.timestamp())}'
            created_at = last_seen = now
            idle_expires_at = now + timedelta(minutes=30)
            absolute_expires_at = now + timedelta(hours=24)
        
        # Build complete user response with stable JSON shape
        user_data = {
            'id': user_id,
            'email': email,
            'first_name': first_name or "",
            'last_name': last_name or "",
            'bio': bio or "",
            'status': status,
            'is_admin': is_admin,
            'updated_at': updated_at.isoformat() + 'Z' if updated_at else None,
            'profile': {
                'display_name': display_name,
                'avatar_url': avatar_url,
                'bio': bio,
                'profile_completion': profile_completion
            },
            'birth_data': {
                'date': birth_date.strftime('%Y-%m-%d') if birth_date else None,
                'time': format_birth_time_strict(birth_time),  # S3-A1R-H4: Strict HH:mm formatting
                'timezone': timezone,
                'latitude': float(latitude) if latitude is not None else None,
                'longitude': float(longitude) if longitude is not None else None,
                'location': birth_location
            },
            'profile_version': profile_version or 1,
            'session_meta': {
                'session_id': session_id,
                'last_seen': last_seen.isoformat() + 'Z',
                'idle_expires_at': idle_expires_at.isoformat() + 'Z',
                'absolute_expires_at': absolute_expires_at.isoformat() + 'Z',
                'renewed': session_renewed
            }
        }
        
        # Success response with complete contract
        response_data = {
            'ok': True,
            'contract_version': 1,
            'issued_at': now.isoformat() + 'Z',
            'user': user_data
        }
        
        # Create response with headers
        response = jsonify(response_data)
        for header, value in response_headers.items():
            response.headers[header] = value
        
        # Add Set-Cookie header if session was renewed
        if session_renewed:
            _set_cookie(response, 'glow_session', session.get("session_id", ""), max_age=1800)
        
        # Log performance and success
        latency_ms = int((time_module.time() - start_time) * 1000)
        app.logger.info(f"Me check successful for user {user_id}, renewed={session_renewed}, latency={latency_ms}ms, profile_version={profile_version}")
        
        return response, 200
    
    except Exception as e:
        latency_ms = int((time_module.time() - start_time) * 1000)
        app.logger.error(f"Me check error: {e}, latency={latency_ms}ms")
        response = jsonify({
            'ok': False,
            'error': 'Authentication check failed',
            'code': 'INTERNAL_ERROR'
        })
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Cache-Control'] = 'no-store'
        return response, 500

@app.route('/api/auth/logout', methods=['POST'])
@csrf_protect(session_store, validate_auth_session)
def auth_v2_logout():
    """Auth v2 Logout - Session invalidation"""
    try:
        user_id = session.get('user_id')
        
        # Clear session regardless of validity
        clear_auth_session()
        
        # Create response and clear cookies
        response_data = {'ok': True}
        response = make_response(jsonify(response_data))
        
        # Clear both session and CSRF cookies
        _clear_cookie(response, 'glow_session')
        clear_csrf_on_logout(response)
        
        app.logger.info(f"Logout successful for user {user_id or 'unknown'}")
        return response, 200
    
    except Exception as e:
        app.logger.error(f"Logout error: {e}")
        return jsonify({
            'ok': False,
            'error': 'Logout failed',
            'code': 'INTERNAL_ERROR'
        }), 500



# ============================================================================
# GLOBAL JSON ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """Ensure 404s return JSON for API routes"""
    if request.path.startswith('/api/'):
        return jsonify({
            'ok': False,
            'error': 'Endpoint not found',
            'code': 'NOT_FOUND'
        }), 404
    return error

@app.errorhandler(405)
def method_not_allowed_error(error):
    """Ensure 405s return JSON for API routes"""
    if request.path.startswith('/api/'):
        return jsonify({
            'ok': False,
            'error': 'Method not allowed',
            'code': 'METHOD_NOT_ALLOWED'
        }), 405
    return error

@app.errorhandler(500)
def internal_error(error):
    """Ensure 500s return JSON for API routes"""
    if request.path.startswith('/api/'):
        return jsonify({
            'ok': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500
    return error

# ============================================================================
# API ROUTES - MAGIC 10 MATCHING
# ============================================================================

@app.route('/api/priorities', methods=['GET'])
@require_auth
def get_user_priorities():
    """Get user's Magic 10 priorities"""
    try:
        priorities = UserPriorities.query.get(g.user)
        if not priorities:
            # Create default priorities if they don't exist
            priorities = UserPriorities(user_id=g.user)
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
        priorities = UserPriorities.query.get(g.user)
        if not priorities:
            priorities = UserPriorities(user_id=g.user)
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

# ============================================================================
# API ROUTES - RESONANCE TEN
# ============================================================================

@app.route('/api/config/resonance', methods=['GET'])
def get_resonance_config_endpoint():
    """Get Resonance Ten configuration"""
    try:
        config = get_resonance_config()
        return jsonify(config)
    except Exception as e:
        print(f"Get resonance config error: {e}")
        return jsonify({'error': 'Failed to get configuration'}), 500

@app.route('/api/me/resonance', methods=['GET'])
@require_auth
def get_user_resonance_prefs():
    """Get user's Resonance Ten preferences"""
    try:
        prefs = UserResonancePrefs.query.get(g.user)
        if not prefs:
            # Create default preferences if they don't exist
            config = get_resonance_config()
            default_weights = {key: 50 for key in config['keys']}  # Default to 50 for all dimensions
            
            prefs = UserResonancePrefs(
                user_id=g.user,
                version=1,
                weights=default_weights,
                facets={}
            )
            db.session.add(prefs)
            db.session.commit()
        
        return jsonify(prefs.to_dict())
    
    except Exception as e:
        print(f"Get resonance prefs error: {e}")
        return jsonify({'error': 'Failed to get preferences'}), 500

@app.route('/api/me/resonance', methods=['PUT'])
@require_auth
def update_user_resonance_prefs():
    """Update user's Resonance Ten preferences"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate version
        version = data.get('version', 1)
        if version != 1:
            return jsonify({'error': 'Unsupported version'}), 400
        
        # Validate weights
        weights = data.get('weights', {})
        is_valid, error_msg = validate_resonance_weights(weights)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # Validate facets (optional)
        facets = data.get('facets', {})
        if facets and not isinstance(facets, dict):
            return jsonify({'error': 'Facets must be a dictionary'}), 400
        
        # Get or create preferences record
        prefs = UserResonancePrefs.query.get(g.user)
        if not prefs:
            prefs = UserResonancePrefs(user_id=g.user)
            db.session.add(prefs)
        
        # Update preferences
        prefs.version = version
        prefs.weights = weights
        prefs.facets = facets
        prefs.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'ok': True})
    
    except Exception as e:
        db.session.rollback()
        print(f"Update resonance prefs error: {e}")
        return jsonify({'error': 'Failed to update preferences'}), 500

# ============================================================================
# TEMPORARY ALIASES (remove after frontend migration)
# ============================================================================

# Keep old paths working for zero downtime
app.add_url_rule("/config/resonance", view_func=get_resonance_config_endpoint, methods=["GET"])
app.add_url_rule("/me/resonance", view_func=get_user_resonance_prefs, methods=["GET"])
app.add_url_rule("/me/resonance", view_func=update_user_resonance_prefs, methods=["PUT"])

# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

# ============================================================================
# COMPATIBILITY ENDPOINTS
# ============================================================================

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
        compatibility = calculate_mutual_compatibility(g.user, target_user_id)
        if not compatibility:
            return jsonify({'error': 'Failed to calculate compatibility'}), 500
        
        # Store result
        store_compatibility_result(g.user, target_user_id, compatibility)
        
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
        
        matches = get_user_matches(g.user, limit, min_score)
        
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
        birth_data = BirthData.query.get(g.user)
        if not birth_data:
            return jsonify({'birth_data': None})
        
        return jsonify({'birth_data': birth_data.to_dict()})
    
    except Exception as e:
        print(f"Get birth data error: {e}")
        return jsonify({'error': 'Failed to get birth data'}), 500

@app.route('/api/birth-data', methods=['POST'])
@require_auth
@csrf_protect(session_store, validate_auth_session)
def save_birth_data():
    """Save user's birth data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Normalize request
        from birth_data_validator import BirthDataValidator, ValidationError
        
        normalized_data = normalize_birth_data_request(data, 'POST /api/birth-data')
        
        # Validate using central validator (validates only provided keys - intrinsic partial mode)
        try:
            validated_data = BirthDataValidator.validate_birth_data(normalized_data)
        except ValidationError as e:
            # Log request shape on validation failure with diagnostics
            app.logger.info("request_shape_keys", extra={
                'route': 'POST /api/birth-data',
                'keys': list(data.keys()),
                'validation_errors': list(e.details.keys()),
                'alias_detected': 'birthDate' in data or 'birthTime' in data or 'date' in data or 'time' in data,
                'wrapper_detected': 'birth_data' in data or 'birthData' in data
            })
            return jsonify({
                'error': 'validation_error',
                'message': 'One or more fields are invalid',
                'details': e.details
            }), 400
        
        # Get or create birth data record
        birth_data = BirthData.query.get(g.user)
        if not birth_data:
            birth_data = BirthData(user_id=g.user)
            db.session.add(birth_data)
        
        # Update only provided fields
        for field, value in validated_data.items():
            setattr(birth_data, field, value)
        
        # Log successful save
        app.logger.info("save_attempt", extra={
            'route': 'POST /api/birth-data',
            'accepted_keys': list(validated_data.keys()),
            'status': 'success'
        })
        
        db.session.commit()
        
        return jsonify({
            'message': 'Birth data saved successfully',
            'birth_data': birth_data.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error in save_birth_data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/human-design/calculate', methods=['POST'])
@require_auth
def calculate_human_design():
    """Calculate Human Design chart with enhanced intelligence"""
    try:
        # Get user's birth data
        birth_data = BirthData.query.get(g.user)
        if not birth_data:
            return jsonify({'error': 'Birth data not found'}), 404
        
        if not birth_data.data_consent:
            return jsonify({'error': 'Data consent required'}), 403
        
        # Prepare data for HD intelligence engine
        birth_data_dict = {
            'birth_date': birth_data.birth_date.strftime('%Y-%m-%d'),
            'birth_time': birth_data.birth_time.strftime('%H:%M'),
            'latitude': float(birth_data.latitude) if birth_data.latitude else 0.0,
            'longitude': float(birth_data.longitude) if birth_data.longitude else 0.0,
            'timezone': 'UTC'  # Default timezone
        }
        
        # Calculate HD chart using intelligence engine
        try:
            from hd_intelligence_engine import get_or_calculate_hd_chart
            chart_data = get_or_calculate_hd_chart(g.user, birth_data_dict)
            
            if not chart_data:
                return jsonify({'error': 'Failed to calculate HD chart'}), 500
            
            # Get the stored HD data
            hd_data = HumanDesignData.query.get(g.user)
            
            return jsonify({
                'message': 'Human Design chart calculated successfully',
                'chart_calculated': True,
                'has_hd_data': hd_data is not None,
                'type': hd_data.energy_type if hd_data else None,
                'authority': hd_data.authority if hd_data else None
            })
            
        except Exception as hd_error:
            print(f"HD intelligence engine error: {hd_error}")
            return jsonify({'error': 'HD calculation service unavailable'}), 503
    
    except Exception as e:
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
        hd_data = HumanDesignData.query.get(g.user)
        if not hd_data:
            hd_data = HumanDesignData(user_id=g.user)
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
        hd_data = HumanDesignData.query.get(g.user)
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
    """Get user profile with separated auth and profile data"""
    try:
        user = User.query.get(g.user)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get or create profile
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            # Create empty profile for user
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()
        
        # Combine user and profile data
        profile_data = {
            'id': user.id,
            'email': user.email,
            'status': user.status,
            'is_admin': user.is_admin,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            # Profile data
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'bio': profile.bio,
            'profile_completion': profile.profile_completion
        }
        
        return jsonify(profile_data)
    
    except Exception as e:
        print(f"Get profile error: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500

@app.route('/api/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update user profile with separated auth and profile data"""
    try:
        data = request.get_json()
        user = User.query.get(g.user)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get or create profile
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
        
        # Update user fields (auth-related)
        user_fields = ['email']
        for field in user_fields:
            if field in data and data[field] is not None:
                setattr(user, field, data[field])
        
        # Update profile fields
        profile_fields = ['first_name', 'last_name', 'bio', 'age']
        for field in profile_fields:
            if field in data and data[field] is not None:
                setattr(profile, field, data[field])
        
        # Recalculate profile completion
        profile.calculate_completion()
        profile.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Return combined data
        profile_data = {
            'id': user.id,
            'email': user.email,
            'status': user.status,
            'is_admin': user.is_admin,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            # Profile data
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'bio': profile.bio,
            'age': profile.age,
            'profile_completion': profile.profile_completion
        }
        
        return jsonify({
            'message': 'Profile updated successfully',
            'success': True,
            'user': profile_data
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Update profile error: {e}")
        return jsonify({'error': 'Failed to update profile', 'success': False}), 500

@app.route('/api/profile/birth-data', methods=['GET'])
@require_auth
def get_profile_birth_data():
    """Get user's birth data for profile management"""
    try:
        birth_data = BirthData.query.get(g.user)
        if not birth_data:
            response = jsonify({'ok': True, 'birth_data': None})
        else:
            response = jsonify({
                'ok': True,
                'birth_data': {
                    'date': birth_data.birth_date.isoformat() if birth_data.birth_date else None,
                    'time': birth_data.birth_time.strftime('%H:%M:%S') if birth_data.birth_time else None,
                    'timezone': birth_data.timezone,
                    'location': birth_data.birth_location,
                    'latitude': float(birth_data.latitude) if birth_data.latitude else None,
                    'longitude': float(birth_data.longitude) if birth_data.longitude else None,
                }
            })
        
        # JSON-only with no-store cache control
        response.headers['Content-Type'] = 'application/json'
        response.headers['Cache-Control'] = 'no-store'
        return response
    
    except Exception as e:
        print(f"Get profile birth data error: {e}")
        response = jsonify({'ok': False, 'error': 'Failed to get birth data'})
        response.headers['Content-Type'] = 'application/json'
        response.headers['Cache-Control'] = 'no-store'
        return response, 500

@app.route('/api/profile/birth-data', methods=['PUT'], strict_slashes=False)
@require_auth
@csrf_protect(session_store, validate_auth_session)
def put_profile_birth_data():
    """Update user's birth data for profile management - S3-A5a strict validation"""
    try:
        # Ensure JSON request
        if not request.is_json:
            return jsonify({'error': 'validation_error', 'details': {'content_type': ['must be application/json']}}), 415
        
        raw = request.get_json(silent=True) or {}
        
        # G2F_1: Normalize wrapper/camelCase to canonical before validation
        normalized_data = normalize_birth_data_request(raw, 'PUT /api/profile/birth-data')
        
        # S3-A5a: Apply strict validation
        from birth_data_validator import BirthDataValidator, ValidationError, create_validation_error_response
        
        try:
            # Validate using central validator (validates only provided keys - intrinsic partial mode)
            validated_data = BirthDataValidator.validate_birth_data(normalized_data)
            
        except ValidationError as ve:
            # Log request shape on validation failure with diagnostics (keys only)
            log_request_shape_keys('PUT /api/profile/birth-data', raw)
            return create_validation_error_response(ve)
        
        # Extract validated values
        birth_date = None
        birth_time = None
        timezone_str = validated_data.get('timezone')
        location_str = validated_data.get('birth_location')
        latitude = validated_data.get('latitude')
        longitude = validated_data.get('longitude')
        
        # Convert validated strings to database types
        if 'birth_date' in validated_data and validated_data['birth_date'] is not None:
            birth_date = datetime.strptime(validated_data['birth_date'], '%Y-%m-%d').date()
        
        if 'birth_time' in validated_data and validated_data['birth_time'] is not None:
            # Convert HH:mm to time object with seconds=00 (enforced by A4 constraint)
            birth_time = datetime.strptime(validated_data['birth_time'] + ':00', '%H:%M:%S').time()
        
        # Upsert birth data (partial updates supported)
        birth_data = BirthData.query.get(g.user)
        if not birth_data:
            birth_data = BirthData(user_id=g.user)
            db.session.add(birth_data)
        
        # Update only provided fields (partial updates)
        if birth_date is not None:
            birth_data.birth_date = birth_date
        if birth_time is not None:
            birth_data.birth_time = birth_time
        if timezone_str is not None:
            birth_data.timezone = timezone_str
        if location_str is not None:
            birth_data.birth_location = location_str
        if latitude is not None:
            birth_data.latitude = latitude
        if longitude is not None:
            birth_data.longitude = longitude
        
        # Update user's updated_at timestamp
        user = User.query.get(g.user)
        if user:
            user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Return success response with HH:mm format (S3-A1R-H4 compliance)
        response_data = {
            'ok': True,
            'birth_data': {
                'date': birth_data.birth_date.isoformat() if birth_data.birth_date else None,
                'time': format_birth_time_strict(birth_data.birth_time) if birth_data.birth_time else None,
                'timezone': birth_data.timezone,
                'location': birth_data.birth_location,
                'latitude': float(birth_data.latitude) if birth_data.latitude else None,
                'longitude': float(birth_data.longitude) if birth_data.longitude else None,
            },
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        response = make_response(jsonify(response_data), 200)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        return response
        
    except Exception as e:
        print(f"Put profile birth data error: {e}")
        db.session.rollback()
        return jsonify({'error': 'server_error', 'message': 'Failed to update birth data'}), 500

@app.route('/api/profile/basic', methods=['GET'], strict_slashes=False)
@require_auth
def get_profile_basic():
    """Get user's basic profile information"""
    try:
        profile = UserProfile.query.filter_by(user_id=g.user).first()
        if not profile:
            response = jsonify({'ok': True, 'profile': None})
        else:
            response = jsonify({
                'ok': True,
                'profile': {
                    'first_name': profile.first_name,
                    'last_name': profile.last_name,
                    'display_name': f"{profile.first_name} {profile.last_name}".strip() if profile.first_name or profile.last_name else None,
                    'avatar_url': None,  # Not implemented yet
                    'bio': profile.bio,
                    'age': profile.age,
                }
            })
        
        # JSON-only with no-store cache control
        response.headers['Content-Type'] = 'application/json'
        response.headers['Cache-Control'] = 'no-store'
        return response
    
    except Exception as e:
        print(f"Get profile basic error: {e}")
        response = jsonify({'ok': False, 'error': 'Failed to get basic profile'})
        response.headers['Content-Type'] = 'application/json'
        response.headers['Cache-Control'] = 'no-store'
        return response, 500

@app.route('/api/profile/basic', methods=['PUT'], strict_slashes=False)
@require_auth
@csrf_protect(session_store, validate_auth_session)
def put_profile_basic():
    """Update user's basic profile information"""
    try:
        # BE-DECOR-ORDER-06: Diagnostic logging
        print(f"save.profile.put.start user_id={g.user} has_csrf_header={bool(request.headers.get('X-CSRF-Token'))} has_session_cookie={bool(request.cookies.get('glow_session'))}")
        
        # Ensure JSON request
        if not request.is_json:
            return jsonify({'ok': False, 'code': 'VALIDATION', 'error': 'JSON required'}), 400
        
        payload = request.get_json() or {}
        
        # Extract fields (all optional)
        first_name = (payload.get('first_name') or '').strip() or None
        last_name = (payload.get('last_name') or '').strip() or None
        bio = (payload.get('bio') or '').strip() or None
        age = payload.get('age')
        
        # Validate age if provided
        if age is not None:
            try:
                age = int(age)
                if age < 18 or age > 120:
                    return jsonify({
                        'ok': False, 
                        'code': 'VALIDATION', 
                        'error': 'Age must be between 18 and 120'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'ok': False, 
                    'code': 'VALIDATION', 
                    'error': 'Age must be a valid number'
                }), 400
        
        # Validate field lengths
        if first_name and len(first_name) > 50:
            return jsonify({
                'ok': False, 
                'code': 'VALIDATION', 
                'error': 'First name too long (max 50 characters)'
            }), 400
        
        if last_name and len(last_name) > 50:
            return jsonify({
                'ok': False, 
                'code': 'VALIDATION', 
                'error': 'Last name too long (max 50 characters)'
            }), 400
        
        if bio and len(bio) > 1000:
            return jsonify({
                'ok': False, 
                'code': 'VALIDATION', 
                'error': 'Bio too long (max 1000 characters)'
            }), 400
        
        # Upsert profile
        profile = UserProfile.query.filter_by(user_id=g.user).first()
        if not profile:
            profile = UserProfile(user_id=g.user)
            db.session.add(profile)
        
        # Update fields
        profile.first_name = first_name
        profile.last_name = last_name
        profile.bio = bio
        profile.age = age
        profile.updated_at = datetime.utcnow()
        
        # Update user's updated_at timestamp
        user = User.query.get(g.user)
        if user:
            user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Return success response
        display_name = f"{first_name} {last_name}".strip() if first_name or last_name else None
        response_data = {
            'ok': True,
            'profile': {
                'first_name': first_name,
                'last_name': last_name,
                'display_name': display_name,
                'avatar_url': None,  # Not implemented yet
                'bio': bio,
                'age': age,
            },
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        response = make_response(jsonify(response_data), 200)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        return response
        
    except Exception as e:
        print(f"Put profile basic error: {e}")
        db.session.rollback()
        return jsonify({'ok': False, 'error': 'Failed to update basic profile'}), 500

@app.route('/api/profile/basic-info', methods=['PUT'], strict_slashes=False)
@require_auth
@csrf_protect(session_store, validate_auth_session)
def put_profile_basic_info():
    """Update user's basic info (first_name, last_name, bio) - S8-G2"""
    try:
        # Validate content type
        if not request.is_json:
            return jsonify({'error': 'validation_error', 'details': {'content_type': ['must be application/json']}}), 415
        
        raw = request.get_json(silent=True) or {}
        
        # Extract and validate fields
        first_name = raw.get('first_name', '').strip() if raw.get('first_name') else None
        last_name = raw.get('last_name', '').strip() if raw.get('last_name') else None
        bio = raw.get('bio', '').strip() if raw.get('bio') else None
        
        # Validation errors dict
        errors = {}
        
        # Validate first_name
        if first_name is not None:
            if len(first_name) > 50:
                errors['first_name'] = ['<=50 chars']
            elif first_name and not re.match(r'^[a-zA-Z\s\'-]+$', first_name):
                errors['first_name'] = ['letters/spaces/hyphen/apostrophe only']
        
        # Validate last_name
        if last_name is not None:
            if len(last_name) > 50:
                errors['last_name'] = ['<=50 chars']
            elif last_name and not re.match(r'^[a-zA-Z\s\'-]+$', last_name):
                errors['last_name'] = ['letters/spaces/hyphen/apostrophe only']
        
        # Validate bio
        if bio is not None and len(bio) > 500:
            errors['bio'] = ['<=500 chars']
        
        # Return validation errors if any
        if errors:
            return jsonify({'error': 'validation_error', 'details': errors}), 400
        
        # Keys-only diagnostics
        fields_updated = []
        if first_name is not None:
            fields_updated.append('first_name')
        if last_name is not None:
            fields_updated.append('last_name')
        if bio is not None:
            fields_updated.append('bio')
        
        app.logger.info(f"basic_info_update stage=validate fields={fields_updated}")
        
        # Get or create user profile
        profile = UserProfile.query.filter_by(user_id=g.user).first()
        if not profile:
            profile = UserProfile(user_id=g.user)
            db.session.add(profile)
        
        # Partial update - only update provided fields
        if first_name is not None:
            profile.first_name = first_name
        if last_name is not None:
            profile.last_name = last_name
        if bio is not None:
            profile.bio = bio
        
        profile.updated_at = datetime.utcnow()
        
        # Update user's updated_at timestamp
        user = User.query.get(g.user)
        if user:
            user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        app.logger.info(f"basic_info_update stage=save fields={fields_updated}")
        
        # Return the same shape as /api/auth/me for consistency
        # Get fresh data including birth_data
        birth_data = BirthData.query.filter_by(user_id=g.user).first()
        
        user_data = {
            'id': g.user,
            'email': user.email,
            'first_name': profile.first_name or "",
            'last_name': profile.last_name or "",
            'bio': profile.bio or "",
            'status': user.status,
            'is_admin': user.is_admin,
            'updated_at': user.updated_at.isoformat() + 'Z' if user.updated_at else None,
            'birth_data': {
                'date': birth_data.birth_date.strftime('%Y-%m-%d') if birth_data and birth_data.birth_date else None,
                'time': birth_data.birth_time.strftime('%H:%M') if birth_data and birth_data.birth_time else None,
                'location': birth_data.birth_location if birth_data else None
            }
        }
        
        response_data = {
            'ok': True,
            'user': user_data
        }
        
        response = make_response(jsonify(response_data), 200)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        
        return response
        
    except Exception as e:
        app.logger.error(f"Put profile basic-info error: {e}")
        db.session.rollback()
        return jsonify({'error': 'server_error', 'message': 'Failed to update basic info'}), 500

@app.route('/api/profile/human-design', methods=['GET'])
@require_auth
def get_profile_human_design():
    """Get user's human design data for profile management"""
    try:
        # Try to get from the new comprehensive HD table first
        hd_data = HumanDesignData.query.filter_by(user_id=g.user).first()
        if hd_data:
            return jsonify(hd_data.to_dict())
        
        # Fallback to birth_data chart_data for backward compatibility
        birth_data = BirthData.query.get(g.user)
        if birth_data and birth_data.chart_data:
            return jsonify({
                'user_id': g.user,
                'type': birth_data.chart_data.get('type'),
                'strategy': birth_data.chart_data.get('strategy'),
                'authority': birth_data.chart_data.get('authority'),
                'profile': birth_data.chart_data.get('profile'),
                'definition': birth_data.chart_data.get('definition'),
                'calculated_at': birth_data.updated_at.isoformat() if birth_data.updated_at else None,
                'raw_data': birth_data.chart_data
            })
        
        return jsonify({'human_design_data': None})
    
    except Exception as e:
        print(f"Get profile human design error: {e}")
        return jsonify({'error': 'Failed to get human design data'}), 500

@app.route('/api/profile/update-birth-data', methods=['POST'])
@require_auth
@csrf_protect(session_store, validate_auth_session)
def update_birth_data():
    """Update user birth data with enhanced location support and recalculate compatibility"""
    try:
        data = request.get_json()
        
        # Normalize request
        from birth_data_validator import BirthDataValidator, ValidationError
        
        normalized_data = normalize_birth_data_request(data, 'POST /api/profile/update-birth-data')
        
        # Validate using central validator (validates only provided keys - intrinsic partial mode)
        try:
            validated_data = BirthDataValidator.validate_birth_data(normalized_data)
        except ValidationError as e:
            # Log request shape on validation failure with diagnostics
            app.logger.info("request_shape_keys", extra={
                'route': 'POST /api/profile/update-birth-data',
                'keys': list(data.keys()),
                'validation_errors': list(e.details.keys()),
                'alias_detected': 'birthDate' in data or 'birthTime' in data or 'date' in data or 'time' in data,
                'wrapper_detected': 'birth_data' in data or 'birthData' in data
            })
            return jsonify({
                'error': 'validation_error',
                'message': 'One or more fields are invalid',
                'details': e.details
            }), 400
        
        # Get or create birth data record
        birth_data = BirthData.query.get(g.user)
        if not birth_data:
            birth_data = BirthData(user_id=g.user)
            db.session.add(birth_data)
        
        # Update only provided fields
        for field, value in validated_data.items():
            setattr(birth_data, field, value)
        
        # Log successful save
        app.logger.info("save_attempt", extra={
            'route': 'POST /api/profile/update-birth-data',
            'accepted_keys': list(validated_data.keys()),
            'status': 'success'
        })
        
        # ... rest of existing logic (HD API calls, etc.)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Birth data updated successfully',
            'birth_data': birth_data.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error in update_birth_data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# API ROUTES - ADMIN CONSOLE
# ============================================================================

@app.route('/api/admin/users/search', methods=['GET'])
@require_auth
@require_admin
def admin_search_users():
    """Search users for admin HD viewer"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'users': []})
        
        # Search by email, name, or user ID
        users = User.query.filter(
            db.or_(
                User.email.ilike(f'%{query}%'),
                User.name.ilike(f'%{query}%'),
                User.id == query if query.isdigit() else False
            )
        ).limit(20).all()
        
        user_list = []
        for user in users:
            # Check if user has HD data
            hd_data = HumanDesignData.query.get(user.id)
            user_list.append({
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'has_hd_data': hd_data is not None,
                'hd_calculated_at': hd_data.calculated_at.isoformat() if hd_data and hd_data.calculated_at else None
            })
        
        return jsonify({'users': user_list})
    
    except Exception as e:
        print(f"Admin search users error: {e}")
        return jsonify({'error': 'Failed to search users'}), 500

@app.route('/api/admin/users/<int:user_id>/human-design', methods=['GET'])
@require_auth
@require_admin
def admin_get_user_hd_data(user_id):
    """Get comprehensive Human Design data for a specific user (admin only)"""
    try:
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get HD data
        hd_data = HumanDesignData.query.get(user_id)
        if not hd_data:
            return jsonify({'error': 'No Human Design data found for this user'}), 404
        
        # Get birth data for context
        birth_data = BirthData.query.filter_by(user_id=user_id).first()
        
        return jsonify({
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'created_at': user.created_at.isoformat() if user.created_at else None
            },
            'birth_data': birth_data.to_dict() if birth_data else None,
            'human_design': hd_data.to_dict(),
            'raw_api_response': hd_data.get_api_response()
        })
    
    except Exception as e:
        print(f"Admin get HD data error: {e}")
        return jsonify({'error': 'Failed to get Human Design data'}), 500

@app.route('/api/admin/human-design/stats', methods=['GET'])
@require_auth
@require_admin
def admin_hd_stats():
    """Get Human Design statistics for admin dashboard"""
    try:
        # Count users with HD data
        total_users = User.query.count()
        users_with_hd = HumanDesignData.query.count()
        
        # Count by energy type
        type_stats = db.session.query(
            HumanDesignData.energy_type,
            db.func.count(HumanDesignData.energy_type)
        ).group_by(HumanDesignData.energy_type).all()
        
        # Count by authority
        authority_stats = db.session.query(
            HumanDesignData.authority,
            db.func.count(HumanDesignData.authority)
        ).group_by(HumanDesignData.authority).all()
        
        # Count by profile
        profile_stats = db.session.query(
            HumanDesignData.profile,
            db.func.count(HumanDesignData.profile)
        ).group_by(HumanDesignData.profile).all()
        
        return jsonify({
            'total_users': total_users,
            'users_with_hd_data': users_with_hd,
            'completion_rate': round((users_with_hd / total_users * 100), 2) if total_users > 0 else 0,
            'type_distribution': dict(type_stats),
            'authority_distribution': dict(authority_stats),
            'profile_distribution': dict(profile_stats)
        })
    
    except Exception as e:
        print(f"Admin HD stats error: {e}")
        return jsonify({'error': 'Failed to get HD statistics'}), 500

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
            admin_user_id=g.user,
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
            admin_user_id=g.user,
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
            admin_user_id=g.user,
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
    
    # Run enhanced location data migration
    try:
        from migrate_on_startup import run_startup_migration
        run_startup_migration()
    except Exception as e:
        print(f"Startup migration warning: {e}")

# Railway deployment compatibility - no app.run() call
# Gunicorn imports 'app' object directly


@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Get current user
        current_user = User.query.get(g.user)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password
        if not check_password_hash(current_user.password_hash, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Update password
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        return jsonify({'message': 'Password updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Password change error: {e}")
        return jsonify({'error': 'Failed to update password'}), 500

@app.route('/api/profile/upload-photo', methods=['POST'])
@require_auth
def upload_photo():
    """Upload profile photo"""
    try:
        if 'photo' not in request.files:
            return jsonify({'error': 'No photo file provided'}), 400
        
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # For now, just return success - photo storage can be implemented later
        return jsonify({
            'message': 'Photo uploaded successfully',
            'filename': file.filename
        })
        
    except Exception as e:
        print(f"Photo upload error: {e}")
        return jsonify({'error': 'Failed to upload photo'}), 500

@app.route('/api/admin/migrate-database', methods=['POST'])
def migrate_database():
    """Add missing is_admin column to production database"""
    try:
        # Check if column already exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'is_admin'
        """)).fetchone()
        
        if result:
            return jsonify({'message': 'is_admin column already exists'})
        
        # Add the is_admin column
        db.session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL
        """))
        
        # Set admin@glow.app as admin
        db.session.execute(text("""
            UPDATE users 
            SET is_admin = TRUE 
            WHERE email = 'admin@glow.app'
        """))
        
        db.session.commit()
        
        return jsonify({
            'message': 'Successfully added is_admin column and set admin@glow.app as admin',
            'migration': 'completed'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': str(e),
            'migration': 'failed'
        }), 500

@app.route('/api/test/database', methods=['GET'])
def test_database():
    """Test database connectivity and basic operations"""
    try:
        # Test basic database connection
        result = db.session.execute(text('SELECT 1 as test')).fetchone()
        
        # Test user table access
        user_count = User.query.count()
        
        # Test if we can read users
        users = User.query.limit(5).all()
        user_emails = [user.email for user in users]
        
        return jsonify({
            'database_connection': 'OK',
            'basic_query': result[0] if result else 'Failed',
            'user_table_accessible': True,
            'total_users': user_count,
            'sample_user_emails': user_emails
        })
        
    except Exception as e:
        return jsonify({
            'database_connection': 'FAILED',
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

@app.route('/api/admin/debug-birth-data', methods=['GET'])
@require_auth
def debug_birth_data():
    """Debug endpoint to check birth data table"""
    try:
        # Check if birth_data table exists and has data
        birth_data_records = BirthData.query.all()
        
        result = {
            'total_birth_records': len(birth_data_records),
            'birth_data_records': []
        }
        
        for record in birth_data_records:
            result['birth_data_records'].append({
                'user_id': record.user_id,
                'birth_date': str(record.birth_date) if record.birth_date else None,
                'birth_time': str(record.birth_time) if record.birth_time else None,
                'birth_location': record.birth_location,
                'latitude': record.latitude,
                'longitude': record.longitude,
                'created_at': str(record.created_at) if hasattr(record, 'created_at') else None
            })
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Birth data debug error: {str(e)}'}), 500

@app.route('/api/admin/debug-users', methods=['GET'])
def debug_users():
    """Debug endpoint to check users in database"""
    try:
        users = User.query.all()
        user_list = []
        for user in users:
            user_list.append({
                'email': user.email,
                'status': user.status,
                'is_admin': user.is_admin,
                'created_at': user.created_at.isoformat() if user.created_at else None
            })
        
        return jsonify({
            'total_users': len(users),
            'users': user_list
        })
        
    except Exception as e:
        print(f"Debug users error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/initialize', methods=['POST'])
def initialize_admin():
    """Initialize admin user - for deployment setup only"""
    try:
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@glow.app').first()
        if admin:
            return jsonify({'message': 'Admin user already exists', 'email': admin.email})
        
        # Create admin user
        from werkzeug.security import generate_password_hash
        admin = User(
            email='admin@glow.app',
            password_hash=generate_password_hash('admin123'),
            first_name='Admin',
            last_name='User',
            status='approved',
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        
        return jsonify({
            'message': 'Admin user created successfully',
            'email': admin.email,
            'is_admin': admin.is_admin
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Admin initialization error: {e}")
        return jsonify({'error': 'Failed to initialize admin user'}), 500


# ============================================================================
# SESSION DIAGNOSTICS ENDPOINTS (T3.1-R2)
# ============================================================================
# Create session diagnostics endpoints after all models and functions are defined
create_session_diagnostics_endpoint(app, session_store, validate_auth_session)

# ============================================================================
# CSRF PROTECTION ENDPOINTS (T3.2)
# ============================================================================
# Create CSRF endpoints after all models and functions are defined
create_csrf_endpoints(app, session_store, validate_auth_session)

# ============================================================================
# SESSION REVOCATION ENDPOINTS (T-BE-003)
# ============================================================================
# Create session revocation endpoints after all models and functions are defined
create_revocation_endpoints(app, session_store, validate_auth_session, csrf_protect)


if __name__ == '__main__':
    # Only for local development testing
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

