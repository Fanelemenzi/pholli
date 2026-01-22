#!/usr/bin/env python
"""
Script to help fix the missing monthly_net_income column issue.
Run this after fixing your database connection.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from django.core.management import execute_from_command_line

def main():
    print("Checking migration status...")
    try:
        # Show current migration status
        execute_from_command_line(['manage.py', 'showmigrations', 'policies'])
        
        print("\nApplying pending migrations...")
        # Apply migrations
        execute_from_command_line(['manage.py', 'migrate', 'policies'])
        
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nIf you're having database connection issues:")
        print("1. Check your DATABASE_URL environment variable")
        print("2. Ensure your database server is running")
        print("3. Check your network connection")

if __name__ == '__main__':
    main()