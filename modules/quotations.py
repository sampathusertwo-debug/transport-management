import streamlit as st
import pandas as pd
import datetime
import uuid
from typing import Dict, List

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
    
    # Customer selection/creation
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get existing customers
        existing_customers = [customer['name'] for customer in st.session_state.customers]
        
        if existing_customers:
            customer_choice = st.selectbox(
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
            customer_phone = st.text_input("Phone*", key="new_customer_phone")
        
        with col2:
            customer_address = st.text_area("Address", key="new_customer_address")
            customer_gst = st.text_input("GST Number", key="new_customer_gst")
            customer_pan = st.text_input("PAN Number", key="new_customer_pan")
    else:
        # Get existing customer details
        customer_data = next((c for c in st.session_state.customers if c['name'] == customer_choice), None)
        if customer_data:
            st.info(f"Customer: {customer_data['name']} | Phone: {customer_data['phone']} | Email: {customer_data.get('email', 'N/A')}")
    
    st.markdown("---")
    
    # Quotation details
    st.markdown("**Quotation Details**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pickup_location = st.text_input("Pickup Location*", key="quotation_pickup")
        delivery_location = st.text_input("Delivery Location*", key="quotation_delivery")
        vehicle_type = st.selectbox(
            "Vehicle Type",
            ["Mini Truck", "Small Truck", "Medium Truck", "Large Truck", "Container", "Trailer"],
            key="quotation_vehicle_type"
        )
    
    with col2:
        distance_km = st.number_input("Distance (KM)", min_value=0.0, value=0.0, key="quotation_distance")
        weight_capacity = st.number_input("Weight Capacity (Tons)", min_value=0.0, value=1.0, key="quotation_weight")
        trip_type = st.selectbox(
            "Trip Type",
            ["Local", "Long Distance", "Contract"],
            key="quotation_trip_type"
        )
    
    with col3:
        base_price = st.number_input("Base Price (₹)*", min_value=0.0, value=0.0, key="quotation_base_price")
        gst_applicable = st.checkbox("GST Applicable", value=True, key="quotation_gst")
        payment_terms = st.selectbox(
            "Payment Terms (Days)*",
            [30, 45, 60, 90],
            key="quotation_payment_terms"
        )
    
    # Additional charges
    st.markdown("**Additional Charges**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fuel_surcharge = st.number_input("Fuel Surcharge (₹)", min_value=0.0, value=0.0, key="quotation_fuel")
        toll_charges = st.number_input("Toll Charges (₹)", min_value=0.0, value=0.0, key="quotation_toll")
    
    with col2:
        loading_charges = st.number_input("Loading Charges (₹)", min_value=0.0, value=0.0, key="quotation_loading")
        unloading_charges = st.number_input("Unloading Charges (₹)", min_value=0.0, value=0.0, key="quotation_unloading")
    
    with col3:
        other_charges = st.number_input("Other Charges (₹)", min_value=0.0, value=0.0, key="quotation_other")
        discount = st.number_input("Discount (₹)", min_value=0.0, value=0.0, key="quotation_discount")
    
    # Calculate total
    subtotal = base_price + fuel_surcharge + toll_charges + loading_charges + unloading_charges + other_charges - discount
    
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
            st.session_state.customers.append(new_customer)
        else:
            customer_data = next((c for c in st.session_state.customers if c['name'] == customer_choice), None)
            customer_id = customer_data['id']
            # Update payment terms for existing customer
            customer_data['payment_terms'] = payment_terms
        
        # Generate quotation number
        from app import generate_quotation_number
        quotation_number = generate_quotation_number()
        
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
            'trip_type': trip_type,
            'base_price': base_price,
            'fuel_surcharge': fuel_surcharge,
            'toll_charges': toll_charges,
            'loading_charges': loading_charges,
            'unloading_charges': unloading_charges,
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
        
        st.session_state.quotations.append(quotation)
        st.success(f"Quotation {quotation_number} created successfully!")
        
        # Clear form
        for key in st.session_state.keys():
            if key.startswith('quotation_') or key.startswith('new_customer_'):
                del st.session_state[key]
        
        st.rerun()

def view_quotations():
    """View and manage existing quotations"""
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
    
    filtered_quotations = [q for q in filtered_quotations if q['created_date'].date() >= date_filter]
    
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
                st.write(f"**Created:** {quotation['created_date'].strftime('%Y-%m-%d')}")
                st.write(f"**GST:** {'Yes' if quotation['gst_applicable'] else 'No'}")
            
            # Action buttons
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button(f"Approve", key=f"approve_{quotation['id']}"):
                    quotation['status'] = 'Approved'
                    st.success("Quotation approved!")
                    st.rerun()
            
            with col2:
                if st.button(f"Reject", key=f"reject_{quotation['id']}"):
                    quotation['status'] = 'Rejected'
                    st.error("Quotation rejected!")
                    st.rerun()
            
            with col3:
                if quotation['status'] == 'Approved':
                    if st.button(f"Create Booking", key=f"book_{quotation['id']}"):
                        # Store quotation ID for booking creation
                        st.session_state.selected_quotation_id = quotation['id']
                        st.success("Navigate to Bookings to create booking from this quotation!")
            
            with col4:
                if st.button(f"Delete", key=f"delete_{quotation['id']}"):
                    st.session_state.quotations = [q for q in st.session_state.quotations if q['id'] != quotation['id']]
                    st.success("Quotation deleted!")
                    st.rerun()
    
    # Export options
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
    
    # Display customers in a table
    customers_data = []
    for customer in st.session_state.customers:
        customers_data.append({
            'Name': customer['name'],
            'Phone': customer['phone'],
            'Email': customer.get('email', ''),
            'GST Number': customer.get('gst_number', ''),
            'Payment Terms': f"{customer.get('payment_terms', 30)} days",
            'Created Date': customer['created_date'].strftime('%Y-%m-%d')
        })
    
    df = pd.DataFrame(customers_data)
    st.dataframe(df, use_container_width=True)
    
    # Export customers
    if st.button("Export Customers to CSV"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"customers_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )