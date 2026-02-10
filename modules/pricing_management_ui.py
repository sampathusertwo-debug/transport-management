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
    st.title("Pricing Management")
    st.write("Manage customer-specific and default pricing matrices")
    
    # Initialize section
    with st.expander("System Setup", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Initialize Pricing Tables"):
                with st.spinner("Creating tables..."):
                    if create_customer_pricing_tables():
                        st.success("Tables created successfully!")
        
        with col2:
            if st.button("Load CSV Pricing Data"):
                with st.spinner("Loading pricing data from CSV files..."):
                    if load_csv_pricing_data():
                        st.balloons()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Customer-Specific Pricing",
        "Default Pricing",
        "Bulk Upload/Update",
        "Pricing Lookup",
        "View All Pricing"
    ])
    
    # Tab 1: Customer-Specific Pricing Management
    with tab1:
        manage_customer_pricing()
    
    # Tab 2: Default Pricing Management
    with tab2:
        manage_default_pricing()
    
    # Tab 3: Bulk Upload/Update
    with tab3:
        bulk_upload_update()
    
    # Tab 4: Pricing Lookup
    with tab4:
        pricing_lookup_tool()
    
    # Tab 5: View All Pricing
    with tab5:
        view_all_pricing()


def manage_customer_pricing():
    """
    Interface for managing customer-specific pricing
    """
    st.header("Customer-Specific Pricing Management")
    
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
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Add New", "Edit Existing", "Delete"])
            
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
                
                if st.button("Add Pricing Entry", key="btn_add_pricing"):
                    if origin and destination and vehicle_type and rate:
                        if add_customer_pricing(customer_id, origin, destination, vehicle_type, rate, halting_charge, unloading_time):
                            st.success(f"Added pricing: {origin} → {destination}, {vehicle_type} @ ₹{rate:,.2f}")
                            st.rerun()
                    else:
                        st.error("Please fill in all required fields")
            
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
                    
                    if st.button("Update Pricing", key="btn_update_pricing"):
                        if update_customer_pricing(selected_pricing['id'], new_rate, new_halting, new_unloading):
                            st.success("Pricing updated successfully!")
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
                    
                    st.warning(f"You are about to delete:\n\n"
                             f"**{selected_pricing['origin']} → {selected_pricing['destination']}**\n\n"
                             f"Vehicle: {selected_pricing['vehicle_type']}, Rate: ₹{selected_pricing['rate']:,.2f}")
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("Confirm Delete", key="btn_delete_pricing", type="primary"):
                            if delete_customer_pricing(selected_pricing['id']):
                                st.success("Pricing deleted successfully!")
                                st.rerun()
                else:
                    st.info("No pricing entries found for this customer.")
        else:
            st.warning("No customers found. Please try a different search term.")


def manage_default_pricing():
    """
    Interface for managing default pricing
    """
    st.header("Default Pricing Management")
    st.write("Manage the default pricing matrix used when no customer-specific pricing is available")
    
    # Sub-tabs
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Add New", "View All", "Delete"])
    
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
        
        if st.button("Add Default Pricing", key="btn_add_default_pricing"):
            if origin and destination and vehicle_type and customer_rate:
                if add_default_pricing(origin, destination, vehicle_type, customer_rate, vendor_rate):
                    st.success(f"Added default pricing: {origin} → {destination}, {vehicle_type}")
                    st.rerun()
            else:
                st.error("Please fill in all required fields")
    
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
                if st.button("Confirm Delete", key="btn_delete_default_pricing", type="primary"):
                    if delete_default_pricing(selected_pricing['id']):
                        st.success("Default pricing deleted successfully!")
                        st.rerun()
        else:
            st.info("No default pricing entries found.")


def bulk_upload_update():
    """
    Bulk upload and update pricing from CSV files
    """
    st.header("Bulk Upload/Update Pricing")
    st.write("Upload CSV files to add or update pricing data")
    
    # Instructions
    with st.expander("Instructions", expanded=True):
        st.markdown("""
        ### File Naming Convention:
        - **Customer-specific pricing:** `price_{customer_name}.csv` (e.g., `price_demrico.csv`)
        - **Default pricing:** `price_default.csv`
        
        ### Required CSV Columns:
        - `origin` - Origin location (e.g., CHENNAI AIRPORT)
        - `destination` - Destination location (e.g., MAHINDRA CITY)
        - `vehicle_type` - Vehicle type (e.g., 7ft, TATA ACE, 8ft, 14ft) - will be auto-normalized
        - `rate` - Price rate (numeric)
        - `unloading_free_time` - Free unloading time in minutes (optional)
        - `halting_charge` - Halting charge per hour (optional)
        
        ### Supported Vehicle Types:
        You can use any of these formats (will be normalized automatically):
        - **7ft vehicles:** TATA ACE, ACE, 7ft, 7 ft
        - **8ft vehicles:** DOSTT, BOLERO, DOST, 8ft, 8 ft
        - **12ft vehicles:** 12ft, 12 ft
        - **14ft vehicles:** 14ft, 14 ft, 407
        - **17ft vehicles:** 17ft, 17 ft
        - **20ft vehicles:** 20ft, 20 ft
        - **24ft vehicles:** 24ft, 24 ft
        - **32ft vehicles:** 32ft, 32 ft
        
        ### Process:
        1. Upload your CSV file
        2. Click **Preview Changes** to see what will be updated
        3. Review the changes (additions/updates)
        4. Click **Save Changes** to apply updates to database
        """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=['csv'],
        help="Upload a CSV file with pricing data",
        key="bulk_pricing_upload"
    )
    
    if uploaded_file is not None:
        try:
            # Parse filename to determine customer or default
            filename = uploaded_file.name.lower()
            
            if not filename.startswith('price_') or not filename.endswith('.csv'):
                st.error("Invalid filename format. File must be named 'price_{customer_name}.csv' or 'price_default.csv'")
                return
            
            # Extract customer name
            customer_name_part = filename[6:-4]  # Remove 'price_' prefix and '.csv' suffix
            
            is_default = (customer_name_part == 'default')
            
            # Read CSV
            df = pd.read_csv(uploaded_file)
            
            # Validate required columns
            required_cols = ['origin', 'destination', 'vehicle_type', 'rate']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"Missing required columns: {', '.join(missing_cols)}")
                st.info("Required columns: origin, destination, vehicle_type, rate")
                return
            
            # Show uploaded data
            st.success(f"File uploaded: **{uploaded_file.name}**")
            st.info(f"Found **{len(df)}** pricing entries")
            
            # Display sample data
            with st.expander("View Uploaded Data", expanded=False):
                st.dataframe(df, use_container_width=True)
            
            # Store data in session state for preview
            st.session_state['bulk_upload_df'] = df
            st.session_state['bulk_upload_filename'] = filename
            st.session_state['bulk_upload_customer_name'] = customer_name_part
            st.session_state['bulk_upload_is_default'] = is_default
            
            # Preview button
            if st.button("Preview Changes", type="primary", key="btn_preview"):
                st.session_state['show_preview'] = True
                st.rerun()
            
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")
            return
    
    # Show preview if triggered
    if st.session_state.get('show_preview', False) and 'bulk_upload_df' in st.session_state:
        show_bulk_upload_preview()


def show_bulk_upload_preview():
    """
    Show preview of changes before applying
    """
    st.markdown("---")
    st.subheader("Preview Changes")
    
    df = st.session_state['bulk_upload_df']
    customer_name_part = st.session_state['bulk_upload_customer_name']
    is_default = st.session_state['bulk_upload_is_default']
    
    from database import execute_query
    
    if is_default:
        st.info("Processing: **Default Pricing Table**")
        
        # Get existing default pricing
        existing_query = """
            SELECT origin, destination, vehicle_type, customer_rate as rate
            FROM default_pricing
            WHERE is_active = TRUE
        """
        existing_data = execute_query(existing_query, fetch=True)
        
    else:
        st.info(f"Processing: **Customer-Specific Pricing** for '{customer_name_part}'")
        
        # Check if customer exists
        customer_query = """
            SELECT id, name FROM customers 
            WHERE LOWER(name) LIKE %s 
            LIMIT 1
        """
        customers = execute_query(customer_query, (f"%{customer_name_part}%",), fetch=True)
        
        if not customers:
            st.warning(f"Customer '{customer_name_part}' not found in database!")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Create Customer", type="primary", key="btn_create_customer"):
                    st.session_state['create_customer_for_upload'] = True
                    st.rerun()
            
            if st.session_state.get('create_customer_for_upload', False):
                st.markdown("---")
                st.subheader("Create New Customer")
                
                with st.form("create_customer_form"):
                    new_customer_name = st.text_input("Customer Name*", value=customer_name_part.title())
                    new_customer_email = st.text_input("Email", placeholder="customer@example.com")
                    new_customer_phone = st.text_input("Phone", placeholder="1234567890")
                    new_customer_address = st.text_area("Address")
                    
                    submitted = st.form_submit_button("Create Customer", type="primary")
                    
                    if submitted:
                        if not new_customer_name:
                            st.error("Customer name is required")
                        else:
                            # Insert customer
                            insert_query = """
                                INSERT INTO customers (id, name, email, phone, address, created_date)
                                VALUES (gen_random_uuid(), %s, %s, %s, %s, NOW())
                                RETURNING id
                            """
                            result = execute_query(
                                insert_query, 
                                (new_customer_name.title(), new_customer_email, new_customer_phone, new_customer_address),
                                fetch=True
                            )
                            
                            if result:
                                st.success(f"Customer '{new_customer_name}' created successfully!")
                                st.session_state['create_customer_for_upload'] = False
                                st.rerun()
                            else:
                                st.error("Failed to create customer")
            
            return
        
        customer_id = customers[0]['id']
        customer_name = customers[0]['name']
        
        st.success(f"Found customer: **{customer_name}**")
        
        # Get existing customer pricing
        existing_query = """
            SELECT origin, destination, vehicle_type, rate
            FROM customer_specific_pricing
            WHERE customer_id = %s AND is_active = TRUE
        """
        existing_data = execute_query(existing_query, (customer_id,), fetch=True)
        
        st.session_state['bulk_upload_customer_id'] = customer_id
    
    # Create lookup dictionary for existing data
    existing_dict = {}
    if existing_data:
        for row in existing_data:
            key = (
                row['origin'].strip().upper(),
                row['destination'].strip().upper(),
                row['vehicle_type'].strip().lower()
            )
            existing_dict[key] = float(row['rate'])
    
    # Helper function to normalize vehicle type names
    def normalize_uploaded_vehicle_type(uploaded_type):
        """Normalize uploaded vehicle type to match database storage format"""
        uploaded_type = str(uploaded_type).strip()
        uploaded_upper = uploaded_type.upper()
        
        # Try exact match with display names first
        from database import get_vehicle_type_mapping
        mapping = get_vehicle_type_mapping()
        
        # Check if it matches a display name
        if uploaded_type in mapping:
            return mapping[uploaded_type]
        
        # Check uppercase version
        for display_name, type_name in mapping.items():
            if display_name.upper() == uploaded_upper:
                return type_name
        
        # Common variations mapping
        variations = {
            'TATA ACE': '7ft',
            'TATAACE': '7ft',
            'ACE': '7ft',
            '7FT': '7ft',
            '7 FT': '7ft',
            'DOSTT': '8ft',
            'BOLERO': '8ft',
            'DOST': '8ft',
            '8FT': '8ft',
            '8 FT': '8ft',
            '12FT': '12ft',
            '12 FT': '12ft',
            '14FT': '14ft',
            '14 FT': '14ft',
            '407': '14ft',
            '17FT': '17ft',
            '17 FT': '17ft',
            '20FT': '20ft',
            '20 FT': '20ft',
            '24FT': '24ft',
            '24 FT': '24ft',
            '32FT': '32ft',
            '32 FT': '32ft'
        }
        
        if uploaded_upper in variations:
            return variations[uploaded_upper]
        
        # If no match found, return lowercase version
        return uploaded_type.lower()
    
    # Analyze changes
    additions = []
    updates = []
    no_change = []
    
    for idx, row in df.iterrows():
        origin = str(row['origin']).strip().upper()
        destination = str(row['destination']).strip().upper()
        vehicle_type = normalize_uploaded_vehicle_type(row['vehicle_type'])
        new_rate = float(row['rate'])
        
        key = (origin, destination, vehicle_type)
        
        if key in existing_dict:
            old_rate = existing_dict[key]
            if abs(old_rate - new_rate) > 0.01:  # Check for meaningful difference
                updates.append({
                    'origin': origin,
                    'destination': destination,
                    'vehicle_type': vehicle_type,
                    'old_rate': old_rate,
                    'new_rate': new_rate,
                    'difference': new_rate - old_rate,
                    'unloading_free_time': row.get('unloading_free_time', None),
                    'halting_charge': row.get('halting_charge', None)
                })
            else:
                no_change.append({
                    'origin': origin,
                    'destination': destination,
                    'vehicle_type': vehicle_type,
                    'rate': new_rate
                })
        else:
            additions.append({
                'origin': origin,
                'destination': destination,
                'vehicle_type': vehicle_type,
                'rate': new_rate,
                'unloading_free_time': row.get('unloading_free_time', None),
                'halting_charge': row.get('halting_charge', None)
            })
    
    # Store analysis in session state
    st.session_state['bulk_additions'] = additions
    st.session_state['bulk_updates'] = updates
    st.session_state['bulk_no_change'] = no_change
    
    # Display summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("New Entries", len(additions))
    with col2:
        st.metric("Updates", len(updates))
    with col3:
        st.metric("✓ No Change", len(no_change))
    
    # Show details
    if additions:
        with st.expander(f"New Entries ({len(additions)})", expanded=True):
            df_additions = pd.DataFrame(additions)
            st.dataframe(
                df_additions,
                use_container_width=True,
                column_config={
                    "rate": st.column_config.NumberColumn("Rate", format="₹ %.2f"),
                    "halting_charge": st.column_config.NumberColumn("Halting Charge", format="₹ %.2f"),
                    "unloading_free_time": st.column_config.TextColumn("Free Time")
                }
            )
    
    if updates:
        with st.expander(f"Updates ({len(updates)})", expanded=True):
            df_updates = pd.DataFrame(updates)
            st.dataframe(
                df_updates,
                use_container_width=True,
                column_config={
                    "old_rate": st.column_config.NumberColumn("Old Rate", format="₹ %.2f"),
                    "new_rate": st.column_config.NumberColumn("New Rate", format="₹ %.2f"),
                    "difference": st.column_config.NumberColumn("Difference", format="₹ %.2f"),
                    "halting_charge": st.column_config.NumberColumn("Halting Charge", format="₹ %.2f"),
                    "unloading_free_time": st.column_config.TextColumn("Free Time")
                }
            )
    
    if no_change:
        with st.expander(f"✓ No Changes ({len(no_change)})", expanded=False):
            df_no_change = pd.DataFrame(no_change)
            st.dataframe(df_no_change, use_container_width=True)
    
    # Save button
    st.markdown("---")
    
    if len(additions) > 0 or len(updates) > 0:
        col1, col2, col3 = st.columns([2, 1, 2])
        
        with col2:
            if st.button("Save Changes", type="primary", key="btn_save_bulk", use_container_width=True):
                apply_bulk_changes(is_default)
    else:
        st.info("No changes to apply. All data is already up to date.")


def apply_bulk_changes(is_default):
    """
    Apply the bulk changes to database
    """
    from database import execute_query
    
    additions = st.session_state.get('bulk_additions', [])
    updates = st.session_state.get('bulk_updates', [])
    
    success_count = 0
    error_count = 0
    
    with st.spinner("Applying changes..."):
        if is_default:
            # Process additions for default pricing
            for item in additions:
                insert_query = """
                    INSERT INTO default_pricing (
                        origin, destination, vehicle_type, customer_rate, 
                        vendor_rate, is_active, created_date
                    )
                    VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
                """
                if execute_query(insert_query, (
                    item['origin'],
                    item['destination'],
                    item['vehicle_type'],
                    item['rate'],
                    item['rate'] * 0.85  # Default vendor rate
                )):
                    success_count += 1
                else:
                    error_count += 1
            
            # Process updates for default pricing
            for item in updates:
                update_query = """
                    UPDATE default_pricing
                    SET customer_rate = %s,
                        vendor_rate = %s,
                        last_modified = NOW()
                    WHERE origin = %s 
                    AND destination = %s 
                    AND vehicle_type = %s
                    AND is_active = TRUE
                """
                if execute_query(update_query, (
                    item['new_rate'],
                    item['new_rate'] * 0.85,
                    item['origin'],
                    item['destination'],
                    item['vehicle_type']
                )):
                    success_count += 1
                else:
                    error_count += 1
        else:
            # Process customer-specific pricing
            customer_id = st.session_state.get('bulk_upload_customer_id')
            
            if not customer_id:
                st.error("Customer ID not found")
                return
            
            # Process additions
            for item in additions:
                insert_query = """
                    INSERT INTO customer_specific_pricing (
                        customer_id, origin, destination, vehicle_type, rate,
                        unloading_free_time, halting_charge, is_active, created_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, NOW())
                """
                if execute_query(insert_query, (
                    customer_id,
                    item['origin'],
                    item['destination'],
                    item['vehicle_type'],
                    item['rate'],
                    item.get('unloading_free_time'),
                    item.get('halting_charge')
                )):
                    success_count += 1
                else:
                    error_count += 1
            
            # Process updates
            for item in updates:
                update_query = """
                    UPDATE customer_specific_pricing
                    SET rate = %s,
                        unloading_free_time = %s,
                        halting_charge = %s,
                        last_modified = NOW()
                    WHERE customer_id = %s
                    AND origin = %s 
                    AND destination = %s 
                    AND vehicle_type = %s
                    AND is_active = TRUE
                """
                if execute_query(update_query, (
                    item['new_rate'],
                    item.get('unloading_free_time'),
                    item.get('halting_charge'),
                    customer_id,
                    item['origin'],
                    item['destination'],
                    item['vehicle_type']
                )):
                    success_count += 1
                else:
                    error_count += 1
    
    # Show results
    if error_count == 0:
        st.success(f"Successfully applied {success_count} changes!")
        st.balloons()
    else:
        st.warning(f"Applied {success_count} changes with {error_count} errors")
    
    # Clear session state
    for key in ['bulk_upload_df', 'bulk_upload_filename', 'bulk_upload_customer_name',
                'bulk_upload_is_default', 'show_preview', 'bulk_additions', 'bulk_updates',
                'bulk_no_change', 'bulk_upload_customer_id', 'create_customer_for_upload']:
        if key in st.session_state:
            del st.session_state[key]
    
    st.rerun()


def pricing_lookup_tool():
    """
    Tool to test pricing lookup
    """
    st.header("Pricing Lookup Tool")
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
                    st.success("Pricing Found!")
                    
                    # Display pricing info in a nice card
                    with st.container():
                        st.markdown("---")
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"### Pricing Details")
                            st.write(f"**Customer:** {customer_name}")
                            st.write(f"**Route:** {pricing['origin']} → {pricing['destination']}")
                            st.write(f"**Vehicle:** {pricing['vehicle_type']}")
                            st.write(f"**Source:** {pricing['source']}")
                        
                        with col2:
                            st.metric("Rate", f"₹ {pricing['rate']:,.2f}")
                            if pricing.get('halting_charge'):
                                st.metric("Halting Charge", f"₹ {pricing['halting_charge']:,.2f}")
                            if pricing.get('unloading_free_time'):
                                st.info(f"{pricing['unloading_free_time']}")
                        
                        st.markdown("---")
                else:
                    st.error("No pricing found for this combination. Please add pricing or check your search criteria.")
        else:
            st.error("Please fill in all fields")


def view_all_pricing():
    """
    View all pricing data
    """
    st.header("View All Pricing Data")
    
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
