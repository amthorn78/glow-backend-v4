#!/usr/bin/env python3
"""
User Profiles Database Migration Script
Separates profile data from authentication data for better architecture
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path to import models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_database_url():
    """Get database URL from environment or use default"""
    return os.getenv('DATABASE_URL', 'sqlite:///glow.db')

def create_user_profiles_table(engine):
    """Create the user_profiles table"""
    print("Creating user_profiles table...")
    
    with engine.connect() as conn:
        # Create user_profiles table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            bio TEXT,
            age INTEGER,
            profile_completion INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
        
        conn.execute(text(create_table_sql))
        conn.commit()
        print("✅ user_profiles table created successfully")

def migrate_existing_data(engine):
    """Migrate existing profile data from users table to user_profiles table"""
    print("Migrating existing profile data...")
    
    with engine.connect() as conn:
        # Check if users have profile data to migrate
        check_columns_sql = "PRAGMA table_info(users);"
        result = conn.execute(text(check_columns_sql))
        columns = [row[1] for row in result.fetchall()]
        
        has_first_name = 'first_name' in columns
        has_last_name = 'last_name' in columns
        
        if not (has_first_name or has_last_name):
            print("ℹ️  No profile data to migrate from users table")
            return
        
        # Get all users with profile data
        if has_first_name and has_last_name:
            select_sql = "SELECT id, first_name, last_name, created_at FROM users WHERE first_name IS NOT NULL OR last_name IS NOT NULL;"
        elif has_first_name:
            select_sql = "SELECT id, first_name, NULL as last_name, created_at FROM users WHERE first_name IS NOT NULL;"
        elif has_last_name:
            select_sql = "SELECT id, NULL as first_name, last_name, created_at FROM users WHERE last_name IS NOT NULL;"
        
        users_result = conn.execute(text(select_sql))
        users_to_migrate = users_result.fetchall()
        
        if not users_to_migrate:
            print("ℹ️  No users with profile data found")
            return
        
        # Insert profile data for each user
        migrated_count = 0
        for user in users_to_migrate:
            user_id, first_name, last_name, created_at = user
            
            # Calculate basic profile completion
            completion = 0
            if first_name: completion += 25
            if last_name: completion += 25
            # Reserve 50% for other profile fields (birth data, bio, etc.)
            
            insert_sql = """
            INSERT OR IGNORE INTO user_profiles (user_id, first_name, last_name, profile_completion, created_at, updated_at)
            VALUES (:user_id, :first_name, :last_name, :completion, :created_at, :updated_at);
            """
            
            conn.execute(text(insert_sql), {
                'user_id': user_id,
                'first_name': first_name,
                'last_name': last_name,
                'completion': completion,
                'created_at': created_at,
                'updated_at': datetime.utcnow()
            })
            migrated_count += 1
        
        conn.commit()
        print(f"✅ Migrated profile data for {migrated_count} users")

def validate_migration(engine):
    """Validate that migration was successful"""
    print("Validating migration...")
    
    with engine.connect() as conn:
        # Count users and profiles
        users_count = conn.execute(text("SELECT COUNT(*) FROM users;")).fetchone()[0]
        profiles_count = conn.execute(text("SELECT COUNT(*) FROM user_profiles;")).fetchone()[0]
        
        print(f"📊 Users: {users_count}, Profiles: {profiles_count}")
        
        # Check for users with profile data
        users_with_names = conn.execute(text("""
            SELECT COUNT(*) FROM users 
            WHERE first_name IS NOT NULL OR last_name IS NOT NULL;
        """)).fetchone()[0]
        
        if users_with_names > 0:
            print(f"✅ Found {users_with_names} users with profile data")
            
            # Verify migration
            migrated_profiles = conn.execute(text("""
                SELECT COUNT(*) FROM user_profiles 
                WHERE first_name IS NOT NULL OR last_name IS NOT NULL;
            """)).fetchone()[0]
            
            print(f"✅ Migrated {migrated_profiles} profiles with name data")
            
            if migrated_profiles >= users_with_names:
                print("✅ Migration validation successful!")
            else:
                print("⚠️  Migration may be incomplete")
        else:
            print("ℹ️  No existing profile data found to validate")

def main():
    """Run the migration"""
    print("🚀 Starting User Profiles Database Migration")
    print("=" * 50)
    
    try:
        # Get database connection
        database_url = get_database_url()
        print(f"📊 Database: {database_url}")
        
        engine = create_engine(database_url)
        
        # Run migration steps
        create_user_profiles_table(engine)
        migrate_existing_data(engine)
        validate_migration(engine)
        
        print("=" * 50)
        print("✅ User Profiles Migration Completed Successfully!")
        print("\n🎯 Next Steps:")
        print("1. Update backend models to use UserProfile")
        print("2. Update API endpoints")
        print("3. Update frontend integration")
        print("4. Test thoroughly")
        print("5. Remove old profile fields from users table")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

