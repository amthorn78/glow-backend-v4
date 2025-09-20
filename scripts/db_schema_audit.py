#!/usr/bin/env python3
"""
Database Schema Audit Script for HD Engine Integration
Generates comprehensive schema documentation and HD touchpoints mapping.
"""
import os
import json
from sqlalchemy import create_engine, text, inspect
from datetime import datetime

DB_URL = 'postgresql://postgres:xXbHcxGLHyIMMhpHBNzBzwqbzGoloFAY@metro.proxy.rlwy.net:52353/railway'

def main():
    engine = create_engine(DB_URL)
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        # 1. Generate schema information
        generate_schema_info(conn, inspector)
        
        # 2. Generate table descriptions
        generate_table_descriptions(conn, inspector)
        
        # 3. Generate foreign key relationships
        generate_fk_relationships(conn)
        
        # 4. Generate sanitized samples
        generate_sanitized_samples(conn)
        
        # 5. Generate HD pins map
        generate_hd_pins_map(conn)
        
        # 6. Generate gaps and proposals
        generate_gaps_and_proposals()
        
        print("Database audit completed successfully!")

def generate_schema_info(conn, inspector):
    """Generate comprehensive schema information"""
    tables = inspector.get_table_names()
    
    schema_info = {
        "database_info": {
            "total_tables": len(tables),
            "tables": tables,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    # Write schema.sql equivalent using information_schema
    with open('artifacts/schema.sql', 'w') as f:
        f.write("-- Database Schema Dump for HD Engine Integration\n")
        f.write(f"-- Generated at: {datetime.utcnow().isoformat()}Z\n")
        f.write("-- Tables: " + ", ".join(tables) + "\n\n")
        
        for table in tables:
            columns = inspector.get_columns(table)
            indexes = inspector.get_indexes(table)
            
            f.write(f"-- Table: {table}\n")
            f.write(f"CREATE TABLE {table} (\n")
            
            col_defs = []
            for col in columns:
                col_def = f"    {col['name']} {col['type']}"
                if not col['nullable']:
                    col_def += " NOT NULL"
                if col.get('default'):
                    col_def += f" DEFAULT {col['default']}"
                col_defs.append(col_def)
            
            f.write(",\n".join(col_defs))
            f.write("\n);\n\n")
            
            # Add indexes
            for idx in indexes:
                f.write(f"CREATE INDEX {idx['name']} ON {table} ({', '.join(idx['column_names'])});\n")
            f.write("\n")

def generate_table_descriptions(conn, inspector):
    """Generate detailed table descriptions"""
    tables = inspector.get_table_names()
    
    for table in tables:
        with open(f'artifacts/tables/{table}.txt', 'w') as f:
            f.write(f"Table: {table}\n")
            f.write("=" * (len(table) + 7) + "\n\n")
            
            # Get column information
            result = conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable, column_default, character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                ORDER BY ordinal_position;
            """))
            
            f.write("Columns:\n")
            for row in result.fetchall():
                f.write(f"  {row[0]}: {row[1]}")
                if row[4]:  # character_maximum_length
                    f.write(f"({row[4]})")
                f.write(f" (nullable: {row[2]})")
                if row[3]:  # default
                    f.write(f" DEFAULT {row[3]}")
                f.write("\n")
            
            # Get indexes
            indexes = inspector.get_indexes(table)
            if indexes:
                f.write("\nIndexes:\n")
                for idx in indexes:
                    f.write(f"  {idx['name']}: {', '.join(idx['column_names'])}")
                    if idx['unique']:
                        f.write(" (UNIQUE)")
                    f.write("\n")
            
            # Get row count
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                f.write(f"\nRow count: {count}\n")
            except:
                f.write("\nRow count: Unable to determine\n")

def generate_fk_relationships(conn):
    """Generate foreign key relationships CSV"""
    result = conn.execute(text("""
        SELECT tc.table_name   AS table,
               kcu.column_name AS column,
               ccu.table_name  AS ref_table,
               ccu.column_name AS ref_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name, kcu.column_name;
    """))
    
    with open('artifacts/fks.csv', 'w') as f:
        f.write("table,column,ref_table,ref_column\n")
        for row in result.fetchall():
            f.write(f"{row[0]},{row[1]},{row[2]},{row[3]}\n")

def generate_sanitized_samples(conn):
    """Generate sanitized sample data for HD-related tables"""
    hd_tables = ['human_design_data', 'user_resonance_prefs', 'user_resonance_signals_private', 'compatibility_matrix']
    
    for table in hd_tables:
        try:
            result = conn.execute(text(f"SELECT * FROM {table} LIMIT 2"))
            columns = result.keys()
            rows = result.fetchall()
            
            samples = []
            for row in rows:
                sample = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Sanitize PII
                    if col in ['email', 'first_name', 'last_name', 'phone']:
                        value = f"[REDACTED_{col.upper()}]"
                    elif isinstance(value, str) and '@' in value:
                        value = "[REDACTED_EMAIL]"
                    sample[col] = value
                samples.append(sample)
            
            with open(f'artifacts/samples/{table}.json', 'w') as f:
                json.dump(samples, f, indent=2, default=str)
                
        except Exception as e:
            # Table might not exist or be empty
            with open(f'artifacts/samples/{table}.json', 'w') as f:
                json.dump({"error": f"Unable to sample {table}: {str(e)}"}, f, indent=2)

def generate_hd_pins_map(conn):
    """Generate HD pins and touchpoints mapping"""
    with open('artifacts/hd_pins_map.md', 'w') as f:
        f.write("# Human Design Pins & Touchpoints Map\n\n")
        f.write("## Current Birth Data Storage\n\n")
        
        # Check birth_data table structure
        try:
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'birth_data'
                ORDER BY ordinal_position;
            """))
            
            f.write("### birth_data table:\n")
            for row in result.fetchall():
                f.write(f"- **{row[0]}**: {row[1]} (nullable: {row[2]})\n")
            
            # Sample birth data structure (sanitized)
            result = conn.execute(text("SELECT * FROM birth_data LIMIT 1"))
            if result.rowcount > 0:
                columns = result.keys()
                sample = result.fetchone()
                f.write("\n### Sample Structure (sanitized):\n```json\n")
                sample_data = {}
                for i, col in enumerate(columns):
                    value = sample[i]
                    if col in ['user_id']:
                        sample_data[col] = "[USER_ID]"
                    else:
                        sample_data[col] = value
                f.write(json.dumps(sample_data, indent=2, default=str))
                f.write("\n```\n")
                
        except Exception as e:
            f.write(f"Error accessing birth_data: {e}\n")
        
        f.write("\n## HD-Related Tables\n\n")
        hd_tables = ['human_design_data', 'user_resonance_prefs', 'user_resonance_signals_private', 'compatibility_matrix']
        
        for table in hd_tables:
            f.write(f"### {table}\n")
            try:
                result = conn.execute(text(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position;
                """))
                for row in result.fetchall():
                    f.write(f"- {row[0]}: {row[1]}\n")
            except:
                f.write("- Table not accessible or doesn't exist\n")
            f.write("\n")
        
        f.write("## Missing Pins for HD Engine\n\n")
        f.write("The following fields may need to be added for complete HD integration:\n\n")
        f.write("- **tzdb_version**: IANA timezone database version (e.g., '2025a')\n")
        f.write("- **geohash_8**: 8-character geohash for location precision\n")
        f.write("- **utc_instant**: Precise UTC timestamp of birth\n")
        f.write("- **fold**: DST fold indicator for ambiguous times\n")
        f.write("- **hd_chart_data**: Canonical HD chart calculations\n")

def generate_gaps_and_proposals():
    """Generate gaps analysis and proposals"""
    with open('artifacts/hd_gaps_and_proposals.md', 'w') as f:
        f.write("# HD Integration Gaps & Proposals\n\n")
        f.write("## Current State Analysis\n\n")
        f.write("### Strengths\n")
        f.write("- ✅ Dedicated HD-related tables exist\n")
        f.write("- ✅ Birth data collection infrastructure in place\n")
        f.write("- ✅ User preferences system supports HD settings\n")
        f.write("- ✅ Compatibility matrix for matching calculations\n")
        f.write("- ✅ Resonance scoring system implemented\n\n")
        
        f.write("### Identified Gaps\n")
        f.write("- ⚠️ Missing timezone database version tracking\n")
        f.write("- ⚠️ No geohash indexing for location-based queries\n")
        f.write("- ⚠️ UTC instant calculation may need verification\n")
        f.write("- ⚠️ DST fold handling for ambiguous birth times\n")
        f.write("- ⚠️ Canonical HD chart storage vs. on-demand calculation\n\n")
        
        f.write("## Proposals for HD Engine Integration\n\n")
        f.write("### Phase 1: Data Enhancement\n")
        f.write("1. **Add timezone metadata fields** to birth_data table\n")
        f.write("2. **Implement geohash indexing** for efficient location queries\n")
        f.write("3. **Add UTC instant calculation** with DST fold handling\n\n")
        
        f.write("### Phase 2: Chart Storage Strategy\n")
        f.write("1. **Option A**: Store canonical HD charts in new `hd_canonical_charts` table\n")
        f.write("2. **Option B**: Calculate charts on-demand with caching layer\n")
        f.write("3. **Recommendation**: Hybrid approach - cache frequently accessed charts\n\n")
        
        f.write("### Phase 3: API Integration\n")
        f.write("1. **Deprecate direct humandesignapi.nl calls** from frontend\n")
        f.write("2. **Centralize HD calculations** in backend HD engine\n")
        f.write("3. **Implement HD data versioning** for schema evolution\n\n")
        
        f.write("## Migration Strategy\n\n")
        f.write("### Non-Breaking Changes (Immediate)\n")
        f.write("- Add new fields to existing tables with NULL defaults\n")
        f.write("- Implement geohash calculation for existing birth data\n")
        f.write("- Add timezone version tracking\n\n")
        
        f.write("### Breaking Changes (Planned)\n")
        f.write("- Modify compatibility_matrix structure if needed\n")
        f.write("- Update HD API response formats\n")
        f.write("- Consolidate resonance calculation methods\n\n")
        
        f.write("## Risk Assessment\n\n")
        f.write("### Low Risk\n")
        f.write("- Adding metadata fields to birth_data\n")
        f.write("- Implementing geohash indexing\n")
        f.write("- UTC instant calculation improvements\n\n")
        
        f.write("### Medium Risk\n")
        f.write("- Modifying compatibility_matrix schema\n")
        f.write("- Changing HD API response formats\n")
        f.write("- Migrating from external HD API to internal engine\n\n")
        
        f.write("### High Risk\n")
        f.write("- Complete HD calculation engine replacement\n")
        f.write("- Major schema restructuring\n")
        f.write("- Breaking changes to existing user data\n")

if __name__ == "__main__":
    main()
