import streamlit as st
import pandas as pd
import datetime
import uuid
from typing import Dict, List

def show():
    """Display the bookings module"""
    st.header("📦 Bookings Management")
    
    tab1, tab2 = st.tabs(["Create Booking", "View Bookings"])
    
    with tab1:
        create_booking()
    
    with tab2:
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
            assigned_vehicle = st.selectbox("Assign Vehicle", ["Not Assigned"] + available_vehicles, key="booking_vehicle")
        else:
            st.warning("No vehicles available. Please add vehicles in Vehicle Master.")
            assigned_vehicle = "Not Assigned"
        
        # Driver assignment
        available_drivers = [d['name'] for d in st.session_state.drivers if d.get('status') == 'Available']
        if available_drivers:
            assigned_driver = st.selectbox("Assign Driver", ["Not Assigned"] + available_drivers, key="booking_driver")
        else:
            st.warning("No drivers available. Please add drivers in Vehicle Master.")
            assigned_driver = "Not Assigned"
    
    with col3:
        priority = st.selectbox("Priority", ["Normal", "High", "Urgent"], key="booking_priority")
        cargo_details = st.text_input("Cargo Details", key="booking_cargo")
        special_instructions = st.text_area("Special Instructions", key="booking_instructions")
    
    # Contact details
    st.markdown("**Contact Information**")
    col1, col2 = st.columns(2)
    
    with col1:
        pickup_contact = st.text_input("Pickup Contact Name", key="booking_pickup_contact")
        pickup_phone = st.text_input("Pickup Contact Phone", key="booking_pickup_phone")
    
    with col2:
        delivery_contact = st.text_input("Delivery Contact Name", key="booking_delivery_contact")
        delivery_phone = st.text_input("Delivery Contact Phone", key="booking_delivery_phone")
    
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
            'total_amount': quotation['total_amount'],
            'payment_terms': quotation['payment_terms'],
            'status': 'Created',
            'created_date': datetime.datetime.now(),
            'created_by': 'Admin'
        }
        
        st.session_state.bookings.append(booking)
        
        # Update quotation status
        quotation['status'] = 'Converted to Booking'
        
        # Clear selected quotation
        if 'selected_quotation_id' in st.session_state:
            del st.session_state.selected_quotation_id
        
        st.success(f"Booking {booking_number} created successfully from quotation {quotation['quotation_number']}!")
        
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
        customer_choice = st.selectbox("Select Customer", ["New Customer"] + existing_customers, key="manual_customer_choice")
    else:
        customer_choice = "New Customer"
        st.info("No existing customers found. Please create a new customer.")
    
    # Customer details for new customer
    if customer_choice == "New Customer":
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("Customer Name*", key="manual_customer_name")
            customer_phone = st.text_input("Phone*", key="manual_customer_phone")
        with col2:
            customer_email = st.text_input("Email", key="manual_customer_email")
            customer_address = st.text_area("Address", key="manual_customer_address")
    else:
        customer_data = next((c for c in st.session_state.customers if c['name'] == customer_choice), None)
        if customer_data:
            st.info(f"Customer: {customer_data['name']} | Phone: {customer_data['phone']}")
    
    st.markdown("---")
    st.markdown("**Trip Details**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pickup_location = st.text_input("Pickup Location*", key="manual_pickup_location")
        delivery_location = st.text_input("Delivery Location*", key="manual_delivery_location")
        pickup_date = st.date_input("Pickup Date*", value=datetime.datetime.now().date(), key="manual_pickup_date")
        pickup_time = st.time_input("Pickup Time", value=datetime.time(9, 0), key="manual_pickup_time")
    
    with col2:
        delivery_date = st.date_input("Expected Delivery Date", 
                                     value=datetime.datetime.now().date() + datetime.timedelta(days=1), 
                                     key="manual_delivery_date")
        vehicle_type = st.selectbox("Vehicle Type", 
                                   ["Mini Truck", "Small Truck", "Medium Truck", "Large Truck", "Container", "Trailer"],
                                   key="manual_vehicle_type")
        trip_type = st.selectbox("Trip Type", ["Local", "Long Distance", "Contract"], key="manual_trip_type")
        distance_km = st.number_input("Distance (KM)", min_value=0.0, value=0.0, key="manual_distance")
    
    with col3:
        priority = st.selectbox("Priority", ["Normal", "High", "Urgent"], key="manual_priority")
        cargo_details = st.text_input("Cargo Details", key="manual_cargo")
        base_amount = st.number_input("Base Amount (₹)*", min_value=0.0, value=0.0, key="manual_amount")
        payment_terms = st.selectbox("Payment Terms (Days)", [30, 45, 60, 90], key="manual_payment_terms")
    
    # Vehicle and driver assignment
    st.markdown("**Assignment**")
    col1, col2 = st.columns(2)
    
    with col1:
        available_vehicles = [v['registration_number'] for v in st.session_state.vehicles if v.get('status') != 'Maintenance']
        if available_vehicles:
            assigned_vehicle = st.selectbox("Assign Vehicle", ["Not Assigned"] + available_vehicles, key="manual_vehicle")
        else:
            assigned_vehicle = "Not Assigned"
        
    with col2:
        available_drivers = [d['name'] for d in st.session_state.drivers if d.get('status') == 'Available']
        if available_drivers:
            assigned_driver = st.selectbox("Assign Driver", ["Not Assigned"] + available_drivers, key="manual_driver")
        else:
            assigned_driver = "Not Assigned"
    
    # Contact information
    st.markdown("**Contact Information**")
    col1, col2 = st.columns(2)
    
    with col1:
        pickup_contact = st.text_input("Pickup Contact Name", key="manual_pickup_contact")
        pickup_phone = st.text_input("Pickup Contact Phone", key="manual_pickup_phone")
    
    with col2:
        delivery_contact = st.text_input("Delivery Contact Name", key="manual_delivery_contact")
        delivery_phone = st.text_input("Delivery Contact Phone", key="manual_delivery_phone")
    
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
        
        # Create new customer if needed
        if customer_choice == "New Customer":
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
            'assigned_vehicle': assigned_vehicle,
            'assigned_driver': assigned_driver,
            'distance_km': distance_km,
            'trip_type': trip_type,
            'priority': priority,
            'cargo_details': cargo_details,
            'special_instructions': special_instructions,
            'pickup_contact': pickup_contact,
            'pickup_phone': pickup_phone,
            'delivery_contact': delivery_contact,
            'delivery_phone': delivery_phone,
            'total_amount': base_amount,
            'payment_terms': payment_terms,
            'status': 'Created',
            'created_date': datetime.datetime.now(),
            'created_by': 'Admin'
        }
        
        st.session_state.bookings.append(booking)
        st.success(f"Manual booking {booking_number} created successfully!")
        
        # Clear form
        for key in st.session_state.keys():
            if key.startswith('manual_'):
                del st.session_state[key]
        
        st.rerun()

def view_bookings():
    """View and manage existing bookings"""
    st.subheader("View Bookings")
    
    if not st.session_state.bookings:
        st.info("No bookings found. Create your first booking in the 'Create Booking' tab.")
        return
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Created", "Confirmed", "Dispatched", "In Transit", "Delivered", "POD Captured", "Cancelled"],
            key="booking_status_filter"
        )
    
    with col2:
        customer_filter = st.selectbox(
            "Filter by Customer",
            ["All"] + list(set([b['customer_name'] for b in st.session_state.bookings])),
            key="booking_customer_filter"
        )
    
    with col3:
        trip_type_filter = st.selectbox(
            "Filter by Trip Type",
            ["All", "Local", "Long Distance", "Contract"],
            key="booking_trip_filter"
        )
    
    with col4:
        date_filter = st.date_input(
            "From Date",
            value=datetime.datetime.now() - datetime.timedelta(days=30),
            key="booking_date_filter"
        )
    
    # Filter bookings
    filtered_bookings = st.session_state.bookings
    
    if status_filter != "All":
        filtered_bookings = [b for b in filtered_bookings if b['status'] == status_filter]
    
    if customer_filter != "All":
        filtered_bookings = [b for b in filtered_bookings if b['customer_name'] == customer_filter]
    
    if trip_type_filter != "All":
        filtered_bookings = [b for b in filtered_bookings if b['trip_type'] == trip_type_filter]
    
    filtered_bookings = [b for b in filtered_bookings if b['created_date'].date() >= date_filter]
    
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
                st.write(f"**Created:** {booking['created_date'].strftime('%Y-%m-%d %H:%M')}")
                if booking.get('cargo_details'):
                    st.write(f"**Cargo:** {booking['cargo_details']}")
            
            # Status update buttons
            st.markdown("**Update Status:**")
            status_options = ["Created", "Confirmed", "Dispatched", "In Transit", "Delivered", "POD Captured", "Cancelled"]
            current_index = status_options.index(booking['status']) if booking['status'] in status_options else 0
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if booking['status'] != 'Confirmed' and st.button(f"Confirm", key=f"confirm_{booking['id']}"):
                    booking['status'] = 'Confirmed'
                    st.success("Booking confirmed!")
                    st.rerun()
            
            with col2:
                if booking['status'] in ['Confirmed'] and st.button(f"Dispatch", key=f"dispatch_{booking['id']}"):
                    booking['status'] = 'Dispatched'
                    booking['dispatched_date'] = datetime.datetime.now()
                    st.success("Booking dispatched!")
                    st.rerun()
            
            with col3:
                if booking['status'] in ['Dispatched', 'In Transit'] and st.button(f"Mark Delivered", key=f"deliver_{booking['id']}"):
                    booking['status'] = 'Delivered'
                    booking['delivered_date'] = datetime.datetime.now()
                    st.success("Booking marked as delivered!")
                    st.rerun()
            
            with col4:
                if booking['status'] == 'Delivered' and st.button(f"Capture POD", key=f"pod_{booking['id']}"):
                    booking['status'] = 'POD Captured'
                    booking['pod_date'] = datetime.datetime.now()
                    st.success("POD captured! Ready for invoicing.")
                    st.rerun()
            
            # Invoice creation button
            if booking['status'] == 'POD Captured' and not any(inv.get('booking_id') == booking['id'] for inv in st.session_state.invoices):
                if st.button(f"Create Invoice", key=f"invoice_{booking['id']}", type="primary"):
                    st.session_state.selected_booking_id = booking['id']
                    st.success("Navigate to Invoicing to create invoice for this booking!")
            
            # Cancel booking
            if booking['status'] not in ['Delivered', 'POD Captured', 'Cancelled']:
                if st.button(f"Cancel Booking", key=f"cancel_{booking['id']}"):
                    booking['status'] = 'Cancelled'
                    booking['cancelled_date'] = datetime.datetime.now()
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