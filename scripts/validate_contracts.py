#!/usr/bin/env python3
"""
Contract drift validator - compares live API responses against schema contracts
"""
import json
import sys
import os
import subprocess
from pathlib import Path

def fetch_live_data(base_url, jar_path):
    """Fetch live API data using curl"""
    # Login first
    login_cmd = [
        'curl', '-sS', '-c', jar_path, 
        '-H', 'Content-Type: application/json',
        '-X', 'POST', f'{base_url}/api/auth/login',
        '--data', '{"email":"admin@glow.app","password":"admin123"}'
    ]
    subprocess.run(login_cmd, capture_output=True, check=True)
    
    # Fetch auth/me
    auth_cmd = ['curl', '-sS', '-b', jar_path, f'{base_url}/api/auth/me']
    auth_result = subprocess.run(auth_cmd, capture_output=True, text=True, check=True)
    auth_data = json.loads(auth_result.stdout)
    
    # Fetch profile/birth-data
    profile_cmd = ['curl', '-sS', '-b', jar_path, f'{base_url}/api/profile/birth-data']
    profile_result = subprocess.run(profile_cmd, capture_output=True, text=True, check=True)
    profile_data = json.loads(profile_result.stdout)
    
    return auth_data, profile_data

def validate_against_schema(data, schema):
    """Enhanced schema validation - checks required fields, types, and unknown fields"""
    def validate_object(obj, schema_obj, path=""):
        if schema_obj.get('type') != 'object':
            return True, "valid"
            
        required = schema_obj.get('required', [])
        properties = schema_obj.get('properties', {})
        
        # Check required fields
        for field in required:
            if field not in obj:
                return False, f"Missing required field: {path}.{field}" if path else f"Missing required field: {field}"
        
        # Check for unknown fields (drift detection)
        unknown_fields = []
        for field in obj.keys():
            if field not in properties:
                field_path = f"{path}.{field}" if path else field
                unknown_fields.append(field_path)
        
        if unknown_fields:
            return False, f"Unknown fields detected: {', '.join(unknown_fields)}"
        
        # Check field types and nested objects
        for field, value in obj.items():
            if field in properties:
                prop_schema = properties[field]
                expected_type = prop_schema.get('type')
                field_path = f"{path}.{field}" if path else field
                
                # Handle nullable types
                if isinstance(expected_type, list) and 'null' in expected_type:
                    if value is None:
                        continue
                    # Get the non-null type
                    expected_type = [t for t in expected_type if t != 'null'][0]
                
                if expected_type == 'string' and not isinstance(value, str):
                    return False, f"Field {field_path} should be string, got {type(value).__name__}"
                elif expected_type == 'number' and not isinstance(value, (int, float)):
                    return False, f"Field {field_path} should be number, got {type(value).__name__}"
                elif expected_type == 'integer' and not isinstance(value, int):
                    return False, f"Field {field_path} should be integer, got {type(value).__name__}"
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    return False, f"Field {field_path} should be boolean, got {type(value).__name__}"
                elif expected_type == 'object' and isinstance(value, dict):
                    nested_result = validate_object(value, prop_schema, field_path)
                    if nested_result[0] is not True:
                        return nested_result
                elif expected_type == 'array' and not isinstance(value, list):
                    return False, f"Field {field_path} should be array, got {type(value).__name__}"
        
        return True, "valid"
    
    return validate_object(data, schema)

def main():
    base_url = os.environ.get('BASE_URL', 'https://www.glowme.io')
    jar_path = '/tmp/contract_validator.jar'
    
    # Load schemas
    schema_dir = Path('contracts/schema/current')
    
    try:
        with open(schema_dir / 'auth_me.json') as f:
            auth_schema = json.load(f)
        with open(schema_dir / 'profile.json') as f:
            profile_schema = json.load(f)
    except FileNotFoundError as e:
        print(f"Schema file not found: {e}")
        sys.exit(1)
    
    try:
        # Fetch live data
        auth_data, profile_data = fetch_live_data(base_url, jar_path)
        
        # Validate auth/me
        print("Validating /api/auth/me response...")
        auth_result, auth_msg = validate_against_schema(auth_data, auth_schema)
        if auth_result:
            print("✅ auth/me: VALID - No contract drift detected")
        else:
            print(f"❌ auth/me: INVALID - {auth_msg}")
            print(f"Response data: {json.dumps(auth_data, indent=2)}")
            sys.exit(1)
        
        # Validate profile
        print("Validating /api/profile/birth-data response...")
        profile_result, profile_msg = validate_against_schema(profile_data, profile_schema)
        if profile_result:
            print("✅ profile: VALID - No contract drift detected")
        else:
            print(f"❌ profile: INVALID - {profile_msg}")
            print(f"Response data: {json.dumps(profile_data, indent=2)}")
            sys.exit(1)
            
        print("\n🎉 All contracts validated successfully - No drift detected!")
            
    except Exception as e:
        print(f"Validation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

