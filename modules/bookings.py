import streamlit as st
import pandas as pd
import datetime
import uuid
import re
from typing import Dict, List
from .quotations import safe_get_date
from .utils import searchable_selectbox, static_selectbox, validate_mobile_number

def show_success_page(title, message, created_item_id=None, created_item_number=None, module_name="bookings"):
    """Show success page with navigation options"""
    st.markdown(f"### ✅ {title}")
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
        if st.button(f"➕ Create Another {module_name.title().rstrip('s')}", type="primary", width="stretch"):
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
        if st.button("🏠 Go to Dashboard", width="stretch"):
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
    
    st.header("📦 Bookings Management")
    
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
        if st.button("➕ Create Booking", 
                    type="primary" if st.session_state.booking_tab_selection == 0 else "secondary",
                    use_container_width=True):
            st.session_state.booking_tab_selection = 0
            st.rerun()
    
    with col2:
        if st.button("📋 View Bookings", 
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
    
    # Simple booking form
    st.markdown("**📋 BOOKING DETAILS**")
    col1, col2 = st.columns(2)
    
    with col1:
        # Load customers from database
        from database import load_data_when_needed
        load_data_when_needed('customers')
        
        if hasattr(st.session_state, 'customers') and st.session_state.customers:
            customer_options = [c['name'] for c in st.session_state.customers]
            customer = searchable_selectbox("Customer*", customer_options, key="booking_customer", help_text="Select existing customer or add new one in Quotations > Customers tab")
        else:
            st.warning("⚠️ No customers found. Please add customers first in Quotations > Customers tab.")
            customer = st.text_input("Customer* (Manual Entry)", placeholder="e.g., Fast Logistics", key="booking_customer_manual")
        
        booking_date = st.date_input("Date*", value=datetime.datetime.now().date(), key="booking_date")
        vehicle_type = st.selectbox("Vehicle Type*", ["7ft", "8ft", "12ft", "14ft", "17ft", "20ft", "24ft", "32ft"], key="booking_vehicle_type")
    
    with col2:
        pickup_location = st.text_input("Pick up*", placeholder="e.g., Mepz", key="booking_pickup")
        destination = st.text_input("Destination*", placeholder="e.g., Airport", key="booking_destination")
    
    st.markdown("**🚛 VEHICLE & DRIVER DETAILS**")
    col1, col2 = st.columns(2)
    
    # Load vehicle and driver data
    from database import load_data_when_needed
    load_data_when_needed('vehicles')
    load_data_when_needed('drivers')
    
    with col1:
        # Vehicle selection
        if hasattr(st.session_state, 'vehicles') and st.session_state.vehicles:
            vehicle_options = ["None"] + [v['registration_number'] for v in st.session_state.vehicles if v.get('status') == 'Active']
            selected_vehicle = searchable_selectbox("Vehicle Reg No", vehicle_options, key="booking_vehicle")
            vehicle_reg_no = selected_vehicle if selected_vehicle != "None" else ""
            
            # Get driver info for selected vehicle
            selected_vehicle_data = next((v for v in st.session_state.vehicles if v['registration_number'] == selected_vehicle), None) if selected_vehicle != "None" else None
            linked_driver_name = selected_vehicle_data.get('linked_driver') if selected_vehicle_data else ""
        else:
            st.warning("No vehicles found. Please add vehicles in Vehicle Master.")
            vehicle_reg_no = st.text_input("Vehicle Reg No", placeholder="e.g., TN1XXXXXX", key="booking_reg_no_manual")
            linked_driver_name = ""
        
        # Driver selection
        if hasattr(st.session_state, 'drivers') and st.session_state.drivers:
            driver_options = ["None"] + [d['name'] for d in st.session_state.drivers if d.get('status') in ['Available', 'On Trip']]
            # Pre-select linked driver if vehicle has one
            default_driver_index = 0
            if linked_driver_name and linked_driver_name in driver_options:
                default_driver_index = driver_options.index(linked_driver_name)
            
            selected_driver = searchable_selectbox("Driver", driver_options, default_index=default_driver_index, key="booking_driver_select")
            driver = selected_driver if selected_driver != "None" else ""
            
            # Get driver phone for selected driver
            selected_driver_data = next((d for d in st.session_state.drivers if d['name'] == selected_driver), None) if selected_driver != "None" else None
            driver_phone_from_master = selected_driver_data.get('phone', '') if selected_driver_data else ''
        else:
            driver = st.text_input("Driver", placeholder="e.g., Driver Name", key="booking_driver_manual")
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
        
        driver_phone = st.text_input("Driver Phone", placeholder="e.g., 7339X XXXXX", key="booking_driver_phone")
        status = st.selectbox("Status", ["CREATED", "CONFIRMED", "DISPATCHED", "DELIVERED", "CANCELLED"], 
                             index=1, key="booking_status")  # Default to CONFIRMED
    
    # Submit button
    if st.button("💾 Create Booking", type="primary", width="stretch"):
        # Validation
        if not customer or not booking_date or not vehicle_type or not pickup_location or not destination:
            st.error("❌ Please fill all required fields marked with *")
            return
        
        # Validate driver phone if provided
        if driver_phone and not validate_mobile_number(driver_phone):
            st.error("❌ Driver phone must be a valid 10-digit number (starting with 6-9)")
            return
        
        # Create booking data
        booking_data = {
            'id': str(uuid.uuid4()),
            'booking_number': booking_number,
            'customer': customer,
            'booking_date': booking_date,
            'vehicle_type': vehicle_type,
            'route_from': pickup_location,
            'route_to': destination,
            'vehicle_reg_no': vehicle_reg_no,
            'driver': driver,
            'driver_phone': driver_phone,
            'status': status,
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
                st.error("❌ Failed to save booking. Please try again.")
        except Exception as e:
            st.error(f"❌ Error creating booking: {str(e)}")

def create_cash_booking():
    """Create cash booking with separate form"""
    st.subheader("Create Cash Booking")
    st.info("📋 Quick cash booking form for immediate transactions.")
    
    # Generate booking number (show it to user)
    from app import generate_booking_number
    booking_number = generate_booking_number()
    
    st.info(f"**Booking Number:** {booking_number}")
    
    # Simple booking form
    st.markdown("**📋 CASH BOOKING DETAILS**")
    col1, col2 = st.columns(2)
    
    with col1:
        # Load customers from database
        from database import load_data_when_needed
        load_data_when_needed('customers')
        
        if hasattr(st.session_state, 'customers') and st.session_state.customers:
            customer_options = ["Cash Customer (No account)"] + [c['name'] for c in st.session_state.customers]
            customer = searchable_selectbox("Customer/Vendor*", customer_options, key="cash_customer", help_text="Select customer or use Cash Customer for walk-in")
        else:
            customer = st.text_input("Customer/Vendor* (Manual Entry)", placeholder="e.g., Cash Customer Name", key="cash_customer_manual")
        
        booking_date = st.date_input("Date*", value=datetime.datetime.now().date(), key="cash_booking_date")
        vehicle_type = st.selectbox("Vehicle Type*", ["7ft", "8ft", "12ft", "14ft", "17ft", "20ft", "24ft", "32ft"], key="cash_booking_vehicle_type")
    
    with col2:
        pickup_location = st.text_input("Pick up*", placeholder="e.g., Mepz", key="cash_booking_pickup")
        destination = st.text_input("Destination*", placeholder="e.g., Airport", key="cash_booking_destination")
    
    st.markdown("**🚛 VEHICLE & DRIVER DETAILS**")
    col1, col2 = st.columns(2)
    
    # Load vehicle and driver data
    from database import load_data_when_needed
    load_data_when_needed('vehicles')
    load_data_when_needed('drivers')
    
    with col1:
        # Vehicle selection
        if hasattr(st.session_state, 'vehicles') and st.session_state.vehicles:
            vehicle_options = ["None"] + [v['registration_number'] for v in st.session_state.vehicles if v.get('status') == 'Active']
            selected_vehicle = searchable_selectbox("Vehicle Reg No", vehicle_options, key="cash_booking_vehicle")
            vehicle_reg_no = selected_vehicle if selected_vehicle != "None" else ""
            
            # Get driver info for selected vehicle
            selected_vehicle_data = next((v for v in st.session_state.vehicles if v['registration_number'] == selected_vehicle), None) if selected_vehicle != "None" else None
            linked_driver_name = selected_vehicle_data.get('linked_driver') if selected_vehicle_data else ""
        else:
            st.warning("No vehicles found. Please add vehicles in Vehicle Master.")
            vehicle_reg_no = st.text_input("Vehicle Reg No", placeholder="e.g., TN1XXXXXX", key="cash_booking_reg_no_manual")
            linked_driver_name = ""
        
        # Driver selection
        if hasattr(st.session_state, 'drivers') and st.session_state.drivers:
            driver_options = ["None"] + [d['name'] for d in st.session_state.drivers if d.get('status') in ['Available', 'On Trip']]
            # Pre-select linked driver if vehicle has one
            default_driver_index = 0
            if linked_driver_name and linked_driver_name in driver_options:
                default_driver_index = driver_options.index(linked_driver_name)
            
            selected_driver = searchable_selectbox("Driver", driver_options, default_index=default_driver_index, key="cash_booking_driver_select")
            driver = selected_driver if selected_driver != "None" else ""
            
            # Get driver phone for selected driver
            selected_driver_data = next((d for d in st.session_state.drivers if d['name'] == selected_driver), None) if selected_driver != "None" else None
            driver_phone_from_master = selected_driver_data.get('phone', '') if selected_driver_data else ''
        else:
            driver = st.text_input("Driver", placeholder="e.g., Nithish", key="cash_booking_driver_manual")
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
        
        driver_phone = st.text_input("Driver Phone", placeholder="e.g., +91 7339X XXXXX", key="cash_booking_driver_phone")
        status = st.selectbox("Status", ["CREATED", "CONFIRMED", "DISPATCHED", "DELIVERED", "CANCELLED"], 
                             index=1, key="cash_booking_status")  # Default to CONFIRMED
    # Submit button
    if st.button("💾 Create Cash Booking", type="primary", width="stretch"):
        # Validation
        if not customer or not booking_date or not vehicle_type or not pickup_location or not destination:
            st.error("❌ Please fill all required fields marked with *")
            return
        
        # Create booking data
        booking_data = {
            'id': str(uuid.uuid4()),
            'booking_number': booking_number,
            'customer': customer,
            'booking_date': booking_date,
            'vehicle_type': vehicle_type,
            'route_from': pickup_location,
            'route_to': destination,
            'vehicle_reg_no': vehicle_reg_no,
            'driver': driver,
            'driver_phone': driver_phone,
            'status': status,
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
                for key in ['cash_booking_customer', 'cash_booking_pickup', 'cash_booking_destination', 
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
                st.error("❌ Failed to save cash booking. Please try again.")
        except Exception as e:
            st.error(f"❌ Error creating cash booking: {str(e)}")

def view_bookings():
    """View and manage existing simplified bookings"""
    st.subheader("📋 View Bookings")
    
    # Refresh bookings from database
    from database import get_cached_data
    st.session_state.bookings = get_cached_data('bookings', limit=None)
    
    if not st.session_state.bookings:
        st.info("📝 No bookings found. Create your first booking in the 'Create Booking' tab.")
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
        st.metric("📊 Total Bookings", len(st.session_state.bookings))
    
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
        st.markdown(f"**📋 Showing {len(filtered_bookings)} bookings**")
        
        for booking in filtered_bookings:
            # Status color coding
            status_colors = {
                'CREATED': '🟡',
                'CONFIRMED': '🔵', 
                'DISPATCHED': '🟠',
                'DELIVERED': '🟢',
                'CANCELLED': '❌'
            }
            status_icon = status_colors.get(booking.get('status', 'CREATED'), '⚪')
            
            with st.expander(f"{status_icon} {booking.get('booking_number', 'N/A')} - {booking.get('customer', 'Unknown')} - {booking.get('status', 'CREATED')}"):
                # Display booking details in a structured way
                detail_col1, detail_col2 = st.columns(2)
                
                with detail_col1:
                    st.markdown("**📋 BOOKING DETAILS**")
                    st.write(f"**Booking No:** {booking.get('booking_number', 'N/A')}")
                    st.write(f"**Customer:** {booking.get('customer', 'N/A')}")
                    st.write(f"**Date:** {booking.get('booking_date', 'N/A')}")
                    st.write(f"**Vehicle Type:** {booking.get('vehicle_type', 'N/A')}")
                    st.write(f"**Route:** {booking.get('route_from', 'N/A')} → {booking.get('route_to', 'N/A')}")
                    
                with detail_col2:
                    st.markdown("**🚛 VEHICLE & DRIVER DETAILS**")
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
                        if st.button("📋 Copy", key=f"copy_btn_{booking.get('id', booking.get('booking_number'))}", help="Click to copy text"):
                            st.session_state[f"show_copy_{booking.get('id', booking.get('booking_number'))}"] = True
                            st.rerun()
                with col_copy2:
                    copy_placeholder = st.empty()
                
                if st.session_state.get(f"show_copy_{booking.get('id', booking.get('booking_number'))}", False):
                    with copy_placeholder.container():
                        st.code(booking_text, language="text")
                        st.success("✅ Select and copy the text above!")
                
                # Action buttons
                st.markdown("---")
                st.markdown("**⚡ Actions:**")
                action_col1, action_col2, action_col3, action_col4 = st.columns(4)
                
                with action_col1:
                    if st.button(f"✏️ Edit", key=f"edit_{booking.get('id', booking.get('booking_number'))}"):
                        st.session_state[f"editing_{booking.get('id', booking.get('booking_number'))}"] = True
                        st.rerun()
                
                with action_col2:
                    # Status progression buttons
                    current_status = booking.get('status', 'CREATED')
                    if current_status == 'CREATED':
                        if st.button(f"✅ Confirm", key=f"confirm_{booking.get('id', booking.get('booking_number'))}", type="primary"):
                            update_booking_status(booking, 'CONFIRMED')
                            st.rerun()
                    elif current_status == 'CONFIRMED':
                        if st.button(f"🚚 Dispatch", key=f"dispatch_{booking.get('id', booking.get('booking_number'))}", type="primary"):
                            update_booking_status(booking, 'DISPATCHED')
                            st.rerun()
                    elif current_status == 'DISPATCHED':
                        if st.button(f"📦 Deliver", key=f"deliver_{booking.get('id', booking.get('booking_number'))}", type="primary"):
                            update_booking_status(booking, 'DELIVERED')
                            st.rerun()
                
                with action_col3:
                    if current_status not in ['DELIVERED', 'CANCELLED']:
                        if st.button(f"❌ Cancel", key=f"cancel_{booking.get('id', booking.get('booking_number'))}"):
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
                
                with action_col4:
                    if st.button(f"📄 Details", key=f"details_{booking.get('id', booking.get('booking_number'))}"):
                        st.info("Full booking details view can be implemented here")
                
                # Edit form
                booking_id = booking.get('id', booking.get('booking_number'))
                if st.session_state.get(f"editing_{booking_id}", False):
                    st.markdown("---")
                    st.markdown("### ✏️ Edit Booking")
                    
                    edit_col1, edit_col2 = st.columns(2)
                    
                    with edit_col1:
                        new_customer = st.text_input("Customer", value=booking.get('customer', ''), key=f"edit_customer_{booking_id}")
                        new_vehicle_type = st.selectbox("Vehicle Type", ["7ft", "8ft", "12ft", "14ft", "17ft", "20ft", "24ft", "32ft"], 
                                                      index=["7ft", "8ft", "12ft", "14ft", "17ft", "20ft", "24ft", "32ft"].index(booking.get('vehicle_type', '7ft')) if booking.get('vehicle_type') in ["7ft", "8ft", "12ft", "14ft", "17ft", "20ft", "24ft", "32ft"] else 0,
                                                      key=f"edit_vehicle_type_{booking_id}")
                        new_pickup_location = st.text_input("Pick up", value=booking.get('route_from', ''), key=f"edit_pickup_{booking_id}")
                        new_destination = st.text_input("Destination", value=booking.get('route_to', ''), key=f"edit_destination_{booking_id}")
                    
                    with edit_col2:
                        new_vehicle_reg = st.text_input("Vehicle Reg No", value=booking.get('vehicle_reg_no', ''), key=f"edit_vehicle_reg_{booking_id}")
                        new_driver = st.text_input("Driver", value=booking.get('driver', ''), key=f"edit_driver_{booking_id}")
                        new_driver_phone = st.text_input("Driver Phone", value=booking.get('driver_phone', ''), key=f"edit_driver_phone_{booking_id}")
                        new_status = st.selectbox("Status", ["CREATED", "CONFIRMED", "DISPATCHED", "DELIVERED", "CANCELLED"], 
                                                 index=["CREATED", "CONFIRMED", "DISPATCHED", "DELIVERED", "CANCELLED"].index(booking.get('status', 'CREATED')) if booking.get('status') in ["CREATED", "CONFIRMED", "DISPATCHED", "DELIVERED", "CANCELLED"] else 0,
                                                 key=f"edit_status_{booking_id}")
                    
                    edit_action_col1, edit_action_col2 = st.columns(2)
                    
                    with edit_action_col1:
                        if st.button(f"💾 Save Changes", key=f"save_{booking_id}", type="primary"):
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
                            update_simplified_booking(booking_id, {
                                'customer': new_customer,
                                'vehicle_type': new_vehicle_type,
                                'route_from': new_pickup_location,
                                'route_to': new_destination,
                                'vehicle_reg_no': new_vehicle_reg,
                                'driver': new_driver,
                                'driver_phone': new_driver_phone,
                                'status': new_status
                            })
                            
                            del st.session_state[f"editing_{booking_id}"]
                            st.success("✅ Booking updated successfully!")
                            st.rerun()
                    
                    with edit_action_col2:
                        if st.button(f"❌ Cancel Edit", key=f"cancel_edit_{booking_id}"):
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
    
    st.success(f"✅ Booking status updated from {old_status} to {new_status}!")