#!/usr/bin/env python3
"""
Convert TimescaleDB schema to plain PostgreSQL schema.

This script removes TimescaleDB-specific features:
- Extension declaration
- Hypertable conversions
- Continuous aggregates
- Retention policies
- Compression policies
"""

import re
import sys
from pathlib import Path


def convert_schema(input_file: Path, output_file: Path):
    """Convert TimescaleDB schema to PostgreSQL schema."""

    with open(input_file, 'r') as f:
        content = f.read()

    lines = content.split('\n')
    converted_lines = []
    skip_until_semicolon = False
    in_continuous_aggregate = False
    ca_buffer = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Remove TimescaleDB extension
        if 'CREATE EXTENSION' in line and 'timescaledb' in line:
            converted_lines.append('-- TimescaleDB extension removed (converted to plain PostgreSQL)')
            i += 1
            continue

        # Skip create_hypertable calls
        if 'SELECT create_hypertable(' in line:
            table_name = re.search(r"'(\w+)'", line)
            if table_name:
                converted_lines.append(f'-- Hypertable conversion removed: {table_name.group(1)} is now a regular table')
            i += 1
            continue

        # Skip retention policies
        if 'SELECT add_retention_policy(' in line:
            table_name = re.search(r"'(\w+)'", line)
            if table_name:
                converted_lines.append(f'-- Retention policy removed: {table_name.group(1)} (handle via cron job)')
            i += 1
            continue

        # Skip compression configurations
        if 'timescaledb.compress' in line:
            while i < len(lines) and ');' not in lines[i]:
                i += 1
            i += 1  # Skip the closing line
            converted_lines.append('-- Compression policy removed (PostgreSQL uses TOAST for compression)')
            continue

        # Skip compression policies
        if 'SELECT add_compression_policy(' in line:
            i += 1
            continue

        # Handle continuous aggregates
        if 'CREATE MATERIALIZED VIEW' in line and i + 1 < len(lines) and 'timescaledb.continuous' in lines[i + 1]:
            # Start collecting continuous aggregate
            in_continuous_aggregate = True
            ca_buffer = [line]
            i += 1
            continue

        if in_continuous_aggregate:
            ca_buffer.append(line)

            # Check if we've reached the end of the aggregate
            if ';' in line and 'SELECT add_continuous_aggregate_policy' not in line:
                # Convert the continuous aggregate
                ca_content = '\n'.join(ca_buffer)

                # Remove timescaledb.continuous clause
                ca_content = re.sub(r'WITH \(timescaledb\.continuous\)\s*', '', ca_content)

                # Replace time_bucket with date_trunc
                ca_content = re.sub(
                    r"time_bucket\('(\d+\s+\w+)',\s*(\w+)\)",
                    r"date_trunc('\1', \2)",
                    ca_content
                )

                converted_lines.append('-- Converted from TimescaleDB continuous aggregate to standard materialized view')
                converted_lines.append(ca_content)

                in_continuous_aggregate = False
                ca_buffer = []

            i += 1
            continue

        # Skip continuous aggregate policies
        if 'SELECT add_continuous_aggregate_policy(' in line:
            while i < len(lines) and ');' not in lines[i]:
                i += 1
            i += 1  # Skip the closing line
            converted_lines.append('-- Continuous aggregate refresh policy removed (use pg_cron or cron job)')
            continue

        # Convert composite primary keys for hypertables to simple UUID primary keys
        # This is more complex - need to identify hypertable tables and fix their PKs
        if 'PRIMARY KEY (id, timestamp)' in line:
            # Just remove timestamp from composite key
            line = line.replace('PRIMARY KEY (id, timestamp)', 'PRIMARY KEY (id)')
            converted_lines.append('    -- Converted from composite PK (id, timestamp) to simple PK (id)')
            converted_lines.append(line)
            i += 1
            continue

        # Keep all other lines
        converted_lines.append(line)
        i += 1

    # Write converted schema
    with open(output_file, 'w') as f:
        f.write('\n'.join(converted_lines))

    print(f"✅ Converted schema written to: {output_file}")
    print(f"   Original: {len(lines)} lines")
    print(f"   Converted: {len(converted_lines)} lines")
    print(f"   Reduction: {len(lines) - len(converted_lines)} lines removed")


if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    input_schema = project_root / 'src/infrastructure/database/schema.sql.timescaledb.backup'
    output_schema = project_root / 'src/infrastructure/database/schema.postgres.sql'

    if not input_schema.exists():
        print(f"❌ Error: {input_schema} not found")
        sys.exit(1)

    print(f"Converting {input_schema} to PostgreSQL-only schema...")
    convert_schema(input_schema, output_schema)
    print("✅ Conversion complete!")
    print(f"\nNext steps:")
    print(f"  1. Review: {output_schema}")
    print(f"  2. If satisfied: mv {output_schema} {project_root / 'src/infrastructure/database/schema.sql'}")
    print(f"  3. Update docker-compose.yml to use postgres:15-alpine")
    print(f"  4. Test: ./rai db reset")
