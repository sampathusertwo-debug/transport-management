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
from .utils import searchable_selectbox, static_selectbox, validate_mobile_number
from .customer_pricing import get_pricing_for_customer, search_customer_by_name

def show_quotation_success_page(title, message, created_item_id=None, created_item_number=None, module_name="quotations"):
    """Show success page with navigation options for quotations"""
    st.markdown(f"### ✅ {title}")
    st.success(message)
    
    if created_item_number:
        st.markdown(f"**Quotation Number:** `{created_item_number}`")
    
    if created_item_id:
        st.markdown(f"**ID:** `{created_item_id}`")
    
    st.markdown("---")
    st.markdown("#### What would you like to do next?")
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Create Another Quotation", type="primary", width="stretch"):
            # Clear any success flags and return to create mode
            if 'show_quotation_success_page' in st.session_state:
                del st.session_state['show_quotation_success_page']
            if 'quotation_success_data' in st.session_state:
                del st.session_state['quotation_success_data']
            st.rerun()
    
    with col2:
        if st.button("👀 View All Quotations", width="stretch"):
            # Navigate to view/list mode
            if 'show_quotation_success_page' in st.session_state:
                del st.session_state['show_quotation_success_page']
            if 'quotation_success_data' in st.session_state:
                del st.session_state['quotation_success_data']
            if 'editing_quotation_id' in st.session_state:
                del st.session_state['editing_quotation_id']
            if 'editing_quotation_mode' in st.session_state:
                del st.session_state['editing_quotation_mode']
            # Switch to appropriate tab
            st.session_state.active_quotation_tab = "view"
            st.rerun()
    
    with col3:
        if st.button("🏠 Go to Dashboard", width="stretch"):
            # Clear success state and go to dashboard
            if 'show_quotation_success_page' in st.session_state:
                del st.session_state['show_quotation_success_page']
            if 'quotation_success_data' in st.session_state:
                del st.session_state['quotation_success_data']
            st.success("Redirecting to Dashboard...")
            st.rerun()

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
    
    # Check if we need to show success page
    if st.session_state.get('show_quotation_success_page', False) and st.session_state.get('quotation_success_data'):
        success_data = st.session_state['quotation_success_data']
        show_quotation_success_page(
            title=success_data.get('title', 'Success!'),
            message=success_data.get('message', 'Operation completed successfully!'),
            created_item_id=success_data.get('created_item_id'),
            created_item_number=success_data.get('created_item_number'),
            module_name=success_data.get('module_name', 'quotations')
        )
        return
    
    st.header("📋 Quotations Management")
    
    # Handle tab switching from success page
    active_tab_index = 1 if st.session_state.get('active_quotation_tab') == "view" else 0
    
    tab1, tab2, tab3 = st.tabs(["Create Quotation", "View Quotations", "Manage Customers"])
    
    with tab1:
        create_quotation()
    
    with tab2:
        view_quotations()
    
    with tab3:
        manage_customers()

def create_quotation():
    """Create a new simplified quotation"""
    st.subheader("Create New Quotation")
    
    # Generate quotation number (show it to user)
    from app import generate_quotation_number
    quotation_number = generate_quotation_number()
    
    st.info(f"**Quotation Number:** {quotation_number}")
    
    # Simple quotation form matching booking structure
    st.markdown("**📋 QUOTATION DETAILS**")
    col1, col2 = st.columns(2)
    
    with col1:
        # Load customers from database
        from database import load_data_when_needed
        load_data_when_needed('customers')
        
        if hasattr(st.session_state, 'customers') and st.session_state.customers:
            customer_options = [c['name'] for c in st.session_state.customers]
            customer = searchable_selectbox("Customer*", customer_options, key="quotation_customer", help_text="Select existing customer or add new one in Customers tab")
        else:
            st.warning("⚠️ No customers found. Please add customers first in the Customers tab.")
            customer = st.text_input("Customer* (Manual Entry)", placeholder="e.g., Fast Logistics", key="quotation_customer_manual")
        
        quotation_date = st.date_input("Date*", value=datetime.datetime.now().date(), key="quotation_date")
        vehicle_type = st.selectbox("Vehicle Type*", ["7ft", "8ft", "12ft", "14ft", "17ft", "20ft", "24ft", "32ft"], key="quotation_vehicle_type")
    
    with col2:
        pickup_location = st.text_input("Pick up*", placeholder="e.g., Mepz", key="quotation_pickup")
        destination = st.text_input("Destination*", placeholder="e.g., Airport", key="quotation_destination")
    
    # Pricing lookup section
    st.markdown("**💰 PRICING**")
    col_price1, col_price2 = st.columns([3, 1])
    
    with col_price1:
        # Initialize pricing in session state
        if 'quotation_suggested_rate' not in st.session_state:
            st.session_state.quotation_suggested_rate = None
        
        # Display pricing if available
        if st.session_state.quotation_suggested_rate:
            pricing_info = st.session_state.quotation_suggested_rate
            st.info(f"💰 **Suggested Rate: ₹ {pricing_info['rate']:,.2f}**\n\n"
                   f"📍 Route: {pricing_info.get('origin', pickup_location)} → {pricing_info.get('destination', destination)}\n\n"
                   f"🚛 Vehicle: {pricing_info.get('vehicle_type', vehicle_type)}\n\n"
                   f"📊 Source: {pricing_info.get('source', 'Unknown')}")
            if pricing_info.get('halting_charge') and pricing_info.get('halting_charge') > 0:
                st.caption(f"⏱️ Halting Charge: ₹ {pricing_info['halting_charge']:,.2f}")
            if pricing_info.get('unloading_free_time'):
                st.caption(f"📦 {pricing_info['unloading_free_time']}")
    
    with col_price2:
        if st.button("🔍 Find Price", key="quotation_find_price", help="Search for pricing based on customer, route, and vehicle"):
            if customer and pickup_location and destination and vehicle_type:
                # Search for customer
                customers = search_customer_by_name(customer)
                customer_id = customers[0]['id'] if customers else None
                
                # Get pricing
                pricing = get_pricing_for_customer(
                    customer_id,
                    customer,
                    pickup_location,
                    destination,
                    vehicle_type
                )
                
                if pricing:
                    st.session_state.quotation_suggested_rate = pricing
                    st.rerun()
                else:
                    st.warning("⚠️ No pricing found for this combination")
                    st.session_state.quotation_suggested_rate = None
            else:
                st.error("❌ Please fill customer, pickup, destination, and vehicle type first")
    
    # Price input field
    price_col1, price_col2, price_col3 = st.columns([2, 1, 1])
    
    with price_col1:
        price = st.number_input(
            "Price* (₹)",
            min_value=0.0,
            step=100.0,
            value=float(st.session_state.quotation_suggested_rate['rate']) if st.session_state.quotation_suggested_rate else 0.0,
            key="quotation_price",
            help="Enter the quotation price"
        )
    
    with price_col2:
        if st.session_state.quotation_suggested_rate:
            st.caption(f"📊 Suggested: ₹{st.session_state.quotation_suggested_rate['rate']:,.0f}")
    
    with price_col3:
        if price > 0 and st.session_state.quotation_suggested_rate:
            diff = price - st.session_state.quotation_suggested_rate['rate']
            diff_pct = (diff / st.session_state.quotation_suggested_rate['rate']) * 100 if st.session_state.quotation_suggested_rate['rate'] > 0 else 0
            color = "🟢" if diff == 0 else ("🔴" if diff < 0 else "🟡")
            st.caption(f"{color} {diff:+.0f} ({diff_pct:+.0f}%)")
    
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
            selected_vehicle = searchable_selectbox("Vehicle Reg No", vehicle_options, key="quotation_vehicle")
            vehicle_reg_no = selected_vehicle if selected_vehicle != "None" else ""
            
            # Get driver info for selected vehicle
            selected_vehicle_data = next((v for v in st.session_state.vehicles if v['registration_number'] == selected_vehicle), None) if selected_vehicle != "None" else None
            linked_driver_name = selected_vehicle_data.get('linked_driver') if selected_vehicle_data else ""
        else:
            st.warning("No vehicles found. Please add vehicles in Vehicle Master.")
            vehicle_reg_no = st.text_input("Vehicle Reg No", placeholder="e.g., TN1XXXXXX", key="quotation_reg_no_manual")
            linked_driver_name = ""
        
        # Driver selection
        if hasattr(st.session_state, 'drivers') and st.session_state.drivers:
            driver_options = ["None"] + [d['name'] for d in st.session_state.drivers if d.get('status') in ['Available', 'On Trip']]
            # Pre-select linked driver if vehicle has one
            default_driver_index = 0
            if linked_driver_name and linked_driver_name in driver_options:
                default_driver_index = driver_options.index(linked_driver_name)
            
            selected_driver = searchable_selectbox("Driver", driver_options, default_index=default_driver_index, key="quotation_driver_select")
            driver = selected_driver if selected_driver != "None" else ""
            
            # Get driver phone for selected driver
            selected_driver_data = next((d for d in st.session_state.drivers if d['name'] == selected_driver), None) if selected_driver != "None" else None
            driver_phone_from_master = selected_driver_data.get('phone', '') if selected_driver_data else ''
        else:
            driver = st.text_input("Driver", placeholder="e.g., Nithish", key="quotation_driver_manual")
            driver_phone_from_master = ""
    
    with col2:
        # Driver phone - dynamically update based on selected driver
        current_driver = st.session_state.get('quotation_driver_select', 'None')
        
        # Check if driver selection has changed and update phone accordingly
        if current_driver != "None" and hasattr(st.session_state, 'drivers') and st.session_state.drivers:
            selected_driver_data = next((d for d in st.session_state.drivers if d['name'] == current_driver), None)
            if selected_driver_data:
                # Update the phone number in session state when driver changes
                new_phone = selected_driver_data.get('phone', '')
                if f'last_quotation_driver' not in st.session_state or st.session_state[f'last_quotation_driver'] != current_driver:
                    st.session_state['quotation_driver_phone'] = new_phone
                    st.session_state[f'last_quotation_driver'] = current_driver
        
        driver_phone = st.text_input("Driver Phone", placeholder="e.g., 7339X XXXXX", key="quotation_driver_phone")
        status = st.selectbox("Status", ["CREATED", "APPROVED", "REJECTED", "CONVERTED"], 
                             index=0, key="quotation_status")  # Default to CREATED
    
    # Submit button
    if st.button("💾 Create Quotation", type="primary", width="stretch"):
        # Validation
        if not customer or not quotation_date or not vehicle_type or not pickup_location or not destination:
            st.error("❌ Please fill all required fields marked with *")
            return
        
        # Validate driver phone if provided
        if driver_phone and not validate_mobile_number(driver_phone):
            st.error("❌ Driver phone must be a valid 10-digit number (starting with 6-9)")
            return
        
        # Create quotation data
        quotation_data = {
            'id': str(uuid.uuid4()),
            'quotation_number': quotation_number,
            'customer': customer,
            'quotation_date': quotation_date,
            'vehicle_type': vehicle_type,
            'route_from': pickup_location,
            'route_to': destination,
            'base_price': price,
            'total_amount': price,
            'vehicle_reg_no': vehicle_reg_no,
            'driver': driver,
            'driver_phone': driver_phone,
            'status': status,
            'created_date': datetime.datetime.now(),
            'last_modified': datetime.datetime.now()
        }
        
        # Save to database
        from app import save_simplified_quotation
        try:
            if save_simplified_quotation(quotation_data):
                # Add to session state for immediate display
                if 'quotations' not in st.session_state:
                    st.session_state.quotations = []
                st.session_state.quotations.insert(0, quotation_data)  # Add at top
                
                # Add note for quotation creation
                from .notes import add_status_note
                add_status_note(
                    record_id=quotation_data['id'],
                    record_type='quotation',
                    old_status=None,
                    new_status='CREATED',
                    changed_by=st.session_state.get('user', 'System'),
                    notes=f"Quotation created - {quotation_data['customer']}",
                    additional_data={
                        'quotation_number': quotation_number,
                        'customer': quotation_data['customer'],
                        'pickup': quotation_data.get('route_from', ''),
                        'destination': quotation_data.get('route_to', '')
                    }
                )
                
                # Clear form
                for key in ['quotation_customer', 'quotation_pickup', 'quotation_destination', 
                           'quotation_vehicle', 'quotation_driver_select', 'quotation_driver_phone']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                # Show success
                st.session_state['show_quotation_success_page'] = True
                st.session_state['quotation_success_data'] = {
                    'title': 'Quotation Created Successfully!',
                    'message': f"Quotation {quotation_number} has been created successfully!",
                    'created_item_number': quotation_number,
                    'module_name': 'quotations'
                }
                st.rerun()
            else:
                st.error("❌ Failed to save quotation. Please try again.")
        except Exception as e:
            st.error(f"❌ Error creating quotation: {str(e)}")


def view_quotations():
    """View and manage existing quotations"""
    
    # Check if we're in edit mode
    if st.session_state.get('editing_quotation_id'):
        if not st.session_state.get('editing_quotation_mode'):
            del st.session_state['editing_quotation_id']
        else:
            edit_quotation()
            return
    
    # Always reload quotations to ensure we have latest data
    from database import get_cached_data
    st.session_state.quotations = get_cached_data('quotations', limit=None)
    
    st.subheader("View Quotations")
    
    if not st.session_state.quotations:
        st.info("No quotations found. Create your first quotation in the 'Create Quotation' tab.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "CREATED", "APPROVED", "REJECTED", "CONVERTED"],
            key="quotation_status_filter"
        )
    
    with col2:
        customer_filter = st.selectbox(
            "Filter by Customer",
            ["All"] + [q['customer'] for q in st.session_state.quotations if 'customer' in q],
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
        filtered_quotations = [q for q in filtered_quotations if q.get('status') == status_filter]
    
    if customer_filter != "All":
        filtered_quotations = [q for q in filtered_quotations if q.get('customer') == customer_filter]
    
    # Handle date filtering with safe date conversion
    filtered_quotations = [q for q in filtered_quotations if safe_get_date(q.get('created_date', datetime.datetime.now())) >= date_filter]
    
    # Display quotations
    for quotation in filtered_quotations:
        # Create route display from route_from and route_to
        route_display = f"{quotation.get('route_from', 'N/A')} → {quotation.get('route_to', 'N/A')}"
        
        with st.expander(f"Quotation {quotation['quotation_number']} - {quotation.get('customer', 'N/A')} - {quotation.get('status', 'N/A')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Customer:** {quotation.get('customer', 'N/A')}")
                st.write(f"**Route:** {route_display}")
                st.write(f"**Vehicle Type:** {quotation.get('vehicle_type', 'N/A')}")
                quotation_price_value = None
                for price_key in ['base_price', 'price', 'total_amount', 'amount', 'rate']:
                    if quotation.get(price_key) not in [None, '']:
                        quotation_price_value = quotation.get(price_key)
                        break
                if quotation_price_value is not None:
                    try:
                        st.write(f"**Price:** ₹ {float(quotation_price_value):,.2f}")
                    except (TypeError, ValueError):
                        st.write(f"**Price:** {quotation_price_value}")
                else:
                    st.write("**Price:** N/A")
                st.write(f"**Vehicle Reg No:** {quotation.get('vehicle_reg_no', 'N/A')}")
                st.write(f"**Driver:** {quotation.get('driver', 'N/A')}")
            
            with col2:
                st.write(f"**Status:** {quotation.get('status', 'N/A')}")
                st.write(f"**Driver Phone:** {quotation.get('driver_phone', 'N/A')}")
                st.write(f"**Date:** {safe_format_date(quotation.get('quotation_date', datetime.date.today()))}")
                st.write(f"**Created:** {safe_format_date(quotation.get('created_date', datetime.datetime.now()))}")
            
            # Copy to clipboard button
            st.markdown("---")
            from .utils import format_quotation_details
            quotation_text = format_quotation_details(quotation)
            
            col_copy1, col_copy2 = st.columns([1, 3])
            with col_copy1:
                if st.session_state.get(f"show_copy_{quotation.get('id')}", False):
                    if st.button("🙈 Hide", key=f"hide_btn_{quotation.get('id')}", help="Hide text"):
                        st.session_state[f"show_copy_{quotation.get('id')}"] = False
                        st.rerun()
                else:
                    if st.button("📋 Copy", key=f"copy_btn_{quotation.get('id')}", help="Click to copy text"):
                        st.session_state[f"show_copy_{quotation.get('id')}"] = True
                        st.rerun()
            with col_copy2:
                copy_placeholder = st.empty()
            
            if st.session_state.get(f"show_copy_{quotation.get('id')}", False):
                with copy_placeholder.container():
                    st.code(quotation_text, language="text")
                    st.success("✅ Select and copy the text above!")
                        
            # Action buttons - adjust based on quotation status
            st.markdown("---")
            if quotation.get('status') in ['CREATED', 'APPROVED']:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"✏️ Edit", key=f"edit_{quotation['id']}"):
                        st.session_state.editing_quotation_id = quotation['id']
                        st.session_state.editing_quotation_mode = True
                        st.rerun()
                
                with col2:
                    if quotation.get('status') == 'CREATED' and st.button(f"✅ Approve", key=f"approve_{quotation['id']}"):
                        if update_quotation_status(quotation['id'], 'APPROVED'):
                            st.success("Quotation approved successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to approve quotation. Please try again.")
                
                with col3:
                    if quotation.get('status') == 'CREATED' and st.button(f"❌ Reject", key=f"reject_{quotation['id']}"):
                        if update_quotation_status(quotation['id'], 'REJECTED'):
                            st.warning("Quotation rejected.")
                            st.rerun()
                        else:
                            st.error("Failed to reject quotation. Please try again.")
                            
            elif quotation.get('status') == 'APPROVED':
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"📦 Create Booking", key=f"booking_{quotation['id']}"):
                        st.session_state.selected_quotation_id = quotation['id']
                        st.session_state.current_page = "Bookings"
                        st.rerun()
                
                with col2:
                    if st.button(f"✏️ Revise", key=f"revise_{quotation['id']}", help="Create a revised version of this quotation"):
                        st.session_state.editing_quotation_id = quotation['id']
                        st.session_state.editing_quotation_mode = True
                        st.session_state.revise_mode = True
                        st.rerun()
                
                with col3:
                    if st.button(f"📋 Convert to Booking", key=f"convert_{quotation['id']}"):
                        if update_quotation_status(quotation['id'], 'CONVERTED'):
                            st.success("Quotation converted!")
                            st.rerun()
                        else:
                            st.error("Failed to convert quotation. Please try again.")
    
    # Export option
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

def edit_quotation():
    """Edit an existing quotation"""
    quotation_id = st.session_state.get('editing_quotation_id')
    
    # Get the quotation to edit
    from database import get_cached_data
    quotations = get_cached_data('quotations', limit=None)
    quotation = next((q for q in quotations if q['id'] == quotation_id), None)
    
    if not quotation:
        st.error("Quotation not found!")
        if st.button("Back to Quotations"):
            del st.session_state['editing_quotation_id']
            if 'editing_quotation_mode' in st.session_state:
                del st.session_state['editing_quotation_mode']
            st.rerun()
        return
    
    st.subheader(f"Edit Quotation - {quotation['quotation_number']}")
    
    # Simple quotation edit form
    st.markdown("**📋 QUOTATION DETAILS**")
    col1, col2 = st.columns(2)
    
    with col1:
        from database import load_data_when_needed
        load_data_when_needed('customers')
        
        if hasattr(st.session_state, 'customers') and st.session_state.customers:
            customer_options = [c['name'] for c in st.session_state.customers]
            customer = st.selectbox("Customer*", customer_options, 
                                  index=customer_options.index(quotation.get('customer', '')) if quotation.get('customer') in customer_options else 0,
                                  key="edit_quotation_customer")
        else:
            customer = st.text_input("Customer*", value=quotation.get('customer', ''), key="edit_quotation_customer")
        
        pickup_location = st.text_input("Pickup Location*", value=quotation.get('route_from', ''), key="edit_quotation_pickup")
        vehicle_type_options = ["7ft", "8ft", "12ft", "14ft", "17ft", "20ft", "24ft", "32ft"]
        vehicle_type = st.selectbox("Vehicle Type*", 
                                   vehicle_type_options,
                                   index=vehicle_type_options.index(quotation.get('vehicle_type', '7ft')) if quotation.get('vehicle_type') in vehicle_type_options else 0,
                                   key="edit_quotation_vehicle")
    
    with col2:
        destination = st.text_input("Destination*", value=quotation.get('route_to', ''), key="edit_quotation_destination")
        
        # Driver selection
        load_data_when_needed('drivers')
        drivers = st.session_state.get('drivers', [])
        if drivers:
            driver_names = [d['name'] for d in drivers]
            driver = st.selectbox("Driver*", driver_names,
                                index=driver_names.index(quotation.get('driver', '')) if quotation.get('driver') in driver_names else 0,
                                key="edit_quotation_driver_select")
            
            # Get driver phone
            selected_driver = next((d for d in drivers if d['name'] == driver), None)
            driver_phone = st.text_input("Driver Phone", 
                                       value=quotation.get('driver_phone', selected_driver.get('phone', '') if selected_driver else ''),
                                       key="edit_quotation_driver_phone",
                                       disabled=True)
        else:
            driver = st.text_input("Driver", value=quotation.get('driver', ''), key="edit_quotation_driver")
            driver_phone = st.text_input("Driver Phone", value=quotation.get('driver_phone', ''), key="edit_quotation_driver_phone")
        
        vehicle_reg_no = st.text_input("Vehicle Reg No.", value=quotation.get('vehicle_reg_no', ''), key="edit_quotation_vehicle_reg")
    
    # Buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Changes", type="primary"):
            # Validation
            if not all([customer, pickup_location, destination, vehicle_type, driver, driver_phone]):
                st.error("❌ Please fill all required fields marked with *")
                return
            
            # Prepare update data
            updated_quotation = {
                'customer': customer,
                'route_from': pickup_location,
                'route_to': destination,
                'vehicle_type': vehicle_type,
                'driver': driver,
                'driver_phone': driver_phone,
                'vehicle_reg_no': vehicle_reg_no,
                'last_modified': datetime.datetime.now()
            }
            
            # Update in database
            from app import update_simplified_quotation
            try:
                if update_simplified_quotation(quotation_id, updated_quotation):
                    st.success("✅ Quotation updated successfully!")
                    
                    # Add note for quotation update
                    from .notes import add_status_note
                    add_status_note(
                        record_id=quotation_id,
                        record_type='quotation',
                        old_status=quotation.get('status'),
                        new_status=quotation.get('status'),
                        changed_by=st.session_state.get('user', 'System'),
                        notes=f"Quotation updated - {customer}",
                        additional_data={
                            'quotation_number': quotation['quotation_number'],
                            'customer': customer,
                            'pickup': pickup_location,
                            'destination': destination
                        }
                    )
                    
                    # Clear edit mode and rerun
                    del st.session_state['editing_quotation_id']
                    if 'editing_quotation_mode' in st.session_state:
                        del st.session_state['editing_quotation_mode']
                    st.rerun()
                else:
                    st.error("❌ Failed to update quotation. Please try again.")
            except Exception as e:
                st.error(f"❌ Error updating quotation: {str(e)}")
    
    with col2:
        if st.button("❌ Cancel", key="edit_cancel"):
            # Add note for edit cancellation
            from .notes import add_status_note
            add_status_note(
                record_id=quotation_id,
                record_type='quotation',
                old_status=quotation.get('status'),
                new_status=quotation.get('status'),
                changed_by=st.session_state.get('user', 'System'),
                notes=f"Edit cancelled for quotation {quotation['quotation_number']}"
            )
            del st.session_state['editing_quotation_id']
            if 'editing_quotation_mode' in st.session_state:
                del st.session_state['editing_quotation_mode']
            st.rerun()
    
    with col3:
        if st.button("🗑️ Delete", key="edit_delete"):
            # Delete quotation
            from database import execute_query
            try:
                execute_query(f"DELETE FROM quotations WHERE id = %s", (quotation_id,))
                st.success("Quotation deleted successfully!")
                
                # Add note for quotation deletion
                from .notes import add_status_note
                add_status_note(
                    record_id=quotation_id,
                    record_type='quotation',
                    old_status=quotation.get('status'),
                    new_status='DELETED',
                    changed_by=st.session_state.get('user', 'System'),
                    notes=f"Quotation deleted - {quotation['quotation_number']}"
                )
                
                del st.session_state['editing_quotation_id']
                if 'editing_quotation_mode' in st.session_state:
                    del st.session_state['editing_quotation_mode']
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting quotation: {str(e)}")

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
    """Generate PDF for quotation in S TRANZ format (same as invoice)"""
    
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
    
    quotation_title_style = ParagraphStyle(
        'QuotationTitle',
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
    
    # Header with company info (same as invoice)
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
            # Quotation title
            Paragraph('<font size="24"><b>QUOTATION</b></font>', quotation_title_style)
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
    
    # Tax line (same as invoice)
    tax_line = Paragraph('<b>TAX PAYABLE ON REVERSE CHARGE: YES</b>', ParagraphStyle(
        'TaxLine', parent=styles['Normal'], fontSize=15, fontName='Helvetica-Bold', alignment=1))
    elements.append(tax_line)
    elements.append(Spacer(1, 12))
    
    # Quotation details and customer info section (matching invoice style)
    customer = next((c for c in st.session_state.customers if c['name'] == quotation['customer_name']), None)
    
    info_data = [
        [
            # Left column - Customer info
            Paragraph(f"""<b>QUOTATION TO:</b><br/>
            {quotation['customer_name']}<br/>
            {customer.get('address', 'N/A') if customer else 'N/A'}""", section_style),
            # Right column - Quotation details
            Paragraph(f"""<b>QUOTATION NO:</b>&nbsp;&nbsp;&nbsp;&nbsp;{quotation['quotation_number']}<br/>
            <b>QUOTATION DATE:</b>&nbsp;&nbsp;&nbsp;&nbsp;{safe_format_date(quotation['created_date'])}<br/>
            <b>VALID UNTIL:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{safe_format_date(quotation['valid_until']) if quotation.get('valid_until') else 'N/A'}<br/>
            <b>VEHICLE TYPE:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{quotation['vehicle_type']}<br/>
            <b>TRIP TYPE:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{quotation['trip_type']}""", section_style)
        ]
    ]
    
    # Add route details
    route_data = [
        [
            Paragraph(f"""<b>ROUTE DETAILS:</b><br/>
            From: {quotation['pickup_location']}<br/>
            To: {quotation['delivery_location']}<br/>
            Distance: {quotation['distance_km']} KM""", section_style),
            Paragraph(f"""<b>LOAD DETAILS:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{quotation.get('material_type', 'GENERAL CARGO')}<br/>
            <b>WEIGHT CAPACITY:</b>&nbsp;&nbsp;&nbsp;{quotation['weight_capacity']} {quotation.get('weight_unit', 'tons')}<br/>
            <b>PAYMENT TERMS:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{quotation['payment_terms']} days<br/>
            <b>REFERENCE NO:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{quotation.get('reference_number', 'N/A')}""", section_style)
        ]
    ]
    
    info_table = Table(info_data + route_data, colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Description section
    desc_text = f"Route: {quotation['pickup_location']} to {quotation['delivery_location']}, Vehicle: {quotation['vehicle_type']}, Distance: {quotation['distance_km']} KM"
    if quotation.get('special_instructions'):
        desc_text += f", Instructions: {quotation['special_instructions']}"
    
    description = Paragraph(f"<b>DESCRIPTION:</b><br/>{desc_text}", section_style)
    elements.append(description)
    elements.append(Spacer(1, 15))
    
    # Charges table in S TRANZ format (matching invoice)
    charges_data = [
        ['CHARGES', 'QTY', 'RATE', 'AMOUNT']
    ]
    
    # Transportation charges section
    charges_data.append(['TRANSPORTATION CHARGES:', '', '', ''])
    charges_data.append(['- Transportation Service', '1', f"{safe_float(quotation.get('base_price')):.2f}", f"{safe_float(quotation.get('base_price')):.2f}"])
    
    # Additional charges
    if quotation.get('loading_charges', 0) > 0:
        charges_data.append([f'- Loading Charges', '1', f"{safe_float(quotation.get('loading_charges')):.2f}", f"{safe_float(quotation.get('loading_charges')):.2f}"])
    if quotation.get('unloading_charges', 0) > 0:
        charges_data.append([f'- Unloading Charges', '1', f"{safe_float(quotation.get('unloading_charges')):.2f}", f"{safe_float(quotation.get('unloading_charges')):.2f}"])
    if quotation.get('fuel_surcharge', 0) > 0:
        charges_data.append([f'- Fuel Surcharge', '1', f"{safe_float(quotation.get('fuel_surcharge')):.2f}", f"{safe_float(quotation.get('fuel_surcharge')):.2f}"])
    if quotation.get('toll_charges', 0) > 0:
        charges_data.append([f'- Toll Charges', '1', f"{safe_float(quotation.get('toll_charges')):.2f}", f"{safe_float(quotation.get('toll_charges')):.2f}"])
    if quotation.get('airport_pass_charges', 0) > 0:
        charges_data.append([f'- Airport Pass', '1', f"{safe_float(quotation.get('airport_pass_charges')):.2f}", f"{safe_float(quotation.get('airport_pass_charges')):.2f}"])
    if quotation.get('halting_charges', 0) > 0:
        charges_data.append([f'- Halting Charges', '1', f"{safe_float(quotation.get('halting_charges')):.2f}", f"{safe_float(quotation.get('halting_charges')):.2f}"])
    if quotation.get('other_charges', 0) > 0:
        charges_data.append([f'- Other Charges', '1', f"{safe_float(quotation.get('other_charges')):.2f}", f"{safe_float(quotation.get('other_charges')):.2f}"])
    if quotation.get('discount', 0) > 0:
        charges_data.append([f'- Discount', '1', f"-{safe_float(quotation.get('discount')):.2f}", f"-{safe_float(quotation.get('discount')):.2f}"])
    
    # Calculate subtotal and total with GST
    subtotal = safe_float(quotation.get('subtotal', 0))
    charges_data.append(['', '', 'SUBTOTAL:', f"{subtotal:.2f}"])
    
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
    
    elements.append(charges_table)
    elements.append(Spacer(1, 15))
    
    # Amount summary section (matching invoice format)
    gst_rate = 0.18  # 18% GST
    gst_amount = subtotal * gst_rate
    total_with_gst = subtotal + gst_amount
    
    # Convert amount to words (reuse from invoicing)
    from .invoicing import convert_amount_to_words
    amount_words = convert_amount_to_words(total_with_gst)
    
    summary_data = [
        ['AMOUNT IN WORDS:', 'SUBTOTAL:', f"{subtotal:.2f}"],
        [Paragraph(amount_words, ParagraphStyle('AmountWords', parent=styles['Normal'], fontSize=14, fontName='Helvetica')), 'GST (18%):', f"{gst_amount:.2f}"],
        ['', 'TOTAL AMOUNT:', f"{total_with_gst:.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[3.5*inch, 1.5*inch, 1.2*inch], rowHeights=[None, 25, None])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (0, 1), (0, 1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (1, 0), (-1, 0), 1, colors.black),  # Line under headers
        ('LINEBELOW', (1, -1), (-1, -1), 2, colors.black),  # Double line under total
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Bank details section (same as invoice)
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
    elements.append(Spacer(1, 15))
    
    # Terms and conditions
    terms = Paragraph("""
    <b>Terms and Conditions:</b><br/>
    1. This quotation is valid for 30 days from the date of issue.<br/>
    2. All charges are subject to change without prior notice.<br/>
    3. Payment terms are as mentioned above.<br/>
    4. Goods once dispatched will not be taken back.<br/>
    5. Risk and insurance of goods in transit is to customer account.<br/>
    6. GST will be charged as applicable at the time of service.
    """, ParagraphStyle('Terms', parent=styles['Normal'], fontSize=14, fontName='Helvetica'))
    elements.append(terms)
    elements.append(Spacer(1, 10))
    
    # Footer (same as invoice)
    footer = Paragraph("""
    <para align="center">
    THANKS FOR YOUR INTEREST. LOOKING FORWARD TO SERVING YOU<br/>
    <i>(This quotation has been generated by our system and is valid without a physical signature)</i>
    </para>
    """, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=14, alignment=1))
    
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data