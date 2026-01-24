"""
Utility functions shared across all modules
"""
import streamlit as st

def searchable_selectbox(label, options, key=None, default_index=0, help_text=None):
    """Create a searchable selectbox for DATABASE-DRIVEN options (customers, vehicles, drivers, etc.)
    
    Args:
        label (str): The label for the selectbox
        options (list): List of options to choose from
        key (str, optional): Unique key for the widget
        default_index (int): Default selected index
        help_text (str, optional): Help text to display
    
    Returns:
        selected option
    """
    import streamlit as st
    
    # Create unique keys for this component
    search_key = f"{key}_search" if key else f"{label.lower().replace(' ', '_')}_search"
    select_key = f"{key}_select" if key else f"{label.lower().replace(' ', '_')}_select"
    
    # Search input
    search_term = st.text_input(
        f"🔍 Search {label}",
        key=search_key,
        help=help_text,
        placeholder=f"Type to filter {label.lower()}..."
    )
    
    # Filter options based on search term
    if search_term:
        # Convert all options to strings for searching
        filtered_options = [
            opt for opt in options 
            if search_term.lower() in str(opt).lower()
        ]
        
        if not filtered_options:
            st.warning(f"No matches found for '{search_term}'")
            filtered_options = options  # Show all if no matches
    else:
        filtered_options = options
    
    # Adjust default index for filtered options
    try:
        if default_index < len(filtered_options):
            selected_index = default_index
        else:
            selected_index = 0
    except:
        selected_index = 0
    
    # Show count of filtered options
    if search_term and len(filtered_options) != len(options):
        st.caption(f"Showing {len(filtered_options)} of {len(options)} options")
    
    # Selectbox with filtered options
    if filtered_options:
        selected = st.selectbox(
            label,
            filtered_options,
            index=selected_index,
            key=select_key
        )
    else:
        st.error("No options available")
        selected = options[default_index] if options else None
    
    return selected

def static_selectbox(label, options, key=None, default_index=0, help_text=None):
    """Create a regular selectbox for STATIC options (priorities, vehicle types, etc.)
    
    Args:
        label (str): The label for the selectbox
        options (list): List of static options to choose from
        key (str, optional): Unique key for the widget
        default_index (int): Default selected index
        help_text (str, optional): Help text to display
    
    Returns:
        selected option
    """
    import streamlit as st
    
    return st.selectbox(
        label,
        options,
        index=default_index,
        key=key,
        help=help_text
    )

def validate_mobile_number(phone):
    """Validate 10-digit mobile number"""
    import re
    if not phone:
        return True  # Empty is allowed
    # Remove any spaces or hyphens
    phone = re.sub(r'[\s\-]', '', phone)
    # Check if it's exactly 10 digits and starts with 6-9
    return re.match(r'^\d{10}$', phone) is not None


def format_booking_details(booking):
    """Format booking details as text for copying to clipboard"""
    details = []
    details.append("S TRANZ LOGISTICS")
    details.append("BOOKING CONFIRMATION\n")
    details.append("📋 BOOKING DETAILS")
    details.append(f"Booking No: {booking.get('booking_number', 'N/A')}")
    details.append(f"Customer: {booking.get('customer', 'N/A')}")
    details.append(f"Date: {booking.get('booking_date', 'N/A')}")
    details.append(f"Vehicle Type: {booking.get('vehicle_type', 'N/A')}")
    route_display = f"{booking.get('route_from', 'N/A')} → {booking.get('route_to', 'N/A')}"
    details.append(f"Route: {route_display}")
    details.append("\n🚛 VEHICLE & DRIVER DETAILS")
    details.append(f"Reg No: {booking.get('vehicle_reg_no', 'Not assigned')}")
    details.append(f"Driver: {booking.get('driver', 'Not assigned')}")
    details.append(f"Phone: {booking.get('driver_phone', 'Not provided')}")
    details.append(f"STATUS: {booking.get('status', 'CREATED')}")
    
    return "\n".join(details)


def format_quotation_details(quotation):
    """Format quotation details as text for copying to clipboard"""
    details = []
    details.append("S TRANZ LOGISTICS")
    details.append("BOOKING CONFIRMATION\n")
    details.append("📋 QUOTATION DETAILS")
    details.append(f"Quotation No: {quotation.get('quotation_number', 'N/A')}")
    details.append(f"Customer: {quotation.get('customer', 'N/A')}")
    details.append(f"Date: {quotation.get('quotation_date', 'N/A')}")
    details.append(f"Vehicle Type: {quotation.get('vehicle_type', 'N/A')}")
    route_display = f"{quotation.get('route_from', 'N/A')} → {quotation.get('route_to', 'N/A')}"
    details.append(f"Route: {route_display}")
    details.append("\n🚛 VEHICLE & DRIVER DETAILS")
    details.append(f"Reg No: {quotation.get('vehicle_reg_no', 'Not assigned')}")
    details.append(f"Driver: {quotation.get('driver', 'Not assigned')}")
    details.append(f"Phone: {quotation.get('driver_phone', 'Not provided')}")
    details.append(f"Status: {quotation.get('status', 'CREATED')}")
    
    return "\n".join(details)


def copy_to_clipboard_button(label, text_to_copy, key=None):
    """Create a button that copies text to clipboard
    
    Args:
        label (str): Button label
        text_to_copy (str): Text to copy to clipboard
        key (str, optional): Unique key for the button
    """
    import streamlit as st
    
    # JavaScript to copy to clipboard
    js_code = f"""
    <script>
    function copyToClipboard(text) {{
        navigator.clipboard.writeText(text).then(() => {{
            alert('Copied to clipboard!');
        }}).catch(err => {{
            console.error('Failed to copy: ', err);
        }});
    }}
    </script>
    """
    
    # Create a copy button using custom HTML + JavaScript
    button_html = f"""
    <button onclick="copyToClipboard(`{text_to_copy.replace(chr(96), chr(39)).replace(chr(10), '\\n')}`)" 
            style="padding: 10px 20px; background-color: #0078d4; color: white; border: none; 
                   border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 14px;">
        📋 {label}
    </button>
    """
    
    col1, col2 = st.columns([1, 10])
    with col1:
        # Use st.write with unsafe_allow_html for button
        if st.button(f"📋 {label}", key=key, use_container_width=True):
            # Store text in session for clipboard
            st.session_state[f'copy_text_{key}'] = text_to_copy
            st.success("✅ Copied to clipboard!")
    
    return