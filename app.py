import streamlit as st
import pandas as pd
import datetime
import json
from typing import Dict, List, Optional
import uuid

# Import modules
from modules import quotations, bookings, invoicing, customer_payments, vendor_management, company_expenses, vehicle_master, dashboard, audit_exports, notes, user_management, pricing_management_ui

# Import database functions
from database import init_database, execute_query, get_next_counter_value, save_to_database, update_in_database, refresh_data

# Make database functions globally available
def save_booking(booking_data):
    """Save booking to database"""
    return save_to_database('bookings', booking_data)

def save_simplified_booking(booking_data):
    """Save simplified booking to database with proper field mapping"""
    # Map the simplified booking data to database fields
    simplified_booking = {
        'id': booking_data.get('id'),
        'booking_number': booking_data.get('booking_number'),
        'customer': booking_data.get('customer'),
        'booking_date': booking_data.get('booking_date'),
        'vehicle_type': booking_data.get('vehicle_type'),
        'route_from': booking_data.get('route_from'),
        'route_to': booking_data.get('route_to'),
        'price': booking_data.get('price'),
        'vehicle_reg_no': booking_data.get('vehicle_reg_no'),
        'driver': booking_data.get('driver'),
        'driver_phone': booking_data.get('driver_phone'),
        'status': booking_data.get('status', 'CREATED'),
        'created_date': booking_data.get('created_date'),
        'last_modified': booking_data.get('last_modified')
    }
    return save_to_database('bookings', simplified_booking)

def save_simplified_quotation(quotation_data):
    """Save simplified quotation to database with proper field mapping"""
    # Map the simplified quotation data to database fields
    simplified_quotation = {
        'id': quotation_data.get('id'),
        'quotation_number': quotation_data.get('quotation_number'),
        'customer': quotation_data.get('customer'),
        'quotation_date': quotation_data.get('quotation_date'),
        'vehicle_type': quotation_data.get('vehicle_type'),
        'route_from': quotation_data.get('route_from'),
        'route_to': quotation_data.get('route_to'),
        'base_price': quotation_data.get('base_price'),
        'total_amount': quotation_data.get('total_amount'),
        'vehicle_reg_no': quotation_data.get('vehicle_reg_no'),
        'driver': quotation_data.get('driver'),
        'driver_phone': quotation_data.get('driver_phone'),
        'status': quotation_data.get('status', 'CREATED'),
        'created_date': quotation_data.get('created_date'),
        'last_modified': quotation_data.get('last_modified')
    }
    return save_to_database('quotations', simplified_quotation)

def update_simplified_booking(booking_id, booking_data):
    """Update simplified booking in database"""
    # Map the simplified booking data to database fields
    # Only include fields that are actually being updated (not None)
    simplified_booking = {}
    
    # Add fields only if they exist in the input data
    if 'customer' in booking_data and booking_data['customer'] is not None:
        simplified_booking['customer'] = booking_data['customer']
    if 'vehicle_type' in booking_data and booking_data['vehicle_type'] is not None:
        simplified_booking['vehicle_type'] = booking_data['vehicle_type']
    if 'route_from' in booking_data:
        simplified_booking['route_from'] = booking_data['route_from']
    if 'route_to' in booking_data:
        simplified_booking['route_to'] = booking_data['route_to']
    if 'price' in booking_data:
        simplified_booking['price'] = booking_data['price']
    if 'vehicle_reg_no' in booking_data:
        simplified_booking['vehicle_reg_no'] = booking_data['vehicle_reg_no']
    if 'driver' in booking_data:
        simplified_booking['driver'] = booking_data['driver']
    if 'driver_phone' in booking_data:
        simplified_booking['driver_phone'] = booking_data['driver_phone']
    if 'status' in booking_data:
        simplified_booking['status'] = booking_data['status']
    
    # Always update last_modified
    simplified_booking['last_modified'] = datetime.datetime.now()
    
    return update_in_database('bookings', simplified_booking, booking_id)

def update_simplified_quotation(quotation_id, quotation_data):
    """Update simplified quotation in database"""
    # Map the simplified quotation data to database fields
    # Only include fields that are actually being updated (not None)
    simplified_quotation = {}
    
    # Add fields only if they exist in the input data
    if 'customer' in quotation_data and quotation_data['customer'] is not None:
        simplified_quotation['customer'] = quotation_data['customer']
    if 'vehicle_type' in quotation_data and quotation_data['vehicle_type'] is not None:
        simplified_quotation['vehicle_type'] = quotation_data['vehicle_type']
    if 'route_from' in quotation_data:
        simplified_quotation['route_from'] = quotation_data['route_from']
    if 'route_to' in quotation_data:
        simplified_quotation['route_to'] = quotation_data['route_to']
    if 'base_price' in quotation_data:
        simplified_quotation['base_price'] = quotation_data['base_price']
    if 'total_amount' in quotation_data:
        simplified_quotation['total_amount'] = quotation_data['total_amount']
    if 'vehicle_reg_no' in quotation_data:
        simplified_quotation['vehicle_reg_no'] = quotation_data['vehicle_reg_no']
    if 'driver' in quotation_data:
        simplified_quotation['driver'] = quotation_data['driver']
    if 'driver_phone' in quotation_data:
        simplified_quotation['driver_phone'] = quotation_data['driver_phone']
    if 'status' in quotation_data:
        simplified_quotation['status'] = quotation_data['status']
    
    # Always update last_modified
    simplified_quotation['last_modified'] = datetime.datetime.now()
    
    return update_in_database('quotations', simplified_quotation, quotation_id)

def save_customer(customer_data):
    """Save customer to database"""
    return save_to_database('customers', customer_data)

def save_quotation(quotation_data):
    """Save quotation to database"""
    return save_to_database('quotations', quotation_data)

def save_invoice(invoice_data):
    """Save invoice to database"""
    return save_to_database('invoices', invoice_data)

def save_payment(payment_data):
    """Save payment to database"""
    return save_to_database('customer_payments', payment_data)

def save_vendor(vendor_data):
    """Save vendor to database"""
    return save_to_database('vendors', vendor_data)

def save_expense(expense_data):
    """Save expense to database"""
    return save_to_database('expenses', expense_data)

def save_vehicle(vehicle_data):
    """Save vehicle to database"""
    return save_to_database('vehicles', vehicle_data)

def save_driver(driver_data):
    """Save driver to database"""
    return save_to_database('drivers', driver_data)

def save_fuel_log(fuel_log_data):
    """Save fuel log to database"""
    return save_to_database('fuel_logs', fuel_log_data)

def save_odometer_log(odometer_log_data):
    """Save odometer log to database"""
    return save_to_database('odometer_logs', odometer_log_data)

def save_vendor_bill(bill_data):
    """Save vendor bill to database"""
    return save_to_database('vendor_bills', bill_data)

def save_vendor_payment(payment_data):
    """Save vendor payment to database"""
    return save_to_database('vendor_payments', payment_data)

# Initialize session state
def init_session_state():
    """Initialize session state and database"""
    # Initialize database tables (only once)
    if 'db_initialized' not in st.session_state:
        if init_database():
            st.session_state.db_initialized = True
            # Auto-fix schema issues
            from database import fix_database_schema, initialize_vehicle_types
            fix_database_schema()
            # Initialize vehicle types
            initialize_vehicle_types()
        else:
            st.error("Failed to connect to database")
            st.stop()
    
    # Check for existing session before initializing defaults
    check_stored_session()
    
    # Initialize session state variables (only if not already set by session restore)
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_full_name' not in st.session_state:
        st.session_state.user_full_name = None
    
    # Initialize empty lists (load data only when needed)
    if 'customers' not in st.session_state:
        st.session_state.customers = []
    if 'quotations' not in st.session_state:
        st.session_state.quotations = []
    if 'bookings' not in st.session_state:
        st.session_state.bookings = []
    if 'invoices' not in st.session_state:
        st.session_state.invoices = []
    if 'customer_payments' not in st.session_state:
        st.session_state.customer_payments = []
    if 'vendors' not in st.session_state:
        st.session_state.vendors = []
    if 'vendor_bills' not in st.session_state:
        st.session_state.vendor_bills = []
    if 'vendor_payments' not in st.session_state:
        st.session_state.vendor_payments = []
    if 'expenses' not in st.session_state:
        st.session_state.expenses = []
    if 'vehicles' not in st.session_state:
        st.session_state.vehicles = []
    if 'drivers' not in st.session_state:
        st.session_state.drivers = []
    if 'fuel_logs' not in st.session_state:
        st.session_state.fuel_logs = []
    if 'odometer_logs' not in st.session_state:
        st.session_state.odometer_logs = []

def authenticate_user(username, password):
    """Authenticate user credentials"""
    # First try database authentication
    from database import authenticate_user_db
    user = authenticate_user_db(username, password)
    
    if user:
        return {
            'role': user['role'],
            'full_name': f"{user['first_name']} {user['last_name']}",
            'user_id': user['id'],
            'password_changed': user['password_changed'],
            'temp_password': user.get('temp_password'),
            'email': user['email']
        }
    
    # Fallback to demo users for backward compatibility
    users = {
        'admin': {
            'password': 'admin123',
            'role': 'Administrator',
            'full_name': 'Admin User'
        },
        'manager': {
            'password': 'manager123',
            'role': 'Manager',
            'full_name': 'Manager User'
        },
        'operator': {
            'password': 'operator123',
            'role': 'Operator',
            'full_name': 'Operator User'
        }
    }
    
    if username in users and users[username]['password'] == password:
        return users[username]
    return None

def show_login_page():
    """Display the login page"""
    # Check for stored session in query params
    check_stored_session()
    
    st.markdown('''
    <div class="login-container">
        <div class="login-card">
            <h1 class="login-title">STRANZ TMS</h1>
            <p class="login-subtitle">Transport Management System</p>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Check if user needs to change password
    if st.session_state.get('password_change_required'):
        show_password_change_form()
        return
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Login to Continue")
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            login_button = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if login_button:
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        # Check if password change is required
                        if user.get('password_changed') == False:
                            st.session_state.username = username
                            st.session_state.user_role = user['role']
                            st.session_state.user_full_name = user['full_name']
                            st.session_state.user_id = user.get('user_id')
                            st.session_state.password_change_required = True
                            st.session_state.temp_password = user.get('temp_password')
                            st.info("Password change required for first login")
                            st.rerun()
                        else:
                            # Store session data
                            store_session(username, user['role'], user['full_name'], user.get('user_id'))
                            st.session_state.authenticated = True
                            st.session_state.username = username
                            st.session_state.user_role = user['role']
                            st.session_state.user_full_name = user['full_name']
                            st.session_state.user_id = user.get('user_id')
                            st.session_state.last_activity = datetime.datetime.now()
                            st.success(f"Welcome, {user['full_name']}!")
                            st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please enter both username and password")

def show_password_change_form():
    """Display password change form for first-time login"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Change Password Required")
        st.info("This is your first login. Please change your password to continue.")
        
        if st.session_state.get('temp_password'):
            st.markdown(f"**Your temporary password is:** `{st.session_state.temp_password}`")
        
        with st.form("password_change_form"):
            new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password")
            
            col_change, col_cancel = st.columns(2)
            
            with col_change:
                change_button = st.form_submit_button("Change Password", type="primary", use_container_width=True)
            
            with col_cancel:
                cancel_button = st.form_submit_button("Cancel", use_container_width=True)
            
            if change_button:
                if not new_password:
                    st.error("Please enter a new password")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    # Update password
                    from database import update_user_password
                    success, message = update_user_password(st.session_state.username, new_password)
                    
                    if success:
                        st.success("Password changed successfully!")
                        # Clear password change requirement and authenticate
                        st.session_state.password_change_required = False
                        st.session_state.authenticated = True
                        if 'temp_password' in st.session_state:
                            del st.session_state['temp_password']
                        st.rerun()
                    else:
                        st.error(f"Failed to change password: {message}")
            
            if cancel_button:
                # Clear session and return to login
                st.session_state.clear()
                st.rerun()

def logout_user():
    """Logout the current user"""
    # Clear session cookie
    clear_session_cookie()
    
    # Clear all session state
    keys_to_clear = ['authenticated', 'username', 'user_role', 'user_full_name', 'user_id', 'last_activity', 'session_token']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def store_session(username, role, full_name, user_id):
    """Store session data in cookies"""
    import time
    import hashlib
    
    # Create session token
    timestamp = str(int(time.time()))
    session_data = f"{username}|{role}|{full_name}|{user_id or ''}|{timestamp}"
    
    # Store in cookie using JavaScript
    st.components.v1.html(f"""
    <script>
        document.cookie = "stranz_session={session_data}; path=/; max-age=7200"; // 2 hours
        document.cookie = "stranz_activity={timestamp}; path=/; max-age=7200";
    </script>
    """, height=0)
    
    # Also store in session state
    st.session_state.session_token = session_data
    st.session_state.last_activity = datetime.datetime.now()

def get_cookie_value(cookie_name):
    """Get cookie value using JavaScript"""
    # This is a workaround since we can't directly access cookies in Streamlit
    # We'll use session state persistence instead
    return None

def check_stored_session():
    """Check for existing session and restore if valid"""
    # Check if session data exists in session state from previous run
    if hasattr(st.session_state, '_session_checked'):
        return
    
    st.session_state._session_checked = True
    
    # Try to restore from session state persistence
    if ('session_token' in st.session_state and 
        'last_activity' in st.session_state and
        not st.session_state.get('authenticated', False)):
        
        try:
            # Restore session without timeout check
            current_time = datetime.datetime.now()
            
            # Parse session token
            token_parts = st.session_state.session_token.split('|')
            if len(token_parts) >= 4:
                username, role, full_name, user_id = token_parts[:4]
                
                # Restore session
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_role = role
                st.session_state.user_full_name = full_name
                st.session_state.user_id = user_id if user_id else None
                st.session_state.last_activity = current_time
        except Exception:
            # Invalid session data, clear it
            clear_session_data()

def clear_session_cookie():
    """Clear session cookies"""
    st.components.v1.html("""
    <script>
        document.cookie = "stranz_session=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        document.cookie = "stranz_activity=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    </script>
    """, height=0)

def clear_session_data():
    """Clear session data from session state"""
    keys_to_clear = ['session_token', 'last_activity']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def check_session_timeout():
    """Session timeout disabled - just update last activity"""
    if st.session_state.get('authenticated'):
        # Update last activity on each interaction (no timeout check)
        st.session_state.last_activity = datetime.datetime.now()
    
    return False

def get_financial_year():
    """Get current financial year token (YYYY format for FY YYYY-YY+1)"""
    current_date = datetime.datetime.now()
    if current_date.month >= 4:  # April onwards is new FY
        return str(current_date.year)[-2:] + str(current_date.year + 1)[-2:]
    else:
        return str(current_date.year - 1)[-2:] + str(current_date.year)[-2:]

def generate_booking_number():
    """Generate booking number: STZB2526-00001"""
    fy_token = get_financial_year()
    counter = get_next_counter_value('booking_counter')
    return f"STZB{fy_token}-{counter:05d}"

def generate_invoice_number():
    """Generate invoice number: 2526STZ-00001"""
    fy_token = get_financial_year()
    counter = get_next_counter_value('invoice_counter')
    return f"{fy_token}STZ-{counter:05d}"

def generate_quotation_number():
    """Generate quotation number: STZQ2526-00001"""
    fy_token = get_financial_year()
    counter = get_next_counter_value('quotation_counter')
    return f"STZQ{fy_token}-{counter:05d}"

def generate_dsr_number():
    """Generate DSR number: DSR251100001"""
    current_date = datetime.datetime.now()
    year_token = str(current_date.year)[-2:]
    month_token = f"{current_date.month:02d}"
    counter = get_next_counter_value('dsr_counter')
    return f"DSR{year_token}{month_token}{counter:05d}"

def main():
    st.set_page_config(
        page_title="Stranz Transport Management System",
        page_icon="🚚",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )
    
    # Force light theme by setting theme configuration
    st.markdown("""
    <script>
    const elements = parent.document.querySelectorAll('.stApp');
    elements.forEach(el => {
        el.setAttribute('data-theme', 'light');
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Database Management Panel (temporary for schema updates)
    if st.sidebar.button("Admin: Reset Database Schema"):
        from database import recreate_database_schema
        with st.spinner("Updating database schema..."):
            if recreate_database_schema():
                st.success("Database schema updated successfully!")
                st.rerun()
            else:
                st.error("Failed to update database schema")
    
    # Check authentication
    if not st.session_state.authenticated:
        show_login_page()
        return
    
    # Session timeout check disabled to prevent automatic logout
    # if check_session_timeout():
    #     return
    
    # Custom CSS for modern UI design
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Import Flaticon uicons */
    @import url('https://cdn-uicons.flaticon.com/2.6.0/uicons-thin-rounded/css/uicons-thin-rounded.css');
    
    /* Global Styles */
    .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f8fafc;
    }
    
    /* Remove forced text colors - let Streamlit handle theme-based colors naturally 
       Only preserve specific styling for metric cards and section headers */
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stActionButton {display:none;}
    
    /* Login Page Styling */
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .login-card {
        background: white;
        padding: 3rem;
        border-radius: 16px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.1);
        width: 100%;
        max-width: 400px;
        text-align: center;
    }
    
    .login-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    
    .login-subtitle {
        color: #64748b;
        margin-bottom: 2rem;
    }
    
    /* Sidebar Styling */
    .stSidebar {
        background: linear-gradient(180deg, #1e293b 0%, #334155 100%) !important;
    }
    
    .stSidebar > div {
        background: linear-gradient(180deg, #1e293b 0%, #334155 100%) !important;
        padding-top: 1rem;
    }
    
    /* Force all sidebar text to be light */
    .stSidebar, .stSidebar *,
    .stSidebar .stMarkdown, .stSidebar .stMarkdown *,
    .stSidebar p, .stSidebar div, .stSidebar span,
    .stSidebar [data-testid="stMarkdownContainer"] *,
    .stSidebar .element-container * {
        color: #e2e8f0 !important;
    }
    
    .stSidebar .stSelectbox label {
        color: #e2e8f0 !important;
        font-weight: 500;
    }
    
    .stSidebar .stMetric {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 0.75rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }
    
    .stSidebar .stMetric [data-testid="metric-container"] {
        background-color: transparent;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stSidebar .stMetric [data-testid="metric-container"] > div {
        color: #e2e8f0 !important;
    }
    
    .stSidebar .stMetric [data-testid="metric-container"] [data-testid="metric-label"] {
        color: #cbd5e1 !important;
        font-size: 0.75rem !important;
    }
    
    .stSidebar .stMetric [data-testid="metric-container"] [data-testid="metric-value"] {
        color: #f1f5f9 !important;
        font-weight: 600 !important;
    }
    
    /* Navigation Button Styling */
    .stSidebar .stButton > button {
        width: 100% !important;
        padding: 0.75rem 1rem !important;
        margin-bottom: 0.5rem !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
        text-align: left !important;
        cursor: pointer;
        transition: all 0.3s ease;
        font-weight: 500 !important;
        justify-content: flex-start !important;
    }
    
    .stSidebar .stButton > button:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        transform: translateX(5px);
        color: white !important;
    }
    
    .stSidebar .stButton > button:focus {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border-color: #667eea !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
    }
    
    .stSidebar .stButton > button:active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border-color: #667eea !important;
        color: white !important;
    }
    
    /* Main Content Area */
    .main .block-container {
        background-color: #f8fafc;
        color: #1e293b;
    }
    
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        color: white !important;
    }
    
    .welcome-text {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0;
        color: white !important;
    }
    
    /* Metric Cards */
    .metric-row {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        flex: 1;
        border-radius: 16px;
        padding: 2rem 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 100px;
        height: 100px;
        background: rgba(255,255,255,0.1);
        border-radius: 50%;
        transform: translate(30px, -30px);
    }
    
    .metric-card-purple {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .metric-card-pink {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    
    .metric-card-blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    
    .metric-card-orange {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }
    
    .metric-title {
        font-size: 0.9rem;
        font-weight: 500;
        opacity: 0.9;
        margin-bottom: 0.5rem;
        color: white !important;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        position: relative;
        z-index: 1;
        color: white !important;
    }
    
    /* Table Styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .stDataFrame > div {
        border-radius: 12px;
    }
    
    /* Section Headers - preserve emoji colors while styling text appropriately */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 2rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Text Elements in main content - let Streamlit handle theme colors */
    
    /* Labels and form elements - remove forced styling */
    
    /* Buttons */
    .main .stButton > button {
        border-radius: 8px !important;
        border: none !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.3s ease;
    }
    
    .main .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
    }
    
    /* Selectbox Styling */
    .stSelectbox > div > div {
        border-radius: 8px;
        border-color: #e2e8f0;
    }
    
    /* Input styling - completely remove ALL styling to let Streamlit handle everything */
    
    /* Status badges */
    .status-delivered {
        background-color: #10b981;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .status-dispatched {
        background-color: #f59e0b;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    /* Expander and alert styling - let Streamlit handle theme colors */
    </style>
    """, unsafe_allow_html=True)
    
    # Header with modern design and user info
    user_name = st.session_state.get('user_full_name', 'User')
    user_role = st.session_state.get('user_role', 'Guest')
    
    # Get current page for header display
    page = st.session_state.get('current_page', 'Dashboard')
    
    header_col1, header_col2 = st.columns([3, 1])
    
    with header_col1:
        st.markdown(f'''
        <div class="main-header" style="padding: 1rem; margin-bottom: 1rem;">
            <div>
                <h3 class="main-title" style="font-size: 1.5rem; margin: 0;">{page}</h3>
            </div>
            <div>
                <p class="welcome-text" style="font-size: 0.8rem;">Welcome, {user_name} ({user_role})</p>
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    with header_col2:
        if st.button("🚪 Logout", key="logout_btn"):
            logout_user()
    
    # Sidebar navigation with modern dark theme
    with st.sidebar:
        # Brand header
        st.markdown('''
        <div style="text-align: center; padding: 1rem 0 2rem 0;">
            <h2 style="color: #e2e8f0; font-weight: 700; font-size: 1.5rem; margin: 0;">STRANZ TMS</h2>
        </div>
        ''', unsafe_allow_html=True)
        
        # Initialize page selection in session state
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "Dashboard"
        
        # Custom CSS for navigation buttons with icons
        st.markdown("""
        <style>
            .nav-link {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.75rem 1rem;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                color: #e2e8f0 !important;
                text-decoration: none;
                font-weight: 500;
                font-size: 0.95rem;
                margin-bottom: 0.5rem;
                background: transparent;
            }
            .nav-link:hover {
                background: rgba(255,255,255,0.15) !important;
            }
            .nav-link.active {
                background: rgba(255,255,255,0.1) !important;
            }
            .nav-link i {
                font-size: 1.2rem;
                width: 1.2rem;
                text-align: center;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Navigation buttons with Flaticon uicons
        pages = [
            ("Dashboard", "fi-tr-dashboard"),
            ("Quotations", "fi-tr-file-invoice"), 
            ("Bookings", "fi-tr-calendar-check"),
            ("Invoicing", "fi-tr-file-invoice-dollar"),
            ("Customer Payments", "fi-tr-hand-holding-usd"),
            ("Vendor Management", "fi-tr-users-alt"),
            ("Company Expenses", "fi-tr-sack-dollar"),
            ("Vehicle Master", "fi-tr-shipping-fast"),
            ("Pricing Management", "fi-tr-tags"),
            ("Notes & Tracking", "fi-tr-comment-alt-dots"),
            ("Audit Exports", "fi-tr-file-export")
        ]
        
        # Add User Management only for administrators
        if st.session_state.get('user_role') == 'Administrator':
            pages.append(("User Management", "fi-tr-users"))
        
        # Create navigation with columns for icon + button
        for page_name, icon_class in pages:
            col1, col2 = st.columns([0.12, 0.88])
            
            with col1:
                # Display icon
                st.markdown(f'<i class="fi {icon_class}" style="color: #e2e8f0; font-size: 1.2rem; line-height: 2.5;"></i>', unsafe_allow_html=True)
            
            with col2:
                # Button without extra spacing
                if st.button(page_name, key=f"nav_{page_name}", use_container_width=True):
                    st.session_state.current_page = page_name
                    st.rerun()
    
    # Main content area based on selected page
    if page == "Dashboard":
        dashboard.show()
    elif page == "Quotations":
        quotations.show()
    elif page == "Bookings":
        bookings.show()
    elif page == "Invoicing":
        invoicing.show()
    elif page == "Customer Payments":
        customer_payments.show()
    elif page == "Vendor Management":
        vendor_management.show()
    elif page == "Company Expenses":
        company_expenses.show()
    elif page == "Vehicle Master":
        vehicle_master.show()
    elif page == "Pricing Management":
        pricing_management_ui.pricing_management_page()
    elif page == "Notes & Tracking":
        notes.show()
    elif page == "Audit Exports":
        audit_exports.show()
    elif page == "User Management":
        user_management.show()
    
    # Footer
    st.markdown("---")
    st.markdown("**Stranz Transport Management System v1.0** | Prepared by: Saran S P | Contact: admin@stranz.in")

if __name__ == "__main__":
    main()