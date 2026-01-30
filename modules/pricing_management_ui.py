"""
Pricing Management UI
Interface for managing customer-specific and default pricing
"""
import streamlit as st
import pandas as pd
from modules.customer_pricing import (
    create_customer_pricing_tables, load_csv_pricing_data,
    get_pricing_for_customer, search_customer_by_name,
    add_customer_pricing, update_customer_pricing, delete_customer_pricing,
    get_all_customer_pricing, get_all_default_pricing,
    add_default_pricing, delete_default_pricing
)

def pricing_management_page():
    """
    Main pricing management interface
    """
    st.title("💰 Pricing Management")
    st.write("Manage customer-specific and default pricing matrices")
    
    # Initialize section
    with st.expander("🔧 System Setup", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("⚙️ Initialize Pricing Tables"):
                with st.spinner("Creating tables..."):
                    if create_customer_pricing_tables():
                        st.success("✅ Tables created successfully!")
        
        with col2:
            if st.button("📥 Load CSV Pricing Data"):
                with st.spinner("Loading pricing data from CSV files..."):
                    if load_csv_pricing_data():
                        st.balloons()
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "👤 Customer-Specific Pricing",
        "🌐 Default Pricing",
        "🔍 Pricing Lookup",
        "📊 View All Pricing"
    ])
    
    # Tab 1: Customer-Specific Pricing Management
    with tab1:
        manage_customer_pricing()
    
    # Tab 2: Default Pricing Management
    with tab2:
        manage_default_pricing()
    
    # Tab 3: Pricing Lookup
    with tab3:
        pricing_lookup_tool()
    
    # Tab 4: View All Pricing
    with tab4:
        view_all_pricing()


def manage_customer_pricing():
    """
    Interface for managing customer-specific pricing
    """
    st.header("👤 Customer-Specific Pricing Management")
    
    # Search for customer
    st.subheader("Select Customer")
    search_term = st.text_input(
        "Search Customer",
        placeholder="Enter customer name to search...",
        key="customer_search"
    )
    
    if search_term:
        customers = search_customer_by_name(search_term)
        
        if customers:
            customer_names = [f"{c['name']} ({c['email'] or 'No email'})" for c in customers]
            selected_customer_idx = st.selectbox(
                "Select Customer",
                range(len(customers)),
                format_func=lambda i: customer_names[i],
                key="selected_customer"
            )
            
            selected_customer = customers[selected_customer_idx]
            customer_id = selected_customer['id']
            customer_name = selected_customer['name']
            
            st.success(f"📌 Selected: **{customer_name}**")
            
            # Sub-tabs for customer pricing
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["➕ Add New", "✏️ Edit Existing", "🗑️ Delete"])
            
            # Add new pricing
            with sub_tab1:
                st.subheader("Add New Pricing Entry")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    origin = st.text_input("Origin Location", value="CHENNAI AIRPORT", key="add_origin")
                    destination = st.text_input("Destination Location", placeholder="e.g., MAHINDRA CITY", key="add_dest")
                    vehicle_type = st.selectbox(
                        "Vehicle Type",
                        ["TATA ACE", "DOST/BOLERO", "14FT", "17FT", "20FT", "Other"],
                        key="add_vehicle"
                    )
                    
                    if vehicle_type == "Other":
                        vehicle_type = st.text_input("Enter Vehicle Type", key="add_vehicle_custom")
                
                with col2:
                    rate = st.number_input("Rate (₹)", min_value=0.0, step=100.0, value=1000.0, key="add_rate")
                    halting_charge = st.number_input("Halting Charge (₹)", min_value=0.0, step=100.0, value=0.0, key="add_halting")
                    unloading_time = st.text_input("Unloading Free Time", value="AFTER LOADING 12 HOURS", key="add_unloading")
                
                if st.button("➕ Add Pricing Entry", key="btn_add_pricing"):
                    if origin and destination and vehicle_type and rate:
                        if add_customer_pricing(customer_id, origin, destination, vehicle_type, rate, halting_charge, unloading_time):
                            st.success(f"✅ Added pricing: {origin} → {destination}, {vehicle_type} @ ₹{rate:,.2f}")
                            st.rerun()
                    else:
                        st.error("❌ Please fill in all required fields")
            
            # Edit existing pricing
            with sub_tab2:
                st.subheader("Edit Existing Pricing")
                
                existing_pricing = get_all_customer_pricing(customer_id)
                
                if existing_pricing:
                    df = pd.DataFrame(existing_pricing)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Select pricing to edit
                    pricing_options = [
                        f"{p['origin']} → {p['destination']} ({p['vehicle_type']})"
                        for p in existing_pricing
                    ]
                    
                    selected_pricing_idx = st.selectbox(
                        "Select Pricing to Edit",
                        range(len(existing_pricing)),
                        format_func=lambda i: pricing_options[i],
                        key="edit_select"
                    )
                    
                    selected_pricing = existing_pricing[selected_pricing_idx]
                    
                    st.write("### Edit Pricing Details")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info(f"**Origin:** {selected_pricing['origin']}")
                        st.info(f"**Destination:** {selected_pricing['destination']}")
                        st.info(f"**Vehicle Type:** {selected_pricing['vehicle_type']}")
                    
                    with col2:
                        new_rate = st.number_input(
                            "New Rate (₹)",
                            min_value=0.0,
                            step=100.0,
                            value=float(selected_pricing['rate']),
                            key="edit_rate"
                        )
                        new_halting = st.number_input(
                            "Halting Charge (₹)",
                            min_value=0.0,
                            step=100.0,
                            value=float(selected_pricing['halting_charge'] or 0),
                            key="edit_halting"
                        )
                        new_unloading = st.text_input(
                            "Unloading Free Time",
                            value=selected_pricing['unloading_free_time'] or "",
                            key="edit_unloading"
                        )
                    
                    if st.button("💾 Update Pricing", key="btn_update_pricing"):
                        if update_customer_pricing(selected_pricing['id'], new_rate, new_halting, new_unloading):
                            st.success("✅ Pricing updated successfully!")
                            st.rerun()
                else:
                    st.info("No pricing entries found for this customer. Add new pricing in the 'Add New' tab.")
            
            # Delete pricing
            with sub_tab3:
                st.subheader("Delete Pricing Entry")
                
                existing_pricing = get_all_customer_pricing(customer_id)
                
                if existing_pricing:
                    df = pd.DataFrame(existing_pricing)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Select pricing to delete
                    pricing_options = [
                        f"{p['origin']} → {p['destination']} ({p['vehicle_type']}) - ₹{p['rate']:,.2f}"
                        for p in existing_pricing
                    ]
                    
                    selected_pricing_idx = st.selectbox(
                        "Select Pricing to Delete",
                        range(len(existing_pricing)),
                        format_func=lambda i: pricing_options[i],
                        key="delete_select"
                    )
                    
                    selected_pricing = existing_pricing[selected_pricing_idx]
                    
                    st.warning(f"⚠️ You are about to delete:\n\n"
                             f"**{selected_pricing['origin']} → {selected_pricing['destination']}**\n\n"
                             f"Vehicle: {selected_pricing['vehicle_type']}, Rate: ₹{selected_pricing['rate']:,.2f}")
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("🗑️ Confirm Delete", key="btn_delete_pricing", type="primary"):
                            if delete_customer_pricing(selected_pricing['id']):
                                st.success("✅ Pricing deleted successfully!")
                                st.rerun()
                else:
                    st.info("No pricing entries found for this customer.")
        else:
            st.warning("No customers found. Please try a different search term.")


def manage_default_pricing():
    """
    Interface for managing default pricing
    """
    st.header("🌐 Default Pricing Management")
    st.write("Manage the default pricing matrix used when no customer-specific pricing is available")
    
    # Sub-tabs
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["➕ Add New", "📋 View All", "🗑️ Delete"])
    
    # Add new default pricing
    with sub_tab1:
        st.subheader("Add New Default Pricing")
        
        col1, col2 = st.columns(2)
        
        with col1:
            origin = st.text_input("Origin Location", value="CHENNAI AIRPORT", key="default_add_origin")
            destination = st.text_input("Destination Location", placeholder="e.g., MAHINDRA CITY", key="default_add_dest")
            vehicle_type = st.selectbox(
                "Vehicle Type",
                ["TATA ACE", "DOST/BOLERO", "14FT", "17FT", "20FT", "Other"],
                key="default_add_vehicle"
            )
            
            if vehicle_type == "Other":
                vehicle_type = st.text_input("Enter Vehicle Type", key="default_add_vehicle_custom")
        
        with col2:
            customer_rate = st.number_input("Customer Rate (₹)", min_value=0.0, step=100.0, value=1000.0, key="default_add_cust_rate")
            vendor_rate = st.number_input("Vendor Rate (₹)", min_value=0.0, step=100.0, value=800.0, key="default_add_vendor_rate")
        
        if st.button("➕ Add Default Pricing", key="btn_add_default_pricing"):
            if origin and destination and vehicle_type and customer_rate:
                if add_default_pricing(origin, destination, vehicle_type, customer_rate, vendor_rate):
                    st.success(f"✅ Added default pricing: {origin} → {destination}, {vehicle_type}")
                    st.rerun()
            else:
                st.error("❌ Please fill in all required fields")
    
    # View all default pricing
    with sub_tab2:
        st.subheader("All Default Pricing Entries")
        
        all_pricing = get_all_default_pricing()
        
        if all_pricing:
            df = pd.DataFrame(all_pricing)
            st.dataframe(
                df[['origin', 'destination', 'vehicle_type', 'customer_rate', 'vendor_rate']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "customer_rate": st.column_config.NumberColumn("Customer Rate", format="₹ %.2f"),
                    "vendor_rate": st.column_config.NumberColumn("Vendor Rate", format="₹ %.2f")
                }
            )
            
            # Download as CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="default_pricing.csv",
                mime="text/csv"
            )
        else:
            st.info("No default pricing entries found. Add new entries in the 'Add New' tab or load CSV data.")
    
    # Delete default pricing
    with sub_tab3:
        st.subheader("Delete Default Pricing")
        
        all_pricing = get_all_default_pricing()
        
        if all_pricing:
            pricing_options = [
                f"{p['origin']} → {p['destination']} ({p['vehicle_type']}) - ₹{p['customer_rate']:,.2f}"
                for p in all_pricing
            ]
            
            selected_pricing_idx = st.selectbox(
                "Select Pricing to Delete",
                range(len(all_pricing)),
                format_func=lambda i: pricing_options[i],
                key="default_delete_select"
            )
            
            selected_pricing = all_pricing[selected_pricing_idx]
            
            st.warning(f"⚠️ You are about to delete:\n\n"
                     f"**{selected_pricing['origin']} → {selected_pricing['destination']}**\n\n"
                     f"Vehicle: {selected_pricing['vehicle_type']}, Customer Rate: ₹{selected_pricing['customer_rate']:,.2f}")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🗑️ Confirm Delete", key="btn_delete_default_pricing", type="primary"):
                    if delete_default_pricing(selected_pricing['id']):
                        st.success("✅ Default pricing deleted successfully!")
                        st.rerun()
        else:
            st.info("No default pricing entries found.")


def pricing_lookup_tool():
    """
    Tool to test pricing lookup
    """
    st.header("🔍 Pricing Lookup Tool")
    st.write("Search for pricing for a specific customer, route, and vehicle type")
    
    # Customer selection
    st.subheader("1. Select Customer")
    search_term = st.text_input(
        "Search Customer",
        placeholder="Enter customer name (leave empty for default pricing)",
        key="lookup_customer_search"
    )
    
    customer_id = None
    customer_name = "Default"
    
    if search_term:
        customers = search_customer_by_name(search_term)
        
        if customers:
            customer_names = [f"{c['name']}" for c in customers]
            selected_customer_idx = st.selectbox(
                "Select Customer",
                range(len(customers)),
                format_func=lambda i: customer_names[i],
                key="lookup_selected_customer"
            )
            
            selected_customer = customers[selected_customer_idx]
            customer_id = selected_customer['id']
            customer_name = selected_customer['name']
    
    # Route and vehicle selection
    st.subheader("2. Select Route and Vehicle")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        origin = st.selectbox(
            "Origin",
            ["CHENNAI AIRPORT", "CHENNAI CFS", "CHENNAI PORT", "Other"],
            key="lookup_origin"
        )
        
        if origin == "Other":
            origin = st.text_input("Enter Origin", key="lookup_origin_custom")
    
    with col2:
        destination = st.text_input(
            "Destination",
            placeholder="e.g., MAHINDRA CITY",
            key="lookup_destination"
        )
    
    with col3:
        vehicle_type = st.selectbox(
            "Vehicle Type",
            ["TATA ACE", "DOST/BOLERO", "14FT", "17FT", "20FT"],
            key="lookup_vehicle"
        )
    
    # Search button
    if st.button("🔎 Search Pricing", key="btn_search_pricing", type="primary"):
        if origin and destination and vehicle_type:
            with st.spinner("Searching..."):
                pricing = get_pricing_for_customer(customer_id, customer_name, origin, destination, vehicle_type)
                
                if pricing:
                    st.success("✅ Pricing Found!")
                    
                    # Display pricing info in a nice card
                    with st.container():
                        st.markdown("---")
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"### 💰 Pricing Details")
                            st.write(f"**Customer:** {customer_name}")
                            st.write(f"**Route:** {pricing['origin']} → {pricing['destination']}")
                            st.write(f"**Vehicle:** {pricing['vehicle_type']}")
                            st.write(f"**Source:** {pricing['source']}")
                        
                        with col2:
                            st.metric("Rate", f"₹ {pricing['rate']:,.2f}")
                            if pricing.get('halting_charge'):
                                st.metric("Halting Charge", f"₹ {pricing['halting_charge']:,.2f}")
                            if pricing.get('unloading_free_time'):
                                st.info(f"📦 {pricing['unloading_free_time']}")
                        
                        st.markdown("---")
                else:
                    st.error("❌ No pricing found for this combination. Please add pricing or check your search criteria.")
        else:
            st.error("❌ Please fill in all fields")


def view_all_pricing():
    """
    View all pricing data
    """
    st.header("📊 View All Pricing Data")
    
    view_type = st.radio(
        "Select Pricing Type",
        ["Customer-Specific Pricing", "Default Pricing"],
        key="view_pricing_type"
    )
    
    if view_type == "Customer-Specific Pricing":
        st.subheader("All Customer-Specific Pricing")
        
        # Get all customer-specific pricing across all customers
        query = """
        SELECT 
            c.name as customer_name,
            csp.origin,
            csp.destination,
            csp.vehicle_type,
            csp.rate,
            csp.halting_charge,
            csp.unloading_free_time
        FROM customer_specific_pricing csp
        JOIN customers c ON csp.customer_id = c.id
        WHERE csp.is_active = TRUE
        ORDER BY c.name, csp.origin, csp.destination, csp.vehicle_type;
        """
        
        from database import execute_query
        results = execute_query(query, fetch=True)
        
        if results:
            df = pd.DataFrame(results)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "rate": st.column_config.NumberColumn("Rate", format="₹ %.2f"),
                    "halting_charge": st.column_config.NumberColumn("Halting Charge", format="₹ %.2f")
                }
            )
            
            # Download
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="customer_specific_pricing.csv",
                mime="text/csv"
            )
        else:
            st.info("No customer-specific pricing found.")
    
    else:  # Default Pricing
        st.subheader("All Default Pricing")
        
        all_pricing = get_all_default_pricing()
        
        if all_pricing:
            df = pd.DataFrame(all_pricing)
            st.dataframe(
                df[['origin', 'destination', 'vehicle_type', 'customer_rate', 'vendor_rate']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "customer_rate": st.column_config.NumberColumn("Customer Rate", format="₹ %.2f"),
                    "vendor_rate": st.column_config.NumberColumn("Vendor Rate", format="₹ %.2f")
                }
            )
            
            # Download
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="default_pricing.csv",
                mime="text/csv"
            )
        else:
            st.info("No default pricing found.")


if __name__ == "__main__":
    pricing_management_page()
