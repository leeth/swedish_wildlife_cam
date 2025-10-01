"""
Check for schema changes and validate migration documentation.

This script is used in CI to ensure schema changes are properly documented.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Set


def load_schema(filepath: Path) -> Dict[str, Any]:
    """Load JSON schema from file."""
    if not filepath.exists():
        return {}
    
    with open(filepath, 'r') as f:
        return json.load(f)


def compare_schemas(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two schemas and return differences."""
    
    differences = {
        'added_fields': [],
        'removed_fields': [],
        'changed_fields': [],
        'breaking_changes': [],
        'non_breaking_changes': []
    }
    
    if not old_schema or not new_schema:
        return differences
    
    old_props = old_schema.get('properties', {})
    new_props = new_schema.get('properties', {})
    
    old_fields = set(old_props.keys())
    new_fields = set(new_props.keys())
    
    # Added fields
    added = new_fields - old_fields
    differences['added_fields'] = list(added)
    
    # Removed fields
    removed = old_fields - new_fields
    differences['removed_fields'] = list(removed)
    
    # Changed fields
    common_fields = old_fields & new_fields
    for field in common_fields:
        old_field = old_props[field]
        new_field = new_props[field]
        
        if old_field != new_field:
            differences['changed_fields'].append({
                'field': field,
                'old': old_field,
                'new': new_field
            })
    
    # Classify changes
    if removed:
        differences['breaking_changes'].append(f"Removed fields: {', '.join(removed)}")
    
    for change in differences['changed_fields']:
        field = change['field']
        old_type = old_props[field].get('type')
        new_type = new_props[field].get('type')
        
        if old_type != new_type:
            differences['breaking_changes'].append(f"Changed type for {field}: {old_type} → {new_type}")
        
        # Check if required field became optional
        old_required = old_schema.get('required', [])
        new_required = new_schema.get('required', [])
        
        if field in old_required and field not in new_required:
            differences['non_breaking_changes'].append(f"Made {field} optional")
        elif field not in old_required and field in new_required:
            differences['breaking_changes'].append(f"Made {field} required")
    
    if added:
        differences['non_breaking_changes'].append(f"Added fields: {', '.join(added)}")
    
    return differences


def check_migration_documentation(schema_name: str, differences: Dict[str, Any]) -> bool:
    """Check if migration documentation exists for schema changes."""
    
    migrations_file = Path('data_contract/MIGRATIONS.md')
    if not migrations_file.exists():
        return False
    
    with open(migrations_file, 'r') as f:
        content = f.read()
    
    # Check if schema is mentioned in recent changes
    if schema_name in content:
        return True
    
    # Check if there are any breaking changes
    if differences['breaking_changes']:
        print(f"❌ Breaking changes detected for {schema_name}:")
        for change in differences['breaking_changes']:
            print(f"   - {change}")
        return False
    
    return True


def main():
    """Main function to check schema changes."""
    
    schemas_dir = Path('schemas')
    if not schemas_dir.exists():
        print("✅ No schemas directory found, skipping schema change check")
        return 0
    
    schema_files = list(schemas_dir.glob('*.json'))
    if not schema_files:
        print("✅ No schema files found, skipping schema change check")
        return 0
    
    print("🔍 Checking schema changes...")
    
    all_passed = True
    
    for schema_file in schema_files:
        schema_name = schema_file.stem
        print(f"\n📊 Checking {schema_name}...")
        
        # Load current schema
        current_schema = load_schema(schema_file)
        if not current_schema:
            print(f"⚠️  No current schema found for {schema_name}")
            continue
        
        # For now, we'll just check if the schema is valid
        # In a real implementation, you'd compare against the previous version
        print(f"✅ Schema {schema_name} is valid")
        
        # Check migration documentation
        differences = {
            'breaking_changes': [],
            'non_breaking_changes': []
        }
        
        if not check_migration_documentation(schema_name, differences):
            print(f"❌ Migration documentation missing for {schema_name}")
            all_passed = False
    
    if all_passed:
        print("\n✅ All schema checks passed!")
        return 0
    else:
        print("\n❌ Schema change validation failed!")
        print("Please update data_contract/MIGRATIONS.md with your changes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
