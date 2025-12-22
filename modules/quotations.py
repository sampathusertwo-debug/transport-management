import streamlit as st
import pandas as pd
import datetime
import uuid
import re
from typing import Dict, List
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
from .utils import searchable_selectbox, static_selectbox

def safe_get_date(date_field):
    """Safely extract date from various date formats"""
    if isinstance(date_field, str):
        try:
            return datetime.datetime.fromisoformat(date_field.replace('Z', '+00:00')).date()
        except:
            try:
                return datetime.datetime.strptime(date_field, '%Y-%m-%d %H:%M:%S').date()
            except:
                try:
                    return datetime.datetime.strptime(date_field, '%Y-%m-%d').date()
                except:
                    return datetime.date.today()
    elif hasattr(date_field, 'date'):
        return date_field.date()
    elif isinstance(date_field, datetime.date):
        return date_field
    else:
        return datetime.date.today()

def safe_format_date(date_field, format_str='%Y-%m-%d'):
    """Safely format date from various date formats"""
    try:
        if isinstance(date_field, str):
            # Try to parse string dates and format them
            try:
                parsed_date = datetime.datetime.fromisoformat(date_field.replace('Z', '+00:00'))
                return parsed_date.strftime(format_str)
            except:
                try:
                    parsed_date = datetime.datetime.strptime(date_field, '%Y-%m-%d %H:%M:%S')
                    return parsed_date.strftime(format_str)
                except:
                    try:
                        parsed_date = datetime.datetime.strptime(date_field, '%Y-%m-%d')
                        return parsed_date.strftime(format_str)
                    except:
                        return date_field  # Return as-is if can't parse
        elif hasattr(date_field, 'strftime'):
            return date_field.strftime(format_str)
        else:
            return str(date_field)
    except:
        return str(date_field)

def update_quotation_status(quotation_id, new_status):
    """Update quotation status in database and refresh session data"""
    from database import update_in_database, get_cached_data
    from .notes import add_status_note
    
    # Find the quotation to get the current status
    quotation = next((q for q in st.session_state.quotations if q['id'] == quotation_id), None)
    old_status = quotation['status'] if quotation else 'Unknown'
    
    success = update_in_database('quotations', {'status': new_status}, quotation_id)
    if success:
        # Add status change note
        quotation_number = quotation['quotation_number'] if quotation else quotation_id
        add_status_note(
            record_id=quotation_id,
            record_type='quotation',
            old_status=old_status,
            new_status=new_status,
            changed_by='Admin',
            notes=f"Quotation {quotation_number} status changed from {old_status} to {new_status}",
            additional_data={'quotation_number': quotation_number}
        )
        
        # Refresh quotations data from database
        st.session_state.quotations = get_cached_data('quotations', limit=100)
        
        # Clear notes cache to ensure fresh data on next load
        if 'notes_data_loaded' in st.session_state:
            st.session_state.notes_data_loaded = False
            
        return True
    return False

def validate_mobile_number(phone):
    """Validate 10-digit mobile number"""
    if not phone:
        return True  # Empty is allowed
    # Remove any spaces or hyphens
    phone = re.sub(r'[\s\-]', '', phone)
    # Check if it's exactly 10 digits and starts with 6-9
    return re.match(r'^[6-9]\d{9}$', phone) is not None

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
    """Display the quotations module"""
    st.header("📋 Quotations Management")
    
    tab1, tab2, tab3 = st.tabs(["Create Quotation", "View Quotations", "Manage Customers"])
    
    with tab1:
        create_quotation()
    
    with tab2:
        view_quotations()
    
    with tab3:
        manage_customers()

def create_quotation():
    """Create a new quotation"""
    st.subheader("Create New Quotation")
    
    # Load customers and quotations to ensure we have latest data
    from database import get_cached_data
    st.session_state.customers = get_cached_data('customers')
    st.session_state.quotations = get_cached_data('quotations', limit=100)
    
    # Customer selection/creation
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get existing customers
        existing_customers = [customer['name'] for customer in st.session_state.customers]
        
        if existing_customers:
            customer_choice = searchable_selectbox(
                "Select Customer",
                ["New Customer"] + existing_customers,
                key="quotation_customer_choice"
            )
        else:
            customer_choice = "New Customer"
            st.info("No existing customers found. Please create a new customer.")
    
    with col2:
        if st.button("Refresh Customers"):
            st.rerun()
    
    # Customer details
    if customer_choice == "New Customer":
        st.markdown("**New Customer Details**")
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("Customer Name*", key="new_customer_name")
            customer_email = st.text_input("Email", key="new_customer_email")
            customer_phone = st.text_input("Phone*", key="new_customer_phone", help="Enter 10-digit mobile number")
            if customer_phone and not validate_mobile_number(customer_phone):
                st.error("Please enter a valid 10-digit mobile number")
        
        with col2:
            customer_address = st.text_area("Address", key="new_customer_address")
            customer_gst = st.text_input("GST Number", key="new_customer_gst")
            customer_pan = st.text_input("PAN Number", key="new_customer_pan")
    else:
        # Get existing customer details
        customer_data = next((c for c in st.session_state.customers if c['name'] == customer_choice), None)
        if customer_data:
            st.success(f"✅ **Customer Selected:** {customer_data['name']}")
            
            # Display customer details in an info box
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"📞 **Phone:** {customer_data['phone']}")
                st.info(f"📧 **Email:** {customer_data.get('email', 'Not provided')}")
            with col2:
                st.info(f"📍 **Address:** {customer_data.get('address', 'Not provided')}")
                st.info(f"💰 **Payment Terms:** {customer_data.get('payment_terms', 30)} days")
    
    st.markdown("---")
    
    # Quotation details
    st.markdown("**Quotation Details**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pickup_location = st.text_input("Pickup Location*", key="quotation_pickup")
        delivery_location = st.text_input("Delivery Location*", key="quotation_delivery")
        vehicle_type = static_selectbox(
            "Vehicle Type",
            ["Tata Ace - 7ft", "Bolero / Dost - 8ft", "12 ft", "14 ft", "17 ft", "20 ft", "24 ft", "32 ft"],
            key="quotation_vehicle_type"
        )
        reference_number = st.text_input("Reference Number", key="quotation_reference", help="Customer or internal reference")
    
    with col2:
        distance_km = st.number_input("Distance (KM)", min_value=0.0, value=0.0, key="quotation_distance")
        
        # Weight with unit selection
        weight_col1, weight_col2 = st.columns([2, 1])
        with weight_col1:
            weight_capacity = st.number_input("Weight Capacity", min_value=0.0, value=1.0, key="quotation_weight")
        with weight_col2:
            weight_unit = static_selectbox("Unit", ["kg", "tons"], key="quotation_weight_unit")
            
        trip_type = static_selectbox(
            "Trip Type",
            ["Local", "Long Distance", "Contract"],
            key="quotation_trip_type"
        )
    
    with col3:
        base_price = st.number_input("Base Price (₹)*", min_value=0.0, value=0.0, key="quotation_base_price")
        gst_applicable = st.checkbox("GST Applicable", value=True, key="quotation_gst")
        payment_terms = static_selectbox(
            "Payment Terms (Days)*",
            [30, 45, 60, 90],
            key="quotation_payment_terms"
        )
    
    # Additional charges
    st.markdown("**Additional Charges**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        loading_charges = st.number_input("Loading Charges (₹)", min_value=0.0, value=0.0, key="quotation_loading")
        unloading_charges = st.number_input("Unloading Charges (₹)", min_value=0.0, value=0.0, key="quotation_unloading")
    
    with col2:
        airport_pass_charges = st.number_input("Airport Pass Charges (₹)", min_value=0.0, value=0.0, key="quotation_airport_pass")
        halting_charges = st.number_input("Halting Charges (₹)", min_value=0.0, value=0.0, key="quotation_halting")
    
    with col3:
        fuel_surcharge = st.number_input("Fuel Surcharge (₹)", min_value=0.0, value=0.0, key="quotation_fuel")
        toll_charges = st.number_input("Toll Charges (₹)", min_value=0.0, value=0.0, key="quotation_toll")
    
    with col4:
        other_charges = st.number_input("Other Charges (₹)", min_value=0.0, value=0.0, key="quotation_other")
        discount = st.number_input("Discount (₹)", min_value=0.0, value=0.0, key="quotation_discount")
    
    # Calculate total
    subtotal = base_price + fuel_surcharge + toll_charges + loading_charges + unloading_charges + airport_pass_charges + halting_charges + other_charges - discount
    
    if gst_applicable:
        gst_amount = subtotal * 0.18  # 18% GST
        total_amount = subtotal + gst_amount
        st.metric("GST (18%)", f"₹{gst_amount:,.2f}")
    else:
        gst_amount = 0
        total_amount = subtotal
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Subtotal", f"₹{subtotal:,.2f}")
    with col2:
        if gst_applicable:
            st.metric("GST Amount", f"₹{gst_amount:,.2f}")
    with col3:
        st.metric("Total Amount", f"₹{total_amount:,.2f}")
    
    # Notes and terms
    special_instructions = st.text_area("Special Instructions", key="quotation_instructions")
    
    # Submit button
    if st.button("Create Quotation", type="primary"):
        # Validation
        if customer_choice == "New Customer":
            if not customer_name or not customer_phone:
                st.error("Customer name and phone are required")
                return
        
        if not pickup_location or not delivery_location or base_price <= 0:
            st.error("Pickup location, delivery location, and base price are required")
            return
        
        # Create new customer if needed
        if customer_choice == "New Customer":
            customer_id = str(uuid.uuid4())
            new_customer = {
                'id': customer_id,
                'name': customer_name,
                'email': customer_email,
                'phone': customer_phone,
                'address': customer_address,
                'gst_number': customer_gst,
                'pan_number': customer_pan,
                'payment_terms': payment_terms,
                'created_date': datetime.datetime.now()
            }
            # Save customer to database
            from app import save_customer
            if save_customer(new_customer):
                # Reload all customers from database to get latest data
                from database import get_cached_data
                st.session_state.customers = get_cached_data('customers')
            else:
                st.error("Failed to save customer. Using local storage.")
        else:
            customer_data = next((c for c in st.session_state.customers if c['name'] == customer_choice), None)
            customer_id = customer_data['id']
            # Update payment terms for existing customer
            customer_data['payment_terms'] = payment_terms
        
        # Generate quotation number
        from app import generate_quotation_number
        quotation_number = generate_quotation_number()
        
        # Validate mobile number for new customer
        if customer_choice == "New Customer":
            if not validate_mobile_number(customer_phone):
                st.error("Please enter a valid mobile number")
                return
        
        # Create quotation
        quotation = {
            'id': str(uuid.uuid4()),
            'quotation_number': quotation_number,
            'customer_id': customer_id,
            'customer_name': customer_name if customer_choice == "New Customer" else customer_choice,
            'pickup_location': pickup_location,
            'delivery_location': delivery_location,
            'vehicle_type': vehicle_type,
            'distance_km': distance_km,
            'weight_capacity': weight_capacity,
            'weight_unit': weight_unit,
            'reference_number': reference_number,
            'trip_type': trip_type,
            'base_price': base_price,
            'fuel_surcharge': fuel_surcharge,
            'toll_charges': toll_charges,
            'loading_charges': loading_charges,
            'unloading_charges': unloading_charges,
            'airport_pass_charges': airport_pass_charges,
            'halting_charges': halting_charges,
            'other_charges': other_charges,
            'discount': discount,
            'subtotal': subtotal,
            'gst_applicable': gst_applicable,
            'gst_amount': gst_amount,
            'total_amount': total_amount,
            'payment_terms': payment_terms,
            'special_instructions': special_instructions,
            'status': 'Draft',
            'created_date': datetime.datetime.now(),
            'created_by': 'Admin'
        }
        
        # Save to database
        from app import save_quotation
        if save_quotation(quotation):
            # Reload all quotations from database to get latest data
            from database import get_cached_data
            st.session_state.quotations = get_cached_data('quotations', limit=100)
            
            st.success(f"Quotation {quotation_number} created successfully!")
            
            # Clear form by removing all quotation and customer form keys
            keys_to_remove = []
            for key in st.session_state.keys():
                if key.startswith('quotation_') or key.startswith('new_customer_'):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del st.session_state[key]
            
            st.rerun()
        else:
            st.error("Failed to save quotation. Using local storage.")

def view_quotations():
    """View and manage existing quotations"""
    # Always reload quotations to ensure we have latest data
    from database import get_cached_data
    st.session_state.quotations = get_cached_data('quotations', limit=100)
    
    st.subheader("View Quotations")
    
    if not st.session_state.quotations:
        st.info("No quotations found. Create your first quotation in the 'Create Quotation' tab.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Draft", "Sent", "Approved", "Rejected", "Expired"],
            key="quotation_status_filter"
        )
    
    with col2:
        customer_filter = st.selectbox(
            "Filter by Customer",
            ["All"] + [q['customer_name'] for q in st.session_state.quotations],
            key="quotation_customer_filter"
        )
    
    with col3:
        date_filter = st.date_input(
            "From Date",
            value=datetime.datetime.now() - datetime.timedelta(days=30),
            key="quotation_date_filter"
        )
    
    # Filter quotations
    filtered_quotations = st.session_state.quotations
    
    if status_filter != "All":
        filtered_quotations = [q for q in filtered_quotations if q['status'] == status_filter]
    
    if customer_filter != "All":
        filtered_quotations = [q for q in filtered_quotations if q['customer_name'] == customer_filter]
    
    # Handle date filtering with safe date conversion
    filtered_quotations = [q for q in filtered_quotations if safe_get_date(q['created_date']) >= date_filter]
    
    # Display quotations
    for quotation in filtered_quotations:
        with st.expander(f"Quotation {quotation['quotation_number']} - {quotation['customer_name']} - ₹{quotation['total_amount']:,.2f}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Customer:** {quotation['customer_name']}")
                st.write(f"**Route:** {quotation['pickup_location']} → {quotation['delivery_location']}")
                st.write(f"**Vehicle:** {quotation['vehicle_type']}")
                st.write(f"**Distance:** {quotation['distance_km']} KM")
                st.write(f"**Trip Type:** {quotation['trip_type']}")
            
            with col2:
                st.write(f"**Status:** {quotation['status']}")
                st.write(f"**Total Amount:** ₹{quotation['total_amount']:,.2f}")
                st.write(f"**Payment Terms:** {quotation['payment_terms']} days")
                st.write(f"**Created:** {safe_format_date(quotation['created_date'])}")
                st.write(f"**GST:** {'Yes' if quotation['gst_applicable'] else 'No'}")
            
            # Action buttons - adjust based on quotation status
            if quotation['status'] == 'Draft':
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    if st.button(f"Send", key=f"send_{quotation['id']}"):
                        if update_quotation_status(quotation['id'], 'Sent'):
                            st.success("Quotation sent to customer!")
                            st.rerun()
                        else:
                            st.error("Failed to mark quotation as sent. Please try again.")
                
                with col2:
                    if st.button(f"Delete", key=f"delete_{quotation['id']}"):
                        # Add deletion note before deleting
                        from .notes import add_status_note
                        add_status_note(
                            record_id=quotation['id'],
                            record_type='quotation',
                            old_status=quotation['status'],
                            new_status='Deleted',
                            changed_by='Admin',
                            notes=f"Quotation {quotation['quotation_number']} deleted",
                            additional_data={'quotation_number': quotation['quotation_number']}
                        )
                        
                        # Delete quotation from database
                        from database import execute_query, get_cached_data
                        try:
                            success = execute_query(
                                "DELETE FROM quotations WHERE id = %s", 
                                (quotation['id'],)
                            )
                            if success:
                                # Refresh quotations data from database
                                st.session_state.quotations = get_cached_data('quotations', limit=100)
                                st.success("Quotation deleted!")
                                st.rerun()
                            else:
                                st.error("Failed to delete quotation from database.")
                        except Exception as e:
                            st.error(f"Error deleting quotation: {str(e)}")
                
                with col3:
                    # PDF Generation Button
                    if st.button(f"Download PDF", key=f"pdf_{quotation['id']}"):
                        try:
                            pdf_data = generate_quotation_pdf(quotation)
                            # Use a different approach to download PDF
                            st.session_state[f'pdf_data_{quotation["id"]}'] = pdf_data
                            st.success("PDF generated! Click button below to download.")
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
                    
                    # Show download button if PDF data exists
                    if f'pdf_data_{quotation["id"]}' in st.session_state:
                        st.download_button(
                            label="📄 Download PDF",
                            data=st.session_state[f'pdf_data_{quotation["id"]}'],
                            file_name=f"Quotation_{quotation['quotation_number']}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_btn_{quotation['id']}"
                        )
                        
            elif quotation['status'] == 'Sent':
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    if st.button(f"Approve", key=f"approve_{quotation['id']}"):
                        if update_quotation_status(quotation['id'], 'Approved'):
                            st.success("Quotation approved successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to approve quotation. Please try again.")
                
                with col2:
                    if st.button(f"Reject", key=f"reject_{quotation['id']}"):
                        if update_quotation_status(quotation['id'], 'Rejected'):
                            st.warning("Quotation rejected.")
                            st.rerun()
                        else:
                            st.error("Failed to reject quotation. Please try again.")
                
                with col3:
                    # PDF Generation Button
                    if st.button(f"Download PDF", key=f"pdf_{quotation['id']}"):
                        try:
                            pdf_data = generate_quotation_pdf(quotation)
                            # Use a different approach to download PDF
                            st.session_state[f'pdf_data_{quotation["id"]}'] = pdf_data
                            st.success("PDF generated! Click button below to download.")
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
                    
                    # Show download button if PDF data exists
                    if f'pdf_data_{quotation["id"]}' in st.session_state:
                        st.download_button(
                            label="📄 Download PDF",
                            data=st.session_state[f'pdf_data_{quotation["id"]}'],
                            file_name=f"Quotation_{quotation['quotation_number']}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_btn_{quotation['id']}"
                        )
                        
            else:  # Approved, Rejected, or Expired quotations
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    # PDF Generation Button
                    if st.button(f"Download PDF", key=f"pdf_{quotation['id']}"):
                        try:
                            pdf_data = generate_quotation_pdf(quotation)
                            # Use a different approach to download PDF
                            st.session_state[f'pdf_data_{quotation["id"]}'] = pdf_data
                            st.success("PDF generated! Click button below to download.")
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
                    
                    # Show download button if PDF data exists
                    if f'pdf_data_{quotation["id"]}' in st.session_state:
                        st.download_button(
                            label="📄 Download PDF",
                            data=st.session_state[f'pdf_data_{quotation["id"]}'],
                            file_name=f"Quotation_{quotation['quotation_number']}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_btn_{quotation['id']}"
                        )
                
                with col2:
                    if quotation['status'] == 'Approved':
                        if st.button(f"Create Booking", key=f"book_{quotation['id']}"):
                            # Store quotation ID for booking creation
                            st.session_state.selected_quotation_id = quotation['id']
                            # Navigate to bookings page
                            st.session_state.current_page = "Bookings"
                            st.success("Navigating to Bookings to create booking from this quotation!")
                            st.rerun()
                
                with col3:
                    # Allow changing status back if needed
                    if quotation['status'] == 'Rejected':
                        if st.button(f"Reopen", key=f"reopen_{quotation['id']}"):
                            if update_quotation_status(quotation['id'], 'Draft'):
                                st.info("Quotation reopened as Draft.")
                                st.rerun()
                            else:
                                st.error("Failed to reopen quotation. Please try again.")
                
                with col4:
                    if quotation['status'] in ['Rejected', 'Expired']:
                        if st.button(f"Delete", key=f"delete_{quotation['id']}"):
                            # Add deletion note before deleting
                            from .notes import add_status_note
                            add_status_note(
                                record_id=quotation['id'],
                                record_type='quotation',
                                old_status=quotation['status'],
                                new_status='Deleted',
                                changed_by='Admin',
                                notes=f"Quotation {quotation['quotation_number']} deleted",
                                additional_data={'quotation_number': quotation['quotation_number']}
                            )
                            
                            # Delete quotation from database
                            from database import execute_query, get_cached_data
                            try:
                                success = execute_query(
                                    "DELETE FROM quotations WHERE id = %s", 
                                    (quotation['id'],)
                                )
                                if success:
                                    # Refresh quotations data from database
                                    st.session_state.quotations = get_cached_data('quotations', limit=100)
                                    st.success("Quotation deleted!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete quotation from database.")
                            except Exception as e:
                                st.error(f"Error deleting quotation: {str(e)}")
    st.markdown("---")
    if st.button("Export Quotations to CSV"):
        df = pd.DataFrame(filtered_quotations)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"quotations_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def manage_customers():
    """Manage customer information"""
    st.subheader("Manage Customers")
    
    if not st.session_state.customers:
        st.info("No customers found. Create customers from the quotation form or add them here.")
        return
    
    # Display customers with actions
    for customer in st.session_state.customers:
        # Create unique display name with phone for customers with same names
        customer_display = customer['name']
        phone_suffix = f" ({customer.get('phone', 'No phone')})"
        # Check if there are other customers with the same name
        same_name_customers = [c for c in st.session_state.customers if c['name'] == customer['name']]
        if len(same_name_customers) > 1:
            customer_display = customer['name'] + phone_suffix
        
        with st.expander(f"👤 {customer_display} - ID: {customer['id'][:8]}..."):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Name:** {customer['name']}")
                st.write(f"**Phone:** {customer.get('phone', 'Not provided')}")
                st.write(f"**Email:** {customer.get('email', 'Not provided')}")
            
            with col2:
                st.write(f"**GST Number:** {customer.get('gst_number', 'Not provided')}")
                st.write(f"**Payment Terms:** {customer.get('payment_terms', 30)} days")
                st.write(f"**Created:** {safe_format_date(customer.get('created_date', ''))}")
            
            with col3:
                st.markdown("**Actions**")
                
                edit_col, remove_col = st.columns(2)
                
                with edit_col:
                    if st.button(f"✏️ Edit", key=f"quot_edit_customer_{customer['id']}"):
                        st.session_state[f"quot_editing_customer_{customer['id']}"] = True
                        st.rerun()
                
                with remove_col:
                    # Check if customer can be deleted
                    can_del, blocking_records = can_delete_customer(customer)
                    
                    if can_del:
                        if st.button(f"🗑️ Remove", key=f"quot_remove_customer_{customer['id']}", type="secondary"):
                            st.session_state[f"quot_removing_{customer['id']}"] = True
                            st.rerun()
                    else:
                        st.button(f"🚫 Remove", key=f"quot_remove_customer_{customer['id']}", 
                                 disabled=True, 
                                 help=f"Cannot delete - has {', '.join(blocking_records)}")
                
                # Remove confirmation
                if st.session_state.get(f"quot_removing_{customer['id']}", False):
                    st.warning(f"⚠️ Confirm removal of customer: **{customer['name']}**")
                    confirm_col, cancel_col = st.columns(2)
                    
                    with confirm_col:
                        if st.button(f"Yes, Remove", key=f"quot_confirm_remove_btn_{customer['id']}", type="primary"):
                            # Remove customer from database
                            from database import delete_from_database
                            if delete_from_database('customers', customer['id']):
                                # Remove customer from session state
                                st.session_state.customers = [c for c in st.session_state.customers if c['id'] != customer['id']]
                                st.success(f"Customer '{customer['name']}' removed successfully!")
                            else:
                                st.error(f"Failed to remove customer '{customer['name']}' from database")
                            del st.session_state[f"quot_removing_{customer['id']}"]
                            st.rerun()
                    
                    with cancel_col:
                        if st.button(f"Cancel", key=f"quot_cancel_remove_btn_{customer['id']}"):
                            del st.session_state[f"quot_removing_{customer['id']}"]
                            st.rerun()
            
            # Edit form
            if st.session_state.get(f"quot_editing_customer_{customer['id']}", False):
                st.markdown("---")
                st.markdown("**Edit Customer Information:**")
                
                edit_col1, edit_col2 = st.columns(2)
                
                with edit_col1:
                    new_name = st.text_input("Customer Name*", value=customer['name'], key=f"quot_edit_name_{customer['id']}")
                    new_phone = st.text_input("Phone", value=customer.get('phone', ''), key=f"quot_edit_phone_{customer['id']}")
                    new_email = st.text_input("Email", value=customer.get('email', ''), key=f"quot_edit_email_{customer['id']}")
                
                with edit_col2:
                    new_gst = st.text_input("GST Number", value=customer.get('gst_number', ''), key=f"quot_edit_gst_{customer['id']}")
                    new_payment_terms = st.selectbox("Payment Terms (Days)", 
                                                   options=[15, 30, 45, 60, 90], 
                                                   index=[15, 30, 45, 60, 90].index(customer.get('payment_terms', 30)),
                                                   key=f"quot_edit_terms_{customer['id']}")
                
                save_col, cancel_col = st.columns(2)
                
                with save_col:
                    if st.button(f"💾 Save Changes", key=f"quot_save_customer_{customer['id']}", type="primary"):
                        # Update customer data
                        customer['name'] = new_name
                        customer['phone'] = new_phone
                        customer['email'] = new_email
                        customer['gst_number'] = new_gst
                        customer['payment_terms'] = new_payment_terms
                        
                        # Update in database
                        from database import update_in_database
                        update_success = update_in_database('customers', {
                            'name': new_name,
                            'phone': new_phone,
                            'email': new_email,
                            'gst_number': new_gst,
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
                            
                            for quotation in st.session_state.quotations:
                                if quotation.get('customer_id') == customer['id']:
                                    quotation['customer_name'] = new_name
                            
                            st.success(f"Customer {new_name} updated successfully!")
                        else:
                            st.error(f"Failed to update customer {new_name} in database")
                        
                        # Clear editing state
                        del st.session_state[f"quot_editing_customer_{customer['id']}"]
                        st.rerun()
                
                with cancel_col:
                    if st.button(f"❌ Cancel", key=f"quot_cancel_customer_{customer['id']}"):
                        del st.session_state[f"quot_editing_customer_{customer['id']}"]
                        st.rerun()
    
    # Export customers
    st.markdown("---")
    if st.button("📊 Export Customers to CSV", key="quot_export_customers"):
        customers_data = []
        for customer in st.session_state.customers:
            customers_data.append({
                'Name': customer['name'],
                'Phone': customer.get('phone', ''),
                'Email': customer.get('email', ''),
                'GST Number': customer.get('gst_number', ''),
                'Payment Terms': f"{customer.get('payment_terms', 30)} days",
                'Created Date': safe_format_date(customer.get('created_date', ''))
            })
        
        df = pd.DataFrame(customers_data)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"customers_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="quot_download_customers"
        )

def generate_quotation_pdf(quotation):
    """Generate PDF for quotation"""
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
    
    # Quotation details
    quote_title = Paragraph(f"<b>QUOTATION: {quotation['quotation_number']}</b>", styles['Heading2'])
    elements.append(quote_title)
    elements.append(Spacer(1, 12))
    
    # Customer and quotation info
    info_data = [
        ['Customer:', quotation['customer_name'], 'Date:', safe_format_date(quotation['created_date'])],
        ['Pickup:', quotation['pickup_location'], 'Delivery:', quotation['delivery_location']],
        ['Vehicle Type:', quotation['vehicle_type'], 'Trip Type:', quotation['trip_type']],
        ['Distance:', f"{quotation['distance_km']} KM", 'Weight:', f"{quotation['weight_capacity']} {quotation.get('weight_unit', 'tons')}"],
        ['Reference:', quotation.get('reference_number', 'N/A'), 'Payment Terms:', f"{quotation['payment_terms']} days"]
    ]
    
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
    charges_data.append(['Base Price', f"{quotation['base_price']:,.2f}"])
    
    if quotation.get('loading_charges', 0) > 0:
        charges_data.append(['Loading Charges', f"{quotation['loading_charges']:,.2f}"])
    if quotation.get('unloading_charges', 0) > 0:
        charges_data.append(['Unloading Charges', f"{quotation['unloading_charges']:,.2f}"])
    if quotation.get('airport_pass_charges', 0) > 0:
        charges_data.append(['Airport Pass Charges', f"{quotation['airport_pass_charges']:,.2f}"])
    if quotation.get('halting_charges', 0) > 0:
        charges_data.append(['Halting Charges', f"{quotation['halting_charges']:,.2f}"])
    if quotation.get('fuel_surcharge', 0) > 0:
        charges_data.append(['Fuel Surcharge', f"{quotation['fuel_surcharge']:,.2f}"])
    if quotation.get('toll_charges', 0) > 0:
        charges_data.append(['Toll Charges', f"{quotation['toll_charges']:,.2f}"])
    if quotation.get('other_charges', 0) > 0:
        charges_data.append(['Other Charges', f"{quotation['other_charges']:,.2f}"])
    if quotation.get('discount', 0) > 0:
        charges_data.append(['Discount', f"-{quotation['discount']:,.2f}"])
    
    charges_data.append(['Subtotal', f"{quotation['subtotal']:,.2f}"])
    
    if quotation.get('gst_applicable', False):
        charges_data.append(['GST (18%)', f"{quotation.get('gst_amount', 0):,.2f}"])
    
    charges_data.append(['Total Amount', f"{quotation['total_amount']:,.2f}"])
    
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
    
    # Special instructions
    if quotation.get('special_instructions'):
        instructions_title = Paragraph("<b>Special Instructions:</b>", styles['Normal'])
        elements.append(instructions_title)
        instructions = Paragraph(quotation['special_instructions'], styles['Normal'])
        elements.append(instructions)
        elements.append(Spacer(1, 20))
    
    # Terms and conditions
    terms = Paragraph("""
    <b>Terms and Conditions:</b><br/>
    1. This quotation is valid for 30 days from the date of issue.<br/>
    2. All charges are subject to change without prior notice.<br/>
    3. Payment terms are as mentioned above.<br/>
    4. Goods once dispatched will not be taken back.<br/>
    5. Risk and insurance of goods in transit is to customer account.<br/>
    """, styles['Normal'])
    elements.append(terms)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data