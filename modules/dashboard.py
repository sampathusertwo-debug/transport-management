import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
from .quotations import safe_get_date

def show():
    """Display the dashboard module"""
    # Load only dashboard-relevant data when needed
    from database import load_data_when_needed
    
    # Load minimal data needed for dashboard
    bookings = load_data_when_needed('bookings')
    invoices = load_data_when_needed('invoices')
    customer_payments = load_data_when_needed('customer_payments')
    customers = load_data_when_needed('customers')
    
    # Period filter
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('''
        <div style="margin-bottom: 1rem;">
            <span style="color: #64748b; font-weight: 500; margin-right: 1rem;">Period:</span>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        period_type = st.selectbox(
            "Period Type",
            ["This Year", "This Month", "Last Month", "Custom Range"],
            key="dashboard_period_type",
            label_visibility="collapsed"
        )
    
    # Calculate metrics
    today = datetime.date.today()
    if period_type == "This Month":
        from_date = datetime.date(today.year, today.month, 1)
        to_date = today
    elif period_type == "Last Month":
        last_month = today.replace(day=1) - timedelta(days=1)
        from_date = datetime.date(last_month.year, last_month.month, 1)
        to_date = last_month
    elif period_type == "This Year":
        from_date = datetime.date(today.year, 1, 1)
        to_date = today
    else:  # Custom Range
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From Date", today - timedelta(days=30), key="dashboard_from_date")
        with col2:
            to_date = st.date_input("To Date", today, key="dashboard_to_date")
    
    # Calculate dashboard metrics
    metrics = calculate_dashboard_metrics(from_date, to_date)
    
    # Display modern metric cards
    display_modern_metric_cards(metrics)
    
    # Show helpful message if no data found
    if (metrics['total_bookings'] == 0 and metrics['total_revenue'] == 0 and 
        metrics['total_receipts'] == 0 and metrics['pending_billings'] == 0):
        st.info(f"No data found for the selected period ({metrics['from_date'].strftime('%d %b %Y')} to {metrics['to_date'].strftime('%d %b %Y')}). Try changing the period filter above or check if there are bookings for different date ranges.")
    
    # Display recent bookings table
    display_recent_bookings_table(from_date, to_date)

    # Customer Outstanding Report
    display_customer_outstanding_report()
    display_detailed_data(from_date, to_date)

def calculate_dashboard_metrics(from_date, to_date):
    """Calculate dashboard metrics for the given date range"""
    # Ensure data is available in session state
    bookings_data = getattr(st.session_state, 'bookings', [])
    invoices_data = getattr(st.session_state, 'invoices', [])
    payments_data = getattr(st.session_state, 'customer_payments', [])
    
    # Filter data by date range with safe date conversion
    filtered_bookings = [
        b for b in bookings_data 
        if from_date <= safe_get_date(b.get('created_date', datetime.datetime.now())) <= to_date
    ]
    
    filtered_invoices = [
        i for i in invoices_data 
        if from_date <= safe_get_date(i.get('created_date', datetime.datetime.now())) <= to_date
    ]
    
    filtered_payments = [
        p for p in payments_data 
        if from_date <= safe_get_date(p.get('created_date', datetime.datetime.now())) <= to_date
    ]
    
    # Calculate metrics
    total_bookings = len(filtered_bookings)
    # For simplified bookings, we don't track total_amount, so calculate from invoices instead
    total_revenue = sum(invoice.get('total_amount', invoice.get('net_amount', 0)) for invoice in filtered_invoices)
    total_receipts = sum(payment.get('payment_amount', payment.get('amount', 0)) for payment in filtered_payments)
    
    # Calculate pending billings (bookings that are delivered but not invoiced)
    pending_billings = len([
        b for b in filtered_bookings 
        if b.get('status') in ['DELIVERED', 'POD Generated'] and 
        not any(i.get('booking_id') == b.get('id') for i in invoices_data)
    ])
    
    return {
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'total_receipts': total_receipts,
        'pending_billings': pending_billings,
        'from_date': from_date,
        'to_date': to_date
    }

def display_modern_metric_cards(metrics):
    """Display modern styled metric cards"""
    # Metric cards with modern styling
    st.markdown('''
    <div class="metric-row">
        <div class="metric-card metric-card-purple">
            <div class="metric-title">Total Bookings</div>
            <div class="metric-value">{}</div>
        </div>
        <div class="metric-card metric-card-pink">
            <div class="metric-title">Total Revenue</div>
            <div class="metric-value">₹{:,}</div>
        </div>
        <div class="metric-card metric-card-blue">
            <div class="metric-title">Total Receipts</div>
            <div class="metric-value">₹{:,}</div>
        </div>
        <div class="metric-card metric-card-orange">
            <div class="metric-title">Pending Billings</div>
            <div class="metric-value">{}</div>
        </div>
    </div>
    '''.format(
        metrics['total_bookings'],
        int(metrics['total_revenue']),
        int(metrics['total_receipts']), 
        metrics['pending_billings']
    ), unsafe_allow_html=True)

def display_recent_bookings_table(from_date, to_date):
    """Display recent bookings in a modern table format"""
    st.markdown('''
    <div class="section-header">
        📦 Recent Bookings
    </div>
    ''', unsafe_allow_html=True)
    
    bookings_data = getattr(st.session_state, 'bookings', [])
    if not bookings_data:
        st.info("No bookings found.")
        return
    
    # Get recent bookings (last 10)
    recent_bookings = sorted(bookings_data, 
                           key=lambda x: x.get('created_date', datetime.datetime.now()), 
                           reverse=True)[:10]
    
    # Prepare data for display
    booking_data = []
    for booking in recent_bookings:
        # Format status with styling
        status = booking.get('status', 'Created')
        if status == 'DELIVERED':
            status_html = '<span class="status-delivered">DELIVERED</span>'
        elif status == 'DISPATCHED':
            status_html = '<span class="status-dispatched">DISPATCHED</span>'
        elif status == 'CONFIRMED':
            status_html = '<span class="status-confirmed">CONFIRMED</span>'
        else:
            status_html = status
            
        booking_data.append({
            'Booking #': booking['booking_number'],
            'Customer': booking.get('customer', 'N/A'),
            'Status': status_html,
            'Route': f"{booking.get('route_from', 'N/A')} → {booking.get('route_to', 'N/A')}",
            'Date': booking.get('booking_date', datetime.date.today()).strftime('%d-%b-%Y') if isinstance(booking.get('booking_date'), datetime.date) else str(booking.get('booking_date', ''))
        })
    
    if booking_data:
        df = pd.DataFrame(booking_data)
        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("No recent bookings to display.")


def display_customer_outstanding_report():
    """Display customer outstanding report"""
    st.markdown("---")
    st.markdown('''
    <div class="section-header">
        💰 Customer Outstanding Report
    </div>
    ''', unsafe_allow_html=True)
    
    # Calculate outstanding amounts for each customer
    customer_outstanding = {}
    
    # Get all customers
    customers_data = getattr(st.session_state, 'customers', [])
    for customer in customers_data:
        customer_outstanding[customer['name']] = {
            'customer_id': customer['id'],
            'customer_name': customer['name'],
            'total_invoices': 0,
            'total_amount': 0,
            'outstanding_amount': 0,
            'paid_amount': 0,
            'overdue_amount': 0,
            'invoices': []
        }
    
    # Calculate outstanding from invoices
    invoices_data = getattr(st.session_state, 'invoices', [])
    for invoice in invoices_data:
        customer_name = invoice['customer_name']
        if customer_name in customer_outstanding:
            customer_outstanding[customer_name]['total_invoices'] += 1
            customer_outstanding[customer_name]['total_amount'] += invoice['total_amount']
            customer_outstanding[customer_name]['outstanding_amount'] += invoice.get('outstanding_amount', invoice['total_amount'])
            customer_outstanding[customer_name]['paid_amount'] += invoice['total_amount'] - invoice.get('outstanding_amount', invoice['total_amount'])
            
            # Check if overdue
            if (invoice.get('due_date') and 
                datetime.datetime.now().date() > invoice['due_date'] and 
                invoice.get('outstanding_amount', invoice['total_amount']) > 0):
                customer_outstanding[customer_name]['overdue_amount'] += invoice.get('outstanding_amount', invoice['total_amount'])
            
            customer_outstanding[customer_name]['invoices'].append(invoice)
    
    # Filter customers with outstanding amounts
    customers_with_outstanding = {k: v for k, v in customer_outstanding.items() if v['outstanding_amount'] > 0}
    
    if not customers_with_outstanding:
        st.success("🎉 No outstanding amounts! All customers are up to date with payments.")
        return
    
    # Customer selection for detailed view
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_customer = st.selectbox(
            "Select Customer for Detailed Report",
            ["All Customers"] + list(customers_with_outstanding.keys()),
            key="outstanding_customer_select"
        )
    
    with col2:
        if st.button("Refresh Outstanding", type="primary"):
            st.rerun()
    
    if selected_customer == "All Customers":
        # Summary table for all customers
        summary_data = []
        total_outstanding = 0
        total_overdue = 0
        
        for customer_name, data in customers_with_outstanding.items():
            summary_data.append({
                'Customer': customer_name,
                'Total Invoices': data['total_invoices'],
                'Total Amount': f"₹{data['total_amount']:,.2f}",
                'Paid Amount': f"₹{data['paid_amount']:,.2f}",
                'Outstanding': f"₹{data['outstanding_amount']:,.2f}",
                'Overdue': f"₹{data['overdue_amount']:,.2f}" if data['overdue_amount'] > 0 else "₹0.00"
            })
            total_outstanding += data['outstanding_amount']
            total_overdue += data['overdue_amount']
        
        # Display summary metrics
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("Total Outstanding", f"₹{total_outstanding:,.2f}")
        with metric_col2:
            st.metric("Total Overdue", f"₹{total_overdue:,.2f}", delta_color="inverse")
        with metric_col3:
            st.metric("Customers with Outstanding", len(customers_with_outstanding))
        
        st.markdown("**Outstanding Summary by Customer:**")
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary, use_container_width=True)
        
        # Export option
        if st.button("Export Outstanding Report"):
            csv = df_summary.to_csv(index=False)
            st.download_button(
                label="Download Outstanding Report CSV",
                data=csv,
                file_name=f"customer_outstanding_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    else:
        # Detailed view for selected customer
        customer_data = customers_with_outstanding[selected_customer]
        
        st.markdown(f"**Outstanding Details for: {selected_customer}**")
        
        # Customer metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Invoices", customer_data['total_invoices'])
        with col2:
            st.metric("Outstanding Amount", f"₹{customer_data['outstanding_amount']:,.2f}")
        with col3:
            st.metric("Overdue Amount", f"₹{customer_data['overdue_amount']:,.2f}", delta_color="inverse")
        with col4:
            collection_rate = ((customer_data['paid_amount'] / customer_data['total_amount']) * 100) if customer_data['total_amount'] > 0 else 0
            st.metric("Collection Rate", f"{collection_rate:.1f}%")
        
        # Invoice details
        st.markdown("**Invoice Details:**")
        invoice_details = []
        
        for invoice in customer_data['invoices']:
            if invoice.get('outstanding_amount', invoice['total_amount']) > 0:  # Only show unpaid invoices
                days_overdue = 0
                if invoice.get('due_date'):
                    days_overdue = max(0, (datetime.datetime.now().date() - invoice['due_date']).days)
                
                status = "🔴 Overdue" if days_overdue > 0 else "🟡 Due"
                
                invoice_details.append({
                    'Status': status,
                    'Invoice Number': invoice['invoice_number'],
                    'Invoice Date': invoice['invoice_date'].strftime('%Y-%m-%d') if isinstance(invoice['invoice_date'], datetime.date) else str(invoice['invoice_date']),
                    'Due Date': invoice['due_date'].strftime('%Y-%m-%d') if isinstance(invoice['due_date'], datetime.date) else str(invoice['due_date']),
                    'Total Amount': f"₹{invoice['total_amount']:,.2f}",
                    'Outstanding': f"₹{invoice.get('outstanding_amount', invoice['total_amount']):,.2f}",
                    'Days Overdue': days_overdue if days_overdue > 0 else 0
                })
        
        if invoice_details:
            df_invoices = pd.DataFrame(invoice_details)
            st.dataframe(df_invoices, use_container_width=True)
        else:
            st.success("No outstanding invoices for this customer.")

def display_detailed_data(from_date, to_date):
    """Display detailed data tables"""
    st.markdown("---")
    st.markdown('''
    <div class="section-header">
        Detailed Data
    </div>
    ''', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["Recent Bookings", "Recent Invoices", "Recent Payments", "Vehicle Status"])
    
    with tab1:
        st.markdown("#### Recent Bookings")
        bookings_data = getattr(st.session_state, 'bookings', [])
        recent_bookings = [
            b for b in bookings_data 
            if from_date <= safe_get_date(b.get('pickup_date', datetime.datetime.now())) <= to_date
        ]
        recent_bookings = sorted(recent_bookings, key=lambda x: safe_get_date(x.get('created_date', datetime.datetime.now())), reverse=True)[:10]
        
        if recent_bookings:
            booking_data = []
            for booking in recent_bookings:
                status_color = {
                    'CREATED': '🟡',
                    'CONFIRMED': '🔵',
                    'DISPATCHED': '🟠',
                    'DELIVERED': '🟢',
                    'CANCELLED': '❌'
                }.get(booking.get('status', 'CREATED'), '⚪')
                
                booking_data.append({
                    'Status': f"{status_color} {booking.get('status', 'Created')}",
                    'Booking Number': booking.get('booking_number', 'N/A'),
                    'Customer': booking.get('customer', 'N/A'),
                    'Route': f"{booking.get('route_from', 'N/A')} → {booking.get('route_to', 'N/A')}",
                    'Date': safe_get_date(booking.get('booking_date', datetime.datetime.now())).strftime('%d-%b-%Y'),
                    'Vehicle': booking.get('vehicle_type', 'N/A')
                })
            
            df_bookings = pd.DataFrame(booking_data)
            st.dataframe(df_bookings, use_container_width=True)
        else:
            st.info("No recent bookings found")
    
    with tab2:
        st.markdown("#### Recent Invoices")
        invoices_data = getattr(st.session_state, 'invoices', [])
        recent_invoices = [
            inv for inv in invoices_data 
            if from_date <= safe_get_date(inv.get('invoice_date', datetime.datetime.now())) <= to_date
        ]
        recent_invoices = sorted(recent_invoices, key=lambda x: safe_get_date(x.get('created_date', datetime.datetime.now())), reverse=True)[:10]
        
        if recent_invoices:
            invoice_data = []
            for invoice in recent_invoices:
                due_date = safe_get_date(invoice.get('due_date', datetime.datetime.now()))
                days_overdue = max(0, (datetime.datetime.now().date() - due_date).days)
                
                outstanding = invoice.get('outstanding_amount', invoice.get('total_amount', 0))
                if outstanding <= 0:
                    status_color = "🟢 Paid"
                elif days_overdue == 0:
                    status_color = "🟡 Current"
                elif days_overdue <= 15:
                    status_color = "🟠 Due Soon"
                else:
                    status_color = "🔴 Overdue"
                
                invoice_data.append({
                    'Status': status_color,
                    'Invoice Number': invoice.get('invoice_number', 'N/A'),
                    'Type': invoice.get('invoice_type', 'N/A'),
                    'Customer': invoice.get('customer_name', 'N/A'),
                    'Date': safe_get_date(invoice.get('invoice_date', datetime.datetime.now())).strftime('%d-%b-%Y'),
                    'Amount': f"₹{invoice.get('total_amount', 0):,.2f}",
                    'Outstanding': f"₹{outstanding:,.2f}"
                })
            
            df_invoices = pd.DataFrame(invoice_data)
            st.dataframe(df_invoices, use_container_width=True)
        else:
            st.info("No recent invoices found")
    
    with tab3:
        st.markdown("#### Recent Payments")
        payments_data = getattr(st.session_state, 'customer_payments', [])
        if payments_data:
            recent_payments = [
                p for p in payments_data 
                if from_date <= safe_get_date(p.get('payment_date', datetime.datetime.now())) <= to_date
            ]
            recent_payments = sorted(recent_payments, key=lambda x: safe_get_date(x.get('created_date', datetime.datetime.now())), reverse=True)[:10]
            
            if recent_payments:
                payment_data = []
                for payment in recent_payments:
                    allocation_icon = "✅" if payment.get('allocation_status', 'Pending') == 'Allocated' else "⏳"
                    
                    payment_data.append({
                        'Status': f"{allocation_icon} {payment.get('allocation_status', 'Pending')}",
                        'Customer': payment.get('customer_name', 'N/A'),
                        'Date': safe_get_date(payment.get('payment_date', datetime.datetime.now())).strftime('%d-%b-%Y'),
                        'Amount': f"₹{payment.get('payment_amount', 0):,.2f}",
                        'Method': payment.get('payment_method', 'N/A'),
                        'Reference': payment.get('reference_number', '')
                    })
                
                df_payments = pd.DataFrame(payment_data)
                st.dataframe(df_payments, use_container_width=True)
            else:
                st.info("No recent payments found")
        else:
            st.info("No payment data available")
    
    with tab4:
        st.markdown("#### Vehicle Status")
        
        vehicles_data = getattr(st.session_state, 'vehicles', [])
        if vehicles_data:
            vehicle_data = []
            for vehicle in vehicles_data:
                status_icon = {
                    'Active': '🟢',
                    'Maintenance': '🟡',
                    'Inactive': '🔴'
                }.get(vehicle.get('status', 'Active'), '⚪')
                
                # Get latest odometer reading if available
                last_reading = "No data"
                last_reading_date = 'N/A'
                odometer_logs_data = getattr(st.session_state, 'odometer_logs', [])
                if odometer_logs_data:
                    vehicle_odometer = [log for log in odometer_logs_data 
                                     if log.get('vehicle_registration') == vehicle.get('registration_number')]
                    
                    if vehicle_odometer:
                        latest_reading = max(vehicle_odometer, key=lambda x: safe_get_date(x.get('date', datetime.datetime.now())))
                        last_reading = f"{latest_reading.get('kilometer_reading', 0):,} KM"
                        last_reading_date = safe_get_date(latest_reading.get('date', datetime.datetime.now())).strftime('%d-%b-%Y')
                
                vehicle_data.append({
                    'Status': f"{status_icon} {vehicle.get('status', 'Active')}",
                    'Registration': vehicle.get('registration_number', 'N/A'),
                    'Type': vehicle.get('vehicle_type', 'N/A'),
                    'Fuel Type': vehicle.get('fuel_type', 'N/A'),
                    'Driver': vehicle.get('linked_driver', 'Not Assigned'),
                    'Last Reading': last_reading,
                    'Last Updated': last_reading_date
                })
            
            df_vehicles = pd.DataFrame(vehicle_data)
            st.dataframe(df_vehicles, use_container_width=True)
        else:
            st.info("No vehicle data available")