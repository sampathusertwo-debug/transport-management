import streamlit as st
import pandas as pd
import datetime
import zipfile
import io
from typing import Dict, List

def show():
    """Display the audit exports module"""
    st.header("📁 Audit-Ready Exports")
    
    st.markdown("""
    Export comprehensive data for audit purposes. All exports include date range filtering 
    and are available in CSV and Excel formats for easy analysis and sharing.
    """)
    
    # Date range selection
    col1, col2, col3 = st.columns(3)
    
    with col1:
        from_date = st.date_input(
            "From Date",
            value=datetime.datetime.now() - datetime.timedelta(days=90),
            key="audit_from_date"
        )
    
    with col2:
        to_date = st.date_input(
            "To Date",
            value=datetime.datetime.now().date(),
            key="audit_to_date"
        )
    
    with col3:
        export_format = st.selectbox(
            "Export Format",
            ["CSV", "Excel"],
            key="audit_format"
        )
    
    st.markdown("---")
    
    # Export options
    st.markdown("### 📋 Select Data to Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Core Business Data")
        
        export_bookings = st.checkbox("Bookings with Status", value=True, key="export_bookings")
        export_invoices = st.checkbox("Invoices (All Types)", value=True, key="export_invoices")
        export_payments = st.checkbox("Customer Payments", value=True, key="export_payments")
        export_quotations = st.checkbox("Quotations", value=True, key="export_quotations")
    
    with col2:
        st.markdown("#### Operational Data")
        
        export_vendors = st.checkbox("Vendor Bills & Payments", value=True, key="export_vendors")
        export_expenses = st.checkbox("Company Expenses", value=True, key="export_expenses")
        export_vehicles = st.checkbox("Vehicle Data & Logs", value=True, key="export_vehicles")
        export_customers = st.checkbox("Customer Master", value=True, key="export_customers")
    
    # Additional options
    st.markdown("#### Additional Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        include_outstanding = st.checkbox("Include Outstanding Analysis", value=True, key="export_outstanding")
        include_aging = st.checkbox("Include Aging Reports", value=True, key="export_aging")
    
    with col2:
        include_summary = st.checkbox("Include Executive Summary", value=True, key="export_summary")
        separate_files = st.checkbox("Create Separate Files per Module", value=True, key="separate_files")
    
    st.markdown("---")
    
    # Preview data counts
    if st.button("Preview Data Counts"):
        preview_data_counts(from_date, to_date)
    
    # Generate export
    if st.button("Generate Audit Export", type="primary"):
        generate_audit_export(from_date, to_date, export_format, {
            'bookings': export_bookings,
            'invoices': export_invoices,
            'payments': export_payments,
            'quotations': export_quotations,
            'vendors': export_vendors,
            'expenses': export_expenses,
            'vehicles': export_vehicles,
            'customers': export_customers,
            'outstanding': include_outstanding,
            'aging': include_aging,
            'summary': include_summary,
            'separate_files': separate_files
        })

def preview_data_counts(from_date, to_date):
    """Preview data counts for the selected period"""
    st.markdown('''
    <div class="section-header">
        📊 Data Preview
    </div>
    ''', unsafe_allow_html=True)
    
    # Calculate counts
    bookings_count = len([b for b in st.session_state.bookings 
                         if from_date <= b['pickup_date'] <= to_date])
    
    invoices_count = len([inv for inv in st.session_state.invoices 
                         if from_date <= inv['invoice_date'] <= to_date])
    
    payments_count = len([p for p in st.session_state.customer_payments 
                         if from_date <= p['payment_date'] <= to_date])
    
    quotations_count = len([q for q in st.session_state.quotations 
                           if from_date <= q['created_date'].date() <= to_date])
    
    vendor_bills_count = len([vb for vb in st.session_state.vendor_bills 
                             if from_date <= vb['bill_date'] <= to_date])
    
    vendor_payments_count = len([vp for vp in st.session_state.vendor_payments 
                                if from_date <= vp['payment_date'] <= to_date])
    
    expenses_count = len([e for e in st.session_state.expenses 
                         if from_date <= e['expense_date'] <= to_date])
    
    fuel_logs_count = len([f for f in st.session_state.fuel_logs 
                          if from_date <= f['date'] <= to_date])
    
    odometer_logs_count = len([o for o in st.session_state.odometer_logs 
                              if from_date <= o['date'] <= to_date])
    
    # Display in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Bookings", bookings_count)
        st.metric("Customer Payments", payments_count)
    
    with col2:
        st.metric("Invoices", invoices_count)
        st.metric("Vendor Bills", vendor_bills_count)
    
    with col3:
        st.metric("Quotations", quotations_count)
        st.metric("Company Expenses", expenses_count)
    
    with col4:
        st.metric("Fuel Logs", fuel_logs_count)
        st.metric("Odometer Logs", odometer_logs_count)
    
    # Additional metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Customers", len(st.session_state.customers))
    
    with col2:
        st.metric("Total Vendors", len(st.session_state.vendors))
    
    with col3:
        st.metric("Total Vehicles", len(st.session_state.vehicles))
    
    with col4:
        st.metric("Total Drivers", len(st.session_state.drivers))

def generate_audit_export(from_date, to_date, export_format, export_options):
    """Generate comprehensive audit export"""
    
    try:
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        exported_files = []
        
        # 1. Bookings Export
        if export_options['bookings']:
            status_text.text("Exporting bookings data...")
            progress_bar.progress(10)
            
            bookings_data = export_bookings_data(from_date, to_date)
            if bookings_data:
                if export_format == "CSV":
                    csv_data = pd.DataFrame(bookings_data).to_csv(index=False)
                    exported_files.append(("bookings.csv", csv_data))
                else:
                    excel_data = create_excel_file(pd.DataFrame(bookings_data), "Bookings")
                    exported_files.append(("bookings.xlsx", excel_data))
        
        # 2. Invoices Export
        if export_options['invoices']:
            status_text.text("Exporting invoices data...")
            progress_bar.progress(20)
            
            invoices_data = export_invoices_data(from_date, to_date)
            if invoices_data:
                if export_format == "CSV":
                    csv_data = pd.DataFrame(invoices_data).to_csv(index=False)
                    exported_files.append(("invoices.csv", csv_data))
                else:
                    excel_data = create_excel_file(pd.DataFrame(invoices_data), "Invoices")
                    exported_files.append(("invoices.xlsx", excel_data))
        
        # Continue with other exports...
        if export_options['payments']:
            status_text.text("Exporting payments data...")
            progress_bar.progress(30)
            
            payments_data = export_payments_data(from_date, to_date)
            if payments_data:
                if export_format == "CSV":
                    csv_data = pd.DataFrame(payments_data).to_csv(index=False)
                    exported_files.append(("customer_payments.csv", csv_data))
                else:
                    excel_data = create_excel_file(pd.DataFrame(payments_data), "Customer Payments")
                    exported_files.append(("customer_payments.xlsx", excel_data))
        
        # Create ZIP file
        status_text.text("Creating download package...")
        progress_bar.progress(100)
        
        if exported_files:
            # Create ZIP file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filename, file_data in exported_files:
                    if isinstance(file_data, str):
                        zip_file.writestr(filename, file_data.encode('utf-8'))
                    else:
                        zip_file.writestr(filename, file_data)
            
            zip_buffer.seek(0)
            
            # Generate filename
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = f"stranz_audit_export_{from_date}_{to_date}_{timestamp}.zip"
            
            st.success(f"✅ Audit export generated successfully! {len(exported_files)} files included.")
            
            # Download button
            st.download_button(
                label="📥 Download Audit Export (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=zip_filename,
                mime="application/zip",
                type="primary"
            )
            
            # Show file list
            st.markdown("**Files included:**")
            for filename, _ in exported_files:
                st.write(f"• {filename}")
        
        else:
            st.warning("No data found for the selected criteria and date range.")
        
        # Clear progress
        progress_bar.empty()
        status_text.empty()
        
    except Exception as e:
        st.error(f"Error generating export: {str(e)}")
        progress_bar.empty()
        status_text.empty()

def create_excel_file(df, sheet_name):
    """Create Excel file from DataFrame"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()

def export_bookings_data(from_date, to_date):
    """Export bookings data"""
    bookings = [b for b in st.session_state.bookings 
               if from_date <= b['pickup_date'] <= to_date]
    
    export_data = []
    for booking in bookings:
        export_data.append({
            'Booking Number': booking['booking_number'],
            'Customer Name': booking['customer_name'],
            'Pickup Location': booking['pickup_location'],
            'Delivery Location': booking['delivery_location'],
            'Pickup Date': booking['pickup_date'],
            'Vehicle Type': booking['vehicle_type'],
            'Trip Type': booking['trip_type'],
            'Total Amount': booking['total_amount'],
            'Status': booking['status'],
            'Created Date': booking['created_date']
        })
    
    return export_data

def export_invoices_data(from_date, to_date):
    """Export invoices data"""
    invoices = [inv for inv in st.session_state.invoices 
               if from_date <= inv['invoice_date'] <= to_date]
    
    export_data = []
    for invoice in invoices:
        export_data.append({
            'Invoice Number': invoice['invoice_number'],
            'Invoice Type': invoice['invoice_type'],
            'Customer Name': invoice['customer_name'],
            'Invoice Date': invoice['invoice_date'],
            'Due Date': invoice['due_date'],
            'Total Amount': invoice['total_amount'],
            'Outstanding Amount': invoice['outstanding_amount'],
            'Status': invoice['status'],
            'Created Date': invoice['created_date']
        })
    
    return export_data

def export_payments_data(from_date, to_date):
    """Export customer payments data"""
    payments = [p for p in st.session_state.customer_payments 
               if from_date <= p['payment_date'] <= to_date]
    
    export_data = []
    for payment in payments:
        export_data.append({
            'Customer Name': payment['customer_name'],
            'Payment Date': payment['payment_date'],
            'Payment Amount': payment['payment_amount'],
            'Payment Method': payment['payment_method'],
            'Allocation Status': payment['allocation_status'],
            'Created Date': payment['created_date']
        })
    
    return export_data