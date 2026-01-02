import streamlit as st
import pandas as pd
import datetime
import uuid

def safe_format_date(date_field, format_str='%Y-%m-%d'):
    """Safely format date from various date formats"""
    try:
        if isinstance(date_field, str):
            try:
                parsed_date = datetime.datetime.fromisoformat(date_field.replace('Z', '+00:00'))
                return parsed_date.strftime(format_str)
            except:
                try:
                    parsed_date = datetime.datetime.strptime(date_field, '%Y-%m-%d %H:%M:%S')
                    return parsed_date.strftime(format_str)
                except:
                    return date_field
        elif hasattr(date_field, 'strftime'):
            return date_field.strftime(format_str)
        else:
            return str(date_field)
    except:
        return str(date_field)
from typing import Dict, List

def show():
    """Display the vendor management module"""
    # Load data when needed
    from database import load_data_when_needed
    load_data_when_needed('vendors')
    load_data_when_needed('vendor_bills')
    load_data_when_needed('vendor_payments')
    
    st.header("🏪 Vendor Management")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Vendor Bills", "Vendor Payments", "Vendor Ledger", "Manage Vendors"])
    
    with tab1:
        vendor_bills()
    
    with tab2:
        vendor_payments()
    
    with tab3:
        vendor_ledger()
    
    with tab4:
        manage_vendors()

def vendor_bills():
    """Record vendor bills"""
    st.subheader("Record Vendor Bills")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Vendor selection
        if st.session_state.vendors:
            vendor_options = [v['name'] for v in st.session_state.vendors]
            selected_vendor = st.selectbox("Select Vendor*", vendor_options, key="bill_vendor")
        else:
            st.warning("No vendors found. Please add vendors first.")
            return
    
    with col2:
        if st.button("Add New Vendor"):
            show_add_vendor_form()
    
    # Bill details
    col1, col2, col3 = st.columns(3)
    
    with col1:
        bill_date = st.date_input("Bill Date*", value=datetime.datetime.now().date(), key="bill_date")
        bill_number = st.text_input("Bill Number", key="bill_number")
        bill_amount = st.number_input("Bill Amount (₹)*", min_value=0.0, value=0.0, key="bill_amount")
    
    with col2:
        bill_category = st.selectbox(
            "Category*",
            ["Fuel", "Maintenance", "Tolls", "Office Expenses", "Loans", "Insurance", 
             "Driver Salary", "Vehicle Parts", "Vehicle Vendor", "Permits", "Other"],
            key="bill_category"
        )
        due_date = st.date_input("Due Date", value=bill_date + datetime.timedelta(days=30), key="bill_due_date")
    
    with col3:
        gst_amount = st.number_input("GST Amount (₹)", min_value=0.0, value=0.0, key="bill_gst")
        total_amount = bill_amount + gst_amount
        st.metric("Total Amount", f"₹{total_amount:,.2f}")
    
    description = st.text_area("Description", key="bill_description")
    
    if st.button("Record Bill", type="primary"):
        if not selected_vendor or bill_amount <= 0:
            st.error("Vendor and bill amount are required")
            return
        
        vendor = next((v for v in st.session_state.vendors if v['name'] == selected_vendor), None)
        
        bill = {
            'id': str(uuid.uuid4()),
            'vendor_id': vendor['id'],
            'vendor_name': vendor['name'],
            'bill_date': bill_date,
            'bill_number': bill_number,
            'bill_amount': bill_amount,
            'gst_amount': gst_amount,
            'total_amount': total_amount,
            'category': bill_category,
            'description': description,
            'due_date': due_date,
            'status': 'Unpaid',
            'outstanding_amount': total_amount,
            'created_date': datetime.datetime.now()
        }
        
        # Save to database
        from app import save_vendor_bill
        if save_vendor_bill(bill):
            st.success(f"Bill recorded for {selected_vendor}!")
            
            # Clear form
            for key in st.session_state.keys():
                if key.startswith('bill_'):
                    del st.session_state[key]
            
            st.rerun()
        else:
            st.error("Failed to save bill. Please try again.")

def vendor_payments():
    """Record vendor payments"""
    st.subheader("Record Vendor Payments")
    
    # Vendor selection
    vendors_with_bills = list(set([bill['vendor_name'] for bill in st.session_state.vendor_bills if bill['outstanding_amount'] > 0]))
    
    if not vendors_with_bills:
        st.info("No vendors with outstanding bills found.")
        return
    
    selected_vendor = st.selectbox("Select Vendor*", vendors_with_bills, key="payment_vendor")
    
    # Show vendor outstanding bills
    vendor_bills = [bill for bill in st.session_state.vendor_bills 
                   if bill['vendor_name'] == selected_vendor and bill['outstanding_amount'] > 0]
    
    st.markdown("**Outstanding Bills:**")
    bill_data = []
    for bill in vendor_bills:
        bill_data.append({
            'Bill Number': bill.get('bill_number', 'N/A'),
            'Date': bill['bill_date'],
            'Category': bill['category'],
            'Amount': f"₹{bill['total_amount']:,.2f}",
            'Outstanding': f"₹{bill['outstanding_amount']:,.2f}"
        })
    
    df = pd.DataFrame(bill_data)
    st.dataframe(df, use_container_width=True)
    
    st.markdown("---")
    st.markdown("**Payment Details**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        payment_date = st.date_input("Payment Date*", value=datetime.datetime.now().date(), key="vendor_payment_date")
        payment_amount = st.number_input("Payment Amount (₹)*", min_value=0.0, value=0.0, key="vendor_payment_amount")
    
    with col2:
        payment_method = st.selectbox(
            "Payment Method*",
            ["Bank Transfer", "Cash", "Cheque", "UPI"],
            key="vendor_payment_method"
        )
        reference_number = st.text_input("Reference Number", key="vendor_payment_reference")
    
    with col3:
        remarks = st.text_area("Remarks", key="vendor_payment_remarks")
    
    # Bill allocation
    st.markdown("**Allocate Payment to Bills:**")
    allocated_bills = []
    total_allocated = 0
    
    for bill in vendor_bills:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"Bill: {bill.get('bill_number', 'N/A')} - {bill['bill_date']} - Outstanding: ₹{bill['outstanding_amount']:,.2f}")
        
        with col2:
            allocate_amount = st.number_input(
                f"Allocate",
                min_value=0.0,
                max_value=float(bill['outstanding_amount']),
                value=0.0,
                key=f"vendor_allocate_{bill['id']}",
                format="%.2f"
            )
            
            if allocate_amount > 0:
                allocated_bills.append(bill['id'])
                total_allocated += allocate_amount
    
    st.write(f"**Total Allocated:** ₹{total_allocated:,.2f}")
    
    if st.button("Record Payment", type="primary"):
        if payment_amount <= 0:
            st.error("Payment amount is required")
            return
        
        if total_allocated != payment_amount:
            st.error("Total allocated amount must equal payment amount")
            return
        
        vendor = next((v for v in st.session_state.vendors if v['name'] == selected_vendor), None)
        
        # Create payment record
        payment = {
            'id': str(uuid.uuid4()),
            'vendor_id': vendor['id'],
            'vendor_name': vendor['name'],
            'payment_date': payment_date,
            'payment_amount': payment_amount,
            'payment_method': payment_method,
            'reference_number': reference_number,
            'remarks': remarks,
            'allocated_bills': allocated_bills,
            'created_date': datetime.datetime.now()
        }
        
        # Save to database
        from app import save_vendor_payment
        if save_vendor_payment(payment):
            # Update bill outstanding amounts
            for bill in vendor_bills:
                allocate_amount = st.session_state.get(f"vendor_allocate_{bill['id']}", 0.0)
                if allocate_amount > 0:
                    bill['outstanding_amount'] -= allocate_amount
                if bill['outstanding_amount'] <= 0:
                    bill['status'] = 'Paid'
                else:
                    bill['status'] = 'Partially Paid'
            
            st.success(f"Payment of ₹{payment_amount:,.2f} recorded for {selected_vendor}!")
            
            # Clear form
            for key in st.session_state.keys():
                if key.startswith('vendor_payment_') or key.startswith('vendor_allocate_'):
                    del st.session_state[key]
            
            st.rerun()
        else:
            st.error("Failed to save payment. Please try again.")

def vendor_ledger():
    """Generate vendor ledger reports"""
    st.subheader("Vendor Ledger Reports")
    
    if not st.session_state.vendors:
        st.info("No vendors found.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        vendor_options = ["All Vendors"] + [v['name'] for v in st.session_state.vendors]
        selected_vendor = st.selectbox("Select Vendor", vendor_options, key="ledger_vendor")
    
    with col2:
        from_date = st.date_input("From Date", value=datetime.datetime.now() - datetime.timedelta(days=30), key="ledger_from_date")
    
    with col3:
        to_date = st.date_input("To Date", value=datetime.datetime.now().date(), key="ledger_to_date")
    
    if st.button("Generate Ledger", type="primary"):
        generate_vendor_ledger_report(selected_vendor, from_date, to_date)

def generate_vendor_ledger_report(vendor_filter, from_date, to_date):
    """Generate and display vendor ledger report"""
    
    # Filter vendors
    if vendor_filter == "All Vendors":
        selected_vendors = st.session_state.vendors
    else:
        selected_vendors = [v for v in st.session_state.vendors if v['name'] == vendor_filter]
    
    for vendor in selected_vendors:
        st.markdown(f"### Vendor Ledger - {vendor['name']}")
        
        # Filter bills and payments for the period
        vendor_bills = [bill for bill in st.session_state.vendor_bills 
                       if bill['vendor_id'] == vendor['id'] and 
                       from_date <= bill['bill_date'] <= to_date]
        
        vendor_payments = [payment for payment in st.session_state.vendor_payments 
                          if payment['vendor_id'] == vendor['id'] and 
                          from_date <= payment['payment_date'] <= to_date]
        
        # Summary
        total_bills = len(vendor_bills)
        total_bill_amount = sum(bill['total_amount'] for bill in vendor_bills)
        total_payments = len(vendor_payments)
        total_payment_amount = sum(payment['payment_amount'] for payment in vendor_payments)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Bills Raised", total_bills)
        with col2:
            st.metric("Total Bills", f"₹{total_bill_amount:,.2f}")
        with col3:
            st.metric("Payments Made", total_payments)
        with col4:
            st.metric("Total Payments", f"₹{total_payment_amount:,.2f}")
        
        # Category breakdown
        if vendor_bills:
            st.markdown("**Category Breakdown:**")
            category_summary = {}
            for bill in vendor_bills:
                category = bill['category']
                if category not in category_summary:
                    category_summary[category] = 0
                category_summary[category] += bill['total_amount']
            
            category_data = [{'Category': cat, 'Amount': f"₹{amt:,.2f}"} 
                           for cat, amt in category_summary.items()]
            
            df_categories = pd.DataFrame(category_data)
            st.dataframe(df_categories, use_container_width=True)
        
        # Bills table
        if vendor_bills:
            st.markdown("**Bills:**")
            bill_data = []
            for bill in vendor_bills:
                bill_data.append({
                    'Date': bill['bill_date'],
                    'Bill Number': bill.get('bill_number', 'N/A'),
                    'Category': bill['category'],
                    'Amount': f"₹{bill['total_amount']:,.2f}",
                    'Outstanding': f"₹{bill['outstanding_amount']:,.2f}",
                    'Status': bill['status']
                })
            
            df_bills = pd.DataFrame(bill_data)
            st.dataframe(df_bills, use_container_width=True)
        
        # Payments table
        if vendor_payments:
            st.markdown("**Payments:**")
            payment_data = []
            for payment in vendor_payments:
                payment_data.append({
                    'Date': payment['payment_date'],
                    'Amount': f"₹{payment['payment_amount']:,.2f}",
                    'Method': payment['payment_method'],
                    'Reference': payment.get('reference_number', ''),
                    'Remarks': payment.get('remarks', '')
                })
            
            df_payments = pd.DataFrame(payment_data)
            st.dataframe(df_payments, use_container_width=True)
        
        st.markdown("---")

def manage_vendors():
    """Manage vendor information"""
    st.subheader("Manage Vendors")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("**Existing Vendors:**")
        
        if st.session_state.vendors:
            vendor_data = []
            for vendor in st.session_state.vendors:
                # Calculate outstanding
                vendor_bills = [bill for bill in st.session_state.vendor_bills if bill['vendor_id'] == vendor['id']]
                total_outstanding = sum(bill['outstanding_amount'] for bill in vendor_bills)
                
                vendor_data.append({
                    'Name': vendor['name'],
                    'Contact': vendor.get('contact_person', '') or vendor.get('phone', ''),
                    'Category': vendor.get('vendor_type', ''),
                    'Outstanding': f"₹{total_outstanding:,.2f}",
                    'Created': safe_format_date(vendor['created_date'])
                })
            
            df = pd.DataFrame(vendor_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No vendors found.")
    
    with col2:
        if st.button("Add New Vendor", type="primary"):
            st.session_state.show_vendor_form = True
            st.rerun()
    
    # Show add vendor form if requested
    if st.session_state.get('show_vendor_form', False):
        show_add_vendor_form()

def show_add_vendor_form():
    """Show form to add new vendor"""
    st.markdown("---")
    st.markdown("### Add New Vendor")
    
    col1, col2 = st.columns(2)
    
    with col1:
        vendor_name = st.text_input("Vendor Name*", key="new_vendor_name")
        vendor_contact = st.text_input("Contact Number", key="new_vendor_contact")
        vendor_email = st.text_input("Email", key="new_vendor_email")
    
    with col2:
        vendor_category = st.selectbox(
            "Category",
            ["Fuel Supplier", "Maintenance", "Parts Supplier", "Insurance", "Bank/Finance", "Government", "Other"],
            key="new_vendor_category"
        )
        vendor_gst = st.text_input("GST Number", key="new_vendor_gst")
        vendor_address = st.text_area("Address", key="new_vendor_address")
    
    button_col1, button_col2, button_col3 = st.columns([1, 1, 2])
    
    with button_col1:
        if st.button("Add Vendor", type="primary"):
            if not vendor_name:
                st.error("Vendor name is required")
                return
            
            vendor = {
                'id': str(uuid.uuid4()),
                'name': vendor_name,
                'contact_person': vendor_contact,  # Use contact_person instead of contact
                'phone': vendor_contact,  # Also map to phone field
                'email': vendor_email,
                'vendor_type': vendor_category,  # Use vendor_type instead of category
                'gst_number': vendor_gst,
                'address': vendor_address,
                'created_date': datetime.datetime.now()
            }
            
            # Save to database
            from app import save_vendor
            if save_vendor(vendor):
                # Refresh vendors data from database
                from database import load_data_when_needed
                st.session_state.vendors = []  # Clear cache to force reload
                load_data_when_needed('vendors')
                
                # Add to session state for immediate display
                if 'vendors' not in st.session_state:
                    st.session_state.vendors = []
                st.session_state.vendors.append(vendor)
                
                st.success(f"Vendor {vendor_name} added successfully!")
                
                # Clear form and hide it
                for key in list(st.session_state.keys()):
                    if key.startswith('new_vendor_'):
                        del st.session_state[key]
                st.session_state.show_vendor_form = False
                
                st.rerun()
            else:
                st.error("Failed to save vendor. Please try again.")
    
    with button_col2:
        if st.button("Cancel"):
            # Clear form and hide it
            for key in list(st.session_state.keys()):
                if key.startswith('new_vendor_'):
                    del st.session_state[key]
            st.session_state.show_vendor_form = False
            st.rerun()