"""
Migration script to update bookings table to simplified structure
Run this once to migrate from complex to simplified bookings table
"""

import psycopg2
import os
import sys

# Database configuration
DATABASE_URL = "postgresql://postgres.juzpbvpvvltqevznuqfz:7+3t6m?>YZL0@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

def migrate_bookings_table():
    """Migrate bookings table to simplified structure"""
    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Starting bookings table migration...")
        
        # Step 1: Backup existing data if table exists
        print("1. Checking if bookings table exists...")
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'bookings'
        """)
        
        table_exists = cur.fetchone()
        
        if table_exists:
            print("2. Creating backup of existing bookings...")
            # Create backup table with timestamp
            backup_table_name = f"bookings_backup_{int(pd.Timestamp.now().timestamp())}"
            cur.execute(f"CREATE TABLE {backup_table_name} AS SELECT * FROM bookings")
            print(f"   Backup created: {backup_table_name}")
            
            print("3. Dropping existing bookings table...")
            cur.execute("DROP TABLE bookings CASCADE")
        else:
            print("2. No existing bookings table found, creating new one...")
        
        # Step 2: Create new simplified bookings table
        print("3. Creating simplified bookings table...")
        cur.execute("""
            CREATE TABLE bookings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                booking_number VARCHAR(50) UNIQUE NOT NULL,
                customer VARCHAR(255) NOT NULL,
                booking_date DATE NOT NULL,
                vehicle_type VARCHAR(50) NOT NULL,
                route_from TEXT NOT NULL,
                route_to TEXT NOT NULL,
                vehicle_reg_no VARCHAR(50),
                driver VARCHAR(255),
                driver_phone VARCHAR(20),
                status VARCHAR(20) DEFAULT 'CREATED',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Step 3: Update quotations table to match simplified structure
        print("4. Updating quotations table structure...")
        
        # Check if quotations table exists
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'quotations'
        """)
        
        quotations_exists = cur.fetchone()
        
        if quotations_exists:
            print("   Creating backup of existing quotations...")
            # Create backup table with timestamp
            backup_quotations_table = f"quotations_backup_{int(pd.Timestamp.now().timestamp())}"
            cur.execute(f"CREATE TABLE {backup_quotations_table} AS SELECT * FROM quotations")
            print(f"   Quotations backup created: {backup_quotations_table}")
            
            print("   Dropping existing quotations table...")
            cur.execute("DROP TABLE quotations CASCADE")
        
        # Create new simplified quotations table
        print("   Creating simplified quotations table...")
        cur.execute("""
            CREATE TABLE quotations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                quotation_number VARCHAR(50) UNIQUE NOT NULL,
                customer VARCHAR(255) NOT NULL,
                quotation_date DATE NOT NULL,
                vehicle_type VARCHAR(50) NOT NULL,
                route_from TEXT NOT NULL,
                route_to TEXT NOT NULL,
                vehicle_reg_no VARCHAR(50),
                driver VARCHAR(255),
                driver_phone VARCHAR(20),
                status VARCHAR(20) DEFAULT 'CREATED',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print("5. Creating indexes for better performance...")
        cur.execute("CREATE INDEX idx_bookings_customer ON bookings(customer)")
        cur.execute("CREATE INDEX idx_bookings_status ON bookings(status)")
        cur.execute("CREATE INDEX idx_bookings_date ON bookings(booking_date)")
        cur.execute("CREATE INDEX idx_bookings_number ON bookings(booking_number)")
        
        cur.execute("CREATE INDEX idx_quotations_customer ON quotations(customer)")
        cur.execute("CREATE INDEX idx_quotations_status ON quotations(status)")
        cur.execute("CREATE INDEX idx_quotations_date ON quotations(quotation_date)")
        cur.execute("CREATE INDEX idx_quotations_number ON quotations(quotation_number)")
        
        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")
        print("   - New simplified bookings table created")
        print("   - New simplified quotations table created")
        print("   - Indexes added for performance")
        print("   - Old data backed up (if existed)")
        
        # Insert sample data for testing
        print("6. Inserting sample booking data...")
        cur.execute("""
            INSERT INTO bookings (
                booking_number, customer, booking_date, vehicle_type, 
                route_from, route_to, vehicle_reg_no, driver, driver_phone, status
            ) VALUES 
            ('BK001', 'Fast Logistics', '2026-01-08', '17ft', 'Mepz', 'Airport', 'TN1XXXXXX', 'Nithish', '+91 7339X XXXXX', 'CONFIRMED'),
            ('BK002', 'Quick Transport', '2026-01-09', '20ft', 'Chennai Central', 'Tambaram', 'TN2YYYYYY', 'Raj', '+91 9876543210', 'CREATED'),
            ('BK003', 'Express Cargo', '2026-01-10', '14ft', 'T.Nagar', 'Velachery', 'TN3ZZZZZZ', 'Kumar', '+91 8765432109', 'DISPATCHED')
        """)
        
        print("7. Inserting sample quotation data...")
        cur.execute("""
            INSERT INTO quotations (
                quotation_number, customer, quotation_date, vehicle_type, 
                route_from, route_to, vehicle_reg_no, driver, driver_phone, status
            ) VALUES 
            ('QT001', 'Fast Logistics', '2026-01-08', '17ft', 'Mepz', 'Airport', 'TN1XXXXXX', 'Nithish', '+91 7339X XXXXX', 'APPROVED'),
            ('QT002', 'Swift Movers', '2026-01-09', '12ft', 'Guindy', 'OMR', '', '', '', 'CREATED'),
            ('QT003', 'City Express', '2026-01-10', '20ft', 'Adyar', 'Porur', 'TN4AAAAAA', 'Senthil', '+91 9988776655', 'APPROVED')
        """)
        
        conn.commit()
        print("   Sample data inserted successfully!")
        
        cur.close()
        conn.close()
        
        print("\n🎉 Migration completed! The application now uses simplified booking structure.")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    # Import pandas for timestamp
    try:
        import pandas as pd
    except ImportError:
        import datetime
        # Simple timestamp fallback
        class pd:
            class Timestamp:
                @staticmethod
                def now():
                    class MockTimestamp:
                        def timestamp(self):
                            return datetime.datetime.now().timestamp()
                    return MockTimestamp()
    
    print("=== BOOKINGS TABLE MIGRATION ===")
    print("This will update your bookings table to the new simplified structure.")
    print("⚠️  WARNING: This will replace your existing bookings table!")
    print("    (But a backup will be created)")
    
    confirm = input("\nProceed with migration? (yes/no): ").lower().strip()
    
    if confirm == 'yes':
        if migrate_bookings_table():
            print("\n✅ Migration successful! You can now run the main application.")
        else:
            print("\n❌ Migration failed. Please check the errors above.")
    else:
        print("Migration cancelled.")