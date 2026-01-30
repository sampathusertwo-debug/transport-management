try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    # Fallback for when psycopg2 is not available
    psycopg2 = None

import streamlit as st
import json
from datetime import datetime, date
import uuid

# Database configuration
DATABASE_URL = "postgresql://postgres.juzpbvpvvltqevznuqfz:7+3t6m?>YZL0@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_data(table_name, limit=None):
    """Get cached data from database"""
    if psycopg2 is None:
        return []
    
    try:
        query = f"SELECT * FROM {table_name} ORDER BY created_date DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        result = execute_query(query, fetch=True)
        
        if result:
            processed_data = []
            for row in result:
                row_dict = dict(row)
                
                # Handle JSON deserialization for specific fields
                json_fields = {
                    'customer_payments': ['allocated_invoices'],
                    'bookings': [],  # Add any JSON fields for bookings if needed
                    'invoices': [],  # Add any JSON fields for invoices if needed
                }
                
                if table_name in json_fields:
                    for field in json_fields[table_name]:
                        if field in row_dict and row_dict[field]:
                            try:
                                row_dict[field] = json.loads(row_dict[field])
                            except (json.JSONDecodeError, TypeError):
                                row_dict[field] = row_dict[field]  # Keep original if not JSON
                
                processed_data.append(row_dict)
            
            return processed_data
        
        return []
    except Exception as e:
        st.error(f"Error fetching {table_name}: {e}")
        return []

def load_data_when_needed(data_type):
    """Load specific data type only when needed"""
    if data_type not in st.session_state or not st.session_state[data_type]:
        if data_type == 'customers':
            st.session_state.customers = get_cached_data('customers')
        elif data_type == 'bookings':
            st.session_state.bookings = get_cached_data('bookings', limit=100)  # Limit recent data
        elif data_type == 'invoices':
            st.session_state.invoices = get_cached_data('invoices', limit=100)
        elif data_type == 'vehicles':
            st.session_state.vehicles = get_cached_data('vehicles')
        elif data_type == 'drivers':
            st.session_state.drivers = get_cached_data('drivers')
        elif data_type == 'quotations':
            st.session_state.quotations = get_cached_data('quotations', limit=100)
        elif data_type == 'vendors':
            st.session_state.vendors = get_cached_data('vendors')
        elif data_type == 'expenses':
            st.session_state.expenses = get_cached_data('expenses', limit=200)
        elif data_type == 'fuel_logs':
            st.session_state.fuel_logs = get_cached_data('fuel_logs', limit=200)
        elif data_type == 'odometer_logs':
            st.session_state.odometer_logs = get_cached_data('odometer_logs', limit=200)
        elif data_type == 'notes':
            st.session_state.notes = get_cached_data('notes', limit=500)  # Status change notes
        elif data_type == 'vendor_bills':
            st.session_state.vendor_bills = get_cached_data('vendor_bills', limit=100)
        elif data_type == 'customer_payments':
            st.session_state.customer_payments = get_cached_data('customer_payments', limit=200)
        # Add other data types as needed
    
    return st.session_state[data_type]

def get_connection():
    """Get database connection with connection pooling"""
    if psycopg2 is None:
        st.error("Database driver not available. Please install psycopg2-binary.")
        return None
    
    try:
        # Use connection pooling for better performance
        conn = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=10,
            application_name="stranz_tms"
        )
        conn.autocommit = True  # Enable autocommit for better performance
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database tables - only run once"""
    if psycopg2 is None:
        st.warning("Running in fallback mode without database connection.")
        return True  # Allow app to continue without database
    
    # Check if already initialized
    if 'db_tables_created' in st.session_state:
        return True
    
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Create users table
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
        
        # Create customers table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                phone VARCHAR(20),
                address TEXT,
                gst_number VARCHAR(15),
                pan_number VARCHAR(10),
                payment_terms INTEGER DEFAULT 30,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create vehicles table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                registration_number VARCHAR(20) UNIQUE NOT NULL,
                vehicle_type VARCHAR(50),
                vehicle_length VARCHAR(20),
                fuel_type VARCHAR(20),
                linked_driver VARCHAR(255),
                capacity_kg DECIMAL(10,2),
                status VARCHAR(20) DEFAULT 'Active',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create drivers table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                license_number VARCHAR(50),
                phone VARCHAR(20),
                address TEXT,
                status VARCHAR(20) DEFAULT 'Available',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create quotations table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quotations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                quotation_number VARCHAR(50) UNIQUE NOT NULL,
                customer_id UUID REFERENCES customers(id),
                customer_name VARCHAR(255),
                pickup_location TEXT,
                delivery_location TEXT,
                vehicle_type VARCHAR(50),
                trip_type VARCHAR(20),
                distance_km DECIMAL(10,2),
                weight_capacity DECIMAL(10,2),
                weight_unit VARCHAR(10),
                reference_number VARCHAR(50),
                base_price DECIMAL(10,2),
                loading_charges DECIMAL(10,2) DEFAULT 0,
                unloading_charges DECIMAL(10,2) DEFAULT 0,
                airport_pass_charges DECIMAL(10,2) DEFAULT 0,
                halting_charges DECIMAL(10,2) DEFAULT 0,
                fuel_surcharge DECIMAL(10,2) DEFAULT 0,
                toll_charges DECIMAL(10,2) DEFAULT 0,
                other_charges DECIMAL(10,2) DEFAULT 0,
                discount DECIMAL(10,2) DEFAULT 0,
                gst_applicable BOOLEAN DEFAULT true,
                gst_amount DECIMAL(10,2) DEFAULT 0,
                total_amount DECIMAL(10,2),
                payment_terms INTEGER DEFAULT 30,
                special_instructions TEXT,
                status VARCHAR(20) DEFAULT 'Draft',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create simplified bookings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
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
        
        # Create invoices table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                invoice_number VARCHAR(50) UNIQUE NOT NULL,
                booking_id UUID REFERENCES bookings(id),
                booking_number VARCHAR(50),
                customer_id UUID REFERENCES customers(id),
                customer_name VARCHAR(255),
                invoice_date DATE,
                movement_type VARCHAR(20),
                invoice_type VARCHAR(50),
                dsr_number VARCHAR(50),
                contract_id VARCHAR(50),
                total_amount DECIMAL(10,2),
                gst_amount DECIMAL(10,2),
                net_amount DECIMAL(10,2),
                outstanding_amount DECIMAL(10,2),
                payment_terms INTEGER DEFAULT 30,
                due_date DATE,
                status VARCHAR(20) DEFAULT 'Pending',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create customer_payments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customer_payments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_id UUID REFERENCES customers(id),
                customer_name VARCHAR(255),
                payment_date DATE,
                payment_amount DECIMAL(10,2),
                payment_mode VARCHAR(50),
                reference_number VARCHAR(50),
                allocation_status VARCHAR(20) DEFAULT 'Unallocated',
                allocated_amount DECIMAL(10,2) DEFAULT 0,
                balance_amount DECIMAL(10,2),
                remarks TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create vendors table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                contact_person VARCHAR(255),
                phone VARCHAR(20),
                email VARCHAR(255),
                address TEXT,
                gst_number VARCHAR(15),
                pan_number VARCHAR(10),
                vendor_type VARCHAR(50),
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create vendor_bills table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vendor_bills (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                vendor_id UUID REFERENCES vendors(id),
                vendor_name VARCHAR(255),
                bill_number VARCHAR(50),
                bill_date DATE,
                bill_amount DECIMAL(10,2),
                gst_amount DECIMAL(10,2),
                total_amount DECIMAL(10,2),
                outstanding_amount DECIMAL(10,2),
                category VARCHAR(50),
                description TEXT,
                status VARCHAR(20) DEFAULT 'Pending',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create vendor_payments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vendor_payments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                vendor_id UUID REFERENCES vendors(id),
                vendor_name VARCHAR(255),
                payment_date DATE,
                payment_amount DECIMAL(10,2),
                payment_mode VARCHAR(50),
                reference_number VARCHAR(50),
                remarks TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create expenses table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                expense_date DATE,
                category VARCHAR(100),
                description TEXT,
                amount DECIMAL(10,2),
                payment_method VARCHAR(50),
                receipt_reference VARCHAR(50),
                remarks TEXT,
                created_by VARCHAR(100),
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create fuel_logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fuel_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                date DATE,
                vehicle_registration VARCHAR(20),
                liters DECIMAL(8,2),
                cost DECIMAL(10,2),
                cost_per_liter DECIMAL(8,2),
                source VARCHAR(255),
                odometer_reading INTEGER,
                remarks TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create odometer_logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS odometer_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                date DATE,
                vehicle_registration VARCHAR(20),
                kilometer_reading INTEGER,
                reading_type VARCHAR(50),
                notes TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create notes table for status tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                record_id UUID NOT NULL,
                record_type VARCHAR(50) NOT NULL,
                old_status VARCHAR(50),
                new_status VARCHAR(50) NOT NULL,
                change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                changed_by VARCHAR(100) DEFAULT 'Admin',
                notes TEXT,
                additional_data JSONB,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_record_id ON notes(record_id);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_record_type ON notes(record_type);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_change_date ON notes(change_date);
        """)
        
        # Create counters table for number generation
        cur.execute("""
            CREATE TABLE IF NOT EXISTS counters (
                id SERIAL PRIMARY KEY,
                counter_name VARCHAR(50) UNIQUE NOT NULL,
                current_value INTEGER DEFAULT 1
            )
        """)
        
        # Initialize counters
        cur.execute("""
            INSERT INTO counters (counter_name, current_value) 
            VALUES ('booking_counter', 1), ('invoice_counter', 1), ('quotation_counter', 1), ('dsr_counter', 1)
            ON CONFLICT (counter_name) DO NOTHING
        """)
        
        # Create default admin user if no users exist
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        
        if user_count == 0:
            import hashlib
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
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Mark as initialized
        st.session_state.db_tables_created = True
        return True
        
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def execute_query(query, params=None, fetch=False):
    """Execute a database query"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        
        if fetch:
            result = cur.fetchall()
        else:
            result = cur.rowcount
            
        conn.commit()
        cur.close()
        conn.close()
        return result
        
    except Exception as e:
        st.error(f"Database query error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return None

def refresh_data(data_type=None):
    """Refresh cached data"""
    if data_type:
        # Clear specific data from cache and session state
        get_cached_data.clear()
        if data_type in st.session_state:
            st.session_state[data_type] = []
    else:
        # Clear all cached data
        get_cached_data.clear()
        for key in ['customers', 'quotations', 'bookings', 'invoices', 'customer_payments', 
                   'vendors', 'vendor_bills', 'vendor_payments', 'expenses', 'vehicles', 
                   'drivers', 'fuel_logs', 'odometer_logs', 'users']:
            st.session_state[key] = []

def authenticate_user_db(username, password):
    """Authenticate user credentials from database"""
    try:
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        query = """
        SELECT id, username, first_name, last_name, email, mobile_number, role, 
               is_active, password_changed, temp_password
        FROM users 
        WHERE username = %s AND password_hash = %s AND is_active = true
        """
        
        result = execute_query(query, (username, password_hash), fetch=True)
        
        if result:
            user = result[0]
            # Update last login
            update_query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
            execute_query(update_query, (user['id'],))
            return user
        return None
        
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None

def create_user(user_data):
    """Create a new user"""
    try:
        import hashlib
        
        # Hash the password
        password_hash = hashlib.sha256(user_data['password'].encode()).hexdigest()
        
        # Check if username already exists
        check_query = "SELECT id FROM users WHERE username = %s"
        existing = execute_query(check_query, (user_data['username'],), fetch=True)
        
        if existing:
            return False, "Username already exists"
        
        # Create user data for database
        db_user_data = {
            'username': user_data['username'],
            'password_hash': password_hash,
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'email': user_data['email'],
            'mobile_number': user_data.get('mobile_number', ''),
            'role': user_data.get('role', 'User'),
            'temp_password': user_data['password'],  # Store temp password for first login
            'created_by': user_data.get('created_by', 'Admin')
        }
        
        result = add_to_database('users', db_user_data)
        
        if result:
            refresh_data('users')
            return True, "User created successfully"
        else:
            return False, "Failed to create user"
            
    except Exception as e:
        return False, f"Error creating user: {e}"

def update_user_password(username, new_password):
    """Update user password"""
    try:
        import hashlib
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        query = """
        UPDATE users 
        SET password_hash = %s, password_changed = true, temp_password = NULL
        WHERE username = %s
        """
        
        result = execute_query(query, (password_hash, username))
        
        if result:
            return True, "Password updated successfully"
        else:
            return False, "Failed to update password"
            
    except Exception as e:
        return False, f"Error updating password: {e}"

def reset_user_password(user_id, new_password):
    """Reset user password and mark for change on next login"""
    try:
        import hashlib
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        query = """
        UPDATE users 
        SET password_hash = %s, password_changed = false, temp_password = %s
        WHERE id = %s
        """
        
        result = execute_query(query, (password_hash, new_password, user_id))
        
        if result:
            refresh_data('users')
            return True, "Password reset successfully"
        else:
            return False, "Failed to reset password"
            
    except Exception as e:
        return False, f"Error resetting password: {e}"

def get_all_users():
    """Get all users from database"""
    try:
        query = """
        SELECT id, username, first_name, last_name, email, mobile_number, 
               role, is_active, password_changed, created_date, last_login, created_by
        FROM users 
        ORDER BY created_date DESC
        """
        
        result = execute_query(query, fetch=True)
        return result or []
        
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return []

def toggle_user_status(user_id, is_active):
    """Enable or disable user"""
    try:
        query = "UPDATE users SET is_active = %s WHERE id = %s"
        result = execute_query(query, (is_active, user_id))
        
        if result:
            refresh_data('users')
            return True, f"User {'enabled' if is_active else 'disabled'} successfully"
        else:
            return False, "Failed to update user status"
            
    except Exception as e:
        return False, f"Error updating user status: {e}"

def delete_user(user_id):
    """Delete user from database"""
    try:
        query = "DELETE FROM users WHERE id = %s"
        result = execute_query(query, (user_id,))
        
        if result:
            refresh_data('users')
            return True, "User deleted successfully"
        else:
            return False, "Failed to delete user"
            
    except Exception as e:
        return False, f"Error deleting user: {e}"

def update_user(user_id, user_data):
    """Update user information in database"""
    try:
        query = """
        UPDATE users 
        SET first_name = %s, 
            last_name = %s, 
            email = %s, 
            mobile_number = %s, 
            role = %s
        WHERE id = %s
        """
        result = execute_query(query, (
            user_data['first_name'],
            user_data['last_name'], 
            user_data['email'],
            user_data['mobile_number'],
            user_data['role'],
            user_id
        ))
        
        if result:
            refresh_data('users')
            return True, "User updated successfully"
        else:
            return False, "Failed to update user"
            
    except Exception as e:
        return False, f"Error updating user: {e}"

def generate_random_password(length=8):
    """Generate a random password"""
    import random
    import string
    
    characters = string.ascii_letters + string.digits + "!@#$%"
    password = ''.join(random.choice(characters) for i in range(length))
    return password

def add_to_database(table_name, data):
    """Add new record to database and refresh cache"""
    if psycopg2 is None:
        # Fallback to session state only
        st.session_state[table_name] = st.session_state.get(table_name, [])
        st.session_state[table_name].append(data)
        return True
    
    try:
        # Generate UUID for id if not present
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        
        # Check for duplicates for specific tables
        if table_name == 'customers':
            # Check for duplicate customers by phone or email
            phone = data.get('phone')
            email = data.get('email')
            if phone or email:
                duplicate_check_conditions = []
                check_values = []
                
                if phone:
                    duplicate_check_conditions.append("phone = %s")
                    check_values.append(phone)
                if email:
                    duplicate_check_conditions.append("email = %s")
                    check_values.append(email)
                
                if duplicate_check_conditions:
                    check_query = f"SELECT id, name, phone, email FROM customers WHERE {' OR '.join(duplicate_check_conditions)}"
                    existing_customers = execute_query(check_query, check_values, fetch=True)
                    
                    if existing_customers:
                        # Return existing customer ID instead of creating duplicate
                        existing = existing_customers[0]
                        st.warning(f"Customer already exists: {existing['name']} (Phone: {existing['phone']}, Email: {existing['email']})")
                        return existing['id']
        
        elif table_name == 'quotations':
            # Check for duplicate quotations by quotation_number
            quotation_number = data.get('quotation_number')
            if quotation_number:
                check_query = "SELECT id FROM quotations WHERE quotation_number = %s"
                existing_quotation = execute_query(check_query, (quotation_number,), fetch=True)
                
                if existing_quotation:
                    st.error(f"Quotation with number {quotation_number} already exists")
                    return False
        
        # Convert datetime objects to strings for database
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif hasattr(value, 'date'):  # date objects
                data[key] = value.isoformat()
            elif isinstance(value, (dict, list)):  # Handle dict/list objects
                data[key] = json.dumps(value)
            elif value is None:
                data[key] = None  # Keep None as NULL
        
        # Convert data dict to insert query
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING id"
        
        result = execute_query(query, list(data.values()), fetch=True)
        
        # Also add to session state for immediate display
        st.session_state[table_name] = st.session_state.get(table_name, [])
        st.session_state[table_name].append(data)
        
        # Refresh cache for this data type
        refresh_data(table_name)
        
        return result[0]['id'] if result else True
    except Exception as e:
        st.error(f"Error adding to {table_name}: {e}")
        # Fallback to session state
        st.session_state[table_name] = st.session_state.get(table_name, [])
        st.session_state[table_name].append(data)
        return False

def save_to_database(table_name, data):
    """Save data to database - wrapper function for compatibility"""
    return add_to_database(table_name, data)

def update_in_database(table_name, data, record_id):
    """Update existing record in database"""
    if psycopg2 is None:
        # Fallback to session state update
        items = st.session_state.get(table_name, [])
        for item in items:
            if item.get('id') == record_id:
                item.update(data)
                break
        return True
    
    try:
        # Convert datetime objects to strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif hasattr(value, 'date'):
                data[key] = value.isoformat()
            elif isinstance(value, (dict, list)):  # Handle dict/list objects
                data[key] = json.dumps(value)
            elif value is None:
                data[key] = None  # Keep None as NULL
        
        # Build update query
        set_clause = ', '.join([f"{key} = %s" for key in data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE id = %s"
        values = list(data.values()) + [record_id]
        
        result = execute_query(query, values)
        
        # Update session state too
        items = st.session_state.get(table_name, [])
        for item in items:
            if item.get('id') == record_id:
                item.update(data)
                break
        
        # Refresh cache
        refresh_data(table_name)
        
        return result is not None
    except Exception as e:
        st.error(f"Error updating {table_name}: {e}")
        return False

def delete_from_database(table_name, record_id):
    """Delete record from database"""
    if psycopg2 is None:
        # Fallback to session state deletion
        items = st.session_state.get(table_name, [])
        st.session_state[table_name] = [item for item in items if item.get('id') != record_id]
        return True
    
    try:
        query = f"DELETE FROM {table_name} WHERE id = %s"
        result = execute_query(query, [record_id])
        
        # Update session state too
        items = st.session_state.get(table_name, [])
        st.session_state[table_name] = [item for item in items if item.get('id') != record_id]
        
        # Refresh cache
        refresh_data(table_name)
        
        return result is not None
    except Exception as e:
        st.error(f"Error deleting from {table_name}: {e}")
        return False

def get_next_counter_value(counter_name):
    """Get next counter value and increment"""
    if psycopg2 is None:
        # Fallback counter
        if 'fallback_counters' not in st.session_state:
            st.session_state.fallback_counters = {
                'booking_counter': 1,
                'invoice_counter': 1,
                'quotation_counter': 1,
                'dsr_counter': 1
            }
        current = st.session_state.fallback_counters.get(counter_name, 1)
        st.session_state.fallback_counters[counter_name] = current + 1
        return current
    
    conn = get_connection()
    if not conn:
        return 1
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE counters 
            SET current_value = current_value + 1 
            WHERE counter_name = %s 
            RETURNING current_value
        """, (counter_name,))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        return result[0] if result else 1
        
    except Exception as e:
        st.error(f"Error updating counter: {e}")
        return 1

def recreate_database_schema():
    """Recreate database schema to match current requirements"""
    if psycopg2 is None:
        st.warning("Database driver not available.")
        return False
    
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Add missing columns instead of dropping tables
        try:
            # Add payment_terms to customers table
            cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS payment_terms INTEGER DEFAULT 30")
            
            # Add weight_capacity to quotations table (rename from weight_value if it exists)
            cur.execute("ALTER TABLE quotations ADD COLUMN IF NOT EXISTS weight_capacity DECIMAL(10,2)")
            try:
                cur.execute("UPDATE quotations SET weight_capacity = weight_value WHERE weight_capacity IS NULL AND weight_value IS NOT NULL")
                cur.execute("ALTER TABLE quotations DROP COLUMN IF EXISTS weight_value")
            except:
                pass  # Column might not exist
            
            # Add weight_capacity to bookings table
            cur.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS weight_capacity DECIMAL(10,2)")
            try:
                cur.execute("UPDATE bookings SET weight_capacity = weight_value WHERE weight_capacity IS NULL AND weight_value IS NOT NULL")
                cur.execute("ALTER TABLE bookings DROP COLUMN IF EXISTS weight_value")
            except:
                pass
            
            # Fix charge column names in quotations
            cur.execute("ALTER TABLE quotations ADD COLUMN IF NOT EXISTS fuel_surcharge DECIMAL(10,2) DEFAULT 0")
            cur.execute("ALTER TABLE quotations ADD COLUMN IF NOT EXISTS airport_pass_charges DECIMAL(10,2) DEFAULT 0")
            try:
                cur.execute("UPDATE quotations SET fuel_surcharge = fuel_charges WHERE fuel_surcharge IS NULL AND fuel_charges IS NOT NULL")
                cur.execute("UPDATE quotations SET airport_pass_charges = airport_pass WHERE airport_pass_charges IS NULL AND airport_pass IS NOT NULL")
                cur.execute("ALTER TABLE quotations DROP COLUMN IF EXISTS fuel_charges")
                cur.execute("ALTER TABLE quotations DROP COLUMN IF EXISTS airport_pass")
            except:
                pass
                
            # Fix airport_pass column name in bookings
            cur.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS airport_pass_charges DECIMAL(10,2) DEFAULT 0")
            try:
                cur.execute("UPDATE bookings SET airport_pass_charges = airport_pass WHERE airport_pass_charges IS NULL AND airport_pass IS NOT NULL")
                cur.execute("ALTER TABLE bookings DROP COLUMN IF EXISTS airport_pass")
            except:
                pass
                
        except Exception as e:
            st.warning(f"Some schema updates skipped: {e}")
        
        cur.close()
        conn.close()
        
        st.success("Database schema updated successfully!")
        return True
        
    except Exception as e:
        st.error(f"Error updating schema: {e}")
        return False
        
def fix_database_schema():
    """Auto-fix database schema issues silently"""
    if psycopg2 is None:
        return
    
    conn = get_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # List of all column additions needed
        schema_fixes = [
            # users table - ensure all columns exist
            ("users", "username", "VARCHAR(100) UNIQUE"),
            ("users", "password_hash", "VARCHAR(255)"),
            ("users", "first_name", "VARCHAR(100)"),
            ("users", "last_name", "VARCHAR(100)"),
            ("users", "email", "VARCHAR(255)"),
            ("users", "mobile_number", "VARCHAR(20)"),
            ("users", "role", "VARCHAR(50) DEFAULT 'User'"),
            ("users", "is_active", "BOOLEAN DEFAULT true"),
            ("users", "password_changed", "BOOLEAN DEFAULT false"),
            ("users", "temp_password", "VARCHAR(255)"),
            ("users", "last_login", "TIMESTAMP"),
            ("users", "created_by", "VARCHAR(100) DEFAULT 'Admin'"),
            
            # customers table
            ("customers", "payment_terms", "INTEGER DEFAULT 30"),
            
            # quotations table
            ("quotations", "weight_capacity", "DECIMAL(10,2)"),
            ("quotations", "base_price", "DECIMAL(10,2)"),
            ("quotations", "total_amount", "DECIMAL(10,2)"),
            ("quotations", "fuel_surcharge", "DECIMAL(10,2) DEFAULT 0"),
            ("quotations", "airport_pass_charges", "DECIMAL(10,2) DEFAULT 0"),
            ("quotations", "reference_number", "VARCHAR(50)"),
            ("quotations", "subtotal", "DECIMAL(10,2) DEFAULT 0"),
            ("quotations", "created_by", "VARCHAR(100) DEFAULT 'Admin'"),
            
            # bookings table
            ("bookings", "weight_capacity", "DECIMAL(10,2)"),
            ("bookings", "price", "DECIMAL(10,2)"),
            ("bookings", "airport_pass_charges", "DECIMAL(10,2) DEFAULT 0"),
            ("bookings", "created_by", "VARCHAR(100) DEFAULT 'Admin'"),
            ("bookings", "can_edit", "BOOLEAN DEFAULT true"),
            
            # invoices table - add missing columns
            ("invoices", "pickup_location", "TEXT"),
            ("invoices", "delivery_location", "TEXT"),
            ("invoices", "pickup_date", "DATE"),
            ("invoices", "vehicle_number", "VARCHAR(50)"),
            ("invoices", "driver_name", "VARCHAR(255)"),
            ("invoices", "distance_km", "DECIMAL(10,2)"),
            ("invoices", "base_amount", "DECIMAL(10,2)"),
            ("invoices", "booking_loading_charges", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "booking_unloading_charges", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "booking_airport_pass_charges", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "booking_halting_charges", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "booking_fuel_charges", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "booking_toll_charges", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "booking_other_charges", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "booking_discount", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "additional_fuel", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "additional_toll", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "additional_loading", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "additional_detention", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "additional_misc", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "additional_charges", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "extra_discount", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "total_discount", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "subtotal", "DECIMAL(10,2) DEFAULT 0"),
            ("invoices", "gst_applicable", "BOOLEAN DEFAULT false"),
            ("invoices", "gst_rate", "INTEGER DEFAULT 0"),
            ("invoices", "gst_type", "VARCHAR(20)"),
            ("invoices", "invoice_notes", "TEXT"),
            ("invoices", "contract_start_date", "DATE"),
            ("invoices", "contract_end_date", "DATE"),
            ("invoices", "contract_period", "VARCHAR(50)"),
            ("invoices", "created_by", "VARCHAR(100) DEFAULT 'Admin'"),
            
            # customer_payments table
            ("customer_payments", "created_by", "VARCHAR(100) DEFAULT 'Admin'"),
            ("customer_payments", "invoice_id", "UUID"),
            ("customer_payments", "allocation_type", "VARCHAR(100)"),
            ("customer_payments", "unallocated_amount", "DECIMAL(10,2) DEFAULT 0"),
            ("customer_payments", "allocated_invoices", "JSONB"),
            ("customer_payments", "reference_number", "VARCHAR(100)"),
            ("customer_payments", "bank_details", "TEXT"),
            ("customer_payments", "bank_name", "VARCHAR(100)"),
            ("customer_payments", "notes", "TEXT"),
            ("customer_payments", "payment_method", "VARCHAR(50)"),
            ("customer_payments", "amount", "DECIMAL(10,2)"),
            ("customer_payments", "payment_status", "VARCHAR(20) DEFAULT 'Completed'"),
            
            # vendor_payments table
            ("vendor_payments", "created_by", "VARCHAR(100) DEFAULT 'Admin'"),
            
            # vendor_bills table  
            ("vendor_bills", "created_by", "VARCHAR(100) DEFAULT 'Admin'"),
        ]
        
        for table, column, definition in schema_fixes:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
            except Exception as e:
                # Log but don't fail
                continue
        
        cur.close()
        conn.close()
        
    except Exception as e:
        pass  # Fail silently