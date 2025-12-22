#!/usr/bin/env python3

import psycopg2
import psycopg2.extras
import hashlib

# Database configuration
DATABASE_URL = "postgresql://postgres.juzpbvpvvltqevznuqfz:7+3t6m?>YZL0@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

def create_users_table_direct():
    """Create users table directly using psycopg2"""
    print("Connecting to database...")
    
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=10,
            application_name="stranz_tms_setup"
        )
        conn.autocommit = True
        
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
        
        # Check if admin user exists
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
            print("Default admin user created successfully!")
        else:
            print(f"Admin user already exists (count: {admin_count})")
        
        # List all users
        print("\nCurrent users in database:")
        cur.execute("SELECT username, first_name, last_name, role, is_active FROM users ORDER BY created_date")
        users = cur.fetchall()
        
        if users:
            for user in users:
                status = "Active" if user[4] else "Disabled"
                print(f"  - {user[0]} ({user[1]} {user[2]}) - {user[3]} - {status}")
        else:
            print("  No users found")
        
        cur.close()
        conn.close()
        
        print("\nDatabase setup completed successfully!")
        print("You can now use the user management system!")
        return True
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

if __name__ == "__main__":
    create_users_table_direct()