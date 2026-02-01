import streamlit as st
import pandas as pd
import datetime
import uuid
import re
from typing import Dict, List
from .quotations import safe_get_date
from .utils import searchable_selectbox, static_selectbox, validate_mobile_number
from .customer_pricing import get_pricing_for_customer, search_customer_by_name

def show_success_page(title, message, created_item_id=None, created_item_number=None, module_name="bookings"):
    """Show success page with navigation options"""
    st.markdown(f"### {title}")
    st.success(message)
    
    if created_item_number:
        st.markdown(f"**{module_name.title().rstrip('s')} Number:** `{created_item_number}`")
    
    if created_item_id:
        st.markdown(f"**ID:** `{created_item_id}`")
    
    st.markdown("---")
    st.markdown("#### What would you like to do next?")
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button(f"Create Another {module_name.title().rstrip('s')}", type="primary", width="stretch"):
            # Clear any success flags and return to create mode
            if 'show_success_page' in st.session_state:
                del st.session_state['show_success_page']
            if 'success_data' in st.session_state:
                del st.session_state['success_data']
            st.rerun()
    
    with col2:
        if st.button(f"👀 View All {module_name.title()}", width="stretch"):
            # Navigate to view/list mode
            if 'show_success_page' in st.session_state:
                del st.session_state['show_success_page']
            if 'success_data' in st.session_state:
                del st.session_state['success_data']
            # Switch to appropriate tab if using tabs
            st.session_state.active_tab = "view" if module_name == "bookings" else f"view_{module_name}"
            st.rerun()
    
    with col3:
        if st.button("Go to Dashboard", width="stretch"):
            # Clear success state and go to dashboard
            if 'show_success_page' in st.session_state:
                del st.session_state['show_success_page']
            if 'success_data' in st.session_state:
                del st.session_state['success_data']
            # This would need integration with main app navigation
            st.success("Redirecting to Dashboard...")
            st.rerun()

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

def show():
    """Display the bookings module"""
    
    # Check if we need to show success page
    if st.session_state.get('show_success_page', False) and st.session_state.get('success_data'):
        success_data = st.session_state['success_data']
        show_success_page(
            title=success_data.get('title', 'Success!'),
            message=success_data.get('message', 'Operation completed successfully!'),
            created_item_id=success_data.get('created_item_id'),
            created_item_number=success_data.get('created_item_number'),
            module_name=success_data.get('module_name', 'bookings')
        )
        return
    
    # Load data when needed
    from database import load_data_when_needed
    load_data_when_needed('bookings')
    load_data_when_needed('customers')
    load_data_when_needed('vehicles')
    load_data_when_needed('drivers')
    
    st.header("Bookings Management")
    
    # Initialize tab selection in session state
    if 'booking_tab_selection' not in st.session_state:
        st.session_state.booking_tab_selection = 0
    
    # Handle navigation from success page
    if st.session_state.get('active_tab') == "view":
        st.session_state.booking_tab_selection = 1
        del st.session_state['active_tab']
    
    # Create custom tab-like buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Create Booking", 
                    key="btn_nav_create_booking",
                    type="primary" if st.session_state.booking_tab_selection == 0 else "secondary",
                    use_container_width=True):
            st.session_state.booking_tab_selection = 0
            st.rerun()
    
    with col2:
        if st.button("View Bookings", 
                    key="btn_nav_view_bookings",
                    type="primary" if st.session_state.booking_tab_selection == 1 else "secondary",
                    use_container_width=True):
            st.session_state.booking_tab_selection = 1
            st.rerun()
    
    st.divider()
    
    # Show selected content
    if st.session_state.booking_tab_selection == 0:
        create_booking()
    else:
        view_bookings()

def create_booking():
    """Create a new simplified booking"""
    st.subheader("Create New Booking")
    
    # Generate booking number (show it to user)
    from app import generate_booking_number
    booking_number = generate_booking_number()
    
    st.info(f"**Booking Number:** {booking_number}")
    
    # Date field at the top
    booking_date = st.date_input("Date*", value=datetime.datetime.now().date(), key="booking_date")
    
    # BOOKING DETAILS section
    st.markdown("**BOOKING DETAILS**")
    col1, col2 = st.columns(2)
    
    with col1:
        # Load customers from database
        from database import load_data_when_needed
        load_data_when_needed('customers')
        
        # Get customer list
        if hasattr(st.session_state, 'customers') and st.session_state.customers:
            customer_options = ["➕ Add New Customer"] + [c['name'] for c in st.session_state.customers]
        else:
            customer_options = ["➕ Add New Customer"]
        
        # Use selectbox with all customers (has built-in search)
        customer_selection = st.selectbox(
            "Customer*",
            customer_options,
            key="booking_customer",
            help="Select existing customer or choose 'Add New Customer' to create one"
        )
        
        # If user selects "Add New Customer", show text input
        if customer_selection == "➕ Add New Customer":
            customer = st.text_input(
                "Enter New Customer Name",
                key="booking_new_customer_name",
                placeholder="e.g., ABC Logistics"
            )
            if customer:
                st.info(f"New customer '{customer}' will be added when you create the booking.")
        else:
            customer = customer_selection
        
        # Load vehicle types from database
        from database import get_vehicle_types
        vehicle_type_options = get_vehicle_types()
        vehicle_type = st.selectbox("Vehicle Type*", vehicle_type_options, key="booking_vehicle_type")
    
    with col2:
        pickup_location = st.text_input("Pick up*", placeholder="e.g., Mepz", key="booking_pickup")
        destination = st.text_input("Destination*", placeholder="e.g., Airport", key="booking_destination")
    
    # VEHICLE & DRIVER DETAILS section
    st.markdown("**VEHICLE & DRIVER DETAILS**")
    col1, col2 = st.columns(2)
    
    # Load vehicle and driver data
    from database import load_data_when_needed
    load_data_when_needed('vehicles')
    load_data_when_needed('drivers')
    
    with col1:
        # Vehicle selection
        if hasattr(st.session_state, 'vehicles') and st.session_state.vehicles:
            vehicle_options = ["➕ Add New Vehicle/Vendor"] + [v['registration_number'] for v in st.session_state.vehicles if v.get('status') == 'Active']
            selected_vehicle = st.selectbox("Vehicle Registation Number*", vehicle_options, key="booking_vehicle", help="Select existing vehicle or choose 'Add New Vehicle/Vendor' to create one")
            
            if selected_vehicle == "➕ Add New Vehicle/Vendor":
                vehicle_reg_no = st.text_input("Enter Vehicle Registration Number", key="booking_new_vehicle_reg", placeholder="e.g., TN01AB1234")
                if vehicle_reg_no:
                    # Load vendors
                    load_data_when_needed('vendors')
                    if hasattr(st.session_state, 'vendors') and st.session_state.vendors:
                        vendor_options = ["None", "➕ Add New Vendor"] + [v['name'] for v in st.session_state.vendors]
                    else:
                        vendor_options = ["None", "➕ Add New Vendor"]
                    
                    selected_vendor = st.selectbox("Select Vendor (Optional)", vendor_options, key="booking_new_vehicle_vendor", help="Link this vehicle to a vendor")
                    
                    if selected_vendor == "➕ Add New Vendor":
                        vendor_name = st.text_input("Enter Vendor Name", key="booking_new_vendor_name", placeholder="e.g., ABC Transport Services")
                        if vendor_name:
                            st.info(f"New vendor '{vendor_name}' will be added when you create the booking.")
                    
                    st.info(f"New vehicle '{vehicle_reg_no}' will be added when you create the booking.")
                linked_driver_name = ""
            else:
                vehicle_reg_no = selected_vehicle
                # Get driver info for selected vehicle
                selected_vehicle_data = next((v for v in st.session_state.vehicles if v['registration_number'] == selected_vehicle), None)
                linked_driver_name = selected_vehicle_data.get('linked_driver') if selected_vehicle_data else ""
        else:
            vehicle_options = ["➕ Add New Vehicle/Vendor"]
            selected_vehicle = st.selectbox("Vehicle Registation Number*", vehicle_options, key="booking_vehicle", help="Select existing vehicle or choose 'Add New Vehicle/Vendor' to create one")
            
            vehicle_reg_no = st.text_input("Enter Vehicle Registration Number", key="booking_new_vehicle_reg", placeholder="e.g., TN01AB1234")
            if vehicle_reg_no:
                # Load vendors
                load_data_when_needed('vendors')
                if hasattr(st.session_state, 'vendors') and st.session_state.vendors:
                    vendor_options = ["None", "➕ Add New Vendor"] + [v['name'] for v in st.session_state.vendors]
                else:
                    vendor_options = ["None", "➕ Add New Vendor"]
                
                selected_vendor = st.selectbox("Select Vendor (Optional)", vendor_options, key="booking_new_vehicle_vendor", help="Link this vehicle to a vendor")
                
                if selected_vendor == "➕ Add New Vendor":
                    vendor_name = st.text_input("Enter Vendor Name", key="booking_new_vendor_name", placeholder="e.g., ABC Transport Services")
                    if vendor_name:
                        st.info(f"New vendor '{vendor_name}' will be added when you create the booking.")
                
                st.info(f"New vehicle '{vehicle_reg_no}' will be added when you create the booking.")
            linked_driver_name = ""
        
        # Driver selection
        if hasattr(st.session_state, 'drivers') and st.session_state.drivers:
            driver_options = ["➕ Add New Driver"] + [d['name'] for d in st.session_state.drivers if d.get('status') in ['Available', 'On Trip']]
            # Pre-select linked driver if vehicle has one
            default_driver_index = 0
            if linked_driver_name and linked_driver_name in driver_options:
                default_driver_index = driver_options.index(linked_driver_name)
            
            selected_driver = st.selectbox("Driver*", driver_options, index=default_driver_index, key="booking_driver_select", help="Select existing driver or choose 'Add New Driver' to create one")
            
            if selected_driver == "➕ Add New Driver":
                driver = st.text_input("Enter New Driver Name", key="booking_new_driver_name", placeholder="e.g., Ravi Kumar")
                if driver:
                    st.info(f"New driver '{driver}' will be added when you create the booking.")
                driver_phone_from_master = ""
            else:
                driver = selected_driver
                # Get driver phone for selected driver
                selected_driver_data = next((d for d in st.session_state.drivers if d['name'] == selected_driver), None)
                driver_phone_from_master = selected_driver_data.get('phone', '') if selected_driver_data else ''
        else:
            driver_options = ["➕ Add New Driver"]
            selected_driver = st.selectbox("Driver*", driver_options, key="booking_driver_select", help="Select existing driver or choose 'Add New Driver' to create one")
            
            driver = st.text_input("Enter New Driver Name", key="booking_new_driver_name", placeholder="e.g., Ravi Kumar")
            if driver:
                st.info(f"New driver '{driver}' will be added when you create the booking.")
            driver_phone_from_master = ""
    
    with col2:
        # Driver phone - dynamically update based on selected driver
        current_driver = st.session_state.get('booking_driver_select', 'None')
        
        # Check if driver selection has changed and update phone accordingly
        if current_driver != "None" and hasattr(st.session_state, 'drivers') and st.session_state.drivers:
            selected_driver_data = next((d for d in st.session_state.drivers if d['name'] == current_driver), None)
            if selected_driver_data:
                # Update the phone number in session state when driver changes
                new_phone = selected_driver_data.get('phone', '')
                if f'last_booking_driver' not in st.session_state or st.session_state[f'last_booking_driver'] != current_driver:
                    st.session_state['booking_driver_phone'] = new_phone
                    st.session_state[f'last_booking_driver'] = current_driver
        
        driver_phone = st.text_input("Driver Phone*", placeholder="e.g., +91 7339X XXXXX", key="booking_driver_phone")
    
    # PRICING section
    st.markdown("**PRICING**")
    
    # Pricing lookup
    col_price1, col_price2 = st.columns([4, 1])
    
    with col_price1:
        # Initialize pricing in session state
        if 'booking_suggested_rate' not in st.session_state:
            st.session_state.booking_suggested_rate = None
        
        # Display pricing if available
        if st.session_state.booking_suggested_rate:
            pricing_info = st.session_state.booking_suggested_rate
            
            # Display in a nice info box
            st.info(
                f"**Suggested Rate: ₹ {pricing_info['rate']:,.2f}**\n\n"
                f"**Route:** {pricing_info.get('origin', pickup_location)} → {pricing_info.get('destination', destination)}\n\n"
                f"**Vehicle:** {pricing_info.get('vehicle_type', vehicle_type)}"
            )
        else:
            st.info("Click 'Find Price' to get suggested pricing for this booking")
    
    with col_price2:
        st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
        if st.button("Find Price", key="booking_find_price", use_container_width=True, type="primary"):
            if customer and pickup_location and destination and vehicle_type:
                # Search for customer
                customers = search_customer_by_name(customer)
                customer_id = customers[0]['id'] if customers else None
                
                # Get pricing (need to normalize vehicle type for lookup)
                from database import normalize_vehicle_type
                normalized_vehicle = normalize_vehicle_type(vehicle_type)
                
                pricing = get_pricing_for_customer(
                    customer_id,
                    customer,
                    pickup_location,
                    destination,
                    normalized_vehicle
                )
                
                if pricing:
                    st.session_state.booking_suggested_rate = pricing
                    st.rerun()
                else:
                    st.warning("No pricing found for this combination")
                    st.session_state.booking_suggested_rate = None
            else:
                st.error("Please fill customer, pickup, destination, and vehicle type first")
    
    # Price input field
    price_col1, price_col2, price_col3 = st.columns([2, 1, 1])
    
    with price_col1:
        price = st.number_input(
            "Price (₹)",
            min_value=0.0,
            step=100.0,
            value=float(st.session_state.booking_suggested_rate['rate']) if st.session_state.booking_suggested_rate else 0.0,
            key="booking_price_input",
            help="Enter the booking price"
        )
    
    with price_col2:
        if st.session_state.booking_suggested_rate:
            st.caption(f"Suggested: ₹{st.session_state.booking_suggested_rate['rate']:,.0f}")
    
    with price_col3:
        if price > 0 and st.session_state.booking_suggested_rate:
            diff = price - st.session_state.booking_suggested_rate['rate']
            variance_pct = (diff / st.session_state.booking_suggested_rate['rate']) * 100 if st.session_state.booking_suggested_rate['rate'] > 0 else 0
            variance_text = "On Target" if diff == 0 else ("Below" if diff < 0 else "Above")
            st.caption(f"{variance_text}: {diff:+.0f} ({variance_pct:+.0f}%)")
    
    # Submit button
    if st.button("Create Booking", key="btn_submit_booking", type="primary", use_container_width=True):
        # Validation
        if not customer or not booking_date or not vehicle_type or not pickup_location or not destination or not vehicle_reg_no or not driver_phone:
            st.error("Please fill all required fields marked with *")
            return
        
        # Validate driver phone
        if not validate_mobile_number(driver_phone):
            st.error("Driver phone must be a valid 10-digit number (starting with 6-9)")
            return
        
        # Check if customer exists, if not create it
        customer_id = None
        if hasattr(st.session_state, 'customers') and st.session_state.customers:
            existing_customer = next((c for c in st.session_state.customers if c['name'].lower() == customer.lower()), None)
            if existing_customer:
                customer_id = existing_customer['id']
            else:
                # Create new customer
                from database import add_to_database
                import uuid
                new_customer_data = {
                    'id': str(uuid.uuid4()),
                    'name': customer.title(),
                    'created_date': datetime.datetime.now()
                }
                customer_id = add_to_database('customers', new_customer_data)
                if customer_id:
                    st.success(f"New customer '{customer}' added successfully!")
                    # Refresh customer list
                    from database import refresh_data
                    refresh_data('customers')
                    load_data_when_needed('customers')
        
        # Check if driver exists, if not create it
        if driver and hasattr(st.session_state, 'drivers'):
            existing_driver = next((d for d in st.session_state.drivers if d['name'].lower() == driver.lower()), None)
            if not existing_driver:
                # Create new driver
                from database import add_to_database
                import uuid
                new_driver_data = {
                    'id': str(uuid.uuid4()),
                    'name': driver.title(),
                    'phone': driver_phone,
                    'status': 'Available',
                    'created_date': datetime.datetime.now()
                }
                driver_id = add_to_database('drivers', new_driver_data)
                if driver_id:
                    st.success(f"New driver '{driver}' added successfully!")
                    # Refresh driver list
                    from database import refresh_data
                    refresh_data('drivers')
                    load_data_when_needed('drivers')
        
        # Check if vehicle exists, if not create it
        if vehicle_reg_no and hasattr(st.session_state, 'vehicles'):
            existing_vehicle = next((v for v in st.session_state.vehicles if v['registration_number'].lower() == vehicle_reg_no.lower()), None)
            if not existing_vehicle:
                # Check if vendor needs to be created
                vendor_id = None
                if st.session_state.get('booking_new_vehicle_vendor') == "➕ Add New Vendor":
                    vendor_name = st.session_state.get('booking_new_vendor_name', '')
                    if vendor_name:
                        # Create new vendor
                        from database import add_to_database
                        import uuid
                        new_vendor_data = {
                            'id': str(uuid.uuid4()),
                            'name': vendor_name.title(),
                            'vendor_type': 'Vehicle Vendor',
                            'created_date': datetime.datetime.now()
                        }
                        vendor_id = add_to_database('vendors', new_vendor_data)
                        if vendor_id:
                            st.success(f"New vendor '{vendor_name}' added successfully!")
                            # Refresh vendor list
                            from database import refresh_data
                            refresh_data('vendors')
                            load_data_when_needed('vendors')
                elif st.session_state.get('booking_new_vehicle_vendor') and st.session_state.get('booking_new_vehicle_vendor') not in ["None", "➕ Add New Vendor"]:
                    # Use existing vendor
                    vendor_name = st.session_state.get('booking_new_vehicle_vendor')
                    existing_vendor = next((v for v in st.session_state.vendors if v['name'] == vendor_name), None)
                    if existing_vendor:
                        vendor_id = existing_vendor['id']
                
                # Create new vehicle
                from database import add_to_database
                import uuid
                new_vehicle_data = {
                    'id': str(uuid.uuid4()),
                    'registration_number': vehicle_reg_no.upper(),
                    'vehicle_type': vehicle_type,
                    'status': 'Active',
                    'created_date': datetime.datetime.now()
                }
                vehicle_id = add_to_database('vehicles', new_vehicle_data)
                if vehicle_id:
                    st.success(f"New vehicle '{vehicle_reg_no}' added successfully!")
                    # Refresh vehicle list
                    from database import refresh_data
                    refresh_data('vehicles')
                    load_data_when_needed('vehicles')
        
        # Create booking data
        booking_data = {
            'id': str(uuid.uuid4()),
            'booking_number': booking_number,
            'customer': customer,
            'booking_date': booking_date,
            'vehicle_type': vehicle_type,
            'route_from': pickup_location,
            'route_to': destination,
            'price': price if price > 0 else None,
            'vehicle_reg_no': vehicle_reg_no,
            'driver': driver,
            'driver_phone': driver_phone,
            'status': "CONFIRMED",
            'created_date': datetime.datetime.now(),
            'last_modified': datetime.datetime.now()
        }
        
        # Save to database
        from app import save_simplified_booking
        try:
            if save_simplified_booking(booking_data):
                # Add to session state for immediate display
                if 'bookings' not in st.session_state:
                    st.session_state.bookings = []
                st.session_state.bookings.insert(0, booking_data)  # Add at top
                
                # Add note for booking creation
                from .notes import add_status_note
                add_status_note(
                    record_id=booking_data['id'],
                    record_type='booking',
                    old_status=None,
                    new_status='CREATED',
                    changed_by=st.session_state.get('user', 'System'),
                    notes=f"Booking created - {booking_data['customer']}",
                    additional_data={
                        'booking_number': booking_number,
                        'customer': booking_data['customer'],
                        'pickup': booking_data.get('route_from', ''),
                        'destination': booking_data.get('route_to', '')
                    }
                )
                
                # Clear form
                for key in ['booking_customer', 'booking_pickup', 'booking_destination', 
                           'booking_vehicle', 'booking_driver_select', 'booking_driver_phone']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                # Show success
                st.session_state['show_success_page'] = True
                st.session_state['success_data'] = {
                    'title': 'Booking Created Successfully!',
                    'message': f"Booking {booking_number} has been created successfully!",
                    'created_item_number': booking_number,
                    'module_name': 'bookings'
                }
                st.rerun()
            else:
                st.error("Failed to save booking. Please try again.")
        except Exception as e:
            st.error(f"Error creating booking: {str(e)}")

def create_cash_booking():
    """Create cash booking with separate form"""
    st.subheader("Create Cash Booking")
    st.info("Quick cash booking form for immediate transactions.")
    
    # Generate booking number (show it to user)
    from app import generate_booking_number
    booking_number = generate_booking_number()
    
    st.info(f"**Booking Number:** {booking_number}")
    
    # Simple booking form
    st.markdown("**CASH BOOKING DETAILS**")
    col1, col2 = st.columns(2)
    
    with col1:
        # Load customers from database
        from database import load_data_when_needed
        load_data_when_needed('customers')
        
        # Get customer list
        if hasattr(st.session_state, 'customers') and st.session_state.customers:
            customer_options = ["➕ Add New Customer", "Cash Customer"] + [c['name'] for c in st.session_state.customers]
        else:
            customer_options = ["➕ Add New Customer", "Cash Customer"]
        
        # Use selectbox with all customers (has built-in search)
        customer_selection = st.selectbox(
            "Customer/Vendor*",
            customer_options,
            key="cash_customer",
            help="Select existing customer or choose 'Add New Customer' to create one"
        )
        
        # If user selects "Add New Customer", show text input
        if customer_selection == "➕ Add New Customer":
            customer = st.text_input(
                "Enter New Customer Name",
                key="cash_new_customer_name",
                placeholder="e.g., XYZ Transport"
            )
            if customer:
                st.info(f"New customer '{customer}' will be added when you create the booking.")
        else:
            customer = customer_selection
        
        booking_date = st.date_input("Date*", value=datetime.datetime.now().date(), key="cash_booking_date")
        
        # Load vehicle types from database
        from database import get_vehicle_types
        vehicle_type_options = get_vehicle_types()
        vehicle_type = st.selectbox("Vehicle Type*", vehicle_type_options, key="cash_booking_vehicle_type")
    
    with col2:
        pickup_location = st.text_input("Pick up*", placeholder="e.g., Mepz", key="cash_booking_pickup")
        destination = st.text_input("Destination*", placeholder="e.g., Airport", key="cash_booking_destination")
    
    # Price input field
    price_col1, price_col2, price_col3 = st.columns([2, 1, 1])
    
    with price_col1:
        price = st.number_input(
            "Price (₹)",
            min_value=0.0,
            step=100.0,
            value=float(st.session_state.booking_suggested_rate['rate']) if st.session_state.booking_suggested_rate else 0.0,
            key="booking_price",
            help="Enter the booking price"
        )
    
    with price_col2:
        if st.session_state.booking_suggested_rate:
            st.caption(f"Suggested: ₹{st.session_state.booking_suggested_rate['rate']:,.0f}")
    
    with price_col3:
        if price > 0 and st.session_state.booking_suggested_rate:
            diff = price - st.session_state.booking_suggested_rate['rate']
            diff_pct = (diff / st.session_state.booking_suggested_rate['rate']) * 100 if st.session_state.booking_suggested_rate['rate'] > 0 else 0
            variance_text = "On Target" if diff == 0 else ("Below" if diff < 0 else "Above")
            st.caption(f"{variance_text}: {diff:+.0f} ({diff_pct:+.0f}%)")
    
    st.markdown("**VEHICLE & DRIVER DETAILS**")
    col1, col2 = st.columns(2)
    
    # Load vehicle and driver data
    from database import load_data_when_needed
    load_data_when_needed('vehicles')
    load_data_when_needed('drivers')
    
    with col1:
        # Vehicle selection
        if hasattr(st.session_state, 'vehicles') and st.session_state.vehicles:
            vehicle_options = ["➕ Add New Vehicle/Vendor"] + [v['registration_number'] for v in st.session_state.vehicles if v.get('status') == 'Active']
            selected_vehicle = st.selectbox("Vehicle Registation Number*", vehicle_options, key="cash_booking_vehicle", help="Select existing vehicle or choose 'Add New Vehicle/Vendor' to create one")
            
            if selected_vehicle == "➕ Add New Vehicle/Vendor":
                vehicle_reg_no = st.text_input("Enter Vehicle Registration Number", key="cash_booking_new_vehicle_reg", placeholder="e.g., TN01AB1234")
                if vehicle_reg_no:
                    # Load vendors
                    load_data_when_needed('vendors')
                    if hasattr(st.session_state, 'vendors') and st.session_state.vendors:
                        vendor_options = ["None", "➕ Add New Vendor"] + [v['name'] for v in st.session_state.vendors]
                    else:
                        vendor_options = ["None", "➕ Add New Vendor"]
                    
                    selected_vendor = st.selectbox("Select Vendor (Optional)", vendor_options, key="cash_booking_new_vehicle_vendor", help="Link this vehicle to a vendor")
                    
                    if selected_vendor == "➕ Add New Vendor":
                        vendor_name = st.text_input("Enter Vendor Name", key="cash_booking_new_vendor_name", placeholder="e.g., ABC Transport Services")
                        if vendor_name:
                            st.info(f"New vendor '{vendor_name}' will be added when you create the booking.")
                    
                    st.info(f"New vehicle '{vehicle_reg_no}' will be added when you create the booking.")
                linked_driver_name = ""
            else:
                vehicle_reg_no = selected_vehicle
                # Get driver info for selected vehicle
                selected_vehicle_data = next((v for v in st.session_state.vehicles if v['registration_number'] == selected_vehicle), None)
                linked_driver_name = selected_vehicle_data.get('linked_driver') if selected_vehicle_data else ""
        else:
            vehicle_options = ["➕ Add New Vehicle/Vendor"]
            selected_vehicle = st.selectbox("Vehicle Registation Number*", vehicle_options, key="cash_booking_vehicle", help="Select existing vehicle or choose 'Add New Vehicle/Vendor' to create one")
            
            vehicle_reg_no = st.text_input("Enter Vehicle Registration Number", key="cash_booking_new_vehicle_reg", placeholder="e.g., TN01AB1234")
            if vehicle_reg_no:
                # Load vendors
                load_data_when_needed('vendors')
                if hasattr(st.session_state, 'vendors') and st.session_state.vendors:
                    vendor_options = ["None", "➕ Add New Vendor"] + [v['name'] for v in st.session_state.vendors]
                else:
                    vendor_options = ["None", "➕ Add New Vendor"]
                
                selected_vendor = st.selectbox("Select Vendor (Optional)", vendor_options, key="cash_booking_new_vehicle_vendor", help="Link this vehicle to a vendor")
                
                if selected_vendor == "➕ Add New Vendor":
                    vendor_name = st.text_input("Enter Vendor Name", key="cash_booking_new_vendor_name", placeholder="e.g., ABC Transport Services")
                    if vendor_name:
                        st.info(f"New vendor '{vendor_name}' will be added when you create the booking.")
                
                st.info(f"New vehicle '{vehicle_reg_no}' will be added when you create the booking.")
            linked_driver_name = ""
        
        # Driver selection
        if hasattr(st.session_state, 'drivers') and st.session_state.drivers:
            driver_options = ["None", "➕ Add New Driver"] + [d['name'] for d in st.session_state.drivers if d.get('status') in ['Available', 'On Trip']]
            # Pre-select linked driver if vehicle has one
            default_driver_index = 0
            if linked_driver_name and linked_driver_name in driver_options:
                default_driver_index = driver_options.index(linked_driver_name)
            
            selected_driver = st.selectbox("Driver*", driver_options, index=default_driver_index, key="cash_booking_driver_select", help="Select existing driver or choose 'Add New Driver' to create one")
            
            if selected_driver == "➕ Add New Driver":
                driver = st.text_input("Enter New Driver Name", key="cash_booking_new_driver_name", placeholder="e.g., Ravi Kumar")
                if driver:
                    st.info(f"New driver '{driver}' will be added when you create the booking.")
                driver_phone_from_master = ""
            else:
                driver = selected_driver
                # Get driver phone for selected driver
                selected_driver_data = next((d for d in st.session_state.drivers if d['name'] == selected_driver), None)
                driver_phone_from_master = selected_driver_data.get('phone', '') if selected_driver_data else ''
        else:
            driver_options = ["➕ Add New Driver"]
            selected_driver = st.selectbox("Driver*", driver_options, key="cash_booking_driver_select", help="Select existing driver or choose 'Add New Driver' to create one")
            
            driver = st.text_input("Enter New Driver Name", key="cash_booking_new_driver_name", placeholder="e.g., Ravi Kumar")
            if driver:
                st.info(f"New driver '{driver}' will be added when you create the booking.")
            driver_phone_from_master = ""

    with col2:
        # Driver phone - dynamically update based on selected driver
        current_driver = st.session_state.get('cash_booking_driver_select', 'None')
        
        # Check if driver selection has changed and update phone accordingly
        if current_driver != "None" and hasattr(st.session_state, 'drivers') and st.session_state.drivers:
            selected_driver_data = next((d for d in st.session_state.drivers if d['name'] == current_driver), None)
            if selected_driver_data:
                # Update the phone number in session state when driver changes
                new_phone = selected_driver_data.get('phone', '')
                if f'last_cash_booking_driver' not in st.session_state or st.session_state[f'last_cash_booking_driver'] != current_driver:
                    st.session_state['cash_booking_driver_phone'] = new_phone
                    st.session_state[f'last_cash_booking_driver'] = current_driver
        
        driver_phone = st.text_input("Driver Phone*", placeholder="e.g., +91 7339X XXXXX", key="cash_booking_driver_phone")
    
    # Submit button
    if st.button("Create Cash Booking", key="btn_submit_cash_booking", type="primary", width="stretch"):
        # Validation
        if not customer or not booking_date or not vehicle_type or not pickup_location or not destination or not vehicle_reg_no or not driver_phone:
            st.error("Please fill all required fields marked with *")
            return
        
        # Validate driver phone
        if not validate_mobile_number(driver_phone):
            st.error("Driver phone must be a valid 10-digit number (starting with 6-9)")
            return
        
        # Check if customer exists, if not create it (except for "Cash Customer")
        customer_id = None
        if customer != "Cash Customer":
            if hasattr(st.session_state, 'customers') and st.session_state.customers:
                existing_customer = next((c for c in st.session_state.customers if c['name'].lower() == customer.lower()), None)
                if existing_customer:
                    customer_id = existing_customer['id']
                else:
                    # Create new customer
                    from database import add_to_database
                    import uuid
                    new_customer_data = {
                        'id': str(uuid.uuid4()),
                        'name': customer.title(),
                        'created_date': datetime.datetime.now()
                    }
                    customer_id = add_to_database('customers', new_customer_data)
                    if customer_id:
                        st.success(f"New customer '{customer}' added successfully!")
                        # Refresh customer list
                        from database import refresh_data
                        refresh_data('customers')
                        load_data_when_needed('customers')
        
        # Check if driver exists, if not create it
        if driver and hasattr(st.session_state, 'drivers'):
            existing_driver = next((d for d in st.session_state.drivers if d['name'].lower() == driver.lower()), None)
            if not existing_driver:
                # Create new driver
                from database import add_to_database
                import uuid
                new_driver_data = {
                    'id': str(uuid.uuid4()),
                    'name': driver.title(),
                    'phone': driver_phone,
                    'status': 'Available',
                    'created_date': datetime.datetime.now()
                }
                driver_id = add_to_database('drivers', new_driver_data)
                if driver_id:
                    st.success(f"New driver '{driver}' added successfully!")
                    # Refresh driver list
                    from database import refresh_data
                    refresh_data('drivers')
                    load_data_when_needed('drivers')
        
        # Check if vehicle exists, if not create it
        if vehicle_reg_no and hasattr(st.session_state, 'vehicles'):
            existing_vehicle = next((v for v in st.session_state.vehicles if v['registration_number'].lower() == vehicle_reg_no.lower()), None)
            if not existing_vehicle:
                # Check if vendor needs to be created
                vendor_id = None
                if st.session_state.get('cash_booking_new_vehicle_vendor') == "➕ Add New Vendor":
                    vendor_name = st.session_state.get('cash_booking_new_vendor_name', '')
                    if vendor_name:
                        # Create new vendor
                        from database import add_to_database
                        import uuid
                        new_vendor_data = {
                            'id': str(uuid.uuid4()),
                            'name': vendor_name.title(),
                            'vendor_type': 'Vehicle Vendor',
                            'created_date': datetime.datetime.now()
                        }
                        vendor_id = add_to_database('vendors', new_vendor_data)
                        if vendor_id:
                            st.success(f"New vendor '{vendor_name}' added successfully!")
                            # Refresh vendor list
                            from database import refresh_data
                            refresh_data('vendors')
                            load_data_when_needed('vendors')
                elif st.session_state.get('cash_booking_new_vehicle_vendor') and st.session_state.get('cash_booking_new_vehicle_vendor') not in ["None", "➕ Add New Vendor"]:
                    # Use existing vendor
                    vendor_name = st.session_state.get('cash_booking_new_vehicle_vendor')
                    existing_vendor = next((v for v in st.session_state.vendors if v['name'] == vendor_name), None)
                    if existing_vendor:
                        vendor_id = existing_vendor['id']
                
                # Create new vehicle
                from database import add_to_database
                import uuid
                new_vehicle_data = {
                    'id': str(uuid.uuid4()),
                    'registration_number': vehicle_reg_no.upper(),
                    'vehicle_type': vehicle_type,
                    'status': 'Active',
                    'created_date': datetime.datetime.now()
                }
                vehicle_id = add_to_database('vehicles', new_vehicle_data)
                if vehicle_id:
                    st.success(f"New vehicle '{vehicle_reg_no}' added successfully!")
                    # Refresh vehicle list
                    from database import refresh_data
                    refresh_data('vehicles')
                    load_data_when_needed('vehicles')
        
        # Create booking data
        from database import normalize_vehicle_type
        booking_data = {
            'id': str(uuid.uuid4()),
            'booking_number': booking_number,
            'customer': customer,
            'booking_date': booking_date,
            'vehicle_type': normalize_vehicle_type(vehicle_type),
            'route_from': pickup_location,
            'route_to': destination,
            'price': price if price > 0 else None,
            'vehicle_reg_no': vehicle_reg_no,
            'driver': driver,
            'driver_phone': driver_phone,
            'status': 'CONFIRMED',
            'created_date': datetime.datetime.now(),
            'last_modified': datetime.datetime.now()
        }
        
        # Save to database
        from app import save_simplified_booking
        try:
            if save_simplified_booking(booking_data):
                # Add to session state for immediate display
                if 'bookings' not in st.session_state:
                    st.session_state.bookings = []
                st.session_state.bookings.insert(0, booking_data)  # Add at top
                
                # Add note for booking creation
                from .notes import add_status_note
                add_status_note(
                    record_id=booking_data['id'],
                    record_type='booking',
                    old_status=None,
                    new_status='CREATED',
                    changed_by=st.session_state.get('user', 'System'),
                    notes=f"Booking created - {booking_data['customer']}",
                    additional_data={
                        'booking_number': booking_number,
                        'customer': booking_data['customer'],
                        'pickup': booking_data.get('route_from', ''),
                        'destination': booking_data.get('route_to', '')
                    }
                )
                
                # Clear form
                for key in ['cash_customer', 'cash_booking_pickup', 'cash_booking_destination', 
                           'cash_booking_vehicle', 'cash_booking_driver_select', 'cash_booking_driver_phone']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                # Show success
                st.session_state['show_success_page'] = True
                st.session_state['success_data'] = {
                    'title': 'Cash Booking Created Successfully!',
                    'message': f"Cash Booking {booking_number} has been created successfully!",
                    'created_item_number': booking_number,
                    'module_name': 'bookings'
                }
                st.rerun()
            else:
                st.error("Failed to save cash booking. Please try again.")
        except Exception as e:
            st.error(f"Error creating cash booking: {str(e)}")

def view_bookings():
    """View and manage existing simplified bookings"""
    st.subheader("View Bookings")
    
    # Refresh bookings from database
    from database import get_cached_data
    st.session_state.bookings = get_cached_data('bookings', limit=None)
    
    if not st.session_state.bookings:
        st.info("No bookings found. Create your first booking in the 'Create Booking' tab.")
        return
    
    # Remove duplicates based on booking_number
    seen_numbers = set()
    unique_bookings = []
    for booking in st.session_state.bookings:
        booking_number = booking.get('booking_number', '')
        if booking_number and booking_number not in seen_numbers:
            unique_bookings.append(booking)
            seen_numbers.add(booking_number)
    st.session_state.bookings = unique_bookings
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All", "CREATED", "CONFIRMED", "DISPATCHED", "DELIVERED", "CANCELLED"])
    
    with col2:
        customer_filter = st.selectbox("Filter by Customer", ["All"] + sorted(list(set([b.get('customer', '') for b in st.session_state.bookings if b.get('customer')]))))
    
    with col3:
        date_from = st.date_input("From Date", value=datetime.datetime.now().date() - datetime.timedelta(days=30))
    
    with col4:
        st.metric("Total Bookings", len(st.session_state.bookings))
    
    # Apply filters
    filtered_bookings = st.session_state.bookings
    
    if status_filter != "All":
        filtered_bookings = [b for b in filtered_bookings if b.get('status') == status_filter]
    
    if customer_filter != "All":
        filtered_bookings = [b for b in filtered_bookings if b.get('customer') == customer_filter]
    
    if date_from:
        filtered_bookings = [b for b in filtered_bookings if safe_get_date(b.get('booking_date')) >= date_from]
    
    # Display bookings in cards
    if filtered_bookings:
        st.markdown(f"**Showing {len(filtered_bookings)} bookings**")
        
        for booking in filtered_bookings:
            # Status color coding
            status_colors = {
                'CREATED': 'CREATED',
                'CONFIRMED': 'CONFIRMED',
                'DISPATCHED': 'DISPATCHED',
                'DELIVERED': 'DELIVERED',
                'CANCELLED': 'CANCELLED'
            }
            status_icon = status_colors.get(booking.get('status', 'CREATED'), '⚪')
            
            with st.expander(f"{status_icon} {booking.get('booking_number', 'N/A')} - {booking.get('customer', 'Unknown')} - {booking.get('status', 'CREATED')}"):
                # Display booking details in a structured way
                detail_col1, detail_col2 = st.columns(2)
                
                with detail_col1:
                    st.markdown("**BOOKING DETAILS**")
                    st.write(f"**Booking No:** {booking.get('booking_number', 'N/A')}")
                    st.write(f"**Customer:** {booking.get('customer', 'N/A')}")
                    st.write(f"**Date:** {booking.get('booking_date', 'N/A')}")
                    st.write(f"**Vehicle Type:** {booking.get('vehicle_type', 'N/A')}")
                    st.write(f"**Route:** {booking.get('route_from', 'N/A')} → {booking.get('route_to', 'N/A')}")
                    booking_price_value = None
                    for price_key in ['price', 'base_price', 'total_amount', 'amount', 'rate']:
                        if booking.get(price_key) not in [None, '']:
                            booking_price_value = booking.get(price_key)
                            break
                    if booking_price_value is not None:
                        try:
                            st.write(f"**Price:** ₹ {float(booking_price_value):,.2f}")
                        except (TypeError, ValueError):
                            st.write(f"**Price:** {booking_price_value}")
                    else:
                        st.write("**Price:** N/A")
                    
                with detail_col2:
                    st.markdown("**VEHICLE & DRIVER DETAILS**")
                    st.write(f"**Reg No:** {booking.get('vehicle_reg_no', 'Not assigned')}")
                    st.write(f"**Driver:** {booking.get('driver', 'Not assigned')}")
                    st.write(f"**Phone:** {booking.get('driver_phone', 'Not provided')}")
                    st.write(f"**STATUS:** {booking.get('status', 'CREATED')}")
                    st.write(f"**Created:** {format_datetime(booking.get('created_date'))}")
                
                # Copy to clipboard button
                st.markdown("---")
                from .utils import format_booking_details
                booking_text = format_booking_details(booking)
                
                col_copy1, col_copy2 = st.columns([1, 3])
                with col_copy1:
                    if st.session_state.get(f"show_copy_{booking.get('id', booking.get('booking_number'))}", False):
                        if st.button("🙈 Hide", key=f"hide_btn_{booking.get('id', booking.get('booking_number'))}", help="Hide text"):
                            st.session_state[f"show_copy_{booking.get('id', booking.get('booking_number'))}"] = False
                            st.rerun()
                    else:
                        if st.button("Copy", key=f"copy_btn_{booking.get('id', booking.get('booking_number'))}", help="Click to copy text"):
                            st.session_state[f"show_copy_{booking.get('id', booking.get('booking_number'))}"] = True
                            st.rerun()
                with col_copy2:
                    copy_placeholder = st.empty()
                
                if st.session_state.get(f"show_copy_{booking.get('id', booking.get('booking_number'))}", False):
                    with copy_placeholder.container():
                        st.code(booking_text, language="text")
                        st.success("Select and copy the text above!")
                
                # Action buttons
                st.markdown("---")
                st.markdown("**⚡ Actions:**")
                action_col1, action_col2, action_col3 = st.columns(3)
                
                with action_col1:
                    if st.button(f"Edit", key=f"edit_{booking.get('id', booking.get('booking_number'))}"):
                        st.session_state[f"editing_{booking.get('id', booking.get('booking_number'))}"] = True
                        st.rerun()
                
                with action_col2:
                    # Status progression buttons
                    current_status = booking.get('status', 'CREATED')
                    if current_status == 'CREATED':
                        if st.button(f"Confirm", key=f"confirm_{booking.get('id', booking.get('booking_number'))}", type="primary"):
                            update_booking_status(booking, 'CONFIRMED')
                            st.rerun()
                    elif current_status == 'CONFIRMED':
                        if st.button(f"Dispatch", key=f"dispatch_{booking.get('id', booking.get('booking_number'))}", type="primary"):
                            update_booking_status(booking, 'DISPATCHED')
                            st.rerun()
                    elif current_status == 'DISPATCHED':
                        if st.button(f"Deliver", key=f"deliver_{booking.get('id', booking.get('booking_number'))}", type="primary"):
                            update_booking_status(booking, 'DELIVERED')
                            st.rerun()
                
                with action_col3:
                    if current_status not in ['DELIVERED', 'CANCELLED']:
                        if st.button(f"Cancel", key=f"cancel_{booking.get('id', booking.get('booking_number'))}"):
                            # Add note for booking cancellation
                            from .notes import add_status_note
                            add_status_note(
                                record_id=booking.get('id'),
                                record_type='booking',
                                old_status=current_status,
                                new_status='CANCELLED',
                                changed_by=st.session_state.get('user', 'System'),
                                notes=f"Booking cancelled - {booking.get('booking_number')}",
                                additional_data={
                                    'booking_number': booking.get('booking_number'),
                                    'customer': booking.get('customer', 'N/A'),
                                    'reason': 'User cancelled'
                                }
                            )
                            update_booking_status(booking, 'CANCELLED')
                            st.rerun()
                
                # Edit form
                booking_id = booking.get('id', booking.get('booking_number'))
                if st.session_state.get(f"editing_{booking_id}", False):
                    st.markdown("---")
                    st.markdown("### Edit Booking")
                    
                    edit_col1, edit_col2 = st.columns(2)
                    
                    with edit_col1:
                        new_customer = st.text_input("Customer", value=booking.get('customer', ''), key=f"edit_customer_{booking_id}")
                        
                        # Load vehicle types from database
                        from database import get_vehicle_types, get_vehicle_display_name
                        vehicle_type_options = get_vehicle_types()
                        current_vehicle_type_stored = booking.get('vehicle_type', '7ft')
                        current_vehicle_type_display = get_vehicle_display_name(current_vehicle_type_stored)
                        vehicle_type_index = vehicle_type_options.index(current_vehicle_type_display) if current_vehicle_type_display in vehicle_type_options else 0
                        new_vehicle_type = st.selectbox("Vehicle Type", vehicle_type_options, 
                                                      index=vehicle_type_index,
                                                      key=f"edit_vehicle_type_{booking_id}")
                        new_pickup_location = st.text_input("Pick up", value=booking.get('route_from', ''), key=f"edit_pickup_{booking_id}")
                        new_destination = st.text_input("Destination", value=booking.get('route_to', ''), key=f"edit_destination_{booking_id}")
                    
                    with edit_col2:
                        new_vehicle_reg = st.text_input("Vehicle Registation Number", value=booking.get('vehicle_reg_no', ''), key=f"edit_vehicle_reg_{booking_id}")
                        new_driver = st.text_input("Driver", value=booking.get('driver', ''), key=f"edit_driver_{booking_id}")
                        new_driver_phone = st.text_input("Driver Phone", value=booking.get('driver_phone', ''), key=f"edit_driver_phone_{booking_id}")
                        new_status = st.selectbox("Status", ["CREATED", "CONFIRMED", "DISPATCHED", "DELIVERED", "CANCELLED"], 
                                                 index=["CREATED", "CONFIRMED", "DISPATCHED", "DELIVERED", "CANCELLED"].index(booking.get('status', 'CREATED')) if booking.get('status') in ["CREATED", "CONFIRMED", "DISPATCHED", "DELIVERED", "CANCELLED"] else 0,
                                                 key=f"edit_status_{booking_id}")
                    
                    edit_action_col1, edit_action_col2 = st.columns(2)
                    
                    with edit_action_col1:
                        if st.button(f"Save Changes", key=f"save_{booking_id}", type="primary"):
                            # Update booking
                            for i, b in enumerate(st.session_state.bookings):
                                if b.get('id', b.get('booking_number')) == booking_id:
                                    st.session_state.bookings[i].update({
                                        'customer': new_customer,
                                        'vehicle_type': new_vehicle_type,
                                        'route_from': new_pickup_location,
                                        'route_to': new_destination,
                                        'vehicle_reg_no': new_vehicle_reg,
                                        'driver': new_driver,
                                        'driver_phone': new_driver_phone,
                                        'status': new_status,
                                        'last_modified': datetime.datetime.now()
                                    })
                                    break
                            
                            # Update in database
                            from app import update_simplified_booking
                            from database import normalize_vehicle_type
                            update_simplified_booking(booking_id, {
                                'customer': new_customer,
                                'vehicle_type': normalize_vehicle_type(new_vehicle_type),
                                'route_from': new_pickup_location,
                                'route_to': new_destination,
                                'vehicle_reg_no': new_vehicle_reg,
                                'driver': new_driver,
                                'driver_phone': new_driver_phone,
                                'status': new_status
                            })
                            
                            del st.session_state[f"editing_{booking_id}"]
                            st.success("Booking updated successfully!")
                            st.rerun()
                    
                    with edit_action_col2:
                        if st.button(f"Cancel Edit", key=f"cancel_edit_{booking_id}"):
                            # Add note for edit cancellation
                            from .notes import add_status_note
                            add_status_note(
                                record_id=booking_id,
                                record_type='booking',
                                old_status=booking.get('status'),
                                new_status=booking.get('status'),
                                changed_by=st.session_state.get('user', 'System'),
                                notes=f"Edit cancelled for booking {booking.get('booking_number', booking_id)}"
                            )
                            del st.session_state[f"editing_{booking_id}"]
                            st.rerun()
    
    else:
        st.info("No bookings found matching the selected filters.")

def update_booking_status(booking, new_status):
    """Update booking status"""
    booking_id = booking.get('id', booking.get('booking_number'))
    old_status = booking.get('status', 'CREATED')
    
    # Update in session state
    for i, b in enumerate(st.session_state.bookings):
        if b.get('id', b.get('booking_number')) == booking_id:
            st.session_state.bookings[i]['status'] = new_status
            st.session_state.bookings[i]['last_modified'] = datetime.datetime.now()
            break
    
    # Update in database
    from app import update_simplified_booking
    update_simplified_booking(booking_id, {'status': new_status})
    
    st.success(f"Booking status updated from {old_status} to {new_status}!")