import streamlit as st
import pandas as pd
import datetime
import uuid
from typing import Dict, List
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import requests
import tempfile
import os
from .quotations import safe_get_date

def update_payment_status():
    """Automatically update payment status based on total payments received"""
    for invoice in st.session_state.invoices:
        # Calculate total payments for this invoice
        total_payments = sum(
            float(payment['amount']) for payment in st.session_state.customer_payments 
            if payment.get('invoice_id') == invoice['id']
        )
        
        # Store old status for tracking
        old_status = invoice['status']
        
        # Update outstanding amount (ensure both are floats)
        invoice_total = float(invoice['total_amount'])
        invoice['outstanding_amount'] = invoice_total - total_payments
        
        # Update status based on payments
        new_status = None
        if total_payments == 0:
            new_status = 'Generated'
        elif total_payments >= invoice_total:
            new_status = 'Paid'
        else:
            new_status = 'Partially Paid'
        
        # Check for overdue (if due date passed and not fully paid)
        if (invoice.get('due_date') and 
            datetime.datetime.now().date() > invoice['due_date'] and 
            total_payments < invoice_total):
            new_status = 'Overdue'
        
        # Track status change if status changed
        if old_status != new_status:
            invoice['status'] = new_status
            from .notes import track_status_change
            track_status_change(
                record_id=invoice['id'],
                record_type='invoice',
                old_status=old_status,
                new_status=new_status,
                notes=f'Payment status updated - Outstanding: ₹{invoice["outstanding_amount"]:,.2f}',
                changed_by='System',
                additional_data={
                    'invoice_number': invoice['invoice_number'],
                    'total_payments': total_payments,
                    'outstanding_amount': invoice['outstanding_amount'],
                    'payment_update': True
                }
            )

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
    
    # Display eligible bookings in a searchable table format
    st.markdown("**Select Booking to Invoice:**")
    
    # Search and filter
    search_term = st.text_input("🔍 Search bookings by number, customer, or route", key="booking_search")
    
    # Filter bookings
    filtered_bookings = []
    for booking in eligible_bookings:
        if not search_term or \
           search_term.lower() in booking['booking_number'].lower() or \
           search_term.lower() in booking['customer_name'].lower() or \
           search_term.lower() in booking['pickup_location'].lower() or \
           search_term.lower() in booking['delivery_location'].lower():
            filtered_bookings.append(booking)
    
    # Display filtered bookings
    for booking in filtered_bookings:
        # Check if already invoiced
        existing_invoice = next((inv for inv in st.session_state.invoices if inv.get('booking_id') == booking['id']), None)
        
        if existing_invoice:
            status_text = f"✅ Already Invoiced ({existing_invoice['invoice_number']})"
            disabled = True
        else:
            status_text = "📋 Ready to Invoice"
            disabled = False
        
        with st.expander(f"{status_text} - {booking['booking_number']} - {booking['customer_name']} - ₹{booking['total_amount']:,.2f}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Booking Number:** {booking['booking_number']}")
                st.write(f"**Customer:** {booking['customer_name']}")
                st.write(f"**Route:** {booking['pickup_location']} → {booking['delivery_location']}")
                st.write(f"**Vehicle Type:** {booking['vehicle_type']}")
            
            with col2:
                st.write(f"**Status:** {booking['status']}")
                st.write(f"**Amount:** ₹{booking['total_amount']:,.2f}")
                st.write(f"**Trip Type:** {booking['trip_type']}")
                st.write(f"**Distance:** {booking['distance_km']} KM")
            
            with col3:
                if not disabled:
                    if st.button(f"Create Invoice", key=f"invoice_booking_{booking['id']}", type="primary"):
                        create_invoice_from_booking(booking)
                        st.rerun()
                else:
                    st.info("Invoice already created for this booking")
                    if existing_invoice and st.button(f"View Invoice {existing_invoice['invoice_number']}", key=f"view_invoice_{existing_invoice['id']}"):
                        st.session_state.selected_invoice_id = existing_invoice['id']
                        st.success(f"Navigate to View Invoices tab to see invoice {existing_invoice['invoice_number']}")
    
    if not filtered_bookings:
        st.info("No bookings match your search criteria.")
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
    
    # Charges breakdown from booking
    st.markdown("**Charges Breakdown (From Booking)**")
    
    # Get booking charges with fallback to 0 and ensure float conversion with None handling
    def safe_float(value, default=0.0):
        """Safely convert value to float, handling None and invalid values"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    booking_base = safe_float(booking.get('base_amount'), 0.0)
    booking_loading = safe_float(booking.get('loading_charges'), 0.0)
    booking_unloading = safe_float(booking.get('unloading_charges'), 0.0)
    booking_airport_pass = safe_float(booking.get('airport_pass_charges'), 0.0)
    booking_halting = safe_float(booking.get('halting_charges'), 0.0)
    booking_fuel = safe_float(booking.get('fuel_charges'), 0.0)
    booking_toll = safe_float(booking.get('toll_charges'), 0.0)
    booking_other = safe_float(booking.get('other_charges'), 0.0)
    booking_discount = safe_float(booking.get('discount'), 0.0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Base Amount", f"₹{booking_base:,.2f}")
        st.metric("Loading Charges", f"₹{booking_loading:,.2f}")
    
    with col2:
        st.metric("Unloading Charges", f"₹{booking_unloading:,.2f}")
        st.metric("Airport Pass", f"₹{booking_airport_pass:,.2f}")
    
    with col3:
        st.metric("Fuel Charges", f"₹{booking_fuel:,.2f}")
        st.metric("Toll Charges", f"₹{booking_toll:,.2f}")
    
    with col4:
        st.metric("Other Charges", f"₹{booking_other:,.2f}")
        st.metric("Discount", f"₹{booking_discount:,.2f}")
    
    # Additional charges/adjustments
    st.markdown("**Additional Charges & Adjustments**")
    st.info("Add any extra charges beyond what was in the original booking")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        additional_fuel = st.number_input("Extra Fuel Charges (₹)", min_value=0.0, value=0.0, key="invoice_fuel")
        additional_toll = st.number_input("Extra Toll Charges (₹)", min_value=0.0, value=0.0, key="invoice_toll")
    
    with col2:
        additional_loading = st.number_input("Extra Loading Charges (₹)", min_value=0.0, value=0.0, key="invoice_loading")
        additional_detention = st.number_input("Detention Charges (₹)", min_value=0.0, value=0.0, key="invoice_detention")
    
    with col3:
        additional_misc = st.number_input("Miscellaneous Charges (₹)", min_value=0.0, value=0.0, key="invoice_misc")
        extra_discount = st.number_input("Extra Discount (₹)", min_value=0.0, value=0.0, key="invoice_discount")
    
    # Calculate amounts - Use booking's existing amounts to avoid GST duplication
    # Get booking's existing GST information
    booking_gst_applicable = booking.get('gst_applicable', True)
    booking_gst_amount = safe_float(booking.get('gst_amount'), 0.0)
    booking_total_amount = safe_float(booking.get('total_amount'), 0.0)
    
    # Base amount should be the booking's subtotal (before GST)
    if booking_gst_applicable and booking_gst_amount > 0:
        # If booking has GST, calculate the pre-GST amount
        booking_subtotal = booking_total_amount - booking_gst_amount
    else:
        booking_subtotal = booking_total_amount
    
    # All booking charges (these are already in the booking subtotal, so don't double count)
    booking_charges_total = float(booking_loading + booking_unloading + booking_airport_pass + booking_halting + booking_fuel + booking_toll + booking_other - booking_discount)
    
    # Additional charges from invoice form (these are new)
    additional_charges = float(additional_fuel + additional_toll + additional_loading + additional_detention + additional_misc - extra_discount)
    
    # Base amount is booking base + additional charges (but not other booking charges as they're already included in booking total)
    base_amount = booking_base + additional_charges
    
    # Calculate total discount
    total_discount = booking_discount + extra_discount
    
    # Calculate new subtotal
    subtotal = base_amount
    
    # GST handling - respect booking's GST settings and only apply to additional charges
    if invoice_type == "GST Invoice":
        gst_applicable = True
        
        # Get customer GST info if available
        customer_data = next((c for c in st.session_state.customers if c['id'] == booking['customer_id']), None)
        customer_gst = customer_data.get('gst_number', '') if customer_data else ''
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Use booking's GST rate if available, otherwise default to 18%
            default_gst_rate = 18
            if booking_gst_applicable and booking_gst_amount > 0 and booking_subtotal > 0:
                calculated_rate = round((booking_gst_amount / booking_subtotal) * 100)
                default_gst_rate = calculated_rate if calculated_rate in [5, 12, 18, 28] else 18
            
            gst_rate = st.selectbox("GST Rate (%)", [5, 12, 18, 28], 
                                 index=[5, 12, 18, 28].index(default_gst_rate) if default_gst_rate in [5, 12, 18, 28] else 2, 
                                 key="gst_rate")
        
        with col2:
            # Show customer GST status
            if customer_gst:
                st.success(f"✅ Customer GST: {customer_gst}")
            else:
                st.warning("⚠️ No customer GST number on file")
        
        with col3:
            # GST calculation options
            gst_type = st.selectbox("GST Type", ["CGST+SGST", "IGST"], key="gst_type",
                                   help="CGST+SGST for same state, IGST for interstate")
        
        # Apply GST to the subtotal (booking base + additional charges)
        gst_amount = float(subtotal * (gst_rate / 100))
        total_amount = float(subtotal + gst_amount)
        
        # Show GST breakdown
        st.markdown(f"**GST Breakdown ({gst_type}):**")
        if additional_charges > 0:
            st.info(f"📝 GST applied only to base amount (₹{booking_base:,.2f}) + additional charges (₹{additional_charges:,.2f})")
        else:
            st.info(f"📝 GST applied to booking base amount (₹{booking_base:,.2f})")
            
        if gst_type == "CGST+SGST":
            cgst = sgst = gst_amount / 2
            st.write(f"CGST ({gst_rate/2}%): ₹{cgst:,.2f}")
            st.write(f"SGST ({gst_rate/2}%): ₹{sgst:,.2f}")
        else:
            st.write(f"IGST ({gst_rate}%): ₹{gst_amount:,.2f}")
            
    elif booking_gst_applicable:
        # If booking had GST but invoice type is not GST invoice, use booking's GST
        st.warning("⚠️ Original booking included GST. Using booking's GST calculation to avoid duplication.")
        gst_applicable = True
        gst_amount = booking_gst_amount
        gst_rate = round((booking_gst_amount / booking_subtotal) * 100) if booking_subtotal > 0 else 18
        gst_type = "From Booking"
        total_amount = float(subtotal + gst_amount)
        
        st.info(f"📝 Using booking's GST: ₹{gst_amount:,.2f} ({gst_rate}%)")
        
    else:
        # No GST applicable
        gst_applicable = False
        gst_rate = 0
        gst_amount = 0.0
        gst_type = ""
        total_amount = float(subtotal)
    
    # Display calculated amounts
    st.markdown("**Invoice Summary**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Base Amount", f"₹{base_amount:,.2f}")
    
    with col2:
        st.metric("Additional Charges", f"₹{additional_charges:,.2f}")
    
    with col3:
        if gst_applicable:
            st.metric(f"GST ({gst_rate}%)", f"₹{gst_amount:,.2f}")
        else:
            st.metric("Total Discount", f"₹{total_discount:,.2f}")
    
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
            # Booking charges
            'booking_loading_charges': booking_loading,
            'booking_unloading_charges': booking_unloading,
            'booking_airport_pass_charges': booking_airport_pass,
            'booking_halting_charges': booking_halting,
            'booking_fuel_charges': booking_fuel,
            'booking_toll_charges': booking_toll,
            'booking_other_charges': booking_other,
            'booking_discount': booking_discount,
            # Additional charges from invoice
            'additional_fuel': additional_fuel,
            'additional_toll': additional_toll,
            'additional_loading': additional_loading,
            'additional_detention': additional_detention,
            'additional_misc': additional_misc,
            'additional_charges': additional_charges,
            'extra_discount': extra_discount,
            'total_discount': total_discount,
            'subtotal': subtotal,
            'gst_applicable': gst_applicable,
            'gst_rate': gst_rate if gst_applicable else 0,
            'gst_amount': gst_amount,
            'gst_type': locals().get('gst_type', ''),
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
            
            # Track status change for new invoice
            from .notes import track_status_change
            track_status_change(
                record_id=invoice['id'],
                record_type='invoice',
                old_status='',
                new_status='Generated',
                notes=f'Invoice generated from booking {booking["booking_number"]}',
                additional_data={
                    'invoice_number': invoice['invoice_number'],
                    'booking_number': booking['booking_number'],
                    'invoice_type': invoice_type,
                    'customer_name': invoice['customer_name'],
                    'total_amount': total_amount
                }
            )
            
            # Update booking status
            old_booking_status = booking['status']
            booking['status'] = 'Invoiced'
            booking['invoiced_date'] = datetime.datetime.now()
            
            # Track booking status change
            track_status_change(
                record_id=booking['id'],
                record_type='booking',
                old_status=old_booking_status,
                new_status='Invoiced',
                notes=f'Booking invoiced - Invoice #{invoice["invoice_number"]} generated',
                additional_data={
                    'booking_number': booking['booking_number'],
                    'invoice_number': invoice['invoice_number']
                }
            )
            
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
        if invoice.get('total_discount', 0) > 0:
            invoice_data.append(["Total Discount", f"-₹{invoice['total_discount']:,.2f}"])
        
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
        outstanding_amount = sum(float(inv['outstanding_amount']) for inv in filtered_invoices)
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
                    st.session_state[f"show_invoice_details_{invoice['id']}"] = True
                    st.rerun()
            
            # Show detailed view if requested
            if st.session_state.get(f"show_invoice_details_{invoice['id']}", False):
                st.markdown("---")
                st.markdown("**📋 Detailed Invoice Breakdown:**")
                
                # Invoice information
                detail_col1, detail_col2, detail_col3 = st.columns(3)
                
                with detail_col1:
                    st.markdown("**Basic Information**")
                    st.write(f"Invoice Number: {invoice['invoice_number']}")
                    st.write(f"Invoice Type: {invoice['invoice_type']}")
                    st.write(f"Movement Type: {invoice['movement_type']}")
                    st.write(f"Invoice Date: {invoice['invoice_date']}")
                    st.write(f"Due Date: {invoice['due_date']}")
                
                with detail_col2:
                    st.markdown("**Trip Information**")
                    st.write(f"Booking: {invoice['booking_number']}")
                    st.write(f"Pickup: {invoice['pickup_location']}")
                    st.write(f"Delivery: {invoice['delivery_location']}")
                    st.write(f"Distance: {invoice['distance_km']} KM")
                    if invoice.get('vehicle_number'):
                        st.write(f"Vehicle: {invoice['vehicle_number']}")
                
                with detail_col3:
                    st.markdown("**Financial Summary**")
                    st.write(f"Base Amount: ₹{invoice['base_amount']:,.2f}")
                    st.write(f"Total Charges: ₹{invoice['subtotal']:,.2f}")
                    if invoice.get('gst_applicable'):
                        st.write(f"GST ({invoice['gst_rate']}%): ₹{invoice['gst_amount']:,.2f}")
                    st.write(f"**Total: ₹{invoice['total_amount']:,.2f}**")
                    st.write(f"**Outstanding: ₹{invoice['outstanding_amount']:,.2f}**")
                
                # Charges breakdown
                if invoice.get('booking_loading_charges', 0) > 0 or invoice.get('additional_fuel', 0) > 0:
                    st.markdown("**Charges Breakdown:**")
                    charges_col1, charges_col2 = st.columns(2)
                    
                    with charges_col1:
                        st.markdown("*From Booking:*")
                        if invoice.get('booking_loading_charges', 0) > 0:
                            st.write(f"Loading: ₹{invoice['booking_loading_charges']:,.2f}")
                        if invoice.get('booking_unloading_charges', 0) > 0:
                            st.write(f"Unloading: ₹{invoice['booking_unloading_charges']:,.2f}")
                        if invoice.get('booking_fuel_charges', 0) > 0:
                            st.write(f"Fuel: ₹{invoice['booking_fuel_charges']:,.2f}")
                        if invoice.get('booking_toll_charges', 0) > 0:
                            st.write(f"Toll: ₹{invoice['booking_toll_charges']:,.2f}")
                    
                    with charges_col2:
                        st.markdown("*Additional:*")
                        if invoice.get('additional_fuel', 0) > 0:
                            st.write(f"Extra Fuel: ₹{invoice['additional_fuel']:,.2f}")
                        if invoice.get('additional_loading', 0) > 0:
                            st.write(f"Extra Loading: ₹{invoice['additional_loading']:,.2f}")
                        if invoice.get('additional_detention', 0) > 0:
                            st.write(f"Detention: ₹{invoice['additional_detention']:,.2f}")
                        if invoice.get('total_discount', 0) > 0:
                            st.write(f"Discount: -₹{invoice['total_discount']:,.2f}")
                
                # Close button
                if st.button(f"Close Details", key=f"close_details_{invoice['id']}"):
                    del st.session_state[f"show_invoice_details_{invoice['id']}"]
                    st.rerun()
            
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

def download_logo_image():
    """Download and cache the S TRANZ logo image"""
    logo_url = "https://www.stranz.in/hs-fs/hubfs/photo_2025-10-25_10-14-37.jpg?width=600"
    
    try:
        # Create a temporary file to store the logo
        temp_dir = tempfile.gettempdir()
        logo_path = os.path.join(temp_dir, "stranz_logo.jpg")
        
        # Check if logo already exists and is recent (less than 1 day old)
        if os.path.exists(logo_path):
            file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(logo_path))
            if file_age.days < 1:
                return logo_path
        
        # Download the logo
        response = requests.get(logo_url, timeout=10)
        response.raise_for_status()
        
        # Save the logo
        with open(logo_path, 'wb') as f:
            f.write(response.content)
        
        return logo_path
    
    except Exception as e:
        print(f"Warning: Could not download logo: {str(e)}")
        return None

def generate_invoice_pdf(invoice):
    """Generate PDF for invoice in S TRANZ format"""
    
    def safe_float(value, default=0.0):
        """Safely convert value to float, handling None and invalid values"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Container for the 'Flowable' objects
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    company_style = ParagraphStyle(
        'CompanyStyle',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        spaceAfter=6,
        textColor=colors.black
    )
    
    invoice_title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Normal'],
        fontSize=24,
        fontName='Helvetica-Bold',
        spaceAfter=12,
        alignment=2,  # Right alignment
        textColor=colors.black
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Normal'],
        fontSize=15,
        fontName='Helvetica-Bold',
        spaceAfter=6,
        textColor=colors.black
    )
    
    # Header with company info and logo
    logo_path = download_logo_image()
    
    # Prepare logo image if available
    logo_img = None
    if logo_path and os.path.exists(logo_path):
        try:
            logo_img = Image(logo_path, width=2*inch, height=1*inch)
            logo_img.hAlign = 'RIGHT'
        except Exception as e:
            print(f"Warning: Could not load logo image: {str(e)}")
            logo_img = None
    
    # Create header with company info and logo/invoice title
    if logo_img:
        header_data = [
            [
                # Company Info Column
                Paragraph("""<font color="black"><b>S TRANZ</b><br/>
                NO.22, PADMALAYAM<br/>
                1st STREET, SARASWATHIPURAM,<br/>
                CHROMPET CHENNAI - 600044<br/>
                GSTIN: 33CGPP57873Q1ZZ<br/>
                Email: info.stranz@gmail.com<br/>
                Phone: +91 73580 47373<br/>
                www.Stranz.in</font>""", company_style),
                # Logo and Invoice title column
                [logo_img, Paragraph('<font size="24"><b>INVOICE</b></font>', invoice_title_style)]
            ]
        ]
        header_table = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
    else:
        # Fallback without logo
        header_data = [
            [
                # Company Info Column
                Paragraph("""<font color="black"><b>S TRANZ</b><br/>
                NO.22, PADMALAYAM<br/>
                1st STREET, SARASWATHIPURAM,<br/>
                CHROMPET CHENNAI - 600044<br/>
                GSTIN: 33CGPP57873Q1ZZ<br/>
                Email: info.stranz@gmail.com<br/>
                Phone: +91 73580 47373<br/>
                www.Stranz.in</font>""", company_style),
                # Invoice title
                Paragraph('<font size="24"><b>INVOICE</b></font>', invoice_title_style)
            ]
        ]
        header_table = Table(header_data, colWidths=[4*inch, 3*inch])
    
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 12))
    
    # Tax line
    tax_line = Paragraph('<b>TAX PAYABLE ON REVERSE CHARGE: YES</b>', ParagraphStyle(
        'TaxLine', parent=styles['Normal'], fontSize=15, fontName='Helvetica-Bold', alignment=1))
    elements.append(tax_line)
    elements.append(Spacer(1, 12))
    
    # Invoice details and customer info section
    # Get booking details for additional info
    booking = next((b for b in st.session_state.bookings if b['booking_number'] == invoice['booking_number']), None)
    customer = next((c for c in st.session_state.customers if c['name'] == invoice['customer_name']), None)
    
    invoice_info_data = [
        [
            # Left column - Invoice To and Shipped To
            Paragraph(f"""<b>INVOICE TO:</b><br/>
            {invoice['customer_name']}<br/>
            {customer.get('address', 'N/A') if customer else 'N/A'}""", section_style),
            # Right column - Invoice details
            Paragraph(f"""<b>INVOICE NO:</b>&nbsp;&nbsp;&nbsp;&nbsp;{invoice['invoice_number']}<br/>
            <b>INVOICE DATE:</b>&nbsp;&nbsp;&nbsp;&nbsp;{invoice['invoice_date'].strftime('%d/%m/%Y') if isinstance(invoice['invoice_date'], datetime.date) else str(invoice['invoice_date'])}<br/>
            <b>DUE DATE:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{invoice['due_date'].strftime('%d/%m/%Y') if isinstance(invoice['due_date'], datetime.date) else str(invoice['due_date'])}<br/>
            <b>PICKUP DATE:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{booking.get('pickup_date', 'N/A') if booking else 'N/A'}<br/>
            <b>DELIVERY DATE:</b>&nbsp;&nbsp;{booking.get('delivery_date', 'N/A') if booking else 'N/A'}""", section_style)
        ]
    ]
    
    # Add shipped to info
    shipped_to_data = [
        [
            Paragraph(f"""<b>SHIPPED TO:</b><br/>
            {invoice['delivery_location']}<br/>
            Contact: {booking.get('delivery_contact', 'N/A') if booking else 'N/A'}""", section_style),
            Paragraph(f"""<b>PICK FROM:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{invoice['pickup_location']}<br/>
            <b>DELIVERED TO:</b>&nbsp;&nbsp;&nbsp;{invoice['delivery_location']}<br/>
            <b>PACKAGE DETAILS:</b>&nbsp;{booking.get('material_type', 'GENERAL CARGO') if booking else 'GENERAL CARGO'}<br/>
            <b>REFERENCE NO:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{invoice['booking_number']}""", section_style)
        ]
    ]
    
    info_table = Table(invoice_info_data + shipped_to_data, colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 12))
    
    # Description section
    desc_text = f"Booking Ref: {invoice['booking_number']}, Vehicle: {invoice.get('vehicle_number', 'N/A')}, Movement: {invoice['movement_type']}"
    if booking and booking.get('description'):
        desc_text += f", {booking['description']}"
    
    description = Paragraph(f"<b>DESCRIPTION:</b><br/>{desc_text}", section_style)
    elements.append(description)
    elements.append(Spacer(1, 15))
    
    # Charges table in S TRANZ format
    charges_data = [
        ['CHARGES', 'QTY', 'RATE', 'AMOUNT']
    ]
    
    # Transportation charges section
    charges_data.append(['TRANSPORTATION CHARGES:', '', '', ''])
    
    # Base transportation charge
    charges_data.append(['- Transportation Service', '1', f"{safe_float(invoice.get('base_amount')):.2f}", f"{safe_float(invoice.get('base_amount')):.2f}"])
    
    # Add all additional charges from invoice (these are the changes/additions)
    additional_charges_added = False
    
    # Fuel charges - check all possible field names
    fuel_charges = []
    if invoice.get('booking_fuel_charges', 0) > 0:
        fuel_charges.append(('Fuel (Booking)', safe_float(invoice.get('booking_fuel_charges', 0))))
    if invoice.get('additional_fuel', 0) > 0:
        fuel_charges.append(('Additional Fuel', safe_float(invoice.get('additional_fuel', 0))))
    if invoice.get('fuel_charges', 0) > 0:  # Legacy field
        fuel_charges.append(('Fuel Charges', safe_float(invoice.get('fuel_charges', 0))))
    
    for fuel_desc, fuel_amt in fuel_charges:
        charges_data.append([f'- {fuel_desc}', '1', f"{fuel_amt:.2f}", f"{fuel_amt:.2f}"])
        additional_charges_added = True
    
    # Toll charges - check all possible field names
    toll_charges = []
    if invoice.get('booking_toll_charges', 0) > 0:
        toll_charges.append(('Toll (Booking)', safe_float(invoice.get('booking_toll_charges', 0))))
    if invoice.get('additional_toll', 0) > 0:
        toll_charges.append(('Additional Toll', safe_float(invoice.get('additional_toll', 0))))
    if invoice.get('toll_charges', 0) > 0:  # Legacy field
        toll_charges.append(('Toll Charges', safe_float(invoice.get('toll_charges', 0))))
    
    for toll_desc, toll_amt in toll_charges:
        charges_data.append([f'- {toll_desc}', '1', f"{toll_amt:.2f}", f"{toll_amt:.2f}"])
        additional_charges_added = True
    
    # Loading/Unloading charges
    loading_charges = []
    if invoice.get('booking_loading_charges', 0) > 0:
        loading_charges.append(('Loading (Booking)', safe_float(invoice.get('booking_loading_charges', 0))))
    if invoice.get('booking_unloading_charges', 0) > 0:
        loading_charges.append(('Unloading (Booking)', safe_float(invoice.get('booking_unloading_charges', 0))))
    if invoice.get('additional_loading', 0) > 0:
        loading_charges.append(('Additional Loading', safe_float(invoice.get('additional_loading', 0))))
    if invoice.get('loading_charges', 0) > 0:  # Legacy field
        loading_charges.append(('Loading Charges', safe_float(invoice.get('loading_charges', 0))))
    
    for loading_desc, loading_amt in loading_charges:
        charges_data.append([f'- {loading_desc}', '1', f"{loading_amt:.2f}", f"{loading_amt:.2f}"])
        additional_charges_added = True
    
    # Detention charges
    if invoice.get('additional_detention', 0) > 0:
        charges_data.append(['- Detention Charges', '1', f"{safe_float(invoice.get('additional_detention')):.2f}", f"{safe_float(invoice.get('additional_detention')):.2f}"])
        additional_charges_added = True
    
    # Other charges - combine various miscellaneous charges
    other_charges = []
    if invoice.get('booking_airport_pass_charges', 0) > 0:
        other_charges.append(('Airport Pass', safe_float(invoice.get('booking_airport_pass_charges', 0))))
    if invoice.get('booking_halting_charges', 0) > 0:
        other_charges.append(('Halting', safe_float(invoice.get('booking_halting_charges', 0))))
    if invoice.get('booking_other_charges', 0) > 0:
        other_charges.append(('Other (Booking)', safe_float(invoice.get('booking_other_charges', 0))))
    if invoice.get('additional_misc', 0) > 0:
        other_charges.append(('Miscellaneous', safe_float(invoice.get('additional_misc', 0))))
    if invoice.get('other_charges', 0) > 0:  # Legacy field
        other_charges.append(('Other Charges', safe_float(invoice.get('other_charges', 0))))
    
    for other_desc, other_amt in other_charges:
        charges_data.append([f'- {other_desc}', '1', f"{other_amt:.2f}", f"{other_amt:.2f}"])
        additional_charges_added = True
    
    # Calculate total charges for subtotal display
    total_charges = safe_float(invoice.get('subtotal', 0))
    charges_data.append(['', '', 'TOTAL:', f"{total_charges:.2f}"])
    
    charges_table = Table(charges_data, colWidths=[3*inch, 0.8*inch, 1.2*inch, 1.2*inch])
    charges_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),  # Transportation charges header
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),  # Line under header
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),  # Line under total
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Bold total row
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    # Add styling for other charges header if it exists
    if additional_charges_added:
        # Find the "TRANSPORTATION CHARGES:" row and make it bold
        for i, row in enumerate(charges_data):
            if row[0] == 'TRANSPORTATION CHARGES:':
                charges_table.setStyle(TableStyle([
                    ('FONTNAME', (0, i), (0, i), 'Helvetica-Bold')
                ]))
                break
    
    elements.append(charges_table)
    elements.append(Spacer(1, 15))
    
    # Amount summary section
    amount_words = convert_amount_to_words(invoice['total_amount'])
    
    # Calculate GST (18% of subtotal)
    subtotal = safe_float(invoice.get('subtotal', 0))
    gst_rate = 0.18  # 18% GST
    gst_amount = subtotal * gst_rate
    
    summary_data = [
        ['AMOUNT IN WORDS:', 'SUBTOTAL:', f"{subtotal:.2f}"],
        [Paragraph(amount_words, ParagraphStyle('AmountWords', parent=styles['Normal'], fontSize=14, fontName='Helvetica')), 'GST (18%):', f"{gst_amount:.2f}"],
        ['', 'TOTAL AMOUNT:', f"{subtotal + gst_amount:.2f}"],
        ['', 'ADVANCE PAID:', f"{invoice.get('advance_paid', 0):.2f}"],
        ['', 'BALANCE DUE:', f"{invoice.get('outstanding_amount', subtotal + gst_amount):.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[3.5*inch, 1.5*inch, 1.2*inch], rowHeights=[None, 25, None, None, None])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (0, 1), (0, 1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (1, 0), (-1, 0), 1, colors.black),  # Line under headers
        ('LINEBELOW', (1, -1), (-1, -1), 2, colors.black),  # Double line under balance due
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Bank details section
    bank_details = Paragraph("""
    <b>BANK DETAILS:</b><br/>
    Bank: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;KARUR VYSYA BANK<br/>
    A/C Name: &nbsp;&nbsp;&nbsp;S TRANZ<br/>
    A/C No: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1650115000002749<br/>
    IFSC Code: &nbsp;&nbsp;KVBL0001650<br/>
    Branch: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Pallavaram Branch
    """, ParagraphStyle('BankDetails', parent=styles['Normal'], fontSize=14, fontName='Helvetica'))
    
    # Signature section
    signature_data = [
        [bank_details, 'For S Tranz']
    ]
    
    signature_table = Table(signature_data, colWidths=[4*inch, 2.5*inch])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (1, 0), (1, 0), 14),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
    ]))
    
    elements.append(signature_table)
    elements.append(Spacer(1, 25))
    
    # Footer
    footer = Paragraph("""
    <para align="center">
    THANKS FOR BEING A VALUED CLIENT. LOOKING FORWARD TO THE NEXT OPPORTUNITY<br/>
    <i>(This invoice has been generated by our accounting system and is valid without a physical signature)</i>
    </para>
    """, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=14, alignment=1))
    
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

def convert_amount_to_words(amount):
    """Convert numerical amount to words in Indian format"""
    try:
        amount = float(amount)
        
        # Handle special cases
        if amount == 0:
            return "Zero Rupees Only"
        
        # For amounts up to 99,999 - basic conversion
        def convert_hundreds(num):
            ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
                   "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", 
                   "Seventeen", "Eighteen", "Nineteen"]
            tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
            
            result = ""
            
            # Hundreds
            if num >= 100:
                result += ones[num // 100] + " Hundred "
                num %= 100
            
            # Tens and ones
            if num >= 20:
                result += tens[num // 10]
                if num % 10 > 0:
                    result += " " + ones[num % 10]
            elif num > 0:
                result += ones[num]
            
            return result.strip()
        
        # Handle amounts in Indian numbering system
        amount_int = int(amount)
        
        if amount_int < 1000:
            words = convert_hundreds(amount_int)
        elif amount_int < 100000:  # Up to 99,999
            thousands = amount_int // 1000
            remainder = amount_int % 1000
            
            words = convert_hundreds(thousands) + " Thousand"
            if remainder > 0:
                words += " " + convert_hundreds(remainder)
        elif amount_int < 10000000:  # Up to 99,99,999 (99 Lakhs)
            lakhs = amount_int // 100000
            remainder = amount_int % 100000
            
            words = convert_hundreds(lakhs) + " Lakh"
            if remainder > 0:
                if remainder >= 1000:
                    thousands = remainder // 1000
                    remainder = remainder % 1000
                    words += " " + convert_hundreds(thousands) + " Thousand"
                if remainder > 0:
                    words += " " + convert_hundreds(remainder)
        else:
            # For very large amounts, use a simpler format
            words = f"Rupees {amount:,.2f}"
        
        # Add "Rupees" and "Only" to complete the format
        if not words.startswith("Rupees"):
            words = words + " Rupees"
        
        # Handle decimals (paise)
        decimal_part = amount - amount_int
        if decimal_part > 0:
            paise = int(round(decimal_part * 100))
            if paise > 0:
                words += f" and {convert_hundreds(paise)} Paise"
        
        words += " Only"
        
        return words
        
    except Exception as e:
        return f"Amount: ₹{amount:,.2f}"