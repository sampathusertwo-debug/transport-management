"""
Pricing Management Module
Handles route pricing matrices based on vehicle types
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import json

# Import database functions
import sys
sys.path.insert(0, '/'.join(__file__.split('/')[:-2]))
from database import execute_query, execute_insert_update

def create_pricing_tables():
    """
    Create the necessary tables for pricing management.
    This should be run once during setup.
    """
    try:
        # Create routes table
        routes_table = """
        CREATE TABLE IF NOT EXISTS routes (
            route_id SERIAL PRIMARY KEY,
            route_name VARCHAR(255) NOT NULL UNIQUE,
            from_location VARCHAR(255) NOT NULL,
            to_location VARCHAR(255) NOT NULL,
            distance_km DECIMAL(10, 2),
            is_active BOOLEAN DEFAULT TRUE,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create vehicle_types table
        vehicle_types_table = """
        CREATE TABLE IF NOT EXISTS vehicle_types (
            vehicle_type_id SERIAL PRIMARY KEY,
            vehicle_type_name VARCHAR(50) NOT NULL UNIQUE,
            capacity_kg DECIMAL(10, 2),
            length_ft DECIMAL(10, 2),
            is_active BOOLEAN DEFAULT TRUE,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create pricing_matrix table (the main pricing lookup table)
        pricing_matrix_table = """
        CREATE TABLE IF NOT EXISTS pricing_matrix (
            pricing_id SERIAL PRIMARY KEY,
            route_id INTEGER NOT NULL REFERENCES routes(route_id),
            vehicle_type_id INTEGER NOT NULL REFERENCES vehicle_types(vehicle_type_id),
            base_price DECIMAL(10, 2) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            effective_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(route_id, vehicle_type_id, effective_date)
        );
        """
        
        # Create index for faster lookups
        pricing_index = """
        CREATE INDEX IF NOT EXISTS idx_pricing_lookup 
        ON pricing_matrix(route_id, vehicle_type_id)
        WHERE is_active = TRUE;
        """
        
        # Execute all table creations
        for sql in [routes_table, vehicle_types_table, pricing_matrix_table, pricing_index]:
            execute_query(sql)
        
        st.success("✅ Pricing tables created successfully!")
        return True
    
    except Exception as e:
        st.error(f"❌ Error creating pricing tables: {e}")
        return False


def add_route(route_name, from_location, to_location, distance_km=None):
    """
    Add a new route to the database
    """
    try:
        query = """
        INSERT INTO routes (route_name, from_location, to_location, distance_km)
        VALUES (%s, %s, %s, %s)
        RETURNING route_id, route_name;
        """
        result = execute_query(query, (route_name, from_location, to_location, distance_km), fetch=True)
        
        if result:
            st.success(f"✅ Route '{route_name}' added successfully!")
            return result[0]['route_id']
        return None
    
    except Exception as e:
        st.error(f"❌ Error adding route: {e}")
        return None


def add_vehicle_type(vehicle_type_name, capacity_kg=None, length_ft=None):
    """
    Add a new vehicle type to the database
    """
    try:
        query = """
        INSERT INTO vehicle_types (vehicle_type_name, capacity_kg, length_ft)
        VALUES (%s, %s, %s)
        RETURNING vehicle_type_id, vehicle_type_name;
        """
        result = execute_query(query, (vehicle_type_name, capacity_kg, length_ft), fetch=True)
        
        if result:
            st.success(f"✅ Vehicle type '{vehicle_type_name}' added successfully!")
            return result[0]['vehicle_type_id']
        return None
    
    except Exception as e:
        st.error(f"❌ Error adding vehicle type: {e}")
        return None


def set_pricing(route_id, vehicle_type_id, base_price):
    """
    Set or update pricing for a route-vehicle combination
    """
    try:
        query = """
        INSERT INTO pricing_matrix (route_id, vehicle_type_id, base_price, effective_date)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (route_id, vehicle_type_id, effective_date) 
        DO UPDATE SET base_price = %s, updated_date = CURRENT_TIMESTAMP
        RETURNING pricing_id;
        """
        result = execute_query(query, (route_id, vehicle_type_id, base_price, base_price), fetch=True)
        
        if result:
            return result[0]['pricing_id']
        return None
    
    except Exception as e:
        st.error(f"❌ Error setting pricing: {e}")
        return None


def get_price(route_id, vehicle_type_id):
    """
    Get pricing for a specific route and vehicle combination
    Returns: price value or None if not found
    """
    try:
        query = """
        SELECT base_price 
        FROM pricing_matrix 
        WHERE route_id = %s AND vehicle_type_id = %s AND is_active = TRUE
        ORDER BY effective_date DESC
        LIMIT 1;
        """
        result = execute_query(query, (route_id, vehicle_type_id), fetch=True)
        
        if result:
            return float(result[0]['base_price'])
        return None
    
    except Exception as e:
        st.error(f"Error fetching price: {e}")
        return None


def get_pricing_by_route_and_vehicle_names(from_location, to_location, vehicle_type_name):
    """
    Get pricing using location names and vehicle type name (user-friendly)
    This is the main function to use when displaying prices to users
    """
    try:
        query = """
        SELECT pm.base_price, r.route_name, vt.vehicle_type_name
        FROM pricing_matrix pm
        JOIN routes r ON pm.route_id = r.route_id
        JOIN vehicle_types vt ON pm.vehicle_type_id = vt.vehicle_type_id
        WHERE r.from_location = %s 
          AND r.to_location = %s 
          AND vt.vehicle_type_name = %s
          AND pm.is_active = TRUE
        ORDER BY pm.effective_date DESC
        LIMIT 1;
        """
        result = execute_query(query, (from_location, to_location, vehicle_type_name), fetch=True)
        
        if result:
            return {
                'price': float(result[0]['base_price']),
                'route': result[0]['route_name'],
                'vehicle_type': result[0]['vehicle_type_name']
            }
        return None
    
    except Exception as e:
        st.error(f"Error fetching price: {e}")
        return None


def get_all_routes():
    """Get all active routes"""
    try:
        query = "SELECT route_id, route_name, from_location, to_location, distance_km FROM routes WHERE is_active = TRUE ORDER BY route_name;"
        return execute_query(query, fetch=True)
    except Exception as e:
        st.error(f"Error fetching routes: {e}")
        return []


def get_all_vehicle_types():
    """Get all active vehicle types"""
    try:
        query = "SELECT vehicle_type_id, vehicle_type_name, capacity_kg, length_ft FROM vehicle_types WHERE is_active = TRUE ORDER BY vehicle_type_name;"
        return execute_query(query, fetch=True)
    except Exception as e:
        st.error(f"Error fetching vehicle types: {e}")
        return []


def get_pricing_matrix():
    """
    Get the complete pricing matrix as a DataFrame
    Rows: Routes, Columns: Vehicle Types, Values: Prices
    """
    try:
        query = """
        SELECT 
            r.route_name,
            r.from_location,
            r.to_location,
            vt.vehicle_type_name,
            pm.base_price
        FROM pricing_matrix pm
        JOIN routes r ON pm.route_id = r.route_id
        JOIN vehicle_types vt ON pm.vehicle_type_id = vt.vehicle_type_id
        WHERE pm.is_active = TRUE
        ORDER BY r.from_location, r.to_location, vt.vehicle_type_name;
        """
        results = execute_query(query, fetch=True)
        
        if not results:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Create pivot table (routes as rows, vehicle types as columns)
        pivot_df = df.pivot_table(
            index=['from_location', 'to_location', 'route_name'],
            columns='vehicle_type_name',
            values='base_price',
            aggfunc='first'
        )
        
        return pivot_df
    
    except Exception as e:
        st.error(f"Error fetching pricing matrix: {e}")
        return pd.DataFrame()


def display_price_info_box(from_location, to_location, vehicle_type_name):
    """
    Display a styled info box with the pricing information
    Use this function when showing price to users
    """
    pricing_info = get_pricing_by_route_and_vehicle_names(
        from_location, to_location, vehicle_type_name
    )
    
    if pricing_info:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.info(
                f"📌 **Reference Price**\n\n"
                f"**Route:** {from_location} → {to_location}\n\n"
                f"**Vehicle:** {vehicle_type_name}\n\n"
                f"**Price:** ₹ {pricing_info['price']:,.2f}",
                icon="💰"
            )
    else:
        st.warning(
            f"⚠️ No pricing found for:\n"
            f"Route: {from_location} → {to_location}\n"
            f"Vehicle: {vehicle_type_name}\n\n"
            f"Please configure pricing in Settings."
        )


def upload_pricing_from_excel(file_data):
    """
    Upload pricing matrix from Excel file
    Expected format: Rows are routes (from->to), Columns are vehicle types
    """
    try:
        df = pd.read_excel(file_data)
        
        # First column should contain route info
        df = df.set_index(df.columns[0])
        
        added_count = 0
        errors = []
        
        for route_idx, row in df.iterrows():
            # Parse route name (assuming format: "FROM LOCATION TO LOCATION")
            route_parts = str(route_idx).split(' TO ')
            if len(route_parts) != 2:
                errors.append(f"Invalid route format: {route_idx}")
                continue
            
            from_loc = route_parts[0].strip()
            to_loc = route_parts[1].strip()
            
            # Get or create route
            route_query = "SELECT route_id FROM routes WHERE from_location = %s AND to_location = %s;"
            route_result = execute_query(route_query, (from_loc, to_loc), fetch=True)
            
            if not route_result:
                route_id = add_route(f"{from_loc} → {to_loc}", from_loc, to_loc)
            else:
                route_id = route_result[0]['route_id']
            
            # Process each vehicle type column
            for vehicle_type, price in row.items():
                if pd.notna(price) and price != '':
                    # Get or create vehicle type
                    vtype_query = "SELECT vehicle_type_id FROM vehicle_types WHERE vehicle_type_name = %s;"
                    vtype_result = execute_query(vtype_query, (vehicle_type,), fetch=True)
                    
                    if not vtype_result:
                        vehicle_type_id = add_vehicle_type(vehicle_type)
                    else:
                        vehicle_type_id = vtype_result[0]['vehicle_type_id']
                    
                    # Set pricing
                    try:
                        set_pricing(route_id, vehicle_type_id, float(price))
                        added_count += 1
                    except Exception as e:
                        errors.append(f"Error setting price for {route_idx} - {vehicle_type}: {e}")
        
        result_message = f"✅ Successfully imported {added_count} pricing entries!"
        if errors:
            result_message += f"\n\n⚠️ {len(errors)} errors encountered:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                result_message += f"\n... and {len(errors) - 5} more errors"
        
        st.success(result_message)
        return True
    
    except Exception as e:
        st.error(f"❌ Error uploading Excel file: {e}")
        return False
