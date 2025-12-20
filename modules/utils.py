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
    return re.match(r'^[6-9]\d{9}$', phone) is not None