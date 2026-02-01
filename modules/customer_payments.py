import streamlit as st
import pandas as pd
import datetime
import uuid
from typing import Dict, List
from decimal import Decimal

def safe_decimal_subtract(original_value, subtract_value):
    """Safely subtract values handling Decimal/float conversion"""
    try:
        original_decimal = Decimal(str(original_value))
        subtract_decimal = Decimal(str(subtract_value))
        return float(original_decimal - subtract_decimal)
    except (ValueError, TypeError):
        # Fallback to regular subtraction
        return float(original_value) - float(subtract_value)

def safe_float(value):
    """Safely convert value to float handling Decimal objects"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def can_delete_customer(customer):
    """Check if customer can be safely deleted"""
    customer_id = customer['id']
    
    # Check for existing bookings (prioritize customer_id)
    customer_bookings = [b for b in st.session_state.bookings if b.get('customer_id') == customer_id]
    
    # Check for existing invoices (prioritize customer_id)
    customer_invoices = [i for i in st.session_state.invoices if i.get('customer_id') == customer_id]
    
    # Check for existing payments (prioritize customer_id)
    customer_payments = [p for p in st.session_state.customer_payments if p.get('customer_id') == customer_id]
    
    # Check for existing quotations (prioritize customer_id)
    customer_quotations = [q for q in st.session_state.quotations if q.get('customer_id') == customer_id]
    
    blocking_records = []
    if customer_bookings:
        blocking_records.append(f"{len(customer_bookings)} booking(s)")
    if customer_invoices:
        blocking_records.append(f"{len(customer_invoices)} invoice(s)")
    if customer_payments:
        blocking_records.append(f"{len(customer_payments)} payment(s)")
    if customer_quotations:
        blocking_records.append(f"{len(customer_quotations)} quotation(s)")
    
    return len(blocking_records) == 0, blocking_records

def show():
    """Display the customer payments module"""
    # Load data when needed
    from database import load_data_when_needed
    load_data_when_needed('invoices')
    load_data_when_needed('customer_payments')
    load_data_when_needed('customers')
    
    st.header("💰 Customer Payments Management")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Record Payment", "View Payments", "Customer Statements", "Outstanding Reports", "Manage Customers", "Unallocated Balances"])
    
    with tab1:
        record_payment()
    
    with tab2:
        view_payments()
    
    with tab3:
        customer_statements()
    
    with tab4:
        outstanding_reports()
    
    with tab5:
        manage_customers()
    
    with tab6:
        manage_unallocated_balances()

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
        outstanding_amount = float(invoice['outstanding_amount'])
        payment_amount = st.number_input(
            "Payment Amount (₹)*", 
            min_value=0.01, 
            value=outstanding_amount,
            max_value=outstanding_amount,
            step=0.01,
            key="payment_amount",
            help=f"Maximum allowed: ₹{outstanding_amount:,.2f}"
        )
        
        # Client-side validation warning
        if payment_amount > outstanding_amount:
            st.error(f"❌ Payment amount (₹{payment_amount:,.2f}) cannot exceed outstanding amount (₹{outstanding_amount:,.2f})")
        elif payment_amount == outstanding_amount:
            st.success("✅ This will fully settle the invoice")
        elif payment_amount > 0:
            st.info(f"💡 Remaining balance after payment: ₹{outstanding_amount - payment_amount:,.2f}")
    
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
    
    # Submit payment - disabled if amount is invalid
    payment_button_disabled = payment_amount <= 0 or payment_amount > outstanding_amount
    
    if st.button("Record Payment", type="primary", disabled=payment_button_disabled):
        # Server-side validation
        if not payment_date:
            st.error("Payment date is required")
            return
            
        if payment_amount <= 0:
            st.error("Payment amount must be greater than 0")
            return
            
        if payment_amount > outstanding_amount:
            st.error(f"Payment amount (₹{payment_amount:,.2f}) cannot exceed outstanding amount (₹{outstanding_amount:,.2f})")
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
            'payment_status': 'Completed',
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
            
            # Update invoice outstanding amount (ensure both are same type)
            from decimal import Decimal
            current_outstanding = Decimal(str(invoice['outstanding_amount']))
            payment_decimal = Decimal(str(payment_amount))
            invoice['outstanding_amount'] = float(current_outstanding - payment_decimal)
            
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
        outstanding = sum(float(inv['outstanding_amount']) for inv in st.session_state.invoices if inv['customer_id'] == customer['id'])
        if outstanding > 0:
            customers_with_outstanding.append(customer)
    
    if not customers_with_outstanding:
        st.info("No customers with outstanding invoices found.")
        return
    
    customer_options = [f"{c['name']} - Outstanding: ₹{sum(float(inv['outstanding_amount']) for inv in st.session_state.invoices if inv['customer_id'] == c['id']):,.2f}" 
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
        
        # Calculate total outstanding for default amount and validation
        total_outstanding_for_customer = sum(float(inv['outstanding_amount']) for inv in customer_invoices)
        
        payment_amount = st.number_input(
            "Payment Amount (₹)*", 
            min_value=0.01, 
            value=float(total_outstanding_for_customer), 
            step=0.01,
            key="manual_payment_amount",
            help=f"Total outstanding: ₹{total_outstanding_for_customer:,.2f}"
        )
        
        # Show payment validation information
        if payment_amount > total_outstanding_for_customer:
            st.warning(f"⚠️ Payment amount (₹{payment_amount:,.2f}) exceeds total outstanding (₹{total_outstanding_for_customer:,.2f}). This will create an unallocated credit balance.")
        elif payment_amount == total_outstanding_for_customer:
            st.success("✅ This will fully settle all outstanding invoices")
        elif payment_amount > 0:
            st.info(f"💡 Remaining outstanding after payment: ₹{total_outstanding_for_customer - payment_amount:,.2f}")
    
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
                outstanding_amount = float(inv['outstanding_amount'])
                allocate_amount = st.number_input(
                    f"Allocate Amount",
                    min_value=0.0,
                    max_value=outstanding_amount,
                    value=0.0,
                    step=0.01,
                    key=f"allocate_{inv['id']}",
                    format="%.2f",
                    help=f"Max: ₹{outstanding_amount:,.2f}"
                )
                
                # Show allocation validation
                if allocate_amount > outstanding_amount:
                    st.error(f"❌ Cannot allocate more than outstanding amount")
                elif allocate_amount == outstanding_amount:
                    st.success("✅ Will fully settle this invoice")
            
            with col3:
                if allocate_amount > 0 and allocate_amount <= outstanding_amount:
                    allocated_invoices.append(inv['invoice_number'])
                    total_allocated += allocate_amount
        
        # Enhanced allocation summary
        st.markdown("**Allocation Summary:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Allocated", f"₹{total_allocated:,.2f}")
        with col2:
            st.metric("Payment Amount", f"₹{payment_amount:,.2f}")
        with col3:
            unallocated = payment_amount - total_allocated
            st.metric("Unallocated", f"₹{unallocated:,.2f}")
        
        # Convert to float for proper comparison
        total_allocated_float = float(total_allocated)
        payment_amount_float = float(payment_amount)
        
        if total_allocated_float > payment_amount_float:
            st.error(f"❌ Total allocated (₹{total_allocated_float:,.2f}) cannot exceed payment amount (₹{payment_amount_float:,.2f})")
            return
    
    # Submit payment
    if st.button("Record Payment", type="primary"):
        if not payment_date or payment_amount <= 0:
            st.error("Payment date and amount are required")
            return
        
        if allocation_type == "Allocate to specific invoices":
            total_allocated_float = float(total_allocated)
            payment_amount_float = float(payment_amount)
            
            if abs(total_allocated_float - payment_amount_float) > 0.01:  # Allow small rounding differences
                st.error(f"Total allocated amount (₹{total_allocated_float:,.2f}) must equal payment amount (₹{payment_amount_float:,.2f})")
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
            'payment_status': 'Completed',
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
                    # Update invoice outstanding amount (ensure both are same type)
                    from decimal import Decimal
                    current_outstanding = Decimal(str(inv['outstanding_amount']))
                    allocation_decimal = Decimal(str(allocate_amount))
                    inv['outstanding_amount'] = float(current_outstanding - allocation_decimal)
                    
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
    col1, col2, col3, col4 = st.columns(4)
    
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
        payment_status_filter = st.selectbox(
            "Payment Status",
            ["All", "Completed", "Pending"],
            key="payment_status_filter"
        )
    
    with col4:
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
    
    if payment_status_filter != "All":
        filtered_payments = [p for p in filtered_payments if p.get('payment_status', 'Completed') == payment_status_filter]
    
    filtered_payments = [p for p in filtered_payments if p['payment_date'] >= date_filter]
    
    # Summary
    total_payments = len(filtered_payments)
    total_amount = sum(p['payment_amount'] for p in filtered_payments)
    allocated_payments = len([p for p in filtered_payments if p['allocation_status'] == 'Allocated'])
    completed_payments = len([p for p in filtered_payments if p.get('payment_status', 'Completed') == 'Completed'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Payments", total_payments)
    with col2:
        st.metric("Total Amount", f"₹{total_amount:,.2f}")
    with col3:
        st.metric("Allocated Payments", f"{allocated_payments}/{total_payments}")
    with col4:
        st.metric("Completed Payments", f"{completed_payments}/{total_payments}")
    
    st.markdown("---")
    
    # Display payments
    for payment in filtered_payments:
        allocation_icon = "✅" if payment['allocation_status'] == 'Allocated' else "⏳"
        payment_status = payment.get('payment_status', 'Completed')
        status_icon = "💚" if payment_status == 'Completed' else "⏳"
        
        with st.expander(f"{allocation_icon} {status_icon} {payment['customer_name']} - ₹{payment['payment_amount']:,.2f} - {payment['payment_date']}"):
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
                st.write(f"**Payment Status:** {payment.get('payment_status', 'Completed')}")
                if payment['allocated_invoices']:
                    st.write(f"**Allocated to:** {', '.join(payment['allocated_invoices'])}")
                if payment.get('bank_name'):
                    st.write(f"**Bank:** {payment['bank_name']}")
                if payment.get('remarks'):
                    st.write(f"**Remarks:** {payment['remarks']}")
            
            # Update allocation for unallocated payments
            if payment['allocation_status'] == 'Unallocated':
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Update Allocation", key=f"update_{payment['id']}"):
                        update_payment_allocation(payment)
                with col2:
                    if st.button(f"Mark as Completed (Unallocated)", key=f"complete_{payment['id']}"):
                        payment['payment_status'] = 'Completed'
                        st.success("Payment marked as completed!")
                        st.rerun()

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
        payment['payment_status'] = 'Completed'
        payment['allocated_invoices'] = allocated_invoices
        
        # Update invoice outstanding
        for inv in customer_invoices:
            allocate_amount = st.session_state.get(f"update_allocate_{inv['id']}", 0.0)
            if allocate_amount > 0:
                # Update invoice outstanding amount (ensure both are same type)
                from decimal import Decimal
                current_outstanding = Decimal(str(inv['outstanding_amount']))
                allocation_decimal = Decimal(str(allocate_amount))
                inv['outstanding_amount'] = float(current_outstanding - allocation_decimal)
                
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
        total_outstanding = sum(float(inv['outstanding_amount']) for inv in all_customer_invoices)
        
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
                'Paid': f"₹{safe_float(inv['total_amount']) - safe_float(inv['outstanding_amount']):,.2f}",
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
                'Status': payment.get('payment_status', 'Completed'),
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
            outstanding_float = safe_float(inv['outstanding_amount'])
            if days_overdue <= 30:
                aging_buckets['0-30'] += outstanding_float
                bucket = '0-30 days'
            elif days_overdue <= 60:
                aging_buckets['31-60'] += outstanding_float
                bucket = '31-60 days'
            elif days_overdue <= 90:
                aging_buckets['61-90'] += outstanding_float
                bucket = '61-90 days'
            else:
                aging_buckets['90+'] += outstanding_float
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
        
        total_invoiced = sum(float(inv['total_amount']) for inv in customer_invoices)
        total_outstanding = sum(safe_float(inv['outstanding_amount']) for inv in customer_invoices)
        
        if total_outstanding > 0:
            # Calculate aging
            aging_buckets = {'0-30': 0, '31-60': 0, '61-90': 0, '90+': 0}
            overdue_invoices = 0
            
            for inv in customer_invoices:
                outstanding_amt = safe_float(inv['outstanding_amount'])
                if outstanding_amt > 0:
                    days_overdue = max(0, (datetime.datetime.now().date() - inv['due_date']).days)
                    
                    if days_overdue > 0:
                        overdue_invoices += 1
                    
                    if days_overdue <= 30:
                        aging_buckets['0-30'] += outstanding_amt
                    elif days_overdue <= 60:
                        aging_buckets['31-60'] += outstanding_amt
                    elif days_overdue <= 90:
                        aging_buckets['61-90'] += outstanding_amt
                    else:
                        aging_buckets['90+'] += outstanding_amt
            
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

def manage_customers():
    """Manage customer records - view, edit, delete"""
    st.subheader("Manage Customers")
    
    # Add section for creating new customer
    st.markdown("---")
    create_col, spacer = st.columns([1, 4])
    
    with create_col:
        if st.button("➕ Create New Customer", key="btn_create_new_customer", use_container_width=True):
            st.session_state.show_create_customer_form = True
    
    # Show create customer form if needed
    if st.session_state.get("show_create_customer_form", False):
        st.markdown("### ➕ Create New Customer")
        
        create_customer_form = st.form("create_new_customer_form")
        
        with create_customer_form:
            col1, col2 = st.columns(2)
            
            with col1:
                new_customer_name = st.text_input("Customer Name*", placeholder="e.g., ABC Logistics", key="new_cust_name")
                new_customer_phone = st.text_input("Phone", placeholder="e.g., 9876543210", key="new_cust_phone")
                new_customer_email = st.text_input("Email", placeholder="e.g., contact@company.com", key="new_cust_email")
            
            with col2:
                new_customer_address = st.text_area("Address", placeholder="e.g., 123 Main Street, City", key="new_cust_address", height=100)
                new_customer_gst = st.text_input("GST Number", placeholder="e.g., 33AABCT1234H1Z0", key="new_cust_gst")
                new_customer_pan = st.text_input("PAN Number", placeholder="e.g., AAATL5055K", key="new_cust_pan")
                new_customer_payment_terms = st.selectbox("Payment Terms (Days)", options=[15, 30, 45, 60, 90], key="new_cust_terms", index=1)
            
            form_col1, form_col2 = st.columns(2)
            
            with form_col1:
                submit_btn = st.form_submit_button("✅ Create Customer", type="primary", use_container_width=True)
            
            with form_col2:
                cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if submit_btn:
            if new_customer_name:
                # Validate phone number if provided
                from .utils import validate_mobile_number
                
                if new_customer_phone and not validate_mobile_number(new_customer_phone):
                    st.error("❌ Phone must be a valid 10-digit number (starting with 6-9)")
                else:
                    # Create new customer
                    from database import execute_query
                    
                    try:
                        query = """
                        INSERT INTO customers (name, email, phone, address, gst_number, pan_number, payment_terms)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, name, email, phone, address, gst_number, pan_number, payment_terms, created_date;
                        """
                        result = execute_query(query, (new_customer_name.title(), new_customer_email, new_customer_phone, 
                                                       new_customer_address, new_customer_gst, new_customer_pan,
                                                       new_customer_payment_terms), fetch=True)
                        
                        if result:
                            new_customer = dict(result[0])
                            new_customer['id'] = str(new_customer['id'])  # Ensure ID is string
                            
                            # Add to session state
                            if not hasattr(st.session_state, 'customers') or st.session_state.customers is None:
                                st.session_state.customers = []
                            st.session_state.customers.append(new_customer)
                            
                            st.success(f"✅ Customer '{new_customer_name}' created successfully!")
                            st.session_state.show_create_customer_form = False
                            st.rerun()
                        else:
                            st.error("❌ Failed to create customer in database")
                    except Exception as e:
                        st.error(f"❌ Error creating customer: {e}")
            else:
                st.error("❌ Customer name is required")
        
        if cancel_btn:
            st.session_state.show_create_customer_form = False
            st.rerun()
        
        st.markdown("---")
    
    if not st.session_state.customers:
        st.info("No customers found. Use the 'Create New Customer' button above or customers are created when bookings or quotations are made.")
        return
    
    # Get unique customers (avoid duplicates by ID, not name)
    unique_customers = {}
    for customer in st.session_state.customers:
        customer_id = customer['id']
        if customer_id not in unique_customers:
            unique_customers[customer_id] = customer
    
    st.info(f"Showing {len(unique_customers)} customers")
    
    # Search/filter
    search_term = st.text_input("🔍 Search customers by name, email, or phone", key="customer_search")
    
    # Filter customers
    filtered_customers = []
    for customer in unique_customers.values():
        if not search_term or \
           search_term.lower() in customer['name'].lower() or \
           search_term.lower() in customer.get('email', '').lower() or \
           search_term.lower() in customer.get('phone', '').lower():
            filtered_customers.append(customer)
    
    # Display customers
    for customer in filtered_customers:
        # Calculate customer stats
        customer_bookings = [b for b in st.session_state.bookings if b.get('customer_id') == customer['id']]
        customer_invoices = [i for i in st.session_state.invoices if i.get('customer_id') == customer['id']]
        total_business = sum(booking.get('total_amount', 0) for booking in customer_bookings)
        outstanding = sum(float(invoice.get('outstanding_amount', 0)) for invoice in customer_invoices)
        
        # Create unique display name with phone for customers with same names
        customer_display = customer['name']
        phone_suffix = f" ({customer.get('phone', 'No phone')})"
        # Check if there are other customers with the same name
        same_name_customers = [c for c in filtered_customers if c['name'] == customer['name']]
        if len(same_name_customers) > 1:
            customer_display = customer['name'] + phone_suffix
        
        with st.expander(f"👤 {customer_display} - {len(customer_bookings)} bookings - ₹{total_business:,.2f} total - ID: {customer['id'][:8]}..."):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Contact Information**")
                st.write(f"**Name:** {customer['name']}")
                st.write(f"**Phone:** {customer.get('phone', 'Not provided')}")
                st.write(f"**Email:** {customer.get('email', 'Not provided')}")
                st.write(f"**Address:** {customer.get('address', 'Not provided')}")
            
            with col2:
                st.markdown("**Business Summary**")
                st.write(f"**Total Bookings:** {len(customer_bookings)}")
                st.write(f"**Total Business:** ₹{total_business:,.2f}")
                st.write(f"**Outstanding:** ₹{outstanding:,.2f}")
                st.write(f"**Payment Terms:** {customer.get('payment_terms', 30)} days")
                st.write(f"**Created:** {customer.get('created_date', 'Unknown')}")
            
            with col3:
                st.markdown("**Actions**")
                
                # Only allow editing if user is creator (for now, allow all admin users)
                user_role = st.session_state.get('user_role', 'Guest')
                can_edit = user_role in ['Administrator', 'Manager']
                
                if can_edit:
                    edit_col, remove_col = st.columns(2)
                    
                    with edit_col:
                        if st.button(f"✏️ Edit", key=f"edit_customer_{customer['id']}"):
                            st.session_state[f"editing_customer_{customer['id']}"] = True
                            st.rerun()
                    
                    with remove_col:
                        # Check if customer can be deleted
                        can_del, blocking_records = can_delete_customer(customer)
                        
                        if can_del:
                            if st.button(f"🗑️ Remove", key=f"remove_customer_{customer['id']}", type="secondary"):
                                st.session_state[f"removing_{customer['id']}"] = True
                                st.rerun()
                        else:
                            st.button(f"🚫 Remove", key=f"remove_customer_{customer['id']}", 
                                     disabled=True, 
                                     help=f"Cannot delete - has {', '.join(blocking_records)}")
                    
                    # Remove confirmation
                    if st.session_state.get(f"removing_{customer['id']}", False):
                        st.warning(f"⚠️ Confirm removal of customer: **{customer['name']}**")
                        confirm_col, cancel_col = st.columns(2)
                        
                        with confirm_col:
                            if st.button(f"Yes, Remove", key=f"confirm_remove_btn_{customer['id']}", type="primary"):
                                # Remove customer from database
                                from database import delete_from_database
                                if delete_from_database('customers', customer['id']):
                                    # Remove customer from session state
                                    st.session_state.customers = [c for c in st.session_state.customers if c['id'] != customer['id']]
                                    st.success(f"Customer '{customer['name']}' removed successfully!")
                                else:
                                    st.error(f"Failed to remove customer '{customer['name']}' from database")
                                del st.session_state[f"removing_{customer['id']}"]
                                st.rerun()
                        
                        with cancel_col:
                            if st.button(f"Cancel", key=f"cancel_remove_btn_{customer['id']}"):
                                del st.session_state[f"removing_{customer['id']}"]
                                st.rerun()
                else:
                    st.info("Edit/Remove permissions restricted")
                
                # Show recent activity
                recent_bookings = sorted(customer_bookings, key=lambda x: x.get('created_date', ''), reverse=True)[:3]
                if recent_bookings:
                    st.markdown("**Recent Bookings:**")
                    for booking in recent_bookings:
                        st.write(f"• {booking['booking_number']} - {booking['status']}")
            
            # Edit form
            if st.session_state.get(f"editing_customer_{customer['id']}", False):
                st.markdown("---")
                st.markdown("**Edit Customer Information:**")
                
                edit_col1, edit_col2 = st.columns(2)
                
                with edit_col1:
                    new_name = st.text_input("Customer Name*", value=customer['name'], key=f"edit_name_{customer['id']}")
                    new_phone = st.text_input("Phone", value=customer.get('phone', ''), key=f"edit_phone_{customer['id']}")
                    new_email = st.text_input("Email", value=customer.get('email', ''), key=f"edit_email_{customer['id']}")
                
                with edit_col2:
                    new_address = st.text_area("Address", value=customer.get('address', ''), key=f"edit_address_{customer['id']}")
                    new_payment_terms = st.selectbox("Payment Terms (Days)", 
                                                   options=[15, 30, 45, 60, 90], 
                                                   index=[15, 30, 45, 60, 90].index(customer.get('payment_terms', 30)),
                                                   key=f"edit_terms_{customer['id']}")
                
                save_col, cancel_col = st.columns(2)
                
                with save_col:
                    if st.button(f"💾 Save Changes", key=f"save_customer_{customer['id']}", type="primary"):
                        # Update customer data
                        customer['name'] = new_name
                        customer['phone'] = new_phone
                        customer['email'] = new_email
                        customer['address'] = new_address
                        customer['payment_terms'] = new_payment_terms
                        
                        # Update in database
                        from database import update_in_database
                        update_success = update_in_database('customers', {
                            'name': new_name,
                            'phone': new_phone,
                            'email': new_email,
                            'address': new_address,
                            'payment_terms': new_payment_terms
                        }, customer['id'])
                        
                        if update_success:
                            # Update related records
                            for booking in st.session_state.bookings:
                                if booking.get('customer_id') == customer['id']:
                                    booking['customer_name'] = new_name
                            
                            for invoice in st.session_state.invoices:
                                if invoice.get('customer_id') == customer['id']:
                                    invoice['customer_name'] = new_name
                            
                            st.success(f"Customer {new_name} updated successfully!")
                        else:
                            st.error(f"Failed to update customer {new_name} in database")
                        
                        # Clear editing state
                        del st.session_state[f"editing_customer_{customer['id']}"]
                        st.rerun()
                
                with cancel_col:
                    if st.button(f"❌ Cancel", key=f"cancel_customer_{customer['id']}"):
                        del st.session_state[f"editing_customer_{customer['id']}"]
                        st.rerun()
    
    # Export customers
    st.markdown("---")
    if st.button("📊 Export Customer List"):
        df = pd.DataFrame([
            {
                'Name': customer['name'],
                'Phone': customer.get('phone', ''),
                'Email': customer.get('email', ''),
                'Address': customer.get('address', ''),
                'Payment Terms': customer.get('payment_terms', 30),
                'Created Date': customer.get('created_date', '')
            }
            for customer in unique_customers.values()
        ])
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Customer List CSV",
            data=csv,
            file_name=f"customers_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def manage_unallocated_balances():
    """Manage customer unallocated payment balances"""
    st.subheader("💳 Unallocated Balance Management")
    st.info("View and allocate customer payments that were not assigned to specific invoices")
    
    # Calculate unallocated balances for each customer
    customer_balances = {}
    
    for payment in st.session_state.customer_payments:
        customer_id = payment['customer_id']
        customer_name = payment['customer_name']
        
        if customer_id not in customer_balances:
            customer_balances[customer_id] = {
                'customer_name': customer_name,
                'unallocated_amount': 0,
                'unallocated_payments': []
            }
        
        # Check if payment has unallocated amount
        unallocated = payment.get('unallocated_amount', 0)
        if unallocated > 0:
            customer_balances[customer_id]['unallocated_amount'] += unallocated
            customer_balances[customer_id]['unallocated_payments'].append(payment)
    
    # Filter customers with unallocated balances
    customers_with_balance = {k: v for k, v in customer_balances.items() if v['unallocated_amount'] > 0}
    
    if not customers_with_balance:
        st.success("🎉 No unallocated balances found! All payments are properly allocated.")
        return
    
    # Summary metrics
    total_unallocated = sum(data['unallocated_amount'] for data in customers_with_balance.values())
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Customers with Unallocated Balances", len(customers_with_balance))
    with col2:
        st.metric("Total Unallocated Amount", f"₹{total_unallocated:,.2f}")
    with col3:
        st.metric("Average per Customer", f"₹{total_unallocated / len(customers_with_balance):,.2f}")
    
    st.markdown("---")
    
    # Display customers with unallocated balances
    for customer_id, balance_data in customers_with_balance.items():
        customer_name = balance_data['customer_name']
        unallocated_amount = balance_data['unallocated_amount']
        
        # Get pending invoices for this customer
        pending_invoices = [inv for inv in st.session_state.invoices 
                          if inv['customer_id'] == customer_id and inv['outstanding_amount'] > 0]
        
        with st.expander(f"💰 {customer_name} - Unallocated: ₹{unallocated_amount:,.2f}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Unallocated Payments:**")
                for payment in balance_data['unallocated_payments']:
                    st.write(f"• {payment['payment_date']} - ₹{payment.get('unallocated_amount', 0):,.2f} ({payment['payment_mode']})")
                    if payment.get('reference_number'):
                        st.write(f"  Ref: {payment['reference_number']}")
            
            with col2:
                st.markdown("**Pending Invoices:**")
                if pending_invoices:
                    for invoice in pending_invoices:
                        days_overdue = max(0, (datetime.datetime.now().date() - invoice['due_date']).days)
                        overdue_text = f" ({days_overdue} days overdue)" if days_overdue > 0 else ""
                        st.write(f"• {invoice['invoice_number']} - ₹{invoice['outstanding_amount']:,.2f}{overdue_text}")
                else:
                    st.info("No pending invoices to allocate to")
            
            # Allocation interface
            if pending_invoices:
                st.markdown("**Allocate Balance to Invoices:**")
                
                # Select invoice to allocate to
                invoice_options = [f"{inv['invoice_number']} - ₹{inv['outstanding_amount']:,.2f}" for inv in pending_invoices]
                selected_invoice_idx = st.selectbox(
                    "Select Invoice",
                    range(len(invoice_options)),
                    format_func=lambda x: invoice_options[x],
                    key=f"allocate_invoice_{customer_id}"
                )
                
                selected_invoice = pending_invoices[selected_invoice_idx]
                
                # Amount to allocate
                max_allocation = min(unallocated_amount, selected_invoice['outstanding_amount'])
                allocation_amount = st.number_input(
                    "Amount to Allocate (₹)",
                    min_value=0.01,
                    max_value=float(max_allocation),
                    value=float(max_allocation),
                    key=f"allocate_amount_{customer_id}"
                )
                
                # Allocate button
                if st.button(f"💱 Allocate ₹{allocation_amount:,.2f}", key=f"allocate_btn_{customer_id}"):
                    # Update invoice outstanding (ensure both are same type)
                    from decimal import Decimal
                    current_outstanding = Decimal(str(selected_invoice['outstanding_amount']))
                    allocation_decimal = Decimal(str(allocation_amount))
                    selected_invoice['outstanding_amount'] = float(current_outstanding - allocation_decimal)
                    
                    # Update invoice status
                    if selected_invoice['outstanding_amount'] <= 0:
                        selected_invoice['status'] = 'Paid'
                    elif selected_invoice['status'] == 'Generated':
                        selected_invoice['status'] = 'Partially Paid'
                    
                    # Update unallocated amounts in payments (FIFO basis)
                    remaining_to_allocate = allocation_amount
                    
                    for payment in balance_data['unallocated_payments']:
                        if remaining_to_allocate <= 0:
                            break
                        
                        current_unallocated = payment.get('unallocated_amount', 0)
                        if current_unallocated > 0:
                            allocation_from_payment = min(remaining_to_allocate, current_unallocated)
                            payment['unallocated_amount'] -= allocation_from_payment
                            remaining_to_allocate -= allocation_from_payment
                            
                            # Add allocation record
                            if 'allocated_invoices' not in payment:
                                payment['allocated_invoices'] = []
                            
                            payment['allocated_invoices'].append({
                                'invoice_id': selected_invoice['id'],
                                'invoice_number': selected_invoice['invoice_number'],
                                'allocated_amount': allocation_from_payment,
                                'allocation_date': datetime.datetime.now()
                            })
                    
                    # Track the allocation
                    from .notes import track_status_change
                    track_status_change(
                        record_id=selected_invoice['id'],
                        record_type='invoice',
                        old_status=selected_invoice.get('old_status', 'Generated'),
                        new_status=selected_invoice['status'],
                        notes=f'Allocated ₹{allocation_amount:,.2f} from unallocated balance',
                        additional_data={
                            'invoice_number': selected_invoice['invoice_number'],
                            'customer_name': customer_name,
                            'allocated_amount': allocation_amount,
                            'remaining_outstanding': selected_invoice['outstanding_amount']
                        }
                    )
                    
                    st.success(f"✅ Allocated ₹{allocation_amount:,.2f} to Invoice {selected_invoice['invoice_number']}")
                    st.rerun()
            
            else:
                # Option to create credit note or refund
                st.markdown("**No Pending Invoices - Options:**")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"📋 Create Credit Note", key=f"credit_{customer_id}"):
                        st.info("Credit note creation feature - to be implemented")
                
                with col2:
                    if st.button(f"💸 Issue Refund", key=f"refund_{customer_id}"):
                        st.info("Refund processing feature - to be implemented")
    
    # Export unallocated balances
    st.markdown("---")
    if st.button("📊 Export Unallocated Balances"):
        export_data = []
        for customer_id, balance_data in customers_with_balance.items():
            export_data.append({
                'Customer Name': balance_data['customer_name'],
                'Unallocated Amount': balance_data['unallocated_amount'],
                'Number of Payments': len(balance_data['unallocated_payments']),
                'Oldest Payment Date': min(p['payment_date'] for p in balance_data['unallocated_payments']) if balance_data['unallocated_payments'] else None
            })
        
        df = pd.DataFrame(export_data)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Unallocated Balances CSV",
            data=csv,
            file_name=f"unallocated_balances_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )