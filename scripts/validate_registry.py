#!/usr/bin/env python
import json
import os
import re
import sys

# Constants
REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__),
    '..',
    'contracts',
    'registry',
    'v1.json'
)
SNAKE_CASE_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
ALLOWED_SPEC_KEYS = {'type', 'values'}

def validate_registry(registry):
    errors = []

    # Rule: registry_version === "v1"
    if registry.get('registry_version') != 'v1':
        errors.append('ERROR: registry_version must be "v1"')

    # Rule: fields exists and is an object/dict
    fields = registry.get('fields')
    if not isinstance(fields, dict):
        errors.append('ERROR: "fields" key must be an object')
        return errors # Stop if fields is not a dict

    for field_name, spec in fields.items():
        # Rule: field name must be snake_case
        if not SNAKE_CASE_PATTERN.match(field_name):
            errors.append(f"ERROR: field name not snake_case: {field_name}")

        # Rule: spec.type is valid
        spec_type = spec.get('type')
        if spec_type not in ["enum", "string", "number", "boolean"]:
            errors.append(f"ERROR: invalid type '{spec_type}' in fields.{field_name}")

        # Rule: enum spec validation
        if spec_type == "enum":
            values = spec.get('values')
            if not isinstance(values, list) or not values:
                errors.append(f"ERROR: enum.values empty in fields.{field_name}")
            else:
                for value in values:
                    if not SNAKE_CASE_PATTERN.match(value):
                        errors.append(f"ERROR: enum value not snake_case: '{value}' in fields.{field_name}")

        # Rule: No unknown keys in spec
        for key in spec.keys():
            if key not in ALLOWED_SPEC_KEYS:
                errors.append(f"ERROR: unknown key '{key}' in fields.{field_name}")

    return errors

def main(file_path=None):
    registry_path = file_path or REGISTRY_PATH
    try:
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {registry_path}", file=sys.stderr)
        return 2
    except json.JSONDecodeError:
        print(f"Invalid JSON in file: {registry_path}", file=sys.stderr)
        return 2

    errors = validate_registry(registry)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("Registry validation successful.")
    return 0

if __name__ == "__main__":
    # Support --file optional arg
    if '--file' in sys.argv:
        try:
            file_index = sys.argv.index('--file')
            file_path = sys.argv[file_index + 1]
            sys.exit(main(file_path=file_path))
        except (IndexError, FileNotFoundError):
            print("Error: --file argument requires a valid file path.", file=sys.stderr)
            sys.exit(2)
    else:
        sys.exit(main())

