#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock streamlit session state
class MockSessionState:
    def __init__(self):
        self._state = {}
    
    def __getattr__(self, name):
        return self._state.get(name, None)
    
    def __setattr__(self, name, value):
        if name == '_state':
            super().__setattr__(name, value)
        else:
            self._state[name] = value
    
    def get(self, key, default=None):
        return self._state.get(key, default)

# Mock streamlit module
class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()
    
    def error(self, msg):
        print(f"ERROR: {msg}")
    
    def warning(self, msg):
        print(f"WARNING: {msg}")
    
    def info(self, msg):
        print(f"INFO: {msg}")
    
    def success(self, msg):
        print(f"SUCCESS: {msg}")
    
    def cache_data(self, ttl=None):
        """Mock cache_data decorator"""
        def decorator(func):
            return func
        return decorator

# Replace streamlit import
sys.modules['streamlit'] = MockStreamlit()
import streamlit as st

# Now import database
from database import get_connection
import hashlib

def create_users_table():
    """Create users table and default admin user"""
    print("Connecting to database...")
    conn = get_connection()
    
    if not conn:
        print("Failed to connect to database")
        return False
    
    try:
        cur = conn.cursor()
        
        print("Creating users table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL,
                mobile_number VARCHAR(20),
                role VARCHAR(50) DEFAULT 'User',
                is_active BOOLEAN DEFAULT true,
                password_changed BOOLEAN DEFAULT false,
                temp_password VARCHAR(255),
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                created_by VARCHAR(100) DEFAULT 'Admin'
            )
        """)
        
        print("Users table created successfully!")
        
        # Create default admin user
        print("Checking for admin user...")
        cur.execute("SELECT COUNT(*) FROM users WHERE username = %s", ('admin',))
        admin_count = cur.fetchone()[0]
        
        if admin_count == 0:
            print("Creating default admin user...")
            admin_password = "admin123"
            password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
            
            cur.execute("""
                INSERT INTO users (username, password_hash, first_name, last_name, email, 
                                 mobile_number, role, is_active, password_changed, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                'admin', password_hash, 'Admin', 'User', 'admin@stranz.in',
                '', 'Administrator', True, True, 'System'
            ))
            print("Default admin user created!")
        else:
            print("Admin user already exists")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("Database setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    create_users_table()