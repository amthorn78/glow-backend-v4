#!/usr/bin/env python3
"""
Registry Validator v1.1
Validates field registry against schema and enforces hard rules.
Produces deterministic artifacts for build-time validation.
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

def load_schema(schema_path):
    """Load JSON schema from file"""
    with open(schema_path, 'r') as f:
        return json.load(f)

def load_registry(registry_path):
    """Load field registry from file"""
    with open(registry_path, 'r') as f:
        return json.load(f)

def validate_json_schema(registry_data, schema_data):
    """Basic JSON schema validation"""
    try:
        import jsonschema
        jsonschema.validate(registry_data, schema_data)
        return True, []
    except ImportError:
        # Fallback validation without jsonschema library
        return validate_basic_structure(registry_data, schema_data)
    except Exception as e:
        return False, [f"Schema validation error: {str(e)}"]

def validate_basic_structure(registry_data, schema_data):
    """Basic structure validation without jsonschema library"""
    errors = []
    
    if not isinstance(registry_data, list):
        errors.append("Registry must be an array")
        return False, errors
    
    required_fields = ["id", "owner", "exposure", "status", "writable", "read_path", "writer", "display", "deps"]
    
    for i, field in enumerate(registry_data):
        if not isinstance(field, dict):
            errors.append(f"Field {i} must be an object")
            continue
            
        for req_field in required_fields:
            if req_field not in field:
                errors.append(f"Field {field.get('id', i)} missing required field: {req_field}")
    
    return len(errors) == 0, errors

def validate_hard_rules(registry_data):
    """Validate hard business rules"""
    errors = []
    order_by_group = defaultdict(list)
    
    for field in registry_data:
        field_id = field.get('id', 'unknown')
        
        # Rule: If control is select/multi_select, enum must exist and be non-empty
        display = field.get('display', {})
        control = display.get('control')
        if control in ['select', 'multi_select']:
            enum_values = field.get('enum', [])
            if not enum_values:
                errors.append(f"Field '{field_id}': {control} control requires non-empty enum")
        
        # Rule: owner must be in allowed set
        owner = field.get('owner')
        if owner not in ['be', 'fe', 'hd']:
            errors.append(f"Field '{field_id}': invalid owner '{owner}', must be be|fe|hd")
        
        # Rule: exposure must be in allowed set
        exposure = field.get('exposure')
        if exposure not in ['api', 'ui', 'hd']:
            errors.append(f"Field '{field_id}': invalid exposure '{exposure}', must be api|ui|hd")
        
        # Rule: status must be in allowed set
        status = field.get('status')
        if status not in ['active', 'parked', 'deprecated']:
            errors.append(f"Field '{field_id}': invalid status '{status}', must be active|parked|deprecated")
        
        # Rule: control must be in allowed set
        if control not in ['text', 'date', 'time', 'select', 'multi_select']:
            errors.append(f"Field '{field_id}': invalid control '{control}', must be text|date|time|select|multi_select")
        
        # Rule: deps entries must match env var pattern
        deps = field.get('deps', [])
        for dep in deps:
            if not dep or not dep[0].isupper() or not all(c.isupper() or c.isdigit() or c == '_' for c in dep):
                errors.append(f"Field '{field_id}': invalid dep '{dep}', must match ^[A-Z][A-Z0-9_]*$")
        
        # Rule: enum values must be snake_case strings
        enum_values = field.get('enum', [])
        for enum_val in enum_values:
            if not isinstance(enum_val, str) or not all(c.islower() or c.isdigit() or c == '_' for c in enum_val):
                errors.append(f"Field '{field_id}': enum value '{enum_val}' must be snake_case string")
        
        # Collect order info for uniqueness check
        group = display.get('group')
        order = display.get('order')
        if group and order is not None:
            order_by_group[group].append((order, field_id))
    
    # Rule: display.order must be unique within its group
    for group, orders in order_by_group.items():
        order_counts = defaultdict(list)
        for order, field_id in orders:
            order_counts[order].append(field_id)
        
        for order, field_ids in order_counts.items():
            if len(field_ids) > 1:
                errors.append(f"Group '{group}': duplicate order {order} in fields: {', '.join(field_ids)}")
    
    return errors

def generate_report(registry_data, validation_errors):
    """Generate deterministic registry report"""
    report_lines = []
    
    # Header
    report_lines.append("Field Registry v1.1 Validation Report")
    report_lines.append("=" * 40)
    report_lines.append("")
    
    # Validation status
    if validation_errors:
        report_lines.append("VALIDATION: FAILED")
        report_lines.append("Errors:")
        for error in sorted(validation_errors):
            report_lines.append(f"  - {error}")
        report_lines.append("")
    else:
        report_lines.append("VALIDATION: PASSED")
        report_lines.append("")
    
    # Sort fields by group -> order -> id for deterministic output
    sorted_fields = sorted(registry_data, key=lambda f: (
        f.get('display', {}).get('group', ''),
        f.get('display', {}).get('order', 999),
        f.get('id', '')
    ))
    
    # Status counts
    status_counts = defaultdict(int)
    for field in registry_data:
        status_counts[field.get('status', 'unknown')] += 1
    
    report_lines.append("Status Summary:")
    for status in sorted(status_counts.keys()):
        report_lines.append(f"  {status}: {status_counts[status]}")
    report_lines.append("")
    
    # Fields with dependencies
    fields_with_deps = [f for f in registry_data if f.get('deps')]
    if fields_with_deps:
        report_lines.append("Fields with Dependencies:")
        for field in sorted(fields_with_deps, key=lambda f: f.get('id', '')):
            deps_str = ', '.join(field.get('deps', []))
            report_lines.append(f"  {field.get('id')}: [{deps_str}]")
        report_lines.append("")
    
    # Field listing
    report_lines.append("Field Listing (by group -> order -> id):")
    current_group = None
    for field in sorted_fields:
        display = field.get('display', {})
        group = display.get('group', 'unknown')
        
        if group != current_group:
            report_lines.append(f"\n{group.upper()} GROUP:")
            current_group = group
        
        order = display.get('order', 'N/A')
        control = display.get('control', 'unknown')
        status = field.get('status', 'unknown')
        owner = field.get('owner', 'unknown')
        
        report_lines.append(f"  [{order:2}] {field.get('id'):20} {control:12} {status:10} ({owner})")
    
    return '\n'.join(report_lines)

def main():
    """Main validator function"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Validate field registry v1.1')
    parser.add_argument('--out', default='artifacts/registry_report.txt', 
                       help='Output path for registry report')
    args = parser.parse_args()
    
    # Paths
    base_dir = Path(__file__).parent.parent
    schema_path = base_dir / 'schemas' / 'fields_v1_1.schema.json'
    registry_path = base_dir / 'docs' / 'registry' / 'fields_v1.json'
    artifacts_dir = base_dir / 'artifacts'
    report_path = Path(args.out) if args.out.startswith('/') else base_dir / args.out
    schemas_ok_path = artifacts_dir / 'schemas_ok.txt'
    
    # Create artifacts directory
    artifacts_dir.mkdir(exist_ok=True)
    report_path.parent.mkdir(exist_ok=True)
    
    try:
        # Load data
        schema_data = load_schema(schema_path)
        registry_data = load_registry(registry_path)
        
        # Validate JSON schema
        schema_valid, schema_errors = validate_json_schema(registry_data, schema_data)
        
        # Validate hard rules
        rule_errors = validate_hard_rules(registry_data)
        
        # Combine errors
        all_errors = schema_errors + rule_errors
        
        # Generate report
        report = generate_report(registry_data, all_errors)
        
        # Write report
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Write schemas_ok status
        with open(schemas_ok_path, 'w') as f:
            if all_errors:
                f.write("SCHEMAS: FAILED\n")
                for error in all_errors:
                    f.write(f"ERROR: {error}\n")
            else:
                f.write("SCHEMAS: OK\n")
        
        # Exit with appropriate code
        if all_errors:
            print(f"Validation failed with {len(all_errors)} errors")
            print("See artifacts/registry_report.txt for details")
            sys.exit(1)
        else:
            print("Validation passed")
            print("Report written to artifacts/registry_report.txt")
            sys.exit(0)
            
    except Exception as e:
        print(f"Validator error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
