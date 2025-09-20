-- Database Schema Dump for HD Engine Integration
-- Generated at: 2025-09-20T22:42:38.964223Z
-- Tables: user_priorities, compatibility_matrix, users, birth_data, human_design_data, admin_action_log, email_notifications, user_sessions, user_profiles, user_resonance_prefs, user_resonance_signals_private, user_preferences

-- Table: user_priorities
CREATE TABLE user_priorities (
    user_id INTEGER NOT NULL,
    love_priority SMALLINT,
    intimacy_priority SMALLINT,
    communication_priority SMALLINT,
    friendship_priority SMALLINT,
    collaboration_priority SMALLINT,
    lifestyle_priority SMALLINT,
    decisions_priority SMALLINT,
    support_priority SMALLINT,
    growth_priority SMALLINT,
    space_priority SMALLINT
);


-- Table: compatibility_matrix
CREATE TABLE compatibility_matrix (
    user_a_id INTEGER NOT NULL,
    user_b_id INTEGER NOT NULL,
    love_score SMALLINT,
    intimacy_score SMALLINT,
    communication_score SMALLINT,
    friendship_score SMALLINT,
    collaboration_score SMALLINT,
    lifestyle_score SMALLINT,
    decisions_score SMALLINT,
    support_score SMALLINT,
    growth_score SMALLINT,
    space_score SMALLINT,
    overall_score SMALLINT,
    calculated_at TIMESTAMP
);


-- Table: users
CREATE TABLE users (
    id INTEGER NOT NULL DEFAULT nextval('users_id_seq'::regclass),
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(20),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    profile_version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX ix_users_email ON users (email);

-- Table: birth_data
CREATE TABLE birth_data (
    user_id INTEGER NOT NULL,
    birth_date DATE,
    birth_time TIME,
    birth_location VARCHAR(255),
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    data_consent BOOLEAN,
    sharing_consent BOOLEAN,
    location_display_name TEXT,
    location_country VARCHAR(100),
    location_state VARCHAR(100),
    location_city VARCHAR(100),
    location_importance NUMERIC(5, 4),
    location_osm_id BIGINT,
    location_osm_type VARCHAR(20),
    timezone VARCHAR(50),
    location_source VARCHAR(20) DEFAULT 'manual'::character varying,
    location_verified BOOLEAN DEFAULT false
);

CREATE INDEX idx_birth_data_city ON birth_data (location_city);
CREATE INDEX idx_birth_data_country ON birth_data (location_country);
CREATE INDEX idx_birth_data_source ON birth_data (location_source);
CREATE INDEX idx_birth_data_verified ON birth_data (location_verified);

-- Table: human_design_data
CREATE TABLE human_design_data (
    user_id INTEGER NOT NULL,
    chart_data TEXT,
    energy_type VARCHAR(50),
    strategy VARCHAR(100),
    authority VARCHAR(100),
    profile VARCHAR(20),
    api_response TEXT,
    calculated_at TIMESTAMP
);


-- Table: admin_action_log
CREATE TABLE admin_action_log (
    id INTEGER NOT NULL DEFAULT nextval('admin_action_log_id_seq'::regclass),
    admin_user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    target_user_id INTEGER,
    details TEXT,
    timestamp TIMESTAMP
);


-- Table: email_notifications
CREATE TABLE email_notifications (
    id INTEGER NOT NULL DEFAULT nextval('email_notifications_id_seq'::regclass),
    user_id INTEGER,
    email_type VARCHAR(50) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    sent_at TIMESTAMP,
    delivery_status VARCHAR(20)
);


-- Table: user_sessions
CREATE TABLE user_sessions (
    id INTEGER NOT NULL DEFAULT nextval('user_sessions_id_seq'::regclass),
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) NOT NULL,
    created_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX ix_user_sessions_session_token ON user_sessions (session_token);

-- Table: user_profiles
CREATE TABLE user_profiles (
    id INTEGER NOT NULL DEFAULT nextval('user_profiles_id_seq'::regclass),
    user_id INTEGER NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    bio TEXT,
    age INTEGER,
    profile_completion INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    display_name VARCHAR(100),
    avatar_url VARCHAR(500)
);

CREATE INDEX user_profiles_user_id_key ON user_profiles (user_id);

-- Table: user_resonance_prefs
CREATE TABLE user_resonance_prefs (
    user_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    weights JSON NOT NULL,
    facets JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);


-- Table: user_resonance_signals_private
CREATE TABLE user_resonance_signals_private (
    user_id INTEGER NOT NULL,
    decision_mode VARCHAR(50) NOT NULL,
    interaction_mode VARCHAR(50) NOT NULL,
    connection_style VARCHAR(50) NOT NULL,
    bridges_count SMALLINT NOT NULL,
    emotion_signal BOOLEAN NOT NULL,
    work_energy BOOLEAN NOT NULL,
    will_signal BOOLEAN NOT NULL,
    expression_signal BOOLEAN NOT NULL,
    mind_signal BOOLEAN NOT NULL,
    role_pattern VARCHAR(50) NOT NULL,
    tempo_pattern VARCHAR(50),
    identity_openness BOOLEAN NOT NULL,
    trajectory_code VARCHAR(20),
    confidence JSON,
    computed_at TIMESTAMP NOT NULL
);


-- Table: user_preferences
CREATE TABLE user_preferences (
    user_id INTEGER NOT NULL,
    prefs JSON,
    updated_at TIMESTAMP
);


