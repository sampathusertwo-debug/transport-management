"""
Pricing Helper Utilities
Helper functions to easily integrate pricing lookup into other modules
"""
from modules.customer_pricing import (
    get_pricing_for_customer,
    search_customer_by_name
)
import streamlit as st

def get_pricing_widget(customer_name, origin, destination, vehicle_type):
    """
    Display a pricing widget that shows the pricing for the given parameters
    
    Args:
        customer_name: Name of the customer
        origin: Origin location
        destination: Destination location
        vehicle_type: Type of vehicle
    
    Returns:
        dict with pricing info or None
    """
    if not all([customer_name, origin, destination, vehicle_type]):
        return None
    
    # Search for customer
    customers = search_customer_by_name(customer_name)
    
    customer_id = None
    if customers and len(customers) > 0:
        customer_id = customers[0]['id']
    
    # Get pricing
    pricing = get_pricing_for_customer(
        customer_id,
        customer_name,
        origin,
        destination,
        vehicle_type
    )
    
    if pricing:
        # Display pricing in a nice format
        with st.container():
            st.markdown("### Suggested Pricing")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.info(f"""
                **Source:** {pricing.get('source', 'Unknown')}
                
                **Route:** {pricing.get('origin', origin)} → {pricing.get('destination', destination)}
                
                **Vehicle:** {pricing.get('vehicle_type', vehicle_type)}
                """)
            
            with col2:
                st.metric("Rate", f"₹ {pricing['rate']:,.2f}")
                
                if pricing.get('halting_charge') and pricing.get('halting_charge') > 0:
                    st.metric("Halting", f"₹ {pricing['halting_charge']:,.2f}")
    
    return pricing


def get_pricing_for_quotation(customer_name, origin, destination, vehicle_type):
    """
    Get pricing for use in quotation module
    Returns just the rate value
    """
    if not all([customer_name, origin, destination, vehicle_type]):
        return None
    
    # Search for customer
    customers = search_customer_by_name(customer_name)
    
    customer_id = None
    if customers and len(customers) > 0:
        customer_id = customers[0]['id']
    
    # Get pricing
    pricing = get_pricing_for_customer(
        customer_id,
        customer_name,
        origin,
        destination,
        vehicle_type
    )
    
    if pricing:
        return pricing['rate']
    
    return None


def show_inline_pricing(customer_name, origin, destination, vehicle_type):
    """
    Show pricing inline as a small info box (for bookings/quotations forms)
    """
    if not all([customer_name, origin, destination, vehicle_type]):
        return None
    
    # Search for customer
    customers = search_customer_by_name(customer_name)
    
    customer_id = None
    if customers and len(customers) > 0:
        customer_id = customers[0]['id']
    
    # Get pricing
    pricing = get_pricing_for_customer(
        customer_id,
        customer_name,
        origin,
        destination,
        vehicle_type
    )
    
    if pricing:
        st.info(f"Suggested Rate: **₹ {pricing['rate']:,.2f}** ({pricing.get('source', 'Unknown')})")
        return pricing['rate']
    else:
        st.warning("No pricing found for this combination")
        return None
