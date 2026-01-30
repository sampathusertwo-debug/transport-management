"""
Customer-Specific Pricing Management Module
Handles customer-specific pricing and default pricing matrices
"""
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from database import execute_query

def create_customer_pricing_tables():
    """
    Create tables for customer-specific pricing
    """
    try:
        # Create customer_pricing_config table
        customer_pricing_config_table = """
        CREATE TABLE IF NOT EXISTS customer_pricing_config (
            id SERIAL PRIMARY KEY,
            customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
            customer_name VARCHAR(255) NOT NULL,
            pricing_type VARCHAR(50) DEFAULT 'custom',
            is_active BOOLEAN DEFAULT TRUE,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(customer_id)
        );
        """
        
        # Create customer_specific_pricing table
        customer_specific_pricing_table = """
        CREATE TABLE IF NOT EXISTS customer_specific_pricing (
            id SERIAL PRIMARY KEY,
            customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
            origin VARCHAR(255) NOT NULL,
            destination VARCHAR(255) NOT NULL,
            vehicle_type VARCHAR(100) NOT NULL,
            rate DECIMAL(10, 2) NOT NULL,
            unloading_free_time VARCHAR(100),
            halting_charge DECIMAL(10, 2),
            is_active BOOLEAN DEFAULT TRUE,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(customer_id, origin, destination, vehicle_type)
        );
        """
        
        # Create default_pricing table (from airport_to_import_and_export.csv)
        default_pricing_table = """
        CREATE TABLE IF NOT EXISTS default_pricing (
            id SERIAL PRIMARY KEY,
            sl_no INTEGER,
            origin VARCHAR(255) NOT NULL,
            destination VARCHAR(255) NOT NULL,
            vehicle_type VARCHAR(100) NOT NULL,
            customer_rate DECIMAL(10, 2),
            vendor_rate DECIMAL(10, 2),
            is_active BOOLEAN DEFAULT TRUE,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(origin, destination, vehicle_type)
        );
        """
        
        # Create indexes for faster lookups
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_customer_pricing_lookup ON customer_specific_pricing(customer_id, origin, destination, vehicle_type) WHERE is_active = TRUE;",
            "CREATE INDEX IF NOT EXISTS idx_default_pricing_lookup ON default_pricing(origin, destination, vehicle_type) WHERE is_active = TRUE;",
            "CREATE INDEX IF NOT EXISTS idx_customer_pricing_config ON customer_pricing_config(customer_id) WHERE is_active = TRUE;"
        ]
        
        # Execute all table creations
        execute_query(customer_pricing_config_table)
        execute_query(customer_specific_pricing_table)
        execute_query(default_pricing_table)
        
        for index_sql in indexes:
            execute_query(index_sql)
        
        st.success("✅ Customer pricing tables created successfully!")
        return True
    
    except Exception as e:
        st.error(f"❌ Error creating customer pricing tables: {e}")
        return False


def load_csv_pricing_data():
    """
    Load pricing data from CSV files in the data folder
    """
    try:
        data_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        
        results = []
        
        # Load default pricing (airport_to_import_and_export.csv)
        default_file = os.path.join(data_folder, 'airport_to_import_and_export.csv')
        if os.path.exists(default_file):
            count = load_default_pricing_from_csv(default_file)
            results.append(f"✅ Default pricing: {count} entries")
        
        # Load customer-specific pricing files
        customer_files = {
            'world_wild_logistic': 'airport_to_world_wild_logistic.csv',
            'demrico': 'pricing_for_demrico.csv',
            'sevenways': 'pricing_for_sevenways.csv'
        }
        
        for customer_name, filename in customer_files.items():
            file_path = os.path.join(data_folder, filename)
            if os.path.exists(file_path):
                count = load_customer_pricing_from_csv(file_path, customer_name)
                results.append(f"✅ {customer_name.title()}: {count} entries")
        
        st.success("\n".join(results))
        return True
        
    except Exception as e:
        st.error(f"❌ Error loading CSV pricing data: {e}")
        return False


def load_default_pricing_from_csv(file_path):
    """
    Load default pricing from airport_to_import_and_export.csv
    Format: SL.NO, Destination, Customer Rate, Vendor Rate (alternating for each vehicle type)
    """
    try:
        # Read CSV file with tab separator
        df = pd.read_csv(file_path, sep='\t', encoding='utf-8', on_bad_lines='skip', skiprows=1)
        
        added_count = 0
        
        # Clean column names
        df.columns = [str(col).strip().replace('\n', ' ').replace('"', '') for col in df.columns]
        
        # Find the destination column (usually second column)
        dest_col = df.columns[1] if len(df.columns) > 1 else None
        
        if not dest_col:
            return 0
        
        origin = "CHENNAI AIRPORT"
        
        # Vehicle type mapping based on column positions
        # Columns after destination: CUSTOMER, VENDOR, DOST, VENDOR, 14FT, VENDOR, 17FT, VENDOR, 20FT, VENDOR
        vehicle_mappings = [
            (2, 3, 'TATA ACE'),  # Column 2 = customer, 3 = vendor
            (4, 5, 'DOST/BOLERO'),
            (6, 7, '14FT'),
            (8, 9, '17FT'),
            (10, 11, '20FT')
        ]
        
        # Process each row
        for _, row in df.iterrows():
            destination = str(row[dest_col]).strip().replace('"', '')
            
            if pd.isna(destination) or destination == '' or destination == 'nan' or 'FROM' in destination.upper():
                continue
            
            # Process each vehicle type
            for customer_col_idx, vendor_col_idx, vehicle_type in vehicle_mappings:
                try:
                    if len(df.columns) > customer_col_idx:
                        customer_rate = row.iloc[customer_col_idx]
                        vendor_rate = row.iloc[vendor_col_idx] if len(df.columns) > vendor_col_idx else None
                        
                        if pd.notna(customer_rate) and str(customer_rate).strip() != '':
                            customer_rate = float(str(customer_rate).replace(',', ''))
                            
                            if vendor_rate and pd.notna(vendor_rate) and str(vendor_rate).strip() != '':
                                vendor_rate = float(str(vendor_rate).replace(',', ''))
                            else:
                                vendor_rate = None
                            
                            # Insert into database
                            query = """
                            INSERT INTO default_pricing (origin, destination, vehicle_type, customer_rate, vendor_rate)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (origin, destination, vehicle_type) 
                            DO UPDATE SET customer_rate = EXCLUDED.customer_rate, vendor_rate = EXCLUDED.vendor_rate, updated_date = CURRENT_TIMESTAMP;
                            """
                            execute_query(query, (origin, destination, vehicle_type, customer_rate, vendor_rate))
                            added_count += 1
                except (ValueError, TypeError, IndexError):
                    continue
        
        return added_count
        
    except Exception as e:
        st.error(f"❌ Error loading default pricing: {e}")
        return 0


def load_customer_pricing_from_csv(file_path, customer_name):
    """
    Load customer-specific pricing from CSV files
    """
    try:
        # Read CSV file - try tab separator first
        try:
            df = pd.read_csv(file_path, sep='\t', encoding='utf-8', on_bad_lines='skip')
        except:
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
        
        # Get or create customer_id
        customer_query = "SELECT id FROM customers WHERE LOWER(name) LIKE %s LIMIT 1;"
        customer_result = execute_query(customer_query, (f'%{customer_name}%',), fetch=True)
        
        customer_id = None
        if customer_result:
            customer_id = customer_result[0]['id']
        else:
            # Create customer if doesn't exist
            insert_query = "INSERT INTO customers (name) VALUES (%s) RETURNING id;"
            result = execute_query(insert_query, (customer_name.replace('_', ' ').title(),), fetch=True)
            if result:
                customer_id = result[0]['id']
        
        if not customer_id:
            return 0
        
        # Register customer in pricing config
        config_query = """
        INSERT INTO customer_pricing_config (customer_id, customer_name, pricing_type)
        VALUES (%s, %s, 'custom')
        ON CONFLICT (customer_id) DO UPDATE SET updated_date = CURRENT_TIMESTAMP;
        """
        execute_query(config_query, (customer_id, customer_name.replace('_', ' ').title()))
        
        added_count = 0
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        # Determine CSV format based on columns
        if any('VEHICLE TYPE' in str(col).upper() for col in df.columns):
            # Demrico format - vertical format
            vehicle_col = [col for col in df.columns if 'VEHICLE' in str(col).upper()][0]
            origin_col = [col for col in df.columns if 'ORIGIN' in str(col).upper()][0] if any('ORIGIN' in str(col).upper() for col in df.columns) else None
            dest_col = [col for col in df.columns if 'DEST' in str(col).upper()][0] if any('DEST' in str(col).upper() for col in df.columns) else None
            rate_cols = [col for col in df.columns if 'RATE' in str(col).upper() or 'FINAL' in str(col).upper() or 'STRANZ' in str(col).upper()]
            
            for _, row in df.iterrows():
                vehicle_type = str(row.get(vehicle_col, '')).strip()
                origin = str(row.get(origin_col, 'CHENNAI AIRPORT')).strip() if origin_col else 'CHENNAI AIRPORT'
                destination = str(row.get(dest_col, '')).strip() if dest_col else ''
                
                # Get rate from available columns
                rate = None
                for rate_col in rate_cols:
                    if rate_col in row and pd.notna(row[rate_col]):
                        try:
                            rate_val = str(row[rate_col]).strip()
                            if rate_val.upper() != 'NIL' and rate_val != '':
                                rate = float(rate_val)
                                break
                        except:
                            continue
                
                if vehicle_type and destination and rate:
                    try:
                        query = """
                        INSERT INTO customer_specific_pricing (customer_id, origin, destination, vehicle_type, rate)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (customer_id, origin, destination, vehicle_type) 
                        DO UPDATE SET rate = EXCLUDED.rate, updated_date = CURRENT_TIMESTAMP;
                        """
                        execute_query(query, (customer_id, origin, destination, vehicle_type, rate))
                        added_count += 1
                    except:
                        continue
        
        else:
            # Matrix format (World Wild Logistic or Sevenways)
            # Find destination column
            dest_col = None
            for col in df.columns:
                if 'FROM' in str(col).upper() or 'TO' in str(col).upper() or 'IMP' in str(col).upper() or 'EXP' in str(col).upper():
                    dest_col = col
                    break
            
            if not dest_col and len(df.columns) > 1:
                dest_col = df.columns[1]
            
            # Get vehicle type columns
            skip_cols = [df.columns[0], dest_col] if dest_col else [df.columns[0]]
            vehicle_columns = [col for col in df.columns if col not in skip_cols and not any(x in str(col).upper() for x in ['S.NO', 'SL.NO', 'S NO'])]
            
            origin = "CHENNAI CFS"
            
            for _, row in df.iterrows():
                if not dest_col:
                    continue
                    
                destination = str(row[dest_col]).strip()
                
                if pd.isna(destination) or destination == '' or destination == 'nan':
                    continue
                
                for vehicle_col in vehicle_columns:
                    rate = row.get(vehicle_col, None)
                    
                    if pd.notna(rate):
                        try:
                            rate = float(str(rate).replace(',', ''))
                            vehicle_type = str(vehicle_col).strip()
                            
                            # Clean vehicle type name
                            vehicle_type = vehicle_type.split('\n')[0].strip()
                            
                            query = """
                            INSERT INTO customer_specific_pricing (customer_id, origin, destination, vehicle_type, rate)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (customer_id, origin, destination, vehicle_type) 
                            DO UPDATE SET rate = EXCLUDED.rate, updated_date = CURRENT_TIMESTAMP;
                            """
                            execute_query(query, (customer_id, origin, destination, vehicle_type, rate))
                            added_count += 1
                        except (ValueError, TypeError):
                            continue
        
        return added_count
        
    except Exception as e:
        st.error(f"❌ Error loading pricing for {customer_name}: {e}")
        return 0


def get_customer_pricing(customer_id, origin, destination, vehicle_type):
    """
    Get customer-specific pricing if available
    """
    try:
        query = """
        SELECT rate, halting_charge, unloading_free_time, origin, destination, vehicle_type
        FROM customer_specific_pricing
        WHERE customer_id = %s 
          AND (LOWER(origin) = LOWER(%s) OR LOWER(origin) LIKE LOWER(%s))
          AND (LOWER(destination) = LOWER(%s) OR LOWER(destination) LIKE LOWER(%s))
          AND (LOWER(vehicle_type) LIKE LOWER(%s) OR LOWER(vehicle_type) = LOWER(%s))
          AND is_active = TRUE
        LIMIT 1;
        """
        result = execute_query(query, (customer_id, origin, f'%{origin}%', destination, f'%{destination}%', f'%{vehicle_type}%', vehicle_type), fetch=True)
        
        if result:
            return {
                'rate': float(result[0]['rate']),
                'halting_charge': float(result[0]['halting_charge']) if result[0]['halting_charge'] else 0,
                'unloading_free_time': result[0]['unloading_free_time'],
                'origin': result[0]['origin'],
                'destination': result[0]['destination'],
                'vehicle_type': result[0]['vehicle_type'],
                'pricing_type': 'customer_specific'
            }
        
        return None
    
    except Exception as e:
        return None


def get_default_pricing(origin, destination, vehicle_type):
    """
    Get default pricing from airport_to_import_and_export matrix
    """
    try:
        query = """
        SELECT customer_rate, vendor_rate, origin, destination, vehicle_type
        FROM default_pricing
        WHERE (LOWER(origin) = LOWER(%s) OR LOWER(origin) LIKE LOWER(%s))
          AND (LOWER(destination) = LOWER(%s) OR LOWER(destination) LIKE LOWER(%s))
          AND (LOWER(vehicle_type) LIKE LOWER(%s) OR LOWER(vehicle_type) = LOWER(%s))
          AND is_active = TRUE
        LIMIT 1;
        """
        result = execute_query(query, (origin, f'%{origin}%', destination, f'%{destination}%', f'%{vehicle_type}%', vehicle_type), fetch=True)
        
        if result:
            return {
                'rate': float(result[0]['customer_rate']) if result[0]['customer_rate'] else 0,
                'vendor_rate': float(result[0]['vendor_rate']) if result[0]['vendor_rate'] else 0,
                'origin': result[0]['origin'],
                'destination': result[0]['destination'],
                'vehicle_type': result[0]['vehicle_type'],
                'pricing_type': 'default'
            }
        
        return None
    
    except Exception as e:
        return None


def get_pricing_for_customer(customer_id, customer_name, origin, destination, vehicle_type):
    """
    Main function to get pricing for a customer
    First checks for customer-specific pricing, then falls back to default
    """
    # First try customer-specific pricing
    pricing = get_customer_pricing(customer_id, origin, destination, vehicle_type)
    
    if pricing:
        pricing['source'] = f'Customer-specific pricing for {customer_name}'
        return pricing
    
    # Fall back to default pricing
    pricing = get_default_pricing(origin, destination, vehicle_type)
    
    if pricing:
        pricing['source'] = 'Default pricing matrix'
        return pricing
    
    return None


def search_customer_by_name(search_term):
    """
    Search for customers by name
    """
    try:
        query = """
        SELECT id, name, email, phone
        FROM customers
        WHERE LOWER(name) LIKE LOWER(%s)
        ORDER BY name
        LIMIT 10;
        """
        results = execute_query(query, (f'%{search_term}%',), fetch=True)
        return results if results else []
    
    except Exception as e:
        return []


def add_customer_pricing(customer_id, origin, destination, vehicle_type, rate, halting_charge=None, unloading_free_time=None):
    """
    Add or update customer-specific pricing
    """
    try:
        query = """
        INSERT INTO customer_specific_pricing 
        (customer_id, origin, destination, vehicle_type, rate, halting_charge, unloading_free_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (customer_id, origin, destination, vehicle_type) 
        DO UPDATE SET 
            rate = EXCLUDED.rate, 
            halting_charge = EXCLUDED.halting_charge,
            unloading_free_time = EXCLUDED.unloading_free_time,
            updated_date = CURRENT_TIMESTAMP;
        """
        execute_query(query, (customer_id, origin, destination, vehicle_type, rate, halting_charge, unloading_free_time))
        return True
    except Exception as e:
        st.error(f"Error adding pricing: {e}")
        return False


def update_customer_pricing(pricing_id, rate, halting_charge=None, unloading_free_time=None):
    """
    Update existing customer pricing
    """
    try:
        query = """
        UPDATE customer_specific_pricing 
        SET rate = %s, halting_charge = %s, unloading_free_time = %s, updated_date = CURRENT_TIMESTAMP
        WHERE id = %s;
        """
        execute_query(query, (rate, halting_charge, unloading_free_time, pricing_id))
        return True
    except Exception as e:
        st.error(f"Error updating pricing: {e}")
        return False


def delete_customer_pricing(pricing_id):
    """
    Delete customer pricing (soft delete by setting is_active to False)
    """
    try:
        query = "UPDATE customer_specific_pricing SET is_active = FALSE WHERE id = %s;"
        execute_query(query, (pricing_id,))
        return True
    except Exception as e:
        st.error(f"Error deleting pricing: {e}")
        return False


def get_all_customer_pricing(customer_id):
    """
    Get all pricing for a specific customer
    """
    try:
        query = """
        SELECT id, origin, destination, vehicle_type, rate, halting_charge, unloading_free_time
        FROM customer_specific_pricing
        WHERE customer_id = %s AND is_active = TRUE
        ORDER BY origin, destination, vehicle_type;
        """
        results = execute_query(query, (customer_id,), fetch=True)
        return results if results else []
    except Exception as e:
        return []


def get_all_default_pricing():
    """
    Get all default pricing
    """
    try:
        query = """
        SELECT id, origin, destination, vehicle_type, customer_rate, vendor_rate
        FROM default_pricing
        WHERE is_active = TRUE
        ORDER BY origin, destination, vehicle_type;
        """
        results = execute_query(query, fetch=True)
        return results if results else []
    except Exception as e:
        return []


def add_default_pricing(origin, destination, vehicle_type, customer_rate, vendor_rate=None):
    """
    Add or update default pricing
    """
    try:
        query = """
        INSERT INTO default_pricing (origin, destination, vehicle_type, customer_rate, vendor_rate)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (origin, destination, vehicle_type) 
        DO UPDATE SET 
            customer_rate = EXCLUDED.customer_rate,
            vendor_rate = EXCLUDED.vendor_rate,
            updated_date = CURRENT_TIMESTAMP;
        """
        execute_query(query, (origin, destination, vehicle_type, customer_rate, vendor_rate))
        return True
    except Exception as e:
        st.error(f"Error adding default pricing: {e}")
        return False


def delete_default_pricing(pricing_id):
    """
    Delete default pricing (soft delete)
    """
    try:
        query = "UPDATE default_pricing SET is_active = FALSE WHERE id = %s;"
        execute_query(query, (pricing_id,))
        return True
    except Exception as e:
        st.error(f"Error deleting pricing: {e}")
        return False
