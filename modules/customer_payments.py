import streamlit as st
import pandas as pd
import datetime
import uuid
from typing import Dict, List

def show():
    """Display the customer payments module"""
    # Load data when needed
    from database import load_data_when_needed
    load_data_when_needed('invoices')
    load_data_when_needed('customer_payments')
    load_data_when_needed('customers')
    
    st.header("💰 Customer Payments Management")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Record Payment", "View Payments", "Customer Statements", "Outstanding Reports"])
    
    with tab1:
        record_payment()
    
    with tab2:
        view_payments()
    
    with tab3:
        customer_statements()
    
    with tab4:
        outstanding_reports()

def record_payment():
    """Record a new customer payment"""
    st.subheader("Record Customer Payment")
    
    # Check for invoice to pay
    if 'selected_invoice_id' in st.session_state:
        invoice = next((inv for inv in st.session_state.invoices if inv['id'] == st.session_state.selected_invoice_id), None)
        if invoice:
            st.info(f"Recording payment for Invoice {invoice['invoice_number']}")
            record_invoice_payment(invoice)
            return
    
    # Manual payment recording
    record_manual_payment()

def record_invoice_payment(invoice):
    """Record payment for specific invoice"""
    st.markdown("**Invoice Details**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Invoice Number:** {invoice['invoice_number']}")
        st.write(f"**Customer:** {invoice['customer_name']}")
        st.write(f"**Invoice Date:** {invoice['invoice_date']}")
        st.write(f"**Due Date:** {invoice['due_date']}")
    
    with col2:
        st.write(f"**Total Amount:** ₹{invoice['total_amount']:,.2f}")
        st.write(f"**Outstanding:** ₹{invoice['outstanding_amount']:,.2f}")
        st.write(f"**Status:** {invoice['status']}")
        
        # Calculate days overdue
        days_overdue = (datetime.datetime.now().date() - invoice['due_date']).days
        if days_overdue > 0:
            st.write(f"**Days Overdue:** {days_overdue}")
    
    st.markdown("---")
    st.markdown("**Payment Details**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        payment_date = st.date_input("Payment Date*", value=datetime.datetime.now().date(), key="payment_date")
        payment_amount = st.number_input(
            "Payment Amount (₹)*", 
            min_value=0.0, 
            value=float(invoice['outstanding_amount']),
            max_value=float(invoice['outstanding_amount']),
            key="payment_amount"
        )
    
    with col2:
        payment_method = st.selectbox(
            "Payment Method*",
            ["Bank Transfer", "Cash", "Cheque", "UPI", "Card", "Net Banking"],
            key="payment_method"
        )
        reference_number = st.text_input("Reference Number", key="payment_reference", 
                                        help="Bank reference, cheque number, UPI transaction ID, etc.")
    
    with col3:
        bank_name = st.text_input("Bank Name", key="payment_bank")
        remarks = st.text_area("Remarks", key="payment_remarks")
    
    # Payment allocation (auto-allocated to this invoice)
    st.markdown("**Payment Allocation**")
    st.info(f"This payment will be automatically allocated to Invoice {invoice['invoice_number']}")
    
    # Submit payment
    if st.button("Record Payment", type="primary"):
        if not payment_date or payment_amount <= 0:
            st.error("Payment date and amount are required")
            return
        
        # Create payment record
        payment = {
            'id': str(uuid.uuid4()),
            'customer_id': invoice['customer_id'],
            'customer_name': invoice['customer_name'],
            'payment_date': payment_date,
            'payment_amount': payment_amount,
            'payment_method': payment_method,
            'reference_number': reference_number,
            'bank_name': bank_name,
            'remarks': remarks,
            'allocation_status': 'Allocated',
            'allocated_invoices': [invoice['invoice_number']],
            'created_date': datetime.datetime.now(),
            'created_by': 'Admin'
        }
        
        # Save to database
        from app import save_payment
        if save_payment(payment):
            # Add to session state for immediate display
            if 'customer_payments' not in st.session_state:
                st.session_state.customer_payments = []
            st.session_state.customer_payments.append(payment)
            
            # Update invoice outstanding
            invoice['outstanding_amount'] -= payment_amount
            
            # Update invoice status
            if invoice['outstanding_amount'] <= 0:
                invoice['status'] = 'Paid'
            else:
                invoice['status'] = 'Partially Paid'
                
            st.success(f"Payment of ₹{payment_amount:,.2f} recorded successfully!")
        else:
            st.error("Failed to save payment. Please try again.")
        
        # Clear selected invoice
        if 'selected_invoice_id' in st.session_state:
            del st.session_state.selected_invoice_id
        
        st.success(f"Payment of ₹{payment_amount:,.2f} recorded successfully!")
        
        # Clear form
        for key in st.session_state.keys():
            if key.startswith('payment_'):
                del st.session_state[key]
        
        st.rerun()

def record_manual_payment():
    """Record payment manually"""
    
    # Customer selection
    customers_with_outstanding = []
    for customer in st.session_state.customers:
        outstanding = sum(inv['outstanding_amount'] for inv in st.session_state.invoices if inv['customer_id'] == customer['id'])
        if outstanding > 0:
            customers_with_outstanding.append(customer)
    
    if not customers_with_outstanding:
        st.info("No customers with outstanding invoices found.")
        return
    
    customer_options = [f"{c['name']} - Outstanding: ₹{sum(inv['outstanding_amount'] for inv in st.session_state.invoices if inv['customer_id'] == c['id']):,.2f}" 
                       for c in customers_with_outstanding]
    
    selected_customer_option = st.selectbox("Select Customer*", customer_options, key="manual_customer_select")
    
    if not selected_customer_option:
        return
    
    customer_name = selected_customer_option.split(" - ")[0]
    selected_customer = next((c for c in customers_with_outstanding if c['name'] == customer_name), None)
    
    if not selected_customer:
        return
    
    # Show customer outstanding invoices
    customer_invoices = [inv for inv in st.session_state.invoices if inv['customer_id'] == selected_customer['id'] and inv['outstanding_amount'] > 0]
    
    st.markdown("**Customer Outstanding Invoices**")
    invoice_data = []
    for inv in customer_invoices:
        days_overdue = max(0, (datetime.datetime.now().date() - inv['due_date']).days)
        invoice_data.append({
            'Invoice Number': inv['invoice_number'],
            'Date': inv['invoice_date'],
            'Due Date': inv['due_date'],
            'Amount': f"₹{inv['total_amount']:,.2f}",
            'Outstanding': f"₹{inv['outstanding_amount']:,.2f}",
            'Days Overdue': days_overdue
        })
    
    df = pd.DataFrame(invoice_data)
    st.dataframe(df, use_container_width=True)
    
    st.markdown("---")
    st.markdown("**Payment Details**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        payment_date = st.date_input("Payment Date*", value=datetime.datetime.now().date(), key="manual_payment_date")
        payment_amount = st.number_input("Payment Amount (₹)*", min_value=0.0, value=0.0, key="manual_payment_amount")
    
    with col2:
        payment_method = st.selectbox(
            "Payment Method*",
            ["Bank Transfer", "Cash", "Cheque", "UPI", "Card", "Net Banking"],
            key="manual_payment_method"
        )
        reference_number = st.text_input("Reference Number", key="manual_payment_reference")
    
    with col3:
        bank_name = st.text_input("Bank Name", key="manual_payment_bank")
        remarks = st.text_area("Remarks", key="manual_payment_remarks")
    
    # Payment allocation options
    st.markdown("**Payment Allocation**")
    
    allocation_type = st.radio(
        "Allocation Type",
        ["Allocate to specific invoices", "Unallocated payment"],
        key="allocation_type",
        help="Unallocated payments reduce total outstanding but can be allocated to specific invoices later"
    )
    
    allocated_invoices = []
    total_allocated = 0
    
    if allocation_type == "Allocate to specific invoices":
        st.markdown("**Select invoices to allocate payment:**")
        
        for inv in customer_invoices:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"{inv['invoice_number']} - Due: {inv['due_date']} - Outstanding: ₹{inv['outstanding_amount']:,.2f}")
            
            with col2:
                allocate_amount = st.number_input(
                    f"Allocate Amount",
                    min_value=0.0,
                    max_value=float(inv['outstanding_amount']),
                    value=0.0,
                    key=f"allocate_{inv['id']}",
                    format="%.2f"
                )
            
            with col3:
                if allocate_amount > 0:
                    allocated_invoices.append(inv['invoice_number'])
                    total_allocated += allocate_amount
        
        st.write(f"**Total Allocated:** ₹{total_allocated:,.2f}")
        
        if total_allocated > payment_amount:
            st.error("Total allocated amount cannot exceed payment amount")
            return
    
    # Submit payment
    if st.button("Record Payment", type="primary"):
        if not payment_date or payment_amount <= 0:
            st.error("Payment date and amount are required")
            return
        
        if allocation_type == "Allocate to specific invoices" and total_allocated != payment_amount:
            st.error("Total allocated amount must equal payment amount")
            return
        
        # Create payment record
        payment = {
            'id': str(uuid.uuid4()),
            'customer_id': selected_customer['id'],
            'customer_name': selected_customer['name'],
            'payment_date': payment_date,
            'payment_amount': payment_amount,
            'payment_method': payment_method,
            'reference_number': reference_number,
            'bank_name': bank_name,
            'remarks': remarks,
            'allocation_status': 'Allocated' if allocation_type == "Allocate to specific invoices" else 'Unallocated',
            'allocated_invoices': allocated_invoices if allocation_type == "Allocate to specific invoices" else [],
            'created_date': datetime.datetime.now(),
            'created_by': 'Admin'
        }
        
        # Save to database
        from app import save_payment
        if save_payment(payment):
            # Add to session state for immediate display
            if 'customer_payments' not in st.session_state:
                st.session_state.customer_payments = []
            st.session_state.customer_payments.append(payment)
            
            # Update invoice outstanding if allocated
            if allocation_type == "Allocate to specific invoices":
                for inv in customer_invoices:
                    allocate_amount = st.session_state.get(f"allocate_{inv['id']}", 0.0)
                if allocate_amount > 0:
                    inv['outstanding_amount'] -= allocate_amount
                    
                    # Update invoice status
                    if inv['outstanding_amount'] <= 0:
                        inv['status'] = 'Paid'
                    else:
                        inv['status'] = 'Partially Paid'
            
            st.success(f"Payment of ₹{payment_amount:,.2f} recorded successfully!")
            
            # Clear form
            for key in st.session_state.keys():
                if key.startswith('manual_payment_') or key.startswith('allocate_'):
                    del st.session_state[key]
            
            st.rerun()
        else:
            st.error("Failed to save payment. Please try again.")

def view_payments():
    """View and manage payments"""
    st.subheader("View Customer Payments")
    
    if not st.session_state.customer_payments:
        st.info("No payments recorded yet.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        customer_filter = st.selectbox(
            "Filter by Customer",
            ["All"] + list(set([p['customer_name'] for p in st.session_state.customer_payments])),
            key="payment_customer_filter"
        )
    
    with col2:
        allocation_filter = st.selectbox(
            "Filter by Allocation",
            ["All", "Allocated", "Unallocated"],
            key="payment_allocation_filter"
        )
    
    with col3:
        date_filter = st.date_input(
            "From Date",
            value=datetime.datetime.now() - datetime.timedelta(days=30),
            key="payment_date_filter"
        )
    
    # Filter payments
    filtered_payments = st.session_state.customer_payments
    
    if customer_filter != "All":
        filtered_payments = [p for p in filtered_payments if p['customer_name'] == customer_filter]
    
    if allocation_filter != "All":
        filtered_payments = [p for p in filtered_payments if p['allocation_status'] == allocation_filter]
    
    filtered_payments = [p for p in filtered_payments if p['payment_date'] >= date_filter]
    
    # Summary
    total_payments = len(filtered_payments)
    total_amount = sum(p['payment_amount'] for p in filtered_payments)
    allocated_payments = len([p for p in filtered_payments if p['allocation_status'] == 'Allocated'])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Payments", total_payments)
    with col2:
        st.metric("Total Amount", f"₹{total_amount:,.2f}")
    with col3:
        st.metric("Allocated Payments", f"{allocated_payments}/{total_payments}")
    
    st.markdown("---")
    
    # Display payments
    for payment in filtered_payments:
        allocation_icon = "✅" if payment['allocation_status'] == 'Allocated' else "⏳"
        
        with st.expander(f"{allocation_icon} {payment['customer_name']} - ₹{payment['payment_amount']:,.2f} - {payment['payment_date']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Customer:** {payment['customer_name']}")
                st.write(f"**Amount:** ₹{payment['payment_amount']:,.2f}")
                st.write(f"**Date:** {payment['payment_date']}")
                st.write(f"**Method:** {payment['payment_method']}")
                if payment.get('reference_number'):
                    st.write(f"**Reference:** {payment['reference_number']}")
            
            with col2:
                st.write(f"**Allocation Status:** {payment['allocation_status']}")
                if payment['allocated_invoices']:
                    st.write(f"**Allocated to:** {', '.join(payment['allocated_invoices'])}")
                if payment.get('bank_name'):
                    st.write(f"**Bank:** {payment['bank_name']}")
                if payment.get('remarks'):
                    st.write(f"**Remarks:** {payment['remarks']}")
            
            # Update allocation for unallocated payments
            if payment['allocation_status'] == 'Unallocated':
                if st.button(f"Update Allocation", key=f"update_{payment['id']}"):
                    update_payment_allocation(payment)

def update_payment_allocation(payment):
    """Update allocation for unallocated payment"""
    st.markdown("### Update Payment Allocation")
    
    # Get customer's outstanding invoices
    customer_invoices = [inv for inv in st.session_state.invoices 
                        if inv['customer_id'] == payment['customer_id'] and inv['outstanding_amount'] > 0]
    
    if not customer_invoices:
        st.warning("No outstanding invoices found for this customer")
        return
    
    st.write(f"**Payment Amount:** ₹{payment['payment_amount']:,.2f}")
    st.markdown("**Outstanding Invoices:**")
    
    allocated_invoices = []
    total_allocated = 0
    
    for inv in customer_invoices:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"{inv['invoice_number']} - Due: {inv['due_date']} - Outstanding: ₹{inv['outstanding_amount']:,.2f}")
        
        with col2:
            allocate_amount = st.number_input(
                f"Amount",
                min_value=0.0,
                max_value=float(min(inv['outstanding_amount'], payment['payment_amount'])),
                value=0.0,
                key=f"update_allocate_{inv['id']}",
                format="%.2f"
            )
            
            if allocate_amount > 0:
                allocated_invoices.append(inv['invoice_number'])
                total_allocated += allocate_amount
    
    st.write(f"**Total Allocated:** ₹{total_allocated:,.2f}")
    
    if st.button("Update Allocation", type="primary"):
        if total_allocated != payment['payment_amount']:
            st.error("Total allocated amount must equal payment amount")
            return
        
        # Update payment allocation
        payment['allocation_status'] = 'Allocated'
        payment['allocated_invoices'] = allocated_invoices
        
        # Update invoice outstanding
        for inv in customer_invoices:
            allocate_amount = st.session_state.get(f"update_allocate_{inv['id']}", 0.0)
            if allocate_amount > 0:
                inv['outstanding_amount'] -= allocate_amount
                
                if inv['outstanding_amount'] <= 0:
                    inv['status'] = 'Paid'
                else:
                    inv['status'] = 'Partially Paid'
        
        st.success("Payment allocation updated successfully!")
        st.rerun()

def customer_statements():
    """Generate customer monthly statements"""
    st.subheader("Customer Monthly Statements")
    
    # Customer and period selection
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.customers:
            customer_options = [c['name'] for c in st.session_state.customers]
            selected_customer = st.selectbox("Select Customer", customer_options, key="statement_customer")
        else:
            st.warning("No customers found")
            return
    
    with col2:
        statement_month = st.selectbox("Month", list(range(1, 13)), index=datetime.datetime.now().month - 1, 
                                     format_func=lambda x: datetime.date(2000, x, 1).strftime('%B'),
                                     key="statement_month")
        statement_year = st.selectbox("Year", [2023, 2024, 2025, 2026], index=2, key="statement_year")
    
    with col3:
        if st.button("Generate Statement", type="primary"):
            generate_monthly_statement(selected_customer, statement_month, statement_year)

def generate_monthly_statement(customer_name, month, year):
    """Generate and display monthly statement for customer"""
    
    customer = next((c for c in st.session_state.customers if c['name'] == customer_name), None)
    if not customer:
        st.error("Customer not found")
        return
    
    # Get data for the period
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    
    # Filter invoices and payments for the period
    period_invoices = [inv for inv in st.session_state.invoices 
                      if inv['customer_id'] == customer['id'] and 
                      start_date <= inv['invoice_date'] <= end_date]
    
    period_payments = [p for p in st.session_state.customer_payments 
                      if p['customer_id'] == customer['id'] and 
                      start_date <= p['payment_date'] <= end_date]
    
    # Get all outstanding invoices (including from previous periods)
    all_customer_invoices = [inv for inv in st.session_state.invoices 
                            if inv['customer_id'] == customer['id'] and inv['outstanding_amount'] > 0]
    
    st.markdown("---")
    st.markdown(f"## Monthly Statement - {customer_name}")
    st.markdown(f"**Period:** {start_date.strftime('%B %Y')} | **Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Customer Details:**")
        st.write(f"Name: {customer['name']}")
        st.write(f"Phone: {customer['phone']}")
        if customer.get('email'):
            st.write(f"Email: {customer['email']}")
        st.write(f"Payment Terms: {customer.get('payment_terms', 30)} days")
    
    with col2:
        # Summary metrics
        total_invoices = len(period_invoices)
        total_invoiced = sum(inv['total_amount'] for inv in period_invoices)
        total_payments = sum(p['payment_amount'] for p in period_payments)
        total_outstanding = sum(inv['outstanding_amount'] for inv in all_customer_invoices)
        
        st.markdown("**Period Summary:**")
        st.write(f"Invoices Generated: {total_invoices}")
        st.write(f"Total Invoiced: ₹{total_invoiced:,.2f}")
        st.write(f"Total Payments: ₹{total_payments:,.2f}")
        st.write(f"Total Outstanding: ₹{total_outstanding:,.2f}")
    
    # Count movements (bookings)
    period_bookings = [b for b in st.session_state.bookings 
                      if b['customer_id'] == customer['id'] and 
                      start_date <= b['pickup_date'] <= end_date and
                      b['status'] == 'Delivered']
    
    st.write(f"**Completed Movements:** {len(period_bookings)}")
    
    st.markdown("---")
    
    # Invoice list
    if period_invoices:
        st.markdown("### Invoices Generated This Period")
        invoice_data = []
        for inv in period_invoices:
            days_overdue = max(0, (datetime.datetime.now().date() - inv['due_date']).days)
            
            # Color coding based on overdue status
            if inv['outstanding_amount'] <= 0:
                status_color = "🟢 Paid"
            elif days_overdue == 0:
                status_color = "🟡 Current"
            elif days_overdue <= 15:
                status_color = "🟠 Due Soon"
            else:
                status_color = "🔴 Overdue"
            
            invoice_data.append({
                'Invoice Number': inv['invoice_number'],
                'Booking Number': inv['booking_number'],
                'Date': inv['invoice_date'],
                'Due Date': inv['due_date'],
                'Amount': f"₹{inv['total_amount']:,.2f}",
                'Paid': f"₹{inv['total_amount'] - inv['outstanding_amount']:,.2f}",
                'Outstanding': f"₹{inv['outstanding_amount']:,.2f}",
                'Days Overdue': days_overdue,
                'Status': status_color
            })
        
        df_invoices = pd.DataFrame(invoice_data)
        st.dataframe(df_invoices, use_container_width=True)
    
    # Payment list
    if period_payments:
        st.markdown("### Payments Received This Period")
        payment_data = []
        for payment in period_payments:
            payment_data.append({
                'Date': payment['payment_date'],
                'Amount': f"₹{payment['payment_amount']:,.2f}",
                'Method': payment['payment_method'],
                'Reference': payment.get('reference_number', ''),
                'Allocation': payment['allocation_status'],
                'Allocated To': ', '.join(payment['allocated_invoices']) if payment['allocated_invoices'] else 'N/A'
            })
        
        df_payments = pd.DataFrame(payment_data)
        st.dataframe(df_payments, use_container_width=True)
    
    # Outstanding summary with aging
    if all_customer_invoices:
        st.markdown("### Outstanding Invoices (All Periods)")
        
        aging_buckets = {'0-30': 0, '31-60': 0, '61-90': 0, '90+': 0}
        outstanding_data = []
        
        for inv in all_customer_invoices:
            days_overdue = max(0, (datetime.datetime.now().date() - inv['due_date']).days)
            
            # Aging bucket
            if days_overdue <= 30:
                aging_buckets['0-30'] += inv['outstanding_amount']
                bucket = '0-30 days'
            elif days_overdue <= 60:
                aging_buckets['31-60'] += inv['outstanding_amount']
                bucket = '31-60 days'
            elif days_overdue <= 90:
                aging_buckets['61-90'] += inv['outstanding_amount']
                bucket = '61-90 days'
            else:
                aging_buckets['90+'] += inv['outstanding_amount']
                bucket = '90+ days'
            
            outstanding_data.append({
                'Invoice Number': inv['invoice_number'],
                'Date': inv['invoice_date'],
                'Due Date': inv['due_date'],
                'Outstanding': f"₹{inv['outstanding_amount']:,.2f}",
                'Days Overdue': days_overdue,
                'Aging Bucket': bucket
            })
        
        df_outstanding = pd.DataFrame(outstanding_data)
        st.dataframe(df_outstanding, use_container_width=True)
        
        # Aging summary
        st.markdown("### Aging Analysis")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("0-30 Days", f"₹{aging_buckets['0-30']:,.2f}")
        with col2:
            st.metric("31-60 Days", f"₹{aging_buckets['31-60']:,.2f}")
        with col3:
            st.metric("61-90 Days", f"₹{aging_buckets['61-90']:,.2f}")
        with col4:
            st.metric("90+ Days", f"₹{aging_buckets['90+']:,.2f}")

def outstanding_reports():
    """Generate outstanding reports"""
    st.subheader("Outstanding Reports")
    
    # All customers outstanding
    st.markdown("### Customer Outstanding Summary")
    
    customer_outstanding = []
    for customer in st.session_state.customers:
        customer_invoices = [inv for inv in st.session_state.invoices if inv['customer_id'] == customer['id']]
        
        total_invoiced = sum(inv['total_amount'] for inv in customer_invoices)
        total_outstanding = sum(inv['outstanding_amount'] for inv in customer_invoices)
        
        if total_outstanding > 0:
            # Calculate aging
            aging_buckets = {'0-30': 0, '31-60': 0, '61-90': 0, '90+': 0}
            overdue_invoices = 0
            
            for inv in customer_invoices:
                if inv['outstanding_amount'] > 0:
                    days_overdue = max(0, (datetime.datetime.now().date() - inv['due_date']).days)
                    
                    if days_overdue > 0:
                        overdue_invoices += 1
                    
                    if days_overdue <= 30:
                        aging_buckets['0-30'] += inv['outstanding_amount']
                    elif days_overdue <= 60:
                        aging_buckets['31-60'] += inv['outstanding_amount']
                    elif days_overdue <= 90:
                        aging_buckets['61-90'] += inv['outstanding_amount']
                    else:
                        aging_buckets['90+'] += inv['outstanding_amount']
            
            customer_outstanding.append({
                'Customer Name': customer['name'],
                'Phone': customer['phone'],
                'Total Invoiced': f"₹{total_invoiced:,.2f}",
                'Total Outstanding': f"₹{total_outstanding:,.2f}",
                'Overdue Invoices': overdue_invoices,
                '0-30 Days': f"₹{aging_buckets['0-30']:,.2f}",
                '31-60 Days': f"₹{aging_buckets['31-60']:,.2f}",
                '61-90 Days': f"₹{aging_buckets['61-90']:,.2f}",
                '90+ Days': f"₹{aging_buckets['90+']:,.2f}"
            })
    
    if customer_outstanding:
        df_outstanding = pd.DataFrame(customer_outstanding)
        st.dataframe(df_outstanding, use_container_width=True)
        
        # Export options
        if st.button("Export Outstanding Report to CSV"):
            csv = df_outstanding.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"outstanding_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    else:
        st.info("No outstanding amounts found.")