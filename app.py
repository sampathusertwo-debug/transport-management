import streamlit as st
import pandas as pd
import datetime
import json
from typing import Dict, List, Optional
import uuid

# Import modules
from modules import quotations, bookings, invoicing, customer_payments, vendor_management, company_expenses, vehicle_master, dashboard, audit_exports

# Initialize session state
def init_session_state():
    """Initialize session state for data storage"""
    if 'quotations' not in st.session_state:
        st.session_state.quotations = []
    if 'bookings' not in st.session_state:
        st.session_state.bookings = []
    if 'invoices' not in st.session_state:
        st.session_state.invoices = []
    if 'customers' not in st.session_state:
        st.session_state.customers = []
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
    if 'counters' not in st.session_state:
        st.session_state.counters = {
            'booking_counter': 1,
            'invoice_counter': 1,
            'quotation_counter': 1,
            'dsr_counter': 1
        }

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
    counter = st.session_state.counters['booking_counter']
    st.session_state.counters['booking_counter'] += 1
    return f"STZB{fy_token}-{counter:05d}"

def generate_invoice_number():
    """Generate invoice number: 2526STZ-00001"""
    fy_token = get_financial_year()
    counter = st.session_state.counters['invoice_counter']
    st.session_state.counters['invoice_counter'] += 1
    return f"{fy_token}STZ-{counter:05d}"

def generate_quotation_number():
    """Generate quotation number: STZQ2526-00001"""
    fy_token = get_financial_year()
    counter = st.session_state.counters['quotation_counter']
    st.session_state.counters['quotation_counter'] += 1
    return f"STZQ{fy_token}-{counter:05d}"

def generate_dsr_number():
    """Generate DSR number: DSR251100001"""
    current_date = datetime.datetime.now()
    year_token = str(current_date.year)[-2:]
    month_token = f"{current_date.month:02d}"
    counter = st.session_state.counters['dsr_counter']
    st.session_state.counters['dsr_counter'] += 1
    return f"DSR{year_token}{month_token}{counter:05d}"

def main():
    st.set_page_config(
        page_title="Stranz Transport Management System",
        page_icon="🚚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        border-bottom: 3px solid #1f77b4;
        padding-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .overdue-red {
        background-color: #ffebee;
        color: #c62828;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
    .overdue-yellow {
        background-color: #fffef7;
        color: #f57f17;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
    .on-time {
        background-color: #e8f5e8;
        color: #2e7d32;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="main-header">🚚 Stranz Transport Management System</div>', unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        
        # Main modules
        st.header("📋 Core Modules")
        page = st.selectbox(
            "Select Module",
            [
                "Dashboard",
                "Quotations",
                "Bookings",
                "Invoicing",
                "Customer Payments",
                "Vendor Management",
                "Company Expenses",
                "Vehicle Master",
                "Audit Exports"
            ]
        )
        
        # Quick stats
        st.header("📊 Quick Stats")
        total_bookings = len(st.session_state.bookings)
        total_invoices = len(st.session_state.invoices)
        total_customers = len(st.session_state.customers)
        total_vehicles = len(st.session_state.vehicles)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Bookings", total_bookings)
            st.metric("Customers", total_customers)
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