import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import uuid
from .utils import searchable_selectbox, static_selectbox

def show():
    """Display the vehicle master module"""
    st.header("🚛 Vehicle Master")
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Vehicle & Driver Management", 
        "Fuel Logs", 
        "Odometer Logs", 
        "Vehicle Reports",
        "Maintenance"
    ])
    
    with tab1:
        vehicle_driver_management()
    
    with tab2:
        fuel_logs()
    
    with tab3:
        odometer_logs()
    
    with tab4:
        vehicle_reports()
    
    with tab5:
        st.info("Maintenance tracking feature coming soon!")

def vehicle_driver_management():
    """Manage vehicles and drivers"""
    # Load vehicles and drivers from database if not loaded
    from database import load_data_when_needed
    load_data_when_needed('vehicles')
    load_data_when_needed('drivers')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Vehicles")
        
        # Add new vehicle form
        with st.expander("Add New Vehicle"):
            add_vehicle_form()
        
        # Display existing vehicles
        if st.session_state.vehicles:
            for vehicle in st.session_state.vehicles:
                with st.expander(f"🚛 {vehicle['registration_number']} - {vehicle['vehicle_type']}"):
                    st.write(f"**Registration:** {vehicle['registration_number']}")
                    st.write(f"**Type:** {vehicle['vehicle_type']}")
                    st.write(f"**Length:** {vehicle.get('vehicle_length', 'N/A')}")
                    st.write(f"**Fuel Type:** {vehicle.get('fuel_type', 'N/A')}")
                    st.write(f"**Status:** {vehicle.get('status', 'Active')}")
                    
                    if vehicle.get('linked_driver'):
                        st.write(f"**Linked Driver:** {vehicle['linked_driver']}")
                    
                    # Status update
                    new_status = st.selectbox(
                        "Update Status",
                        ["Active", "Maintenance", "Inactive"],
                        index=["Active", "Maintenance", "Inactive"].index(vehicle.get('status', 'Active')),
                        key=f"status_{vehicle['id']}"
                    )
                    
                    if st.button(f"Update Status", key=f"update_{vehicle['id']}"):
                        vehicle['status'] = new_status
                        st.success("Status updated!")
                        st.rerun()
        else:
            st.info("No vehicles found. Add your first vehicle above.")
    
    with col2:
        st.markdown("### Drivers")
        
        # Add new driver form
        with st.expander("Add New Driver"):
            add_driver_form()
        
        # Display existing drivers
        if st.session_state.drivers:
            for driver in st.session_state.drivers:
                with st.expander(f"👤 {driver['name']} - {driver.get('license_number', 'N/A')}"):
                    st.write(f"**Name:** {driver['name']}")
                    st.write(f"**License Number:** {driver.get('license_number', 'N/A')}")
                    st.write(f"**Phone:** {driver.get('phone', 'N/A')}")
                    st.write(f"**Status:** {driver.get('status', 'Available')}")
                    
                    # Status update
                    new_status = st.selectbox(
                        "Update Status",
                        ["Available", "On Trip", "On Leave", "Inactive"],
                        index=["Available", "On Trip", "On Leave", "Inactive"].index(driver.get('status', 'Available')),
                        key=f"driver_status_{driver['id']}"
                    )
                    
                    if st.button(f"Update Status", key=f"driver_update_{driver['id']}"):
                        driver['status'] = new_status
                        st.success("Driver status updated!")
                        st.rerun()
        else:
            st.info("No drivers found. Add your first driver above.")

def add_vehicle_form():
    """Form to add new vehicle"""
    col1, col2 = st.columns(2)
    
    with col1:
        registration_number = st.text_input("Registration Number*", key="new_vehicle_reg")
        vehicle_type = static_selectbox(
            "Vehicle Type*",
            ["Mini Truck", "Small Truck", "Medium Truck", "Large Truck", "Container", "Trailer"],
            key="new_vehicle_type"
        )
        vehicle_length = st.text_input("Vehicle Length", key="new_vehicle_length")
    
    with col2:
        fuel_type = static_selectbox(
            "Fuel Type",
            ["Diesel", "Petrol", "CNG", "Electric"],
            key="new_vehicle_fuel"
        )
        
        # Driver assignment
        available_drivers = ["None"] + [d['name'] for d in st.session_state.drivers if d.get('status') == 'Available']
        linked_driver = searchable_selectbox("Link Driver", available_drivers, key="new_vehicle_driver")
    
    if st.button("Add Vehicle"):
        if not registration_number:
            st.error("Registration number is required")
            return
        
        vehicle = {
            'id': str(uuid.uuid4()),
            'registration_number': registration_number,
            'vehicle_type': vehicle_type,
            'vehicle_length': vehicle_length,
            'fuel_type': fuel_type,
            'linked_driver': linked_driver if linked_driver != "None" else None,
            'status': 'Active',
            'created_date': datetime.datetime.now()
        }
        
        # Save to database
        from app import save_vehicle
        if save_vehicle(vehicle):
            # Refresh cached data properly
            from database import refresh_data, get_cached_data
            refresh_data('vehicles')
            st.session_state.vehicles = get_cached_data('vehicles')
            
            st.success(f"Vehicle {registration_number} added successfully!")
            
            # Clear form
            for key in list(st.session_state.keys()):
                if key.startswith('new_vehicle_'):
                    del st.session_state[key]
            
            st.rerun()
        else:
            st.error("Failed to save vehicle. Please try again.")

def add_driver_form():
    """Form to add new driver"""
    col1, col2 = st.columns(2)
    
    with col1:
        driver_name = st.text_input("Driver Name*", key="new_driver_name")
        license_number = st.text_input("License Number", key="new_driver_license")
    
    with col2:
        driver_phone = st.text_input("Phone Number", key="new_driver_phone")
        driver_address = st.text_area("Address", key="new_driver_address")
    
    if st.button("Add Driver"):
        if not driver_name:
            st.error("Driver name is required")
            return
        
        driver = {
            'id': str(uuid.uuid4()),
            'name': driver_name,
            'license_number': license_number,
            'phone': driver_phone,
            'address': driver_address,
            'status': 'Available',
            'created_date': datetime.datetime.now()
        }
        
        # Save to database
        from app import save_driver
        if save_driver(driver):
            # Refresh cached data properly
            from database import refresh_data, get_cached_data
            refresh_data('drivers')
            st.session_state.drivers = get_cached_data('drivers')
            
            st.success(f"Driver {driver_name} added successfully!")
            
            # Clear form
            for key in list(st.session_state.keys()):
                if key.startswith('new_driver_'):
                    del st.session_state[key]
            
            st.rerun()
        else:
            st.error("Failed to save driver. Please try again.")

def fuel_logs():
    """Manage fuel logs"""
    # Load data when needed
    from database import load_data_when_needed
    load_data_when_needed('vehicles')
    load_data_when_needed('fuel_logs')
    
    st.subheader("Fuel Logs")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Add Fuel Entry")
        
        col1a, col1b, col1c = st.columns(3)
        
        with col1a:
            fuel_date = st.date_input("Date*", value=datetime.datetime.now().date(), key="fuel_date")
            
            if st.session_state.vehicles:
                vehicle_options = [v['registration_number'] for v in st.session_state.vehicles]
                selected_vehicle = st.selectbox("Vehicle*", vehicle_options, key="fuel_vehicle")
            else:
                st.warning("No vehicles found")
                return
        
        with col1b:
            fuel_liters = st.number_input("Liters*", min_value=0.0, value=0.0, key="fuel_liters")
            fuel_cost = st.number_input("Cost (₹)*", min_value=0.0, value=0.0, key="fuel_cost")
        
        with col1c:
            fuel_source = st.text_input("Source (Pump/Station)", key="fuel_source")
            odometer_reading = st.number_input("Odometer Reading (KM)", min_value=0, value=0, key="fuel_odometer")
        
        remarks = st.text_area("Remarks", key="fuel_remarks")
        
        if st.button("Add Fuel Entry", type="primary"):
            if not selected_vehicle or fuel_liters <= 0 or fuel_cost <= 0:
                st.error("Vehicle, liters, and cost are required")
                return
            
            fuel_log = {
                'id': str(uuid.uuid4()),
                'date': fuel_date,
                'vehicle_registration': selected_vehicle,
                'liters': fuel_liters,
                'cost': fuel_cost,
                'cost_per_liter': fuel_cost / fuel_liters,
                'source': fuel_source,
                'odometer_reading': odometer_reading,
                'remarks': remarks,
                'created_date': datetime.datetime.now()
            }
            
            # Save to database
            from app import save_fuel_log
            if save_fuel_log(fuel_log):
                # Add to session state for immediate display
                if 'fuel_logs' not in st.session_state:
                    st.session_state.fuel_logs = []
                st.session_state.fuel_logs.append(fuel_log)
                
                st.success("Fuel entry added successfully!")
                
                # Clear form
                for key in list(st.session_state.keys()):
                    if key.startswith('fuel_'):
                        del st.session_state[key]
                
                st.rerun()
            else:
                st.error("Failed to save fuel entry. Please try again.")
            for key in list(st.session_state.keys()):
                if key.startswith('fuel_'):
                    del st.session_state[key]
            
            st.rerun()
    
    with col2:
        st.markdown("### Recent Fuel Entries")
        
        recent_logs = sorted(st.session_state.fuel_logs, key=lambda x: x['date'], reverse=True)[:5]
        
        for log in recent_logs:
            with st.container():
                st.write(f"**{log['vehicle_registration']}** - {log['date']}")
                st.write(f"₹{log['cost']:,.2f} for {log['liters']:.2f}L")
                st.write(f"Rate: ₹{log['cost_per_liter']:.2f}/L")
                st.markdown("---")
    
    # Display all fuel logs
    if st.session_state.fuel_logs:
        st.markdown("### All Fuel Logs")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            vehicle_filter = st.selectbox(
                "Filter by Vehicle",
                ["All"] + [v['registration_number'] for v in st.session_state.vehicles],
                key="fuel_filter_vehicle"
            )
        
        with col2:
            from_date = st.date_input(
                "From Date",
                value=datetime.datetime.now() - datetime.timedelta(days=30),
                key="fuel_from_date"
            )
        
        with col3:
            to_date = st.date_input(
                "To Date",
                value=datetime.datetime.now().date(),
                key="fuel_to_date"
            )
        
        # Filter and display logs
        filtered_logs = st.session_state.fuel_logs
        
        if vehicle_filter != "All":
            filtered_logs = [log for log in filtered_logs if log['vehicle_registration'] == vehicle_filter]
        
        filtered_logs = [log for log in filtered_logs if from_date <= log['date'] <= to_date]
        
        if filtered_logs:
            log_data = []
            for log in filtered_logs:
                log_data.append({
                    'Date': log['date'],
                    'Vehicle': log['vehicle_registration'],
                    'Liters': f"{log['liters']:.2f}",
                    'Cost': f"₹{log['cost']:,.2f}",
                    'Rate/L': f"₹{log['cost_per_liter']:.2f}",
                    'Source': log.get('source', ''),
                    'Odometer': log.get('odometer_reading', 0),
                    'Remarks': log.get('remarks', '')
                })
            
            df = pd.DataFrame(log_data)
            st.dataframe(df, use_container_width=True)
            
            # Summary
            total_cost = sum(log['cost'] for log in filtered_logs)
            total_liters = sum(log['liters'] for log in filtered_logs)
            avg_rate = total_cost / total_liters if total_liters > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Cost", f"₹{total_cost:,.2f}")
            with col2:
                st.metric("Total Liters", f"{total_liters:.2f}")
            with col3:
                st.metric("Average Rate", f"₹{avg_rate:.2f}/L")

def odometer_logs():
    """Manage odometer logs"""
    # Load data when needed
    from database import load_data_when_needed
    load_data_when_needed('vehicles')
    load_data_when_needed('odometer_logs')
    
    st.subheader("Odometer Logs")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Add Odometer Reading")
        
        col1a, col1b = st.columns(2)
        
        with col1a:
            odometer_date = st.date_input("Date*", value=datetime.datetime.now().date(), key="odometer_date")
            
            if st.session_state.vehicles:
                vehicle_options = [v['registration_number'] for v in st.session_state.vehicles]
                selected_vehicle = st.selectbox("Vehicle*", vehicle_options, key="odometer_vehicle")
            else:
                st.warning("No vehicles found")
                return
        
        with col1b:
            kilometer_reading = st.number_input("Kilometer Reading*", min_value=0, value=0, key="odometer_km")
            reading_type = st.selectbox(
                "Reading Type",
                ["Regular", "Trip Start", "Trip End", "Maintenance"],
                key="odometer_type"
            )
        
        notes = st.text_area("Notes", key="odometer_notes")
        
        if st.button("Add Odometer Reading", type="primary"):
            if not selected_vehicle or kilometer_reading <= 0:
                st.error("Vehicle and kilometer reading are required")
                return
            
            # Check for duplicate or decreasing readings
            existing_readings = [log for log in st.session_state.odometer_logs 
                               if log['vehicle_registration'] == selected_vehicle]
            
            if existing_readings:
                last_reading = max(existing_readings, key=lambda x: x['kilometer_reading'])
                if kilometer_reading <= last_reading['kilometer_reading']:
                    st.warning(f"Warning: This reading ({kilometer_reading}) is not higher than the last reading ({last_reading['kilometer_reading']})")
            
            odometer_log = {
                'id': str(uuid.uuid4()),
                'date': odometer_date,
                'vehicle_registration': selected_vehicle,
                'kilometer_reading': kilometer_reading,
                'reading_type': reading_type,
                'notes': notes,
                'created_date': datetime.datetime.now()
            }
            
            # Save to database
            from app import save_odometer_log
            if save_odometer_log(odometer_log):
                # Add to session state for immediate display
                if 'odometer_logs' not in st.session_state:
                    st.session_state.odometer_logs = []
                st.session_state.odometer_logs.append(odometer_log)
                
                st.success("Odometer reading added successfully!")
            else:
                st.error("Failed to save odometer reading. Please try again.")
            
            # Clear form
            for key in list(st.session_state.keys()):
                if key.startswith('odometer_'):
                    del st.session_state[key]
            
            st.rerun()
    
    with col2:
        st.markdown("### Recent Readings")
        
        recent_logs = sorted(st.session_state.odometer_logs, key=lambda x: x['date'], reverse=True)[:5]
        
        for log in recent_logs:
            st.write(f"**{log['vehicle_registration']}**")
            st.write(f"{log['kilometer_reading']:,} KM - {log['date']}")
            st.write(f"Type: {log['reading_type']}")
            st.markdown("---")
    
    # Display all odometer logs
    if st.session_state.odometer_logs:
        st.markdown("### All Odometer Logs")
        
        # Filter and display
        vehicle_filter = st.selectbox(
            "Filter by Vehicle",
            ["All"] + [v['registration_number'] for v in st.session_state.vehicles],
            key="odometer_filter_vehicle"
        )
        
        filtered_logs = st.session_state.odometer_logs
        
        if vehicle_filter != "All":
            filtered_logs = [log for log in filtered_logs if log['vehicle_registration'] == vehicle_filter]
        
        if filtered_logs:
            log_data = []
            for log in sorted(filtered_logs, key=lambda x: x['date'], reverse=True):
                log_data.append({
                    'Date': log['date'],
                    'Vehicle': log['vehicle_registration'],
                    'Reading (KM)': f"{log['kilometer_reading']:,}",
                    'Type': log['reading_type'],
                    'Notes': log.get('notes', '')
                })
            
            df = pd.DataFrame(log_data)
            st.dataframe(df, use_container_width=True)

def vehicle_reports():
    """Generate vehicle performance reports"""
    st.subheader("Vehicle Reports")
    
    if not st.session_state.vehicles:
        st.info("No vehicles found.")
        return
    
    # Month selection
    col1, col2 = st.columns(2)
    
    with col1:
        report_month = st.selectbox("Month", list(range(1, 13)), index=datetime.datetime.now().month - 1, 
                                   format_func=lambda x: datetime.date(2000, x, 1).strftime('%B'),
                                   key="report_month")
        report_year = st.selectbox("Year", [2023, 2024, 2025, 2026], index=1, key="report_year")
    
    with col2:
        if st.button("Generate Report", type="primary"):
            generate_vehicle_performance_report(report_month, report_year)

def generate_vehicle_performance_report(month, year):
    """Generate vehicle performance report"""
    
    # Date range for the month
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    
    st.markdown(f"## Vehicle Performance Report - {datetime.date(year, month, 1).strftime('%B %Y')}")
    
    vehicle_reports = []
    
    for vehicle in st.session_state.vehicles:
        # Get fuel logs for the period
        vehicle_fuel_logs = [log for log in st.session_state.fuel_logs 
                           if log['vehicle_registration'] == vehicle['registration_number'] and 
                           start_date <= log['date'] <= end_date]
        
        # Get odometer logs for the period
        vehicle_odometer_logs = [log for log in st.session_state.odometer_logs 
                               if log['vehicle_registration'] == vehicle['registration_number'] and 
                               start_date <= log['date'] <= end_date]
        
        if vehicle_fuel_logs or vehicle_odometer_logs:
            # Calculate metrics
            total_fuel_consumed = sum(log['liters'] for log in vehicle_fuel_logs)
            total_fuel_cost = sum(log['cost'] for log in vehicle_fuel_logs)
            
            # Calculate kilometers run
            if len(vehicle_odometer_logs) >= 2:
                sorted_readings = sorted(vehicle_odometer_logs, key=lambda x: x['date'])
                start_reading = sorted_readings[0]['kilometer_reading']
                end_reading = sorted_readings[-1]['kilometer_reading']
                total_kilometers = end_reading - start_reading
            else:
                total_kilometers = 0
            
            # Calculate efficiency
            if total_fuel_consumed > 0 and total_kilometers > 0:
                kmpl = total_kilometers / total_fuel_consumed
                fuel_per_100km = (total_fuel_consumed / total_kilometers) * 100
                
                # Check for overutilization (20% deviation from baseline)
                baseline_kmpl = 6.0
                deviation = abs(kmpl - baseline_kmpl) / baseline_kmpl
                overutilization_flag = deviation > 0.20
            else:
                kmpl = 0
                fuel_per_100km = 0
                overutilization_flag = False
            
            vehicle_reports.append({
                'Vehicle': vehicle['registration_number'],
                'Type': vehicle['vehicle_type'],
                'Total KM': total_kilometers,
                'Fuel Consumed (L)': f"{total_fuel_consumed:.2f}",
                'Fuel Cost': f"₹{total_fuel_cost:,.2f}",
                'KMPL': f"{kmpl:.2f}",
                'L/100KM': f"{fuel_per_100km:.2f}",
                'Overutilization': "🔴 Yes" if overutilization_flag else "🟢 No",
                'Fuel Entries': len(vehicle_fuel_logs),
                'Odometer Entries': len(vehicle_odometer_logs)
            })
    
    if vehicle_reports:
        df = pd.DataFrame(vehicle_reports)
        st.dataframe(df, use_container_width=True)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_vehicles = len(vehicle_reports)
            st.metric("Vehicles Tracked", total_vehicles)
        
        with col2:
            total_km = sum(int(report['Total KM']) for report in vehicle_reports)
            st.metric("Total KM", f"{total_km:,.0f}")
        
        with col3:
            total_fuel = sum(float(report['Fuel Consumed (L)']) for report in vehicle_reports)
            st.metric("Total Fuel (L)", f"{total_fuel:.2f}")
        
        with col4:
            overutilization_count = sum(1 for report in vehicle_reports if "Yes" in report['Overutilization'])
            st.metric("Overutilization Issues", overutilization_count, delta_color="inverse")
        
        # Export option
        if st.button("Export Report to CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"vehicle_report_{year}{month:02d}.csv",
                mime="text/csv"
            )
    else:
        st.info("No vehicle data found for the selected period.")