#!/usr/bin/env python
"""Check database schema and add missing column if needed"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection

# Get all columns for the predictions_marketcategory table
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'predictions_marketcategory'
        ORDER BY column_name
    """)
    columns = [row[0] for row in cursor.fetchall()]
    print(f"Columns in predictions_marketcategory table:")
    for col in columns:
        print(f"  - {col}")
    
    if 'total_volume' not in columns:
        print("\n❌ 'total_volume' column is MISSING!")
        print("Adding the column...")
        try:
            cursor.execute("""
                ALTER TABLE predictions_marketcategory
                ADD COLUMN total_volume numeric(18, 2) DEFAULT 0
            """)
            print("✅ Column added successfully!")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("\n✅ 'total_volume' column exists")
