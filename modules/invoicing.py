import streamlit as st
import pandas as pd
import datetime
import uuid
from typing import Dict, List
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
from .quotations import safe_get_date

def update_payment_status():
    """Automatically update payment status based on total payments received"""
    for invoice in st.session_state.invoices:
        # Calculate total payments for this invoice
        total_payments = sum(
            payment['amount'] for payment in st.session_state.customer_payments 
            if payment.get('invoice_id') == invoice['id']
        )
        
        # Update outstanding amount
        invoice['outstanding_amount'] = invoice['total_amount'] - total_payments
        
        # Update status based on payments
        if total_payments == 0:
            invoice['status'] = 'Generated'
        elif total_payments >= invoice['total_amount']:
            invoice['status'] = 'Paid'
        else:
            invoice['status'] = 'Partially Paid'
        
        # Check for overdue (if due date passed and not fully paid)
        if (invoice.get('due_date') and 
            datetime.datetime.now().date() > invoice['due_date'] and 
            total_payments < invoice['total_amount']):
            invoice['status'] = 'Overdue'

def show():
    """Display the invoicing module"""
    # Load data when needed
    from database import load_data_when_needed
    load_data_when_needed('bookings')
    load_data_when_needed('invoices')
    load_data_when_needed('customers')
    
    st.header("🧾 Invoicing Management")
    
    tab1, tab2 = st.tabs(["Create Invoice", "View Invoices"])
    
    with tab1:
        create_invoice()
    
    with tab2:
        view_invoices()

def create_invoice():
    """Create a new invoice"""
    st.subheader("Create New Invoice")
    
    # Check for booking to convert
    if 'selected_booking_id' in st.session_state:
        booking = next((b for b in st.session_state.bookings if b['id'] == st.session_state.selected_booking_id), None)
        if booking:
            st.info(f"Creating invoice from Booking {booking['booking_number']}")
            create_invoice_from_booking(booking)
            return
    
    # Manual invoice selection - Show all completed bookings with POD generated
    eligible_bookings = [b for b in st.session_state.bookings if b['status'] in ['POD Generated', 'Delivered']]
    
    if not eligible_bookings:
        st.warning("No eligible bookings found. Only bookings with POD generated or delivered status can be invoiced.")
        return
    
    st.markdown("**Select Booking to Invoice**")
    
    # Create a more informative display of available bookings
    booking_data = []
    for booking in eligible_bookings:
        booking_data.append({
            'Booking Number': booking['booking_number'],
            'Customer': booking['customer_name'],
            'Route': f"{booking['pickup_location']} → {booking['delivery_location']}",
            'Pickup Date': booking['pickup_date'].strftime('%Y-%m-%d') if isinstance(booking['pickup_date'], datetime.date) else str(booking['pickup_date']),
            'Amount': f"₹{booking['total_amount']:,.2f}",
            'Status': booking['status'],
            'Select': False
        })
    
    if booking_data:
        df = pd.DataFrame(booking_data)
        
        # Display table with selection
        st.dataframe(df.drop('Select', axis=1), use_container_width=True)
        
        # Selection dropdown
        booking_options = [f"{b['booking_number']} - {b['customer_name']} - ₹{b['total_amount']:,.2f}" for b in eligible_bookings]
        selected_booking_option = st.selectbox("Select Booking to Invoice", booking_options, key="invoice_booking_select")
        
        if selected_booking_option:
            booking_number = selected_booking_option.split(" - ")[0]
            selected_booking = next((b for b in eligible_bookings if b['booking_number'] == booking_number), None)
            
            if selected_booking:
                create_invoice_from_booking(selected_booking)

def create_invoice_from_booking(booking):
    """Create invoice from booking"""
    st.markdown("**Booking Details**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Booking Number:** {booking['booking_number']}")
        st.write(f"**Customer:** {booking['customer_name']}")
        st.write(f"**Route:** {booking['pickup_location']} → {booking['delivery_location']}")
        st.write(f"**Pickup Date:** {booking['pickup_date']}")
        st.write(f"**Vehicle:** {booking.get('assigned_vehicle', 'Not Assigned')}")
    
    with col2:
        st.write(f"**Trip Type:** {booking['trip_type']}")
        st.write(f"**Distance:** {booking['distance_km']} KM")
        st.write(f"**Status:** {booking['status']}")
        st.write(f"**Amount:** ₹{booking['total_amount']:,.2f}")
        st.write(f"**Payment Terms:** {booking['payment_terms']} days")
    
    st.markdown("---")
    st.markdown("**Invoice Configuration**")
    
    # Movement type selection (required before invoice generation)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        movement_type = st.selectbox(
            "Movement Type*",
            ["Local", "Long"],
            key="invoice_movement_type",
            help="This determines routing and pricing structure"
        )
    
    with col2:
        invoice_date = st.date_input(
            "Invoice Date*",
            value=datetime.datetime.now().date(),
            key="invoice_date"
        )
    
    with col3:
        invoice_type = st.selectbox(
            "Invoice Type*",
            ["GST Invoice", "Cash Invoice", "Contract Invoice"],
            key="invoice_type",
            help="GST: Standard with new number, Cash: Uses booking number, Contract: Includes DSR"
        )
    
    # Invoice type specific fields
    if invoice_type == "Contract Invoice":
        st.markdown("**Contract Details**")
        col1, col2 = st.columns(2)
        
        with col1:
            contract_start_date = st.date_input("Contract Start Date*", key="contract_start_date")
            contract_period = st.selectbox("Contract Period", ["Monthly", "Quarterly", "Half-Yearly", "Yearly"], key="contract_period")
        
        with col2:
            contract_end_date = st.date_input("Contract End Date*", key="contract_end_date")
            
            # Generate DSR number
            from app import generate_dsr_number
            dsr_number = generate_dsr_number()
            st.write(f"**DSR Number:** {dsr_number}")
    
    # Additional charges/adjustments
    st.markdown("**Additional Charges & Adjustments**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        additional_fuel = st.number_input("Additional Fuel Charges (₹)", min_value=0.0, value=0.0, key="invoice_fuel")
        additional_toll = st.number_input("Additional Toll Charges (₹)", min_value=0.0, value=0.0, key="invoice_toll")
    
    with col2:
        additional_loading = st.number_input("Additional Loading Charges (₹)", min_value=0.0, value=0.0, key="invoice_loading")
        additional_detention = st.number_input("Detention Charges (₹)", min_value=0.0, value=0.0, key="invoice_detention")
    
    with col3:
        additional_misc = st.number_input("Miscellaneous Charges (₹)", min_value=0.0, value=0.0, key="invoice_misc")
        discount = st.number_input("Discount (₹)", min_value=0.0, value=0.0, key="invoice_discount")
    
    # Calculate amounts (ensure all are float for compatibility)
    base_amount = float(booking['total_amount'])
    additional_charges = additional_fuel + additional_toll + additional_loading + additional_detention + additional_misc
    subtotal = base_amount + additional_charges - discount
    
    # GST calculation (only for GST invoices)
    if invoice_type == "GST Invoice":
        gst_applicable = True
        gst_rate = st.selectbox("GST Rate (%)", [5, 12, 18, 28], index=2, key="gst_rate")
        gst_amount = subtotal * (gst_rate / 100)
        total_amount = subtotal + gst_amount
    else:
        gst_applicable = False
        gst_amount = 0
        total_amount = subtotal
    
    # Display calculated amounts
    st.markdown("**Invoice Summary**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Base Amount", f"₹{base_amount:,.2f}")
    
    with col2:
        st.metric("Additional Charges", f"₹{additional_charges:,.2f}")
    
    with col3:
        if gst_applicable:
            st.metric(f"GST ({gst_rate if gst_applicable else 0}%)", f"₹{gst_amount:,.2f}")
        else:
            st.metric("Discount", f"₹{discount:,.2f}")
    
    with col4:
        st.metric("Total Amount", f"₹{total_amount:,.2f}", delta=f"₹{total_amount - base_amount:,.2f}")
    
    # Notes and terms
    invoice_notes = st.text_area("Invoice Notes", key="invoice_notes", 
                                placeholder="Additional terms, conditions, or notes for the invoice")
    
    # Generate invoice button
    if st.button("Generate Invoice", type="primary"):
        if not movement_type or not invoice_date:
            st.error("Movement type and invoice date are required")
            return
        
        if invoice_type == "Contract Invoice" and (not contract_start_date or not contract_end_date):
            st.error("Contract start and end dates are required for contract invoices")
            return
        
        # Generate invoice number based on type
        from app import generate_invoice_number
        
        if invoice_type == "Cash Invoice":
            # Use booking number for cash invoices
            invoice_number = booking['booking_number']
        else:
            # Generate new number for GST and Contract invoices
            invoice_number = generate_invoice_number()
        
        # Calculate due date
        due_date = invoice_date + datetime.timedelta(days=booking['payment_terms'])
        
        # Create invoice
        invoice = {
            'id': str(uuid.uuid4()),
            'invoice_number': invoice_number,
            'booking_id': booking['id'],
            'booking_number': booking['booking_number'],
            'customer_id': booking['customer_id'],
            'customer_name': booking['customer_name'],
            'invoice_type': invoice_type,
            'movement_type': movement_type,
            'invoice_date': invoice_date,
            'due_date': due_date,
            'pickup_location': booking['pickup_location'],
            'delivery_location': booking['delivery_location'],
            'pickup_date': booking['pickup_date'],
            'vehicle_number': booking.get('assigned_vehicle', ''),
            'driver_name': booking.get('assigned_driver', ''),
            'distance_km': booking['distance_km'],
            'base_amount': base_amount,
            'additional_fuel': additional_fuel,
            'additional_toll': additional_toll,
            'additional_loading': additional_loading,
            'additional_detention': additional_detention,
            'additional_misc': additional_misc,
            'additional_charges': additional_charges,
            'discount': discount,
            'subtotal': subtotal,
            'gst_applicable': gst_applicable,
            'gst_rate': gst_rate if gst_applicable else 0,
            'gst_amount': gst_amount,
            'total_amount': total_amount,
            'payment_terms': booking['payment_terms'],
            'invoice_notes': invoice_notes,
            'status': 'Generated',
            'outstanding_amount': total_amount,
            'created_date': datetime.datetime.now(),
            'created_by': 'Admin'
        }
        
        # Add contract-specific fields
        if invoice_type == "Contract Invoice":
            invoice.update({
                'contract_start_date': contract_start_date,
                'contract_end_date': contract_end_date,
                'contract_period': contract_period,
                'dsr_number': dsr_number
            })
        
        # Save to database
        from app import save_invoice
        if save_invoice(invoice):
            # Add to session state for immediate display
            if 'invoices' not in st.session_state:
                st.session_state.invoices = []
            st.session_state.invoices.append(invoice)
            
            # Update booking status
            booking['status'] = 'Invoiced'
            booking['invoiced_date'] = datetime.datetime.now()
            
            # Clear selected booking
            if 'selected_booking_id' in st.session_state:
                del st.session_state.selected_booking_id
            
            st.success(f"Invoice {invoice_number} generated successfully!")
        else:
            st.error("Failed to save invoice. Please try again.")
        
        # Show invoice preview
        show_invoice_preview(invoice)
        
        # Clear form
        for key in st.session_state.keys():
            if key.startswith('invoice_') or key.startswith('contract_'):
                del st.session_state[key]
        
        st.rerun()

def show_invoice_preview(invoice):
    """Show a preview of the generated invoice"""
    st.markdown("---")
    st.markdown('''
    <div class="section-header">
        📄 Invoice Preview
    </div>
    ''', unsafe_allow_html=True)
    
    with st.container():
        # Header
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**STRANZ TRANSPORT**")
            st.markdown("Transport Management Services")
            st.markdown("Email: admin@stranz.in")
        
        with col2:
            st.markdown(f"**{invoice['invoice_type'].upper()}**")
            st.markdown(f"**Invoice No:** {invoice['invoice_number']}")
            st.markdown(f"**Date:** {invoice['invoice_date']}")
            st.markdown(f"**Due Date:** {invoice['due_date']}")
        
        st.markdown("---")
        
        # Bill to and shipment details
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**BILL TO:**")
            st.markdown(f"{invoice['customer_name']}")
            st.markdown(f"Payment Terms: {invoice['payment_terms']} days")
            
        with col2:
            st.markdown("**SHIPMENT DETAILS:**")
            st.markdown(f"Booking: {invoice['booking_number']}")
            st.markdown(f"From: {invoice['pickup_location']}")
            st.markdown(f"To: {invoice['delivery_location']}")
            st.markdown(f"Vehicle: {invoice.get('vehicle_number', 'N/A')}")
            st.markdown(f"Movement: {invoice['movement_type']}")
        
        # Contract details for contract invoices
        if invoice['invoice_type'] == "Contract Invoice":
            st.markdown("---")
            st.markdown("**CONTRACT DETAILS:**")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"Period: {invoice['contract_start_date']} to {invoice['contract_end_date']}")
                st.markdown(f"DSR Number: {invoice['dsr_number']}")
            with col2:
                st.markdown(f"Contract Period: {invoice['contract_period']}")
        
        st.markdown("---")
        
        # Invoice items
        st.markdown("**CHARGES:**")
        
        invoice_data = [
            ["Base Transportation Charges", f"₹{invoice['base_amount']:,.2f}"],
        ]
        
        if invoice['additional_fuel'] > 0:
            invoice_data.append(["Additional Fuel Charges", f"₹{invoice['additional_fuel']:,.2f}"])
        if invoice['additional_toll'] > 0:
            invoice_data.append(["Additional Toll Charges", f"₹{invoice['additional_toll']:,.2f}"])
        if invoice['additional_loading'] > 0:
            invoice_data.append(["Additional Loading Charges", f"₹{invoice['additional_loading']:,.2f}"])
        if invoice['additional_detention'] > 0:
            invoice_data.append(["Detention Charges", f"₹{invoice['additional_detention']:,.2f}"])
        if invoice['additional_misc'] > 0:
            invoice_data.append(["Miscellaneous Charges", f"₹{invoice['additional_misc']:,.2f}"])
        if invoice['discount'] > 0:
            invoice_data.append(["Discount", f"-₹{invoice['discount']:,.2f}"])
        
        invoice_data.append(["Subtotal", f"₹{invoice['subtotal']:,.2f}"])
        
        if invoice['gst_applicable']:
            invoice_data.append([f"GST ({invoice['gst_rate']}%)", f"₹{invoice['gst_amount']:,.2f}"])
        
        invoice_data.append(["**TOTAL AMOUNT**", f"**₹{invoice['total_amount']:,.2f}**"])
        
        df_invoice = pd.DataFrame(invoice_data, columns=["Description", "Amount"])
        st.table(df_invoice)
        
        if invoice.get('invoice_notes'):
            st.markdown("**Notes:**")
            st.markdown(invoice['invoice_notes'])

def view_invoices():
    """View and manage existing invoices"""
    st.subheader("View Invoices")
    
    # Update payment status automatically
    update_payment_status()
    
    if not st.session_state.invoices:
        st.info("No invoices found. Create your first invoice in the 'Create Invoice' tab.")
        return
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        invoice_type_filter = st.selectbox(
            "Filter by Type",
            ["All", "GST Invoice", "Cash Invoice", "Contract Invoice"],
            key="invoice_type_filter"
        )
    
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Generated", "Sent", "Paid", "Partially Paid", "Overdue", "Cancelled"],
            key="invoice_status_filter"
        )
    
    with col3:
        customer_filter = st.selectbox(
            "Filter by Customer",
            ["All"] + list(set([inv['customer_name'] for inv in st.session_state.invoices])),
            key="invoice_customer_filter"
        )
    
    with col4:
        date_filter = st.date_input(
            "From Date",
            value=datetime.datetime.now() - datetime.timedelta(days=30),
            key="invoice_date_filter"
        )
    
    # Filter invoices
    filtered_invoices = st.session_state.invoices
    
    if invoice_type_filter != "All":
        filtered_invoices = [inv for inv in filtered_invoices if inv['invoice_type'] == invoice_type_filter]
    
    if status_filter != "All":
        filtered_invoices = [inv for inv in filtered_invoices if inv['status'] == status_filter]
    
    if customer_filter != "All":
        filtered_invoices = [inv for inv in filtered_invoices if inv['customer_name'] == customer_filter]
    
    filtered_invoices = [inv for inv in filtered_invoices if safe_get_date(inv['created_date']) >= date_filter]
    
    # Calculate overdue status
    current_date = datetime.datetime.now().date()
    for invoice in filtered_invoices:
        days_overdue = (current_date - invoice['due_date']).days
        
        if invoice['outstanding_amount'] <= 0:
            invoice['overdue_status'] = 'Paid'
            invoice['days_overdue'] = 0
        elif days_overdue <= 0:
            invoice['overdue_status'] = 'On Time'
            invoice['days_overdue'] = 0
        elif days_overdue <= 15:
            invoice['overdue_status'] = 'Due Soon'
            invoice['days_overdue'] = days_overdue
        else:
            invoice['overdue_status'] = 'Overdue'
            invoice['days_overdue'] = days_overdue
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_invoices = len(filtered_invoices)
        st.metric("Total Invoices", total_invoices)
    
    with col2:
        total_amount = sum(inv['total_amount'] for inv in filtered_invoices)
        st.metric("Total Amount", f"₹{total_amount:,.2f}")
    
    with col3:
        outstanding_amount = sum(inv['outstanding_amount'] for inv in filtered_invoices)
        st.metric("Outstanding", f"₹{outstanding_amount:,.2f}")
    
    with col4:
        overdue_invoices = len([inv for inv in filtered_invoices if inv.get('overdue_status') == 'Overdue'])
        st.metric("Overdue Invoices", overdue_invoices, delta_color="inverse")
    
    st.markdown("---")
    
    # Display invoices
    for invoice in filtered_invoices:
        # Determine color based on overdue status
        if invoice.get('overdue_status') == 'Paid':
            color = "🟢"
        elif invoice.get('overdue_status') == 'On Time':
            color = "🟡"
        elif invoice.get('overdue_status') == 'Due Soon':
            color = "🟠"
        else:
            color = "🔴"
        
        overdue_text = ""
        if invoice.get('days_overdue', 0) > 0:
            overdue_text = f" ({invoice['days_overdue']} days overdue)"
        
        with st.expander(f"{color} {invoice['invoice_number']} - {invoice['customer_name']} - ₹{invoice['total_amount']:,.2f}{overdue_text}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Type:** {invoice['invoice_type']}")
                st.write(f"**Booking:** {invoice['booking_number']}")
                st.write(f"**Customer:** {invoice['customer_name']}")
                st.write(f"**Route:** {invoice['pickup_location']} → {invoice['delivery_location']}")
                st.write(f"**Movement:** {invoice['movement_type']}")
                if invoice.get('vehicle_number'):
                    st.write(f"**Vehicle:** {invoice['vehicle_number']}")
            
            with col2:
                st.write(f"**Invoice Date:** {invoice['invoice_date']}")
                st.write(f"**Due Date:** {invoice['due_date']}")
                st.write(f"**Total Amount:** ₹{invoice['total_amount']:,.2f}")
                st.write(f"**Outstanding:** ₹{invoice['outstanding_amount']:,.2f}")
                st.write(f"**Status:** {invoice['status']}")
                if invoice.get('gst_applicable'):
                    st.write(f"**GST:** {invoice['gst_rate']}% (₹{invoice['gst_amount']:,.2f})")
            
            # Contract details
            if invoice['invoice_type'] == "Contract Invoice":
                st.markdown("**Contract Details:**")
                st.write(f"Period: {invoice['contract_start_date']} to {invoice['contract_end_date']}")
                st.write(f"DSR Number: {invoice['dsr_number']}")
            
            # Action buttons
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button(f"View Details", key=f"view_{invoice['id']}"):
                    show_invoice_preview(invoice)
            
            with col2:
                # PDF Generation Button
                if st.button(f"Download PDF", key=f"pdf_{invoice['id']}"):
                    try:
                        pdf_data = generate_invoice_pdf(invoice)
                        st.download_button(
                            label="Download Invoice PDF",
                            data=pdf_data,
                            file_name=f"Invoice_{invoice['invoice_number']}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_{invoice['id']}"
                        )
                    except Exception as e:
                        st.error(f"Error generating PDF: {str(e)}")
            
            with col3:
                if invoice['outstanding_amount'] > 0:
                    if st.button(f"Record Payment", key=f"payment_{invoice['id']}"):
                        st.session_state.selected_invoice_id = invoice['id']
                        st.success("Navigate to Customer Payments to record payment for this invoice!")
            
            with col4:
                if invoice['status'] == 'Generated':
                    if st.button(f"Mark as Sent", key=f"sent_{invoice['id']}"):
                        invoice['status'] = 'Sent'
                        st.success("Invoice marked as sent!")
                        st.rerun()
    
    # Export options
    st.markdown("---")
    if st.button("Export Invoices to CSV"):
        export_data = []
        for inv in filtered_invoices:
            export_data.append({
                'Invoice Number': inv['invoice_number'],
                'Invoice Type': inv['invoice_type'],
                'Customer': inv['customer_name'],
                'Booking Number': inv['booking_number'],
                'Invoice Date': inv['invoice_date'],
                'Due Date': inv['due_date'],
                'Total Amount': inv['total_amount'],
                'Outstanding': inv['outstanding_amount'],
                'Status': inv['status'],
                'Days Overdue': inv.get('days_overdue', 0),
                'Movement Type': inv['movement_type'],
                'Route': f"{inv['pickup_location']} → {inv['delivery_location']}"
            })
        
        df = pd.DataFrame(export_data)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"invoices_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def generate_invoice_pdf(invoice):
    """Generate PDF for invoice"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    # Header
    title = Paragraph("STRANZ TRANSPORT MANAGEMENT", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Invoice details
    invoice_title = Paragraph(f"<b>{invoice['invoice_type'].upper()}: {invoice['invoice_number']}</b>", styles['Heading2'])
    elements.append(invoice_title)
    elements.append(Spacer(1, 12))
    
    # Customer and invoice info
    info_data = [
        ['Customer:', invoice['customer_name'], 'Invoice Date:', invoice['invoice_date'].strftime('%Y-%m-%d') if isinstance(invoice['invoice_date'], datetime.date) else str(invoice['invoice_date'])],
        ['Booking:', invoice['booking_number'], 'Due Date:', invoice['due_date'].strftime('%Y-%m-%d') if isinstance(invoice['due_date'], datetime.date) else str(invoice['due_date'])],
        ['Pickup:', invoice['pickup_location'], 'Delivery:', invoice['delivery_location']],
        ['Movement:', invoice['movement_type'], 'Distance:', f"{invoice.get('distance_km', 0)} KM"],
        ['Vehicle:', invoice.get('vehicle_number', 'N/A'), 'Driver:', invoice.get('driver_name', 'N/A')]
    ]
    
    # Add contract details if applicable
    if invoice['invoice_type'] == "Contract Invoice":
        info_data.append(['Contract Period:', f"{invoice['contract_start_date']} to {invoice['contract_end_date']}", 'DSR Number:', invoice.get('dsr_number', 'N/A')])
    
    info_table = Table(info_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Charges table
    charges_data = [['Description', 'Amount (₹)']]
    charges_data.append(['Base Amount', f"{invoice['base_amount']:,.2f}"])
    
    if invoice.get('additional_fuel', 0) > 0:
        charges_data.append(['Additional Fuel Charges', f"{invoice['additional_fuel']:,.2f}"])
    if invoice.get('additional_toll', 0) > 0:
        charges_data.append(['Additional Toll Charges', f"{invoice['additional_toll']:,.2f}"])
    if invoice.get('additional_loading', 0) > 0:
        charges_data.append(['Additional Loading Charges', f"{invoice['additional_loading']:,.2f}"])
    if invoice.get('additional_detention', 0) > 0:
        charges_data.append(['Detention Charges', f"{invoice['additional_detention']:,.2f}"])
    if invoice.get('additional_misc', 0) > 0:
        charges_data.append(['Miscellaneous Charges', f"{invoice['additional_misc']:,.2f}"])
    if invoice.get('discount', 0) > 0:
        charges_data.append(['Discount', f"-{invoice['discount']:,.2f}"])
    
    charges_data.append(['Subtotal', f"{invoice['subtotal']:,.2f}"])
    
    if invoice.get('gst_applicable', False):
        charges_data.append([f"GST ({invoice.get('gst_rate', 18)}%)", f"{invoice.get('gst_amount', 0):,.2f}"])
    
    charges_data.append(['Total Amount', f"{invoice['total_amount']:,.2f}"])
    
    charges_table = Table(charges_data, colWidths=[4*inch, 2*inch])
    charges_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))
    
    elements.append(charges_table)
    elements.append(Spacer(1, 20))
    
    # Notes
    if invoice.get('invoice_notes'):
        notes_title = Paragraph("<b>Notes:</b>", styles['Normal'])
        elements.append(notes_title)
        notes = Paragraph(invoice['invoice_notes'], styles['Normal'])
        elements.append(notes)
        elements.append(Spacer(1, 20))
    
    # Payment details
    payment_info = Paragraph(f"""
    <b>Payment Information:</b><br/>
    Total Amount: ₹{invoice['total_amount']:,.2f}<br/>
    Outstanding: ₹{invoice.get('outstanding_amount', invoice['total_amount']):,.2f}<br/>
    Payment Terms: {invoice.get('payment_terms', 30)} days<br/>
    Status: {invoice.get('status', 'Generated')}
    """, styles['Normal'])
    elements.append(payment_info)
    elements.append(Spacer(1, 20))
    
    # Terms and conditions
    terms = Paragraph("""
    <b>Terms and Conditions:</b><br/>
    1. Payment should be made within the specified payment terms.<br/>
    2. All disputes should be reported within 7 days of invoice date.<br/>
    3. Interest will be charged on overdue amounts as per company policy.<br/>
    4. Goods once dispatched will not be taken back.<br/>
    5. This is a computer generated invoice and does not require signature.<br/>
    """, styles['Normal'])
    elements.append(terms)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data