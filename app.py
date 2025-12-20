import streamlit as st
import pandas as pd
import datetime
import json
from typing import Dict, List, Optional
import uuid

# Import modules
from modules import quotations, bookings, invoicing, customer_payments, vendor_management, company_expenses, vehicle_master, dashboard, audit_exports

# Import database functions
from database import init_database, execute_query, get_next_counter_value, save_to_database, update_in_database, refresh_data

# Make database functions globally available
def save_booking(booking_data):
    """Save booking to database"""
    return save_to_database('bookings', booking_data)

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
            from database import fix_database_schema
            fix_database_schema()
        else:
            st.error("Failed to connect to database")
            st.stop()
    
    # Initialize session state variables
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
    # Demo users - in production, this would connect to a database
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
    st.markdown('''
    <div class="login-container">
        <div class="login-card">
            <h1 class="login-title">STRANZ TMS</h1>
            <p class="login-subtitle">Transport Management System</p>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Login to Continue")
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col_login, col_demo = st.columns(2)
            
            with col_login:
                login_button = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            with col_demo:
                demo_button = st.form_submit_button("Demo Login", use_container_width=True)
            
            if login_button:
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.user_role = user['role']
                        st.session_state.user_full_name = user['full_name']
                        st.success(f"Welcome, {user['full_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please enter both username and password")
            
            if demo_button:
                # Demo login as admin
                st.session_state.authenticated = True
                st.session_state.username = 'admin'
                st.session_state.user_role = 'Administrator'
                st.session_state.user_full_name = 'Admin User'
                st.success("Demo login successful!")
                st.rerun()
        
        # Demo credentials info
        with st.expander("🔍 Demo Credentials"):
            st.markdown("""
            **Administrator:**
            - Username: `admin`
            - Password: `admin123`
            
            **Manager:**
            - Username: `manager`
            - Password: `manager123`
            
            **Operator:**
            - Username: `operator`
            - Password: `operator123`
            """)

def logout_user():
    """Logout the current user"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_role = None
    st.session_state.user_full_name = None
    st.rerun()

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
    if st.sidebar.button("🔧 Admin: Reset Database Schema"):
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
    
    # Custom CSS for modern UI design
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
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
    
    header_col1, header_col2 = st.columns([3, 1])
    
    with header_col1:
        st.markdown(f'''
        <div class="main-header">
            <div>
                <h1 class="main-title">Dashboard</h1>
            </div>
            <div>
                <p class="welcome-text">Welcome, {user_name} ({user_role})</p>
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    with header_col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
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
        
        # Navigation buttons
        pages = [
            ("Dashboard", "📊"),
            ("Quotations", "📋"), 
            ("Bookings", "📦"),
            ("Invoicing", "🧾"),
            ("Customer Payments", "💰"),
            ("Vendor Management", "🚛"),
            ("Company Expenses", "💸"),
            ("Vehicle Master", "🚗"),
            ("Audit Exports", "📤")
        ]
        
        for page_name, icon in pages:
            if st.button(f"{icon} {page_name}", key=f"nav_{page_name}", use_container_width=True):
                st.session_state.current_page = page_name
                st.rerun()
        
        page = st.session_state.current_page
        
        # Quick stats with modern styling
        st.markdown('''
        <div style="margin-top: 2rem;">
            <h3 style="color: #e2e8f0; font-size: 0.9rem; font-weight: 500; margin-bottom: 1rem; opacity: 0.8;">📊 QUICK STATS</h3>
        </div>
        ''', unsafe_allow_html=True)
        
        total_bookings = len(st.session_state.bookings)
        total_invoices = len(st.session_state.invoices)
        # Count unique customers by name, not total booking instances
        unique_customers = len(set(customer['name'] for customer in st.session_state.customers))
        total_vehicles = len(st.session_state.vehicles)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Bookings", total_bookings)
            st.metric("Customers", unique_customers)
        with col2:
            st.metric("Invoices", total_invoices)
            st.metric("Vehicles", total_vehicles)
    
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
    elif page == "Audit Exports":
        audit_exports.show()
    
    # Footer
    st.markdown("---")
    st.markdown("**Stranz Transport Management System v1.0** | Prepared by: Saran S P | Contact: admin@stranz.in")

if __name__ == "__main__":
    main()