"""
Pricing Configuration Interface
Allows administrators to manage routes, vehicle types, and pricing matrices
"""
import streamlit as st
import pandas as pd
from modules.pricing import (
    create_pricing_tables, add_route, add_vehicle_type, set_pricing,
    get_all_routes, get_all_vehicle_types, get_pricing_matrix,
    upload_pricing_from_excel, display_price_info_box
)

def pricing_settings_page():
    """Main pricing settings page"""
    st.title("💰 Pricing Management")
    
    # Initialize tables if needed
    if st.button("Initialize Pricing System", key="init_pricing"):
        create_pricing_tables()
        st.rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Pricing Matrix",
        "🛣️ Routes",
        "Vehicle Types",
        "⚙️ Set Pricing",
        "📥 Import from Excel"
    ])
    
    # Tab 1: View Pricing Matrix
    with tab1:
        st.header("Pricing Matrix Viewer")
        st.write("View the current pricing matrix for all routes and vehicle types")
        
        matrix_df = get_pricing_matrix()
        
        if not matrix_df.empty:
            st.dataframe(
                matrix_df.fillna("-"),
                use_container_width=True,
                column_config={
                    col: st.column_config.NumberColumn(format="₹ %.2f")
                    for col in matrix_df.columns
                }
            )
            
            # Download button
            csv = matrix_df.to_csv()
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="pricing_matrix.csv",
                mime="text/csv"
            )
        else:
            st.info("No pricing data available. Please add routes, vehicle types, and pricing first.")
    
    # Tab 2: Manage Routes
    with tab2:
        st.header("Manage Routes")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Add New Route")
            route_name = st.text_input(
                "Route Name",
                placeholder="e.g., ALANDUR → AMBATTUR",
                help="Descriptive name for the route"
            )
            from_location = st.text_input(
                "From Location",
                placeholder="e.g., ALANDUR"
            )
            to_location = st.text_input(
                "To Location",
                placeholder="e.g., AMBATTUR"
            )
            distance_km = st.number_input(
                "Distance (KM)",
                min_value=0.0,
                step=0.5,
                value=0.0
            )
            
            if st.button("➕ Add Route"):
                if route_name and from_location and to_location:
                    if add_route(route_name, from_location, to_location, distance_km):
                        st.rerun()
                else:
                    st.error("Please fill in all required fields")
        
        with col2:
            st.subheader("Existing Routes")
            routes = get_all_routes()
            if routes:
                routes_df = pd.DataFrame(routes)
                st.dataframe(
                    routes_df[['route_name', 'from_location', 'to_location']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No routes added yet")
    
    # Tab 3: Manage Vehicle Types
    with tab3:
        st.header("Manage Vehicle Types")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Add New Vehicle Type")
            vtype_name = st.text_input(
                "Vehicle Type Name",
                placeholder="e.g., TATA ACE, 14FT/407, 20FT",
                help="Name of the vehicle type"
            )
            capacity = st.number_input(
                "Capacity (KG)",
                min_value=0.0,
                step=100.0,
                value=1000.0
            )
            length = st.number_input(
                "Length (FT)",
                min_value=0.0,
                step=0.5,
                value=0.0
            )
            
            if st.button("➕ Add Vehicle Type"):
                if vtype_name:
                    if add_vehicle_type(vtype_name, capacity, length):
                        st.rerun()
                else:
                    st.error("Please enter vehicle type name")
        
        with col2:
            st.subheader("Existing Vehicle Types")
            vehicle_types = get_all_vehicle_types()
            if vehicle_types:
                vtype_df = pd.DataFrame(vehicle_types)
                st.dataframe(
                    vtype_df[['vehicle_type_name', 'capacity_kg', 'length_ft']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No vehicle types added yet")
    
    # Tab 4: Set Pricing
    with tab4:
        st.header("Set Pricing for Route & Vehicle")
        
        routes = get_all_routes()
        vehicle_types = get_all_vehicle_types()
        
        if not routes or not vehicle_types:
            st.error("❌ Please add routes and vehicle types first!")
        else:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                selected_route = st.selectbox(
                    "Select Route",
                    routes,
                    format_func=lambda x: x['route_name']
                )
                route_id = selected_route['route_id']
            
            with col2:
                selected_vtype = st.selectbox(
                    "Select Vehicle Type",
                    vehicle_types,
                    format_func=lambda x: x['vehicle_type_name']
                )
                vehicle_type_id = selected_vtype['vehicle_type_id']
            
            with col3:
                price = st.number_input(
                    "Base Price (₹)",
                    min_value=0.0,
                    step=100.0,
                    value=1000.0
                )
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("Set Pricing", key="set_price_btn"):
                    if set_pricing(route_id, vehicle_type_id, price):
                        st.success(f"✅ Price set: ₹{price:,.2f}")
            
            with col_btn2:
                st.info("✨ Tip: You can bulk import prices from Excel")
    
    # Tab 5: Import from Excel
    with tab5:
        st.header("Import Pricing from Excel")
        
        st.write("### Format Requirements:")
        st.markdown("""
        - **First column**: Route names (format: "FROM LOCATION TO LOCATION")
        - **Other columns**: Vehicle type names
        - **Values**: Prices in numeric format
        
        **Example structure:**
        | Route | TATA ACE | BOLERO | 14FT |
        |-------|----------|--------|------|
        | ALANDUR TO AMBATTUR | 1000 | 1500 | 2300 |
        | ALANDUR TO AMBUR | 1500 | 2000 | 3000 |
        """)
        
        uploaded_file = st.file_uploader(
            "Choose an Excel file",
            type=['xlsx', 'xls'],
            key="pricing_excel"
        )
        
        if uploaded_file:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📥 Import Pricing Data"):
                    with st.spinner("Importing..."):
                        if upload_pricing_from_excel(uploaded_file):
                            st.rerun()
            
            with col2:
                # Show preview
                try:
                    preview_df = pd.read_excel(uploaded_file)
                    st.subheader("Preview")
                    st.dataframe(preview_df.head(10), use_container_width=True)
                except Exception as e:
                    st.error(f"Could not preview file: {e}")


def test_pricing_lookup():
    """Test function to show pricing lookup in action"""
    st.divider()
    st.header("🧪 Test Pricing Lookup")
    
    st.write("Test how users will see pricing information:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        from_loc = st.selectbox(
            "From Location",
            ["ALANDUR", "AMBATTUR", "AMBUR", "CHENGALPATTU"],
            key="test_from"
        )
    
    with col2:
        to_loc = st.selectbox(
            "To Location",
            ["ALANDUR", "AMBATTUR", "AMBUR", "CHENGALPATTU"],
            key="test_to"
        )
    
    with col3:
        vtype = st.selectbox(
            "Vehicle Type",
            ["TATA ACE", "DOST/BOLERO", "14FT/407", "15FT", "20FT"],
            key="test_vtype"
        )
    
    if st.button("🔍 Get Price"):
        display_price_info_box(from_loc, to_loc, vtype)


if __name__ == "__main__":
    pricing_settings_page()
    test_pricing_lookup()
