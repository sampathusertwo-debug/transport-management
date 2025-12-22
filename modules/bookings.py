import streamlit as st
import pandas as pd
import datetime
import uuid
import re
from typing import Dict, List
from .quotations import safe_get_date
from .utils import searchable_selectbox, static_selectbox, validate_mobile_number

def format_datetime(date_field):
    """Safely format datetime from various formats"""
    if not date_field:
        return "Not set"
    
    if isinstance(date_field, str):
        try:
            # Try parsing ISO format with timezone
            dt = datetime.datetime.fromisoformat(date_field.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            try:
                # Try parsing standard format
                dt = datetime.datetime.strptime(date_field, '%Y-%m-%d %H:%M:%S')
                return dt.strftime('%Y-%m-%d %H:%M')
            except:
                try:
                    # Try parsing date only
                    dt = datetime.datetime.strptime(date_field, '%Y-%m-%d')
                    return dt.strftime('%Y-%m-%d')
                except:
                    return str(date_field)  # Return as is if can't parse
    elif hasattr(date_field, 'strftime'):
        return date_field.strftime('%Y-%m-%d %H:%M')
    else:
        return str(date_field)

def can_edit_booking(booking):
    """Check if booking can be edited based on status"""
    return booking.get('status') not in ['Dispatched', 'Delivered', 'POD Generated']

def show():
    """Display the bookings module"""    # Load data when needed
    from database import load_data_when_needed
    load_data_when_needed('quotations')
    load_data_when_needed('bookings')
    load_data_when_needed('customers')
    load_data_when_needed('vehicles')
    load_data_when_needed('drivers')
    
    st.header("📦 Bookings Management")
    
    # Initialize active tab in session state
    if 'booking_active_tab' not in st.session_state:
        st.session_state.booking_active_tab = "Create Booking"
    
    # Create tab selection
    selected_tab = st.selectbox(
        "Select Tab",
        ["Create Booking", "Cash Booking", "View Bookings"],
        index=["Create Booking", "Cash Booking", "View Bookings"].index(st.session_state.booking_active_tab) if st.session_state.booking_active_tab in ["Create Booking", "Cash Booking", "View Bookings"] else 0,
        key="booking_tab_selector"
    )
    
    # Update session state when tab changes
    if selected_tab != st.session_state.booking_active_tab:
        st.session_state.booking_active_tab = selected_tab
    
    if selected_tab == "Create Booking":
        create_booking()
    elif selected_tab == "Cash Booking":
        create_cash_booking()
    else:
        view_bookings()

def create_booking():
    """Create a new booking"""
    st.subheader("Create New Booking")
    
    # Check for quotation to convert
    if 'selected_quotation_id' in st.session_state:
        quotation = next((q for q in st.session_state.quotations if q['id'] == st.session_state.selected_quotation_id), None)
        if quotation:
            st.info(f"Creating booking from Quotation {quotation['quotation_number']}")
            create_booking_from_quotation(quotation)
            return
    
    # Manual booking creation
    create_manual_booking()

def create_booking_from_quotation(quotation):
    """Create booking from approved quotation"""
    st.markdown("**Quotation Details**")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Quotation Number:** {quotation['quotation_number']}")
        st.write(f"**Customer:** {quotation['customer_name']}")
        st.write(f"**Route:** {quotation['pickup_location']} → {quotation['delivery_location']}")
        st.write(f"**Vehicle Type:** {quotation['vehicle_type']}")
    
    with col2:
        st.write(f"**Trip Type:** {quotation['trip_type']}")
        st.write(f"**Total Amount:** ₹{quotation['total_amount']:,.2f}")
        st.write(f"**Payment Terms:** {quotation['payment_terms']} days")
        st.write(f"**Distance:** {quotation['distance_km']} KM")
    
    st.markdown("---")
    st.markdown("**Additional Booking Details**")
    
    # Booking specific details
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pickup_date = st.date_input("Pickup Date*", value=datetime.datetime.now().date(), key="booking_pickup_date")
        pickup_time = st.time_input("Pickup Time", value=datetime.time(9, 0), key="booking_pickup_time")
        delivery_date = st.date_input("Expected Delivery Date", value=pickup_date + datetime.timedelta(days=1), key="booking_delivery_date")
    
    with col2:
        # Vehicle assignment
        available_vehicles = [v['registration_number'] for v in st.session_state.vehicles if v.get('status') != 'Maintenance']
        if available_vehicles:
            assigned_vehicle = searchable_selectbox("Assign Vehicle", ["Not Assigned"] + available_vehicles, key="booking_vehicle")
        else:
            st.warning("No vehicles available. Please add vehicles in Vehicle Master.")
            assigned_vehicle = "Not Assigned"
        
        # Driver assignment
        available_drivers = [d['name'] for d in st.session_state.drivers if d.get('status') == 'Available']
        if available_drivers:
            assigned_driver = searchable_selectbox("Assign Driver", ["Not Assigned"] + available_drivers, key="booking_driver")
        else:
            st.warning("No drivers available. Please add drivers in Vehicle Master.")
            assigned_driver = "Not Assigned"
    
    with col3:
        priority = static_selectbox("Priority", ["Normal", "High", "Urgent"], key="booking_priority")
        cargo_details = st.text_input("Cargo Details", key="booking_cargo")
        special_instructions = st.text_area("Special Instructions", key="booking_instructions")
    
    # Contact details
    st.markdown("**Contact Information**")
    col1, col2 = st.columns(2)
    
    with col1:
        pickup_contact = st.text_input("Pickup Contact Name", key="booking_pickup_contact")
        pickup_phone = st.text_input("Pickup Contact Phone", key="booking_pickup_phone", help="Enter 10-digit mobile number")
        if pickup_phone and not validate_mobile_number(pickup_phone):
            st.error("Please enter a valid 10-digit pickup contact number")
    
    with col2:
        delivery_contact = st.text_input("Delivery Contact Name", key="booking_delivery_contact")
        delivery_phone = st.text_input("Delivery Contact Phone", key="booking_delivery_phone", help="Enter 10-digit mobile number")
        if delivery_phone and not validate_mobile_number(delivery_phone):
            st.error("Please enter a valid 10-digit delivery contact number")
    
    # Submit button
    if st.button("Create Booking", type="primary"):
        if not pickup_date:
            st.error("Pickup date is required")
            return
        
        # Generate booking number
        from app import generate_booking_number
        booking_number = generate_booking_number()
        
        # Create booking
        booking = {
            'id': str(uuid.uuid4()),
            'booking_number': booking_number,
            'quotation_id': quotation['id'],
            'quotation_number': quotation['quotation_number'],
            'customer_id': quotation['customer_id'],
            'customer_name': quotation['customer_name'],
            'pickup_location': quotation['pickup_location'],
            'delivery_location': quotation['delivery_location'],
            'pickup_date': pickup_date,
            'pickup_time': pickup_time,
            'delivery_date': delivery_date,
            'vehicle_type': quotation['vehicle_type'],
            'assigned_vehicle': assigned_vehicle,
            'assigned_driver': assigned_driver,
            'distance_km': quotation['distance_km'],
            'trip_type': quotation['trip_type'],
            'priority': priority,
            'cargo_details': cargo_details,
            'special_instructions': special_instructions,
            'pickup_contact': pickup_contact,
            'pickup_phone': pickup_phone,
            'delivery_contact': delivery_contact,
            'delivery_phone': delivery_phone,
            'weight_capacity': quotation.get('weight_capacity', 0),
            'weight_unit': quotation.get('weight_unit', 'kg'),
            'base_amount': quotation.get('base_amount', quotation['total_amount']),
            'gst_applicable': quotation.get('gst_applicable', True),
            'gst_amount': quotation.get('gst_amount', 0),
            'advance_payment': 0,
            'balance_amount': quotation['total_amount'],
            'assignment_type': 'Own Vehicle',
            'total_amount': quotation['total_amount'],
            'payment_terms': quotation['payment_terms'],
            'status': 'Created',
            'created_date': datetime.datetime.now()
        }
        
        # Save to database
        from app import save_booking
        if save_booking(booking):
            # Load existing bookings from database if not already loaded
            from database import load_data_when_needed
            load_data_when_needed('bookings')
            
            # Add to session state for immediate display
            if 'bookings' not in st.session_state:
                st.session_state.bookings = []
            st.session_state.bookings.append(booking)
            
            # Track status change for new booking
            from .notes import track_status_change
            track_status_change(
                record_id=booking['id'],
                record_type='booking',
                old_status='',
                new_status='Created',
                notes=f'Booking created from quotation {quotation["quotation_number"]}',
                additional_data={
                    'booking_number': booking['booking_number'],
                    'quotation_number': quotation['quotation_number'],
                    'customer_name': booking['customer_name']
                }
            )
            
            # Update quotation status
            quotation['status'] = 'Converted to Booking'
            
            # Clear selected quotation
            if 'selected_quotation_id' in st.session_state:
                del st.session_state.selected_quotation_id
            
            st.success(f"Booking {booking_number} created successfully from quotation {quotation['quotation_number']}!")
        else:
            st.error("Failed to save booking. Please try again.")
        
        # Clear form
        for key in st.session_state.keys():
            if key.startswith('booking_'):
                del st.session_state[key]
        
        st.rerun()

def create_manual_booking():
    """Create booking manually without quotation"""
    st.markdown("**Customer Information**")
    
    # Customer selection
    existing_customers = [customer['name'] for customer in st.session_state.customers]
    
    if existing_customers:
        customer_choice = searchable_selectbox("Select Customer", ["New Customer"] + existing_customers, key="manual_customer_choice")
    else:
        customer_choice = "New Customer"
        st.info("No existing customers found. Please create a new customer.")
    
    # Customer details for new customer
    if customer_choice == "New Customer":
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("Customer Name*", key="manual_customer_name")
            customer_phone = st.text_input("Phone*", key="manual_customer_phone", help="Enter 10-digit mobile number")
            # Validate mobile number
            if customer_phone and not validate_mobile_number(customer_phone):
                st.error("Please enter a valid 10-digit mobile number")
        with col2:
            customer_email = st.text_input("Email", key="manual_customer_email")
            customer_address = st.text_area("Address", key="manual_customer_address")
    else:
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
    st.markdown("**Trip Details**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pickup_location = st.text_input("Pickup Location*", key="manual_pickup_location")
        delivery_location = st.text_input("Delivery Location*", key="manual_delivery_location")
        pickup_date = st.date_input("Pickup Date*", value=datetime.datetime.now().date(), key="manual_pickup_date")
        pickup_time = st.time_input("Pickup Time", value=datetime.time(9, 0), key="manual_pickup_time")
        reference_number = st.text_input("Reference Number", key="manual_reference_number", help="Customer or internal reference")
    
    with col2:
        delivery_date = st.date_input("Expected Delivery Date", 
                                     value=datetime.datetime.now().date() + datetime.timedelta(days=1), 
                                     key="manual_delivery_date")
        vehicle_type = static_selectbox("Vehicle Type", 
                                   ["Tata Ace - 7ft", "Bolero / Dost - 8ft", "12 ft", "14 ft", "17 ft", "20 ft", "24 ft", "32 ft"],
                                   key="manual_vehicle_type")
        trip_type = static_selectbox("Trip Type", ["Local", "Long Distance", "Contract"], key="manual_trip_type")
        distance_km = st.number_input("Distance (KM)", min_value=0.0, value=0.0, key="manual_distance")
        
        # Weight with unit selection
        weight_col1, weight_col2 = st.columns([2, 1])
        with weight_col1:
            weight_value = st.number_input("Weight", min_value=0.0, value=1.0, key="manual_weight_value")
        with weight_col2:
            weight_unit = static_selectbox("Unit", ["kg", "tons"], key="manual_weight_unit")
    
    with col3:
        cargo_details = st.text_input("Cargo Details", key="manual_cargo")
        base_amount = st.number_input("Base Amount (₹)*", min_value=0.0, value=0.0, key="manual_amount")
        payment_terms = static_selectbox("Payment Terms (Days)", [30, 45, 60, 90], key="manual_payment_terms")
        priority = static_selectbox("Priority", ["Normal", "High", "Urgent"], key="manual_priority")
    
    # Contract-specific fields
    if trip_type == "Contract":
        st.markdown("---")
        st.markdown("**Contract Details**")
        
        contract_col1, contract_col2, contract_col3 = st.columns(3)
        
        with contract_col1:
            contract_start_date = st.date_input("Contract Start Date*", value=datetime.datetime.now().date(), key="contract_start")
            contract_period = st.selectbox("Contract Period", ["Daily", "Weekly", "Monthly", "Quarterly"], key="contract_period")
        
        with contract_col2:
            contract_end_date = st.date_input("Contract End Date*", value=datetime.datetime.now().date() + datetime.timedelta(days=30), key="contract_end")
            billing_frequency = st.selectbox("Billing Frequency", ["Per Trip", "Weekly", "Monthly"], key="billing_freq")
        
        with contract_col3:
            contract_rate = st.number_input("Contract Rate (₹)", min_value=0.0, value=0.0, key="contract_rate", 
                                           help="Rate per trip/day/month as per contract period")
            contract_number = st.text_input("Contract Number", key="contract_number", help="Customer contract reference")
        
        # Contract terms
        contract_terms = st.text_area("Contract Terms & Conditions", key="contract_terms",
                                     placeholder="Special terms, conditions, or requirements for this contract")
    else:
        # Set default values for non-contract bookings
        contract_start_date = contract_end_date = None
        contract_period = billing_frequency = ""
        contract_rate = 0.0
        contract_number = contract_terms = ""
        gst_applicable = st.checkbox("GST Applicable", value=True, key="manual_gst")
        advance_payment = st.number_input("Advance Payment (₹)", min_value=0.0, value=0.0, key="manual_advance")
    
    # Charges Breakdown
    st.markdown("**Charges Breakdown**")
    charges_col1, charges_col2, charges_col3, charges_col4 = st.columns(4)
    
    with charges_col1:
        loading_charges = st.number_input("Loading Charges (₹)", min_value=0.0, value=0.0, key="manual_loading")
        unloading_charges = st.number_input("Unloading Charges (₹)", min_value=0.0, value=0.0, key="manual_unloading")
    
    with charges_col2:
        airport_pass_charges = st.number_input("Airport Pass Charges (₹)", min_value=0.0, value=0.0, key="manual_airport_pass")
        halting_charges = st.number_input("Halting Charges (₹)", min_value=0.0, value=0.0, key="manual_halting")
    
    with charges_col3:
        fuel_charges = st.number_input("Fuel Charges (₹)", min_value=0.0, value=0.0, key="manual_fuel")
        toll_charges = st.number_input("Toll Charges (₹)", min_value=0.0, value=0.0, key="manual_toll")
    
    with charges_col4:
        other_charges = st.number_input("Other Charges (₹)", min_value=0.0, value=0.0, key="manual_other")
        discount = st.number_input("Discount (₹)", min_value=0.0, value=0.0, key="manual_discount")
    
    # Calculate totals
    subtotal = base_amount + loading_charges + unloading_charges + airport_pass_charges + halting_charges + fuel_charges + toll_charges + other_charges - discount
    
    if gst_applicable:
        gst_amount = subtotal * 0.18  # 18% GST
        total_amount = subtotal + gst_amount
    else:
        gst_amount = 0
        total_amount = subtotal
    
    balance_amount = total_amount - advance_payment
    
    # Display totals
    st.markdown("**Amount Summary**")
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    with summary_col1:
        st.metric("Subtotal", f"₹{subtotal:,.2f}")
    with summary_col2:
        st.metric("GST (18%)" if gst_applicable else "GST", f"₹{gst_amount:,.2f}")
    with summary_col3:
        st.metric("Total Amount", f"₹{total_amount:,.2f}")
    with summary_col4:
        st.metric("Balance Amount", f"₹{balance_amount:,.2f}")
    
    # Vehicle and driver assignment
    st.markdown("**Assignment**")
    col1, col2 = st.columns(2)
    
    with col1:
        assignment_type = static_selectbox("Assignment Type", ["Own Vehicle", "Vendor"], key="manual_assignment_type")
        
        if assignment_type == "Own Vehicle":
            available_vehicles = [v['registration_number'] for v in st.session_state.vehicles if v.get('status') != 'Maintenance']
            if available_vehicles:
                assigned_vehicle = searchable_selectbox("Assign Vehicle", ["Not Assigned"] + available_vehicles, key="manual_vehicle")
                vendor_vehicle_number = None
                vendor_name = None
            else:
                st.warning("No vehicles available. Please add vehicles in Vehicle Master.")
                assigned_vehicle = "Not Assigned"
                vendor_vehicle_number = None
                vendor_name = None
        else:  # Vendor
            assigned_vehicle = "Vendor"
            vendor_vehicle_number = st.text_input("Vehicle Number", key="manual_vendor_vehicle", help="Enter vendor vehicle registration number")
            
            # Vendor selection/creation
            existing_vendors = [vendor['name'] for vendor in st.session_state.vendors]
            if existing_vendors:
                vendor_choice = searchable_selectbox("Select Vendor", ["New Vendor"] + existing_vendors, key="manual_vendor_choice")
                if vendor_choice == "New Vendor":
                    vendor_name = st.text_input("Vendor Name*", key="manual_new_vendor")
                else:
                    vendor_name = vendor_choice
            else:
                st.info("No existing vendors found. Creating new vendor.")
                vendor_name = st.text_input("Vendor Name*", key="manual_new_vendor")
                vendor_choice = "New Vendor"
        
    with col2:
        if assignment_type == "Own Vehicle":
            available_drivers = [d['name'] for d in st.session_state.drivers if d.get('status') == 'Available']
            if available_drivers:
                assigned_driver = searchable_selectbox("Assign Driver", ["Not Assigned"] + available_drivers, key="manual_driver")
            else:
                assigned_driver = "Not Assigned"
        else:  # Vendor
            assigned_driver = st.text_input("Vendor Driver Name", key="manual_vendor_driver", help="Enter vendor driver name")
    
    # Contact information
    st.markdown("**Contact Information**")
    col1, col2 = st.columns(2)
    
    with col1:
        pickup_contact = st.text_input("Pickup Contact Name", key="manual_pickup_contact")
        pickup_phone = st.text_input("Pickup Contact Phone", key="manual_pickup_phone", help="Enter 10-digit mobile number")
        if pickup_phone and not validate_mobile_number(pickup_phone):
            st.error("Please enter a valid 10-digit pickup contact number")
    
    with col2:
        delivery_contact = st.text_input("Delivery Contact Name", key="manual_delivery_contact")
        delivery_phone = st.text_input("Delivery Contact Phone", key="manual_delivery_phone", help="Enter 10-digit mobile number")
        if delivery_phone and not validate_mobile_number(delivery_phone):
            st.error("Please enter a valid 10-digit delivery contact number")
    
    special_instructions = st.text_area("Special Instructions", key="manual_instructions")
    
    # Submit button
    if st.button("Create Manual Booking", type="primary"):
        # Validation
        if customer_choice == "New Customer":
            if not customer_name or not customer_phone:
                st.error("Customer name and phone are required")
                return
        
        if not pickup_location or not delivery_location or not pickup_date or base_amount <= 0:
            st.error("Pickup location, delivery location, pickup date, and base amount are required")
            return
        
        # Additional validation for vendor assignment
        if assignment_type == "Vendor":
            if not vendor_vehicle_number:
                st.error("Vehicle number is required for vendor assignment")
                return
            if not vendor_name:
                st.error("Vendor name is required for vendor assignment")
                return
        
        # Validate mobile numbers
        if pickup_phone and not validate_mobile_number(pickup_phone):
            st.error("Please enter a valid pickup contact number")
            return
        if delivery_phone and not validate_mobile_number(delivery_phone):
            st.error("Please enter a valid delivery contact number")
            return
        
        # Create new customer if needed
        if customer_choice == "New Customer":
            if not validate_mobile_number(customer_phone):
                st.error("Please enter a valid customer phone number")
                return
            customer_id = str(uuid.uuid4())
            new_customer = {
                'id': customer_id,
                'name': customer_name,
                'email': customer_email,
                'phone': customer_phone,
                'address': customer_address,
                'payment_terms': payment_terms,
                'created_date': datetime.datetime.now()
            }
            st.session_state.customers.append(new_customer)
        else:
            customer_data = next((c for c in st.session_state.customers if c['name'] == customer_choice), None)
            customer_id = customer_data['id']
        
        # Create new vendor if needed
        if assignment_type == "Vendor" and vendor_choice == "New Vendor":
            new_vendor = {
                'id': str(uuid.uuid4()),
                'name': vendor_name,
                'created_date': datetime.datetime.now()
            }
            st.session_state.vendors.append(new_vendor)
        
        # Generate booking number
        from app import generate_booking_number
        booking_number = generate_booking_number()
        
        # Create booking
        booking = {
            'id': str(uuid.uuid4()),
            'booking_number': booking_number,
            'quotation_id': None,
            'quotation_number': None,
            'customer_id': customer_id,
            'customer_name': customer_name if customer_choice == "New Customer" else customer_choice,
            'pickup_location': pickup_location,
            'delivery_location': delivery_location,
            'pickup_date': pickup_date,
            'pickup_time': pickup_time,
            'delivery_date': delivery_date,
            'vehicle_type': vehicle_type,
            'assigned_vehicle': vendor_vehicle_number if assignment_type == "Vendor" else assigned_vehicle,
            'assigned_driver': vendor_name if assignment_type == "Vendor" else assigned_driver,
            'assignment_type': assignment_type,
            'distance_km': distance_km,
            'trip_type': trip_type,
            'cargo_details': cargo_details,
            'weight_capacity': weight_value,
            'weight_unit': weight_unit,
            'reference_number': reference_number,
            'special_instructions': special_instructions,
            'pickup_contact': pickup_contact,
            'pickup_phone': pickup_phone,
            'delivery_contact': delivery_contact,
            'delivery_phone': delivery_phone,
            'base_amount': base_amount,
            'loading_charges': loading_charges,
            'unloading_charges': unloading_charges,
            'airport_pass_charges': airport_pass_charges,
            'halting_charges': halting_charges,
            'fuel_charges': fuel_charges,
            'toll_charges': toll_charges,
            'other_charges': other_charges,
            'discount': discount,
            'gst_applicable': gst_applicable,
            'gst_amount': gst_amount,
            'total_amount': total_amount,
            'advance_payment': advance_payment,
            'balance_amount': balance_amount,
            'payment_terms': payment_terms,
            'status': 'Created',
            'priority': priority,
            'created_date': datetime.datetime.now(),
            'can_edit': True,
            # Contract fields
            'contract_start_date': contract_start_date,
            'contract_end_date': contract_end_date,
            'contract_period': contract_period,
            'billing_frequency': billing_frequency,
            'contract_rate': contract_rate,
            'contract_number': contract_number,
            'contract_terms': contract_terms
        }
        
        # Save to database
        from app import save_booking
        if save_booking(booking):
            # Add to session state for immediate display
            if 'bookings' not in st.session_state:
                st.session_state.bookings = []
            st.session_state.bookings.append(booking)
            
            st.success(f"Manual booking {booking_number} created successfully!")
            
            # Clear form
            for key in st.session_state.keys():
                if key.startswith('manual_'):
                    del st.session_state[key]
        else:
            st.error("Failed to save booking. Please try again.")
        
        st.rerun()

def view_bookings():
    """View and manage existing bookings"""
    st.subheader("View Bookings")
    
    if not st.session_state.bookings:
        st.info("No bookings found. Create your first booking in the 'Create Booking' tab.")
        return
    
    # Filters - consolidated to single line
    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)
    
    with filter_col1:
        status_filter = static_selectbox(
            "Status",
            ["All", "Created", "Confirmed", "Dispatched", "In Transit", "Delivered", "POD Captured", "Cancelled"],
            key="booking_status_filter"
        )
    
    with filter_col2:
        customer_filter = searchable_selectbox(
            "Customer",
            ["All"] + list(set([b['customer_name'] for b in st.session_state.bookings])),
            key="booking_customer_filter"
        )
    
    with filter_col3:
        trip_type_filter = static_selectbox(
            "Trip Type",
            ["All", "Local", "Long Distance", "Contract"],
            key="booking_trip_filter"
        )
    
    with filter_col4:
        date_filter = st.date_input(
            "From Date",
            value=datetime.datetime.now() - datetime.timedelta(days=30),
            key="booking_date_filter"
        )
    
    with filter_col5:
        # Show count
        st.metric("Total", len(st.session_state.bookings))
    
    # Filter bookings
    filtered_bookings = st.session_state.bookings
    
    if status_filter != "All":
        filtered_bookings = [b for b in filtered_bookings if b['status'] == status_filter]
    
    if customer_filter != "All":
        filtered_bookings = [b for b in filtered_bookings if b['customer_name'] == customer_filter]
    
    if trip_type_filter != "All":
        filtered_bookings = [b for b in filtered_bookings if b['trip_type'] == trip_type_filter]
    
    filtered_bookings = [b for b in filtered_bookings if safe_get_date(b['created_date']) >= date_filter]
    
    # Display bookings
    for booking in filtered_bookings:
        status_color = {
            'Created': '🟡',
            'Confirmed': '🔵',
            'Dispatched': '🟠',
            'In Transit': '🟣',
            'Delivered': '🟢',
            'POD Captured': '✅',
            'Cancelled': '❌'
        }.get(booking['status'], '⚪')
        
        with st.expander(f"{status_color} {booking['booking_number']} - {booking['customer_name']} - ₹{booking['total_amount']:,.2f}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Customer:** {booking['customer_name']}")
                st.write(f"**Route:** {booking['pickup_location']} → {booking['delivery_location']}")
                st.write(f"**Pickup Date:** {booking['pickup_date']}")
                st.write(f"**Vehicle Type:** {booking['vehicle_type']}")
                st.write(f"**Assigned Vehicle:** {booking.get('assigned_vehicle', 'Not Assigned')}")
                st.write(f"**Trip Type:** {booking['trip_type']}")
                if booking.get('quotation_number'):
                    st.write(f"**From Quotation:** {booking['quotation_number']}")
            
            with col2:
                st.write(f"**Status:** {booking['status']}")
                st.write(f"**Priority:** {booking.get('priority', 'Normal')}")
                st.write(f"**Assigned Driver:** {booking.get('assigned_driver', 'Not Assigned')}")
                st.write(f"**Distance:** {booking['distance_km']} KM")
                st.write(f"**Total Amount:** ₹{booking['total_amount']:,.2f}")
                st.write(f"**Created:** {format_datetime(booking.get('created_date'))}")
                if booking.get('cargo_details'):
                    st.write(f"**Cargo:** {booking['cargo_details']}")
            
            # Action buttons
            st.markdown("**Actions:**")
            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            
            with action_col1:
                if can_edit_booking(booking) and st.button(f"Edit", key=f"edit_{booking['id']}"):
                    st.session_state[f"edit_booking_{booking['id']}"] = True
                    st.rerun()
            
            with action_col2:
                if booking['status'] != 'Confirmed' and booking['status'] != 'Dispatched' and st.button(f"Confirm", key=f"confirm_{booking['id']}"):
                    # Keep on View Bookings tab
                    st.session_state.booking_active_tab = "View Bookings"
                    # Find and update the actual booking in session state
                    for i, b in enumerate(st.session_state.bookings):
                        if b['id'] == booking['id']:
                            st.session_state.bookings[i]['status'] = 'Confirmed'
                            booking['status'] = 'Confirmed'  # Update local reference too
                            # Update in database (don't insert new record)
                            from database import update_in_database
                            update_in_database('bookings', {'status': 'Confirmed'}, booking['id'])
                            break
                    st.success(f"Booking {booking['booking_number']} confirmed!")
                    st.rerun()
            
            with action_col3:
                if booking['status'] in ['Confirmed', 'Created'] and st.button(f"Dispatch", key=f"dispatch_{booking['id']}"):
                    # Keep on View Bookings tab
                    st.session_state.booking_active_tab = "View Bookings"
                    # Find and update the actual booking in session state
                    old_status = booking['status']
                    for i, b in enumerate(st.session_state.bookings):
                        if b['id'] == booking['id']:
                            st.session_state.bookings[i]['status'] = 'Dispatched'
                            st.session_state.bookings[i]['can_edit'] = False  # Lock editing after dispatch
                            booking['status'] = 'Dispatched'  # Update local reference too
                            booking['can_edit'] = False
                            # Track status change
                            from .notes import track_status_change
                            track_status_change(
                                record_id=booking['id'],
                                record_type='booking',
                                old_status=old_status,
                                new_status='Dispatched',
                                notes='Booking dispatched to driver',
                                additional_data={'booking_number': booking['booking_number']}
                            )
                            # Update in database (don't insert new record)
                            from database import update_in_database
                            update_in_database('bookings', {'status': 'Dispatched', 'can_edit': False}, booking['id'])
                            break
                    st.success(f"Booking {booking['booking_number']} dispatched!")
                    st.rerun()
            
            with action_col4:
                if booking['status'] == 'Dispatched' and st.button(f"Generate POD", key=f"pod_{booking['id']}"):
                    # Keep on View Bookings tab
                    st.session_state.booking_active_tab = "View Bookings"
                    # Find and update the actual booking in session state
                    for i, b in enumerate(st.session_state.bookings):
                        if b['id'] == booking['id']:
                            st.session_state.bookings[i]['status'] = 'POD Generated'
                            st.session_state.bookings[i]['pod_date'] = datetime.datetime.now()
                            booking['status'] = 'POD Generated'  # Update local reference too
                            booking['pod_date'] = datetime.datetime.now()
                            # Track status change
                            from .notes import track_status_change
                            track_status_change(
                                record_id=booking['id'],
                                record_type='booking',
                                old_status='Dispatched',
                                new_status='POD Generated',
                                notes='Proof of delivery generated',
                                additional_data={
                                    'booking_number': booking['booking_number'],
                                    'pod_date': datetime.datetime.now().isoformat()
                                }
                            )
                            # Update in database (don't insert new record)
                            from database import update_in_database
                            update_in_database('bookings', {
                                'status': 'POD Generated',
                                'pod_date': datetime.datetime.now().isoformat()
                            }, booking['id'])
                            break
                    st.success(f"POD generated for booking {booking['booking_number']}!")
                    st.rerun()
            
            # Edit form
            if st.session_state.get(f"edit_booking_{booking['id']}", False):
                st.markdown("---")
                st.markdown("**Edit Booking:**")
                
                if not can_edit_booking(booking):
                    st.error("This booking cannot be edited as it has been dispatched or POD has been generated.")
                    if st.button(f"Close Edit", key=f"close_edit_{booking['id']}"):
                        del st.session_state[f"edit_booking_{booking['id']}"]
                        st.rerun()
                else:
                    # Edit form (simplified for now - can be expanded)
                    edit_col1, edit_col2 = st.columns(2)
                    
                    with edit_col1:
                        new_pickup_date = st.date_input("Pickup Date", value=booking['pickup_date'], key=f"edit_pickup_{booking['id']}")
                        new_delivery_date = st.date_input("Delivery Date", value=booking['delivery_date'], key=f"edit_delivery_{booking['id']}")
                        new_cargo = st.text_input("Cargo Details", value=booking.get('cargo_details', ''), key=f"edit_cargo_{booking['id']}")
                    
                    with edit_col2:
                        new_instructions = st.text_area("Special Instructions", value=booking.get('special_instructions', ''), key=f"edit_instructions_{booking['id']}")
                        new_advance = st.number_input("Advance Payment", value=float(booking.get('advance_payment', 0)), key=f"edit_advance_{booking['id']}")
                    
                    edit_action_col1, edit_action_col2 = st.columns(2)
                    
                    with edit_action_col1:
                        if st.button(f"Save Changes", key=f"save_{booking['id']}", type="primary"):
                            booking['pickup_date'] = new_pickup_date
                            booking['delivery_date'] = new_delivery_date
                            booking['cargo_details'] = new_cargo
                            booking['special_instructions'] = new_instructions
                            booking['advance_payment'] = new_advance
                            booking['balance_amount'] = booking['total_amount'] - new_advance
                            booking['last_modified'] = datetime.datetime.now()
                            
                            del st.session_state[f"edit_booking_{booking['id']}"]
                            st.success(f"Booking {booking['booking_number']} updated successfully!")
                            st.rerun()
                    
                    with edit_action_col2:
                        if st.button(f"Cancel", key=f"cancel_edit_{booking['id']}"):
                            del st.session_state[f"edit_booking_{booking['id']}"]
                            st.rerun()
            
            # Invoice creation button
            if booking['status'] == 'POD Captured' and not any(inv.get('booking_id') == booking['id'] for inv in st.session_state.invoices):
                if st.button(f"Create Invoice", key=f"invoice_{booking['id']}", type="primary"):
                    st.session_state.selected_booking_id = booking['id']
                    st.success("Navigate to Invoicing to create invoice for this booking!")
            
            # Cancel booking
            if booking['status'] not in ['Delivered', 'POD Captured', 'Cancelled']:
                if st.button(f"Cancel Booking", key=f"cancel_{booking['id']}"):
                    # Keep on View Bookings tab
                    st.session_state.booking_active_tab = "View Bookings"
                    # Find and update the actual booking in session state
                    old_status = booking['status']
                    for i, b in enumerate(st.session_state.bookings):
                        if b['id'] == booking['id']:
                            st.session_state.bookings[i]['status'] = 'Cancelled'
                            st.session_state.bookings[i]['cancelled_date'] = datetime.datetime.now()
                            booking['status'] = 'Cancelled'  # Update local reference too
                            booking['cancelled_date'] = datetime.datetime.now()
                            # Track status change
                            from .notes import track_status_change
                            track_status_change(
                                record_id=booking['id'],
                                record_type='booking',
                                old_status=old_status,
                                new_status='Cancelled',
                                notes='Booking cancelled by user',
                                additional_data={
                                    'booking_number': booking['booking_number'],
                                    'cancelled_date': datetime.datetime.now().isoformat()
                                }
                            )
                            # Update in database (don't insert new record)
                            from database import update_in_database
                            update_in_database('bookings', {
                                'status': 'Cancelled',
                                'cancelled_date': datetime.datetime.now().isoformat()
                            }, booking['id'])
                            break
                    st.error("Booking cancelled!")
                    st.rerun()
    
    # Export options
    st.markdown("---")
    if st.button("Export Bookings to CSV"):
        df = pd.DataFrame(filtered_bookings)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"bookings_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def create_cash_booking():
    """Create a simple cash booking for immediate trips"""
    st.subheader("💰 Cash Booking - Quick Entry")
    st.info("For immediate cash-based bookings with simplified entry")
    
    # Basic details in a compact form
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Trip Details**")
        pickup_location = st.text_input("From*", key="cash_pickup")
        delivery_location = st.text_input("To*", key="cash_delivery") 
        vehicle_type = static_selectbox("Vehicle", 
                                       ["Tata Ace - 7ft", "Bolero / Dost - 8ft", "12 ft", "14 ft", "17 ft", "20 ft", "24 ft", "32 ft"],
                                       key="cash_vehicle")
        distance_km = st.number_input("Distance (KM)", min_value=0.0, value=0.0, key="cash_distance")
    
    with col2:
        st.markdown("**Customer & Payment**")
        customer_name = st.text_input("Customer Name*", key="cash_customer_name")
        customer_phone = st.text_input("Phone*", key="cash_customer_phone")
        cash_amount = st.number_input("Cash Amount (₹)*", min_value=0.0, value=0.0, key="cash_amount")
        advance_received = st.number_input("Advance Received (₹)", min_value=0.0, value=0.0, key="cash_advance")
    
    # Optional details
    with st.expander("📋 Additional Details (Optional)"):
        detail_col1, detail_col2 = st.columns(2)
        
        with detail_col1:
            pickup_time = st.time_input("Pickup Time", value=datetime.time(9, 0), key="cash_time")
            cargo_details = st.text_input("Cargo Details", key="cash_cargo")
            reference_number = st.text_input("Reference", key="cash_reference")
        
        with detail_col2:
            pickup_contact = st.text_input("Pickup Contact", key="cash_pickup_contact")
            delivery_contact = st.text_input("Delivery Contact", key="cash_delivery_contact")
            special_notes = st.text_area("Notes", key="cash_notes", help="Special instructions or remarks")
    
    # Vehicle assignment
    st.markdown("**Vehicle Assignment**")
    assignment_col1, assignment_col2 = st.columns(2)
    
    with assignment_col1:
        available_vehicles = [v['registration_number'] for v in st.session_state.vehicles if v.get('status') != 'Maintenance']
        if available_vehicles:
            assigned_vehicle = searchable_selectbox("Vehicle", ["Not Assigned"] + available_vehicles, key="cash_assigned_vehicle")
        else:
            assigned_vehicle = "Not Assigned"
            st.warning("No vehicles available")
    
    with assignment_col2:
        available_drivers = [d['name'] for d in st.session_state.drivers if d.get('status') == 'Available']
        if available_drivers:
            assigned_driver = searchable_selectbox("Driver", ["Not Assigned"] + available_drivers, key="cash_assigned_driver")
        else:
            assigned_driver = "Not Assigned"
            st.warning("No drivers available")
    
    # Summary
    balance_amount = cash_amount - advance_received
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Amount", f"₹{cash_amount:,.2f}")
    with col2:
        st.metric("Advance Received", f"₹{advance_received:,.2f}")
    with col3:
        st.metric("Balance Due", f"₹{balance_amount:,.2f}")
    
    # Create booking button
    if st.button("💾 Create Cash Booking", type="primary"):
        # Validation
        if not all([pickup_location, delivery_location, customer_name, customer_phone, cash_amount > 0]):
            st.error("Please fill all required fields (*)")
            return
        
        if customer_phone and not validate_mobile_number(customer_phone):
            st.error("Please enter a valid 10-digit mobile number")
            return
        
        # Create customer (cash customers are typically one-time)
        customer_id = str(uuid.uuid4())
        cash_customer = {
            'id': customer_id,
            'name': customer_name,
            'phone': customer_phone,
            'email': '',
            'address': '',
            'gst_number': '',
            'pan_number': '',
            'payment_terms': 0,  # Immediate payment
            'customer_type': 'Cash',
            'created_date': datetime.datetime.now()
        }
        
        # Add customer to session state
        if 'customers' not in st.session_state:
            st.session_state.customers = []
        st.session_state.customers.append(cash_customer)
        
        # Generate booking number
        from app import generate_booking_number
        booking_number = generate_booking_number()
        
        # Create cash booking
        cash_booking = {
            'id': str(uuid.uuid4()),
            'booking_number': booking_number,
            'quotation_id': None,
            'quotation_number': None,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'pickup_location': pickup_location,
            'delivery_location': delivery_location,
            'pickup_date': datetime.datetime.now().date(),
            'pickup_time': pickup_time,
            'delivery_date': datetime.datetime.now().date(),
            'vehicle_type': vehicle_type,
            'assigned_vehicle': assigned_vehicle,
            'assigned_driver': assigned_driver,
            'distance_km': distance_km,
            'trip_type': 'Cash',
            'cargo_details': cargo_details,
            'weight_capacity': 0,
            'weight_unit': 'kg',
            'reference_number': reference_number,
            'special_instructions': special_notes,
            'pickup_contact': pickup_contact,
            'pickup_phone': customer_phone,
            'delivery_contact': delivery_contact,
            'delivery_phone': '',
            'base_amount': cash_amount,
            'loading_charges': 0,
            'unloading_charges': 0,
            'airport_pass_charges': 0,
            'halting_charges': 0,
            'fuel_charges': 0,
            'toll_charges': 0,
            'other_charges': 0,
            'discount': 0,
            'gst_applicable': False,  # Cash bookings typically no GST
            'gst_amount': 0,
            'total_amount': cash_amount,
            'advance_payment': advance_received,
            'balance_amount': balance_amount,
            'payment_terms': 0,
            'status': 'Confirmed' if advance_received > 0 else 'Created',
            'priority': 'Normal',
            'booking_type': 'Cash',
            'created_date': datetime.datetime.now(),
            'can_edit': True
        }
        
        # Save booking
        from app import save_booking
        if save_booking(cash_booking):
            # Add to session state for immediate display
            if 'bookings' not in st.session_state:
                st.session_state.bookings = []
            st.session_state.bookings.append(cash_booking)
            
            st.success(f"✅ Cash Booking {booking_number} created successfully!")
            
            # Show booking summary
            st.info(f"📋 **Booking Summary:**\n"
                   f"- Booking Number: {booking_number}\n"
                   f"- Customer: {customer_name} ({customer_phone})\n"
                   f"- Route: {pickup_location} → {delivery_location}\n"
                   f"- Vehicle: {vehicle_type}\n"
                   f"- Amount: ₹{cash_amount:,.2f}\n"
                   f"- Status: {'Confirmed' if advance_received > 0 else 'Created'}")
            
            # Clear form fields
            for key in st.session_state.keys():
                if key.startswith('cash_'):
                    del st.session_state[key]
            
            st.rerun()
        else:
            st.error("Failed to save booking. Please try again.")