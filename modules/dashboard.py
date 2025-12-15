import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta

def show():
    """Display the dashboard module"""
    st.header("📊 Dashboard")
    
    # Date filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        period_type = st.selectbox(
            "Period Type",
            ["Day-wise", "Month-wise", "Year-wise"],
            key="dashboard_period_type"
        )
    
    # Calculate date ranges based on period type
    today = datetime.date.today()
    
    if period_type == "Day-wise":
        from_date = st.date_input("From Date", today, key="dashboard_from_date")
        to_date = st.date_input("To Date", today, key="dashboard_to_date")
    elif period_type == "Month-wise":
        from_date = datetime.date(today.year, today.month, 1)
        to_date = today
        with col2:
            st.info(f"Current Month: {from_date.strftime('%B %Y')}")
    else:  # Year-wise
        from_date = datetime.date(today.year, 1, 1)
        to_date = today
        with col2:
            st.info(f"Current Year: {today.year}")
    
    with col3:
        if st.button("Refresh Dashboard", type="primary"):
            st.rerun()
    
    # Calculate metrics based on selected period
    metrics = calculate_dashboard_metrics(from_date, to_date)
    
    # Display KPI cards
    display_kpi_cards(metrics)
    
    # Display charts
    display_charts(metrics, period_type, from_date, to_date)
    
    # Display detailed tables
    display_detailed_data(from_date, to_date)

def calculate_dashboard_metrics(from_date, to_date):
    """Calculate dashboard metrics for the selected period"""
    
    # Filter data by date range
    period_bookings = [
        b for b in st.session_state.bookings 
        if from_date <= b['pickup_date'] <= to_date
    ]
    
    period_invoices = [
        inv for inv in st.session_state.invoices 
        if from_date <= inv['invoice_date'] <= to_date
    ]
    
    period_payments = [
        p for p in st.session_state.customer_payments 
        if from_date <= p['payment_date'] <= to_date
    ]
    
    period_fuel_logs = [
        f for f in st.session_state.fuel_logs 
        if from_date <= f['date'] <= to_date
    ]
    
    # Calculate metrics
    metrics = {
        'total_bookings': len(period_bookings),
        'confirmed_bookings': len([b for b in period_bookings if b['status'] not in ['Cancelled']]),
        'delivered_bookings': len([b for b in period_bookings if b['status'] in ['Delivered', 'POD Captured']]),
        'cancelled_bookings': len([b for b in period_bookings if b['status'] == 'Cancelled']),
        
        'total_invoices': len(period_invoices),
        'gst_invoices': len([inv for inv in period_invoices if inv['invoice_type'] == 'GST Invoice']),
        'cash_invoices': len([inv for inv in period_invoices if inv['invoice_type'] == 'Cash Invoice']),
        'contract_invoices': len([inv for inv in period_invoices if inv['invoice_type'] == 'Contract Invoice']),
        
        'pending_billings': len([b for b in period_bookings if b['status'] == 'POD Captured' and 
                               not any(inv.get('booking_id') == b['id'] for inv in st.session_state.invoices)]),
        
        'total_revenue': sum(inv['total_amount'] for inv in period_invoices),
        'total_receipts': sum(p['payment_amount'] for p in period_payments),
        
        'outstanding_amount': sum(inv['outstanding_amount'] for inv in st.session_state.invoices),
        
        'fuel_consumption': sum(f['liters'] for f in period_fuel_logs),
        'fuel_cost': sum(f['cost'] for f in period_fuel_logs),
        
        'active_vehicles': len([v for v in st.session_state.vehicles if v.get('status') == 'Active']),
        'available_drivers': len([d for d in st.session_state.drivers if d.get('status') == 'Available']),
        
        # Cash and carry movements
        'cash_carry_movements': len([b for b in period_bookings if b.get('trip_type') == 'Local' and 
                                   any(inv.get('booking_id') == b['id'] and inv['invoice_type'] == 'Cash Invoice' 
                                       for inv in period_invoices)])
    }
    
    return metrics

def display_kpi_cards(metrics):
    """Display KPI cards"""
    st.markdown("### 📈 Key Performance Indicators")
    
    # First row - Bookings and Operations
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Bookings", 
            metrics['total_bookings'],
            delta=f"+{metrics['confirmed_bookings'] - metrics['cancelled_bookings']}"
        )
    
    with col2:
        st.metric(
            "Delivered", 
            metrics['delivered_bookings'],
            delta=f"{(metrics['delivered_bookings']/max(metrics['total_bookings'], 1)*100):.1f}%"
        )
    
    with col3:
        st.metric(
            "Invoices Generated", 
            metrics['total_invoices']
        )
    
    with col4:
        st.metric(
            "Pending Billings", 
            metrics['pending_billings'],
            delta_color="inverse"
        )
    
    # Second row - Financial
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Revenue", 
            f"₹{metrics['total_revenue']:,.0f}"
        )
    
    with col2:
        st.metric(
            "Total Receipts", 
            f"₹{metrics['total_receipts']:,.0f}"
        )
    
    with col3:
        collection_efficiency = (metrics['total_receipts'] / max(metrics['total_revenue'], 1)) * 100
        st.metric(
            "Collection Efficiency", 
            f"{collection_efficiency:.1f}%",
            delta=f"₹{metrics['total_revenue'] - metrics['total_receipts']:,.0f}"
        )
    
    with col4:
        st.metric(
            "Total Outstanding", 
            f"₹{metrics['outstanding_amount']:,.0f}",
            delta_color="inverse"
        )
    
    # Third row - Operations
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Fuel Consumed", 
            f"{metrics['fuel_consumption']:.1f}L"
        )
    
    with col2:
        st.metric(
            "Fuel Cost", 
            f"₹{metrics['fuel_cost']:,.0f}"
        )
    
    with col3:
        st.metric(
            "Active Vehicles", 
            metrics['active_vehicles']
        )
    
    with col4:
        st.metric(
            "Cash & Carry", 
            metrics['cash_carry_movements']
        )

def display_charts(metrics, period_type, from_date, to_date):
    """Display various charts and visualizations"""
    st.markdown("---")
    st.markdown("### 📊 Analytics & Trends")
    
    # Create two columns for charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Revenue vs Receipts Chart
        st.markdown("#### Revenue vs Receipts")
        
        # Get trend data
        if period_type == "Day-wise":
            trend_data = get_daily_trend(from_date, to_date)
            x_axis = "Date"
        elif period_type == "Month-wise":
            trend_data = get_daily_trend(from_date, to_date)
            x_axis = "Date"
        else:
            trend_data = get_monthly_trend(from_date, to_date)
            x_axis = "Month"
        
        if trend_data:
            df_trend = pd.DataFrame(trend_data)
            st.bar_chart(df_trend.set_index(x_axis)[['Revenue', 'Receipts']])
        else:
            st.info("No data available for the selected period")
    
    with col2:
        # Booking Status Distribution
        st.markdown("#### Booking Status Distribution")
        
        period_bookings = [
            b for b in st.session_state.bookings 
            if from_date <= b['pickup_date'] <= to_date
        ]
        
        if period_bookings:
            status_counts = {}
            for booking in period_bookings:
                status = booking['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            if status_counts:
                status_df = pd.DataFrame(list(status_counts.items()), 
                                       columns=['Status', 'Count'])
                st.bar_chart(status_df.set_index('Status'))
        else:
            st.info("No bookings found for the selected period")
    
    # Vehicle fuel consumption chart
    st.markdown("#### Vehicle Fuel Consumption")
    
    period_fuel_logs = [
        f for f in st.session_state.fuel_logs 
        if from_date <= f['date'] <= to_date
    ]
    
    if period_fuel_logs:
        vehicle_fuel = {}
        for log in period_fuel_logs:
            vehicle = log['vehicle_registration']
            if vehicle not in vehicle_fuel:
                vehicle_fuel[vehicle] = {'liters': 0, 'cost': 0}
            vehicle_fuel[vehicle]['liters'] += log['liters']
            vehicle_fuel[vehicle]['cost'] += log['cost']
        
        if vehicle_fuel:
            fuel_df = pd.DataFrame(vehicle_fuel).T
            fuel_df.index.name = 'Vehicle'
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### Fuel Consumption (Liters)")
                st.bar_chart(fuel_df['liters'])
            
            with col2:
                st.markdown("##### Fuel Cost (₹)")
                st.bar_chart(fuel_df['cost'])
    else:
        st.info("No fuel data found for the selected period")

def get_daily_trend(from_date, to_date):
    """Get daily trend data"""
    trend_data = []
    
    current_date = from_date
    while current_date <= to_date:
        day_invoices = [
            inv for inv in st.session_state.invoices 
            if inv['invoice_date'] == current_date
        ]
        
        day_payments = [
            p for p in st.session_state.customer_payments 
            if p['payment_date'] == current_date
        ]
        
        revenue = sum(inv['total_amount'] for inv in day_invoices)
        receipts = sum(p['payment_amount'] for p in day_payments)
        
        trend_data.append({
            'Date': current_date.strftime('%Y-%m-%d'),
            'Revenue': revenue,
            'Receipts': receipts
        })
        
        current_date += datetime.timedelta(days=1)
    
    return trend_data

def get_monthly_trend(from_date, to_date):
    """Get monthly trend data"""
    trend_data = []
    
    current_month = from_date.month
    current_year = from_date.year
    
    while current_year <= to_date.year and (current_year < to_date.year or current_month <= to_date.month):
        month_start = datetime.date(current_year, current_month, 1)
        if current_month == 12:
            month_end = datetime.date(current_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            month_end = datetime.date(current_year, current_month + 1, 1) - datetime.timedelta(days=1)
        
        month_invoices = [
            inv for inv in st.session_state.invoices 
            if month_start <= inv['invoice_date'] <= month_end
        ]
        
        month_payments = [
            p for p in st.session_state.customer_payments 
            if month_start <= p['payment_date'] <= month_end
        ]
        
        revenue = sum(inv['total_amount'] for inv in month_invoices)
        receipts = sum(p['payment_amount'] for p in month_payments)
        
        trend_data.append({
            'Month': datetime.date(current_year, current_month, 1).strftime('%Y-%m'),
            'Revenue': revenue,
            'Receipts': receipts
        })
        
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1
    
    return trend_data

def display_detailed_data(from_date, to_date):
    """Display detailed data tables"""
    st.markdown("---")
    st.markdown("### 📋 Detailed Data")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Recent Bookings", "Recent Invoices", "Recent Payments", "Vehicle Status"])
    
    with tab1:
        st.markdown("#### Recent Bookings")
        recent_bookings = [
            b for b in st.session_state.bookings 
            if from_date <= b['pickup_date'] <= to_date
        ]
        recent_bookings = sorted(recent_bookings, key=lambda x: x['created_date'], reverse=True)[:10]
        
        if recent_bookings:
            booking_data = []
            for booking in recent_bookings:
                status_color = {
                    'Created': '🟡',
                    'Confirmed': '🔵',
                    'Dispatched': '🟠',
                    'In Transit': '🟣',
                    'Delivered': '🟢',
                    'POD Captured': '✅',
                    'Cancelled': '❌'
                }.get(booking['status'], '⚪')
                
                booking_data.append({
                    'Status': f"{status_color} {booking['status']}",
                    'Booking Number': booking['booking_number'],
                    'Customer': booking['customer_name'],
                    'Route': f"{booking['pickup_location']} → {booking['delivery_location']}",
                    'Pickup Date': booking['pickup_date'],
                    'Amount': f"₹{booking['total_amount']:,.2f}"
                })
            
            df_bookings = pd.DataFrame(booking_data)
            st.dataframe(df_bookings, use_container_width=True)
        else:
            st.info("No recent bookings found")
    
    with tab2:
        st.markdown("#### Recent Invoices")
        recent_invoices = [
            inv for inv in st.session_state.invoices 
            if from_date <= inv['invoice_date'] <= to_date
        ]
        recent_invoices = sorted(recent_invoices, key=lambda x: x['created_date'], reverse=True)[:10]
        
        if recent_invoices:
            invoice_data = []
            for invoice in recent_invoices:
                days_overdue = max(0, (datetime.datetime.now().date() - invoice['due_date']).days)
                
                if invoice['outstanding_amount'] <= 0:
                    status_color = "🟢 Paid"
                elif days_overdue == 0:
                    status_color = "🟡 Current"
                elif days_overdue <= 15:
                    status_color = "🟠 Due Soon"
                else:
                    status_color = "🔴 Overdue"
                
                invoice_data.append({
                    'Status': status_color,
                    'Invoice Number': invoice['invoice_number'],
                    'Type': invoice['invoice_type'],
                    'Customer': invoice['customer_name'],
                    'Date': invoice['invoice_date'],
                    'Amount': f"₹{invoice['total_amount']:,.2f}",
                    'Outstanding': f"₹{invoice['outstanding_amount']:,.2f}"
                })
            
            df_invoices = pd.DataFrame(invoice_data)
            st.dataframe(df_invoices, use_container_width=True)
        else:
            st.info("No recent invoices found")
    
    with tab3:
        st.markdown("#### Recent Payments")
        recent_payments = [
            p for p in st.session_state.customer_payments 
            if from_date <= p['payment_date'] <= to_date
        ]
        recent_payments = sorted(recent_payments, key=lambda x: x['created_date'], reverse=True)[:10]
        
        if recent_payments:
            payment_data = []
            for payment in recent_payments:
                allocation_icon = "✅" if payment['allocation_status'] == 'Allocated' else "⏳"
                
                payment_data.append({
                    'Status': f"{allocation_icon} {payment['allocation_status']}",
                    'Customer': payment['customer_name'],
                    'Date': payment['payment_date'],
                    'Amount': f"₹{payment['payment_amount']:,.2f}",
                    'Method': payment['payment_method'],
                    'Reference': payment.get('reference_number', '')
                })
            
            df_payments = pd.DataFrame(payment_data)
            st.dataframe(df_payments, use_container_width=True)
        else:
            st.info("No recent payments found")
    
    with tab4:
        st.markdown("#### Vehicle Status")
        
        if st.session_state.vehicles:
            vehicle_data = []
            for vehicle in st.session_state.vehicles:
                status_icon = {
                    'Active': '🟢',
                    'Maintenance': '🟡',
                    'Inactive': '🔴'
                }.get(vehicle.get('status', 'Active'), '⚪')
                
                # Get latest odometer reading
                vehicle_odometer = [log for log in st.session_state.odometer_logs 
                                 if log['vehicle_registration'] == vehicle['registration_number']]
                
                if vehicle_odometer:
                    latest_reading = max(vehicle_odometer, key=lambda x: x['date'])
                    last_reading = f"{latest_reading['kilometer_reading']:,} KM"
                    last_reading_date = latest_reading['date']
                else:
                    last_reading = "No data"
                    last_reading_date = None
                
                vehicle_data.append({
                    'Status': f"{status_icon} {vehicle.get('status', 'Active')}",
                    'Registration': vehicle['registration_number'],
                    'Type': vehicle['vehicle_type'],
                    'Fuel Type': vehicle.get('fuel_type', 'N/A'),
                    'Driver': vehicle.get('linked_driver', 'Not Assigned'),
                    'Last Reading': last_reading,
                    'Last Updated': last_reading_date or 'N/A'
                })
            
            df_vehicles = pd.DataFrame(vehicle_data)
            st.dataframe(df_vehicles, use_container_width=True)
        else:
            st.info("No vehicles found")