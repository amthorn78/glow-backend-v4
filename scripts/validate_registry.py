#!/usr/bin/env python
import json
import os
import re
import sys
from jsonschema import validate, ValidationError

# Constants
REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__),
    '..',
    'contracts',
    'registry',
    'v1.json'
)
SNAKE_CASE_PATTERN = re.compile(r'^[a-z0-9_]+$')

def get_all_keys(data, parent_key=''):
    """Recursively get all keys from a nested dictionary."""
    keys = set()
    for k, v in data.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        keys.add(new_key)
        if isinstance(v, dict):
            keys.update(get_all_keys(v, new_key))
    return keys

def validate_snake_case(data):
    """Validate that all keys in the dictionary are snake_case."""
    errors = []
    properties = data.get('properties', {})
    for key in get_all_keys(properties):
        for key_segment in key.split('.'):
             if not SNAKE_CASE_PATTERN.match(key_segment):
                errors.append(f"Validation Error: Key segment '{key_segment}' in '{key}' is not snake_case.")
    return errors

def compare_registries(base_registry, head_registry):
    """Compare two registry files and return a key-path-only diff."""
    base_keys = get_all_keys(base_registry.get('schema', {}).get('properties', {}))
    head_keys = get_all_keys(head_registry.get('schema', {}).get('properties', {}))

    added_keys = head_keys - base_keys
    removed_keys = base_keys - head_keys

    diffs = []
    if added_keys:
        for key in sorted(list(added_keys)):
            diffs.append(f"+ {key}")
    if removed_keys:
        for key in sorted(list(removed_keys)):
            diffs.append(f"- {key}")

    return diffs

def main(registry_path=REGISTRY_PATH):
    """Main validation function."""
    try:
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    except FileNotFoundError:
        print(f"Error: Registry file not found at {registry_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {registry_path}", file=sys.stderr)
        return 1

    schema = registry.get('schema')
    if not schema:
        print("Error: Registry does not contain a 'schema' key.", file=sys.stderr)
        return 1

    # 1. Validate snake_case keys
    snake_case_errors = validate_snake_case(schema)
    if snake_case_errors:
        for error in snake_case_errors:
            print(error, file=sys.stderr)
        return 1

    # 2. Validate against a sample payload to enforce schema rules
    try:
        validate(instance={"preferred_pace": "slow"}, schema=schema)
    except ValidationError as e:
        print(f"Schema validation failed for a valid instance: {e.message}", file=sys.stderr)
        return 1

    try:
        validate(instance={"unknown_field": "test"}, schema=schema)
        print("Schema Error: 'additionalProperties' is not false. Unknown keys are allowed.", file=sys.stderr)
        return 1
    except ValidationError as e:
        if "'unknown_field' was unexpected" not in e.message:
             print(f"Schema validation failed unexpectedly for an invalid instance: {e.message}", file=sys.stderr)
             return 1

    print("Registry validation successful.")
    return 0

if __name__ == "__main__":
    if len(sys.argv) == 3:
        base_file_path = sys.argv[1]
        head_file_path = sys.argv[2]
        try:
            with open(base_file_path, 'r') as f:
                base_registry = json.load(f)
            with open(head_file_path, 'r') as f:
                head_registry = json.load(f)

            diff = compare_registries(base_registry, head_registry)
            if diff:
                print("Registry key-path diff detected:", file=sys.stderr)
                for line in diff:
                    print(line, file=sys.stderr)
                sys.exit(1)
            else:
                print("No registry key changes detected.")
                sys.exit(0)

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error comparing registries: {e}", file=sys.stderr)
            sys.exit(1)
    elif len(sys.argv) == 2:
        sys.exit(main(sys.argv[1]))
    else:
        sys.exit(main())

