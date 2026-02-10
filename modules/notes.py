import streamlit as st
import pandas as pd
import datetime
import uuid
from typing import Dict, List, Optional
from .utils import searchable_selectbox, static_selectbox

def get_notes_from_database(page=1, page_size=10, search_term=None, record_type=None, 
                          status_filter=None, start_date=None, end_date=None):
    """Get notes from database with pagination and search filters"""
    try:
        from database import execute_query
        import psycopg2
        
        # Check if database connection is available
        if psycopg2 is None:
            # Fallback to session state data
            return get_notes_from_session_state(page, page_size, search_term, record_type, status_filter, start_date, end_date)
        
        # Build the WHERE clause
        where_conditions = []
        params = []
        
        if record_type and record_type != "All":
            where_conditions.append("record_type = %s")
            params.append(record_type.lower())
        
        if status_filter and status_filter != "All":
            where_conditions.append("new_status = %s")
            params.append(status_filter)
        
        if start_date:
            where_conditions.append("change_date >= %s")
            params.append(start_date.strftime('%Y-%m-%d'))
        
        if end_date:
            where_conditions.append("change_date <= %s")
            params.append((end_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d'))
        
        if search_term:
            # Simplified search to avoid complex subqueries
            where_conditions.append("(notes ILIKE %s OR additional_data::text ILIKE %s)")
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern])
        
        # Build the complete query
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Count total records
        count_query = f"SELECT COUNT(*) FROM notes {where_clause}"
        
        count_result = execute_query(count_query, params, fetch=True)
        if count_result is None:
            # Database error, fallback to session state
            return get_notes_from_session_state(page, page_size, search_term, record_type, status_filter, start_date, end_date)
            
        total_count = count_result[0]['count'] if count_result else 0
        
        # Get paginated data
        offset = (page - 1) * page_size
        data_query = f"""SELECT id, record_id, record_type, old_status, new_status, 
                           change_date, changed_by, notes, additional_data, created_date 
                        FROM notes {where_clause} 
                        ORDER BY change_date DESC 
                        LIMIT %s OFFSET %s"""
        
        data_params = params + [page_size, offset]
        result = execute_query(data_query, data_params, fetch=True)
        
        if result is None:
            # Database error, fallback to session state
            return get_notes_from_session_state(page, page_size, search_term, record_type, status_filter, start_date, end_date)
        
        # Convert to list of dictionaries
        notes = []
        if result:
            for row in result:
                # Handle both dict and tuple results
                if isinstance(row, dict):
                    note = {
                        'id': row['id'],
                        'record_id': row['record_id'],
                        'record_type': row['record_type'],
                        'old_status': row['old_status'],
                        'new_status': row['new_status'],
                        'change_date': row['change_date'] if isinstance(row['change_date'], datetime.datetime) else datetime.datetime.fromisoformat(str(row['change_date'])),
                        'changed_by': row['changed_by'],
                        'notes': row['notes'] or '',
                        'additional_data': row['additional_data'] if row['additional_data'] else {},
                        'created_date': row['created_date'] if isinstance(row['created_date'], datetime.datetime) else datetime.datetime.fromisoformat(str(row['created_date']))
                    }
                else:
                    note = {
                        'id': row[0],
                        'record_id': row[1],
                        'record_type': row[2],
                        'old_status': row[3],
                        'new_status': row[4],
                        'change_date': row[5] if isinstance(row[5], datetime.datetime) else datetime.datetime.fromisoformat(str(row[5])),
                        'changed_by': row[6],
                        'notes': row[7] or '',
                        'additional_data': row[8] if row[8] else {},
                        'created_date': row[9] if isinstance(row[9], datetime.datetime) else datetime.datetime.fromisoformat(str(row[9]))
                    }
                notes.append(note)
        
        return notes, total_count
        
    except Exception as e:
        # Fallback to session state on any error
        st.warning(f"Database connection issue, using local data: {str(e)}")
        return get_notes_from_session_state(page, page_size, search_term, record_type, status_filter, start_date, end_date)

def get_notes_from_session_state(page=1, page_size=10, search_term=None, record_type=None, 
                                status_filter=None, start_date=None, end_date=None):
    """Fallback function to get notes from session state with pagination"""
    # Ensure notes are loaded
    if 'notes' not in st.session_state:
        from database import load_data_when_needed
        load_data_when_needed('notes')
    
    notes = st.session_state.get('notes', []).copy()
    
    # Apply filters
    if record_type and record_type != "All":
        notes = [note for note in notes if note['record_type'] == record_type.lower()]
    
    if status_filter and status_filter != "All":
        notes = [note for note in notes if note['new_status'] == status_filter]
    
    if start_date:
        notes = [note for note in notes if note['change_date'].date() >= start_date]
    
    if end_date:
        notes = [note for note in notes if note['change_date'].date() <= end_date]
    
    if search_term:
        filtered_notes = []
        for note in notes:
            # Search in notes and additional data
            search_fields = [
                note.get('notes', ''),
                str(note.get('additional_data', {}))
            ]
            if any(search_term.lower() in str(field).lower() for field in search_fields):
                filtered_notes.append(note)
        notes = filtered_notes
    
    # Sort by date (newest first)
    notes.sort(key=lambda x: x['change_date'], reverse=True)
    
    # Apply pagination
    total_count = len(notes)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_notes = notes[start_idx:end_idx]
    
    return paginated_notes, total_count

def search_records_in_database(search_term, record_types=None):
    """Search for records in database by number or customer name"""
    try:
        from database import execute_query
        import psycopg2
        
        # Check if database connection is available
        if psycopg2 is None:
            return search_records_in_session_state(search_term, record_types)
        
        results = []
        
        # Search quotations
        if not record_types or 'quotation' in record_types:
            query = "SELECT id, quotation_number, customer_name FROM quotations WHERE quotation_number ILIKE %s OR customer_name ILIKE %s ORDER BY created_date DESC LIMIT 20"
            search_pattern = f"%{search_term}%"
            quotations = execute_query(query, [search_pattern, search_pattern], fetch=True)
            if quotations:
                for q in quotations:
                    if isinstance(q, dict):
                        results.append({
                            'id': q['id'],
                            'type': 'quotation',
                            'number': q['quotation_number'],
                            'customer': q['customer_name']
                        })
                    else:
                        results.append({
                            'id': q[0],
                            'type': 'quotation',
                            'number': q[1],
                            'customer': q[2]
                        })
        
        # Search bookings
        if not record_types or 'booking' in record_types:
            query = "SELECT id, booking_number, customer_name FROM bookings WHERE booking_number ILIKE %s OR customer_name ILIKE %s ORDER BY created_date DESC LIMIT 20"
            search_pattern = f"%{search_term}%"
            bookings = execute_query(query, [search_pattern, search_pattern], fetch=True)
            if bookings:
                for b in bookings:
                    if isinstance(b, dict):
                        results.append({
                            'id': b['id'],
                            'type': 'booking',
                            'number': b['booking_number'],
                            'customer': b['customer_name']
                        })
                    else:
                        results.append({
                            'id': b[0],
                            'type': 'booking',
                            'number': b[1],
                            'customer': b[2]
                        })
        
        # Search invoices
        if not record_types or 'invoice' in record_types:
            query = "SELECT id, invoice_number, customer_name FROM invoices WHERE invoice_number ILIKE %s OR customer_name ILIKE %s ORDER BY created_date DESC LIMIT 20"
            search_pattern = f"%{search_term}%"
            invoices = execute_query(query, [search_pattern, search_pattern], fetch=True)
            if invoices:
                for i in invoices:
                    if isinstance(i, dict):
                        results.append({
                            'id': i['id'],
                            'type': 'invoice',
                            'number': i['invoice_number'],
                            'customer': i['customer_name']
                        })
                    else:
                        results.append({
                            'id': i[0],
                            'type': 'invoice',
                            'number': i[1],
                            'customer': i[2]
                        })
        
        return results
        
    except Exception as e:
        st.warning(f"Database search error, using local data: {str(e)}")
        return search_records_in_session_state(search_term, record_types)

def search_records_in_session_state(search_term, record_types=None):
    """Fallback function to search records in session state"""
    results = []
    
    try:
        # Search quotations
        if not record_types or 'quotation' in record_types:
            quotations = st.session_state.get('quotations', [])
            for q in quotations:
                if (search_term.lower() in q.get('quotation_number', '').lower() or 
                    search_term.lower() in q.get('customer', '').lower()):
                    results.append({
                        'id': q['id'],
                        'type': 'quotation',
                        'number': q['quotation_number'],
                        'customer': q.get('customer', 'N/A')
                    })
        
        # Search bookings
        if not record_types or 'booking' in record_types:
            bookings = st.session_state.get('bookings', [])
            for b in bookings:
                if (search_term.lower() in b.get('booking_number', '').lower() or 
                    search_term.lower() in b.get('customer', '').lower()):
                    results.append({
                        'id': b['id'],
                        'type': 'booking',
                        'number': b['booking_number'],
                        'customer': b.get('customer', 'N/A')
                    })
        
        # Search invoices
        if not record_types or 'invoice' in record_types:
            invoices = st.session_state.get('invoices', [])
            for i in invoices:
                if (search_term.lower() in i.get('invoice_number', '').lower() or 
                    search_term.lower() in i.get('customer', '').lower()):
                    results.append({
                        'id': i['id'],
                        'type': 'invoice',
                        'number': i['invoice_number'],
                        'customer': i.get('customer', 'N/A')
                    })
        
    except Exception as e:
        st.error(f"Search error: {str(e)}")
    
    return results[:20]  # Limit results

def add_status_note(record_id: str, record_type: str, old_status: str, new_status: str, 
                    changed_by: str = "Admin", notes: str = "", additional_data: Dict = None):
    """
    Add a status change note to track all status changes
    
    Args:
        record_id: ID of the record (booking, invoice, quotation, etc.)
        record_type: Type of record (booking, invoice, quotation, vehicle, bill, etc.)
        old_status: Previous status
        new_status: New status
        changed_by: User who made the change
        notes: Additional notes about the change
        additional_data: Additional data related to the change
    """
    if 'notes' not in st.session_state:
        st.session_state.notes = []
    
    note = {
        'id': str(uuid.uuid4()),
        'record_id': record_id,
        'record_type': record_type.lower(),
        'old_status': old_status,
        'new_status': new_status,
        'change_date': datetime.datetime.now(),
        'changed_by': changed_by,
        'notes': notes,
        'additional_data': additional_data or {},
        'created_date': datetime.datetime.now()
    }
    
    st.session_state.notes.append(note)
    
    # Save to database if available
    try:
        from database import save_to_database
        save_to_database('notes', note)
        # Invalidate cache to ensure fresh data on next load
        if 'notes_data_loaded' in st.session_state:
            st.session_state.notes_data_loaded = False
    except Exception as e:
        # Show warning instead of error to prevent disrupting user flow
        st.warning(f"Note saved locally but failed to sync with database: {e}")

def get_status_history(record_id: str, record_type: str = None) -> List[Dict]:
    """
    Get status history for a specific record
    
    Args:
        record_id: ID of the record
        record_type: Type of record (optional filter)
    
    Returns:
        List of status change notes
    """
    if 'notes' not in st.session_state:
        return []
    
    history = [note for note in st.session_state.notes if note['record_id'] == record_id]
    
    if record_type:
        history = [note for note in history if note['record_type'] == record_type.lower()]
    
    # Sort by date (newest first)
    history.sort(key=lambda x: x['change_date'], reverse=True)
    
    return history

def refresh_notes_data():
    """Refresh notes data from database"""
    try:
        from database import load_data_when_needed
        # Clear the data loaded flag to force refresh
        if 'notes_data_loaded' in st.session_state:
            del st.session_state.notes_data_loaded
        load_data_when_needed('notes')
        st.session_state.notes_data_loaded = True
    except Exception as e:
        st.warning(f"Failed to refresh notes data: {e}")

def get_all_notes(record_type: str = None, date_filter: datetime.date = None, 
                  status_filter: str = None) -> List[Dict]:
    """
    Get all notes with optional filters
    
    Args:
        record_type: Filter by record type
        date_filter: Filter by date (notes from this date onwards)
        status_filter: Filter by new status
    
    Returns:
        Filtered list of notes
    """
    if 'notes' not in st.session_state:
        return []
    
    notes = st.session_state.notes.copy()
    
    if record_type:
        notes = [note for note in notes if note['record_type'] == record_type.lower()]
    
    if date_filter:
        notes = [note for note in notes if note['change_date'].date() >= date_filter]
    
    if status_filter and status_filter != "All":
        notes = [note for note in notes if note['new_status'] == status_filter]
    
    # Sort by date (newest first)
    notes.sort(key=lambda x: x['change_date'], reverse=True)
    
    return notes

def get_record_info(record_id: str, record_type: str) -> Dict:
    """
    Get basic information about a record
    
    Args:
        record_id: ID of the record
        record_type: Type of record
    
    Returns:
        Dictionary with record information
    """
    record_type = record_type.lower()
    
    if record_type == 'booking':
        booking = next((b for b in st.session_state.get('bookings', []) if b['id'] == record_id), None)
        if booking:
            return {
                'number': booking.get('booking_number', 'N/A'),
                'customer': booking.get('customer', 'N/A'),
                'route': f"{booking.get('pickup_location', '')} → {booking.get('delivery_location', '')}",
                'amount': booking.get('total_amount', 0)
            }
    
    elif record_type == 'quotation':
        quotation = next((q for q in st.session_state.get('quotations', []) if q['id'] == record_id), None)
        if quotation:
            return {
                'number': quotation.get('quotation_number', 'N/A'),
                'customer': quotation.get('customer', 'N/A'),
                'route': f"{quotation.get('pickup_location', '')} → {quotation.get('delivery_location', '')}",
                'amount': quotation.get('total_amount', 0)
            }
    
    elif record_type == 'invoice':
        invoice = next((i for i in st.session_state.get('invoices', []) if i['id'] == record_id), None)
        if invoice:
            return {
                'number': invoice.get('invoice_number', 'N/A'),
                'customer': invoice.get('customer', 'N/A'),
                'booking': invoice.get('booking_number', 'N/A'),
                'amount': invoice.get('total_amount', 0)
            }
    
    elif record_type == 'vehicle':
        vehicle = next((v for v in st.session_state.get('vehicles', []) if v['id'] == record_id), None)
        if vehicle:
            return {
                'number': vehicle.get('registration_number', 'N/A'),
                'make': vehicle.get('make', 'N/A'),
                'model': vehicle.get('model', 'N/A'),
                'type': vehicle.get('vehicle_type', 'N/A')
            }
    
    elif record_type == 'bill':
        bill = next((b for b in st.session_state.get('vendor_bills', []) if b['id'] == record_id), None)
        if bill:
            return {
                'number': bill.get('bill_number', 'N/A'),
                'vendor': bill.get('vendor_name', 'N/A'),
                'category': bill.get('category', 'N/A'),
                'amount': bill.get('amount', 0)
            }
    
    return {
        'number': 'N/A',
        'info': 'Record not found'
    }

def show_status_timeline(record_id: str, record_type: str):
    """
    Display status timeline for a specific record
    
    Args:
        record_id: ID of the record
        record_type: Type of record
    """
    st.markdown("### Status Timeline")
    
    history = get_status_history(record_id, record_type)
    
    if not history:
        st.info("No status changes recorded for this record.")
        return
    
    # Get record info
    record_info = get_record_info(record_id, record_type)
    
    st.markdown(f"**{record_type.title()} #{record_info.get('number', 'N/A')}**")
    
    for i, note in enumerate(history):
        # Status change visualization
        status_color = get_status_color(note['new_status'])
        old_color = get_status_color(note['old_status'])
        
        # Create a timeline entry
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            st.markdown(f"**{note['change_date'].strftime('%m/%d %H:%M')}**")
        
        with col2:
            st.markdown(f"{old_color} {note['old_status']} → {status_color} {note['new_status']}")
            if note['notes']:
                st.markdown(f"*{note['notes']}*")
            if note['additional_data']:
                st.markdown(f"Additional info: {note['additional_data']}")
        
        with col3:
            st.markdown(f"*by {note['changed_by']}*")
        
        if i < len(history) - 1:  # Don't show divider after last item
            st.markdown("---")

def get_status_color(status: str) -> str:
    """Get emoji color for status"""
    status_colors = {
        # Booking statuses
        'Created': '🟡',
        'Confirmed': '🔵',
        'Dispatched': '🟠',
        'In Transit': '🟣',
        'Delivered': '🟢',
        'POD Captured': '✅',
        'POD Generated': '✅',
        'Cancelled': '❌',
        'Invoiced': '📄',
        
        # Invoice statuses
        'Generated': '📄',
        'Sent': '📤',
        'Paid': '💰',
        'Partially Paid': '💳',
        'Overdue': '⚠️',
        
        # Quotation statuses
        'Draft': '📝',
        'Sent': '📤',
        'Sent to Customer': '📤',
        'Approved': '✅',
        'Rejected': '❌',
        'Expired': '⏰',
        'Converted to Booking': '🔄',
        'Deleted': '🗑️',
        
        # Vehicle statuses
        'Active': '🟢',
        'Maintenance': '🔧',
        'Inactive': '⚪',
        
        # Payment/Bill statuses
        'Unpaid': '🔴',
        'Paid': '💰',
        'Partially Paid': '💳'
    }
    
    return status_colors.get(status, '⚪')

def show():
    """Display the notes module"""
    # Initialize session state for tab persistence
    if 'notes_active_tab' not in st.session_state:
        st.session_state.notes_active_tab = 0
    
    # Load minimal data when needed for lookups - more efficient approach
    from database import load_data_when_needed
    
    # Only load essential data for record lookups
    if 'notes_lookup_data_loaded' not in st.session_state:
        load_data_when_needed('quotations')
        load_data_when_needed('bookings') 
        load_data_when_needed('invoices')
        load_data_when_needed('vehicles')
        load_data_when_needed('vendor_bills')
        # Don't load all notes into session state - we'll query as needed
        st.session_state.notes_lookup_data_loaded = True
    
    st.header("Notes & Status Tracking")
    
    # Initialize notes if not exists (for backward compatibility)
    if 'notes' not in st.session_state:
        st.session_state.notes = []
    
    tab1, tab2, tab3, tab4 = st.tabs(["Activity Dashboard", "Status History", "Search Records", "Add Manual Note"])
    
    with tab1:
        show_activity_dashboard()
    
    with tab2:
        show_status_history_tab()
    
    with tab3:
        show_search_records()
    
    with tab4:
        show_add_manual_note()

def show_activity_dashboard():
    """Show recent activity dashboard with pagination"""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Recent Activity Dashboard")
    with col2:
        if st.button("🔄 Refresh", key="refresh_activity", help="Refresh activity data"):
            # Clear pagination state to force refresh
            if 'activity_current_page' in st.session_state:
                st.session_state.activity_current_page = 1
            st.success("Data refreshed successfully!")
    
    # Initialize pagination state
    if 'activity_current_page' not in st.session_state:
        st.session_state.activity_current_page = 1
    
    # Search and filters
    st.markdown("#### 🔍 Search & Filters")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input(
            "Search",
            placeholder="Record number, customer name...",
            key="activity_search"
        )
    
    with col2:
        record_type_filter = static_selectbox(
            "Record Type",
            ["All", "Booking", "Quotation", "Invoice", "Vehicle", "Bill"],
            key="activity_record_type_filter"
        )
    
    with col3:
        status_filter = static_selectbox(
            "Status",
            ["All", "Draft", "Sent", "Created", "Confirmed", "Dispatched", "Delivered", "Generated", "Paid", "Cancelled", "Approved", "Rejected"],
            key="activity_status_filter"
        )
    
    # Date filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        days_filter = static_selectbox(
            "Time Period",
            ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
            key="activity_days_filter"
        )
    
    # Calculate date filter
    start_date = None
    end_date = datetime.date.today()
    
    if days_filter == "Last 7 days":
        start_date = datetime.date.today() - datetime.timedelta(days=7)
    elif days_filter == "Last 30 days":
        start_date = datetime.date.today() - datetime.timedelta(days=30)
    elif days_filter == "Last 90 days":
        start_date = datetime.date.today() - datetime.timedelta(days=90)
    
    with col2:
        if start_date:
            start_date = st.date_input(
                "From Date",
                value=start_date,
                key="activity_start_date"
            )
    
    with col3:
        end_date = st.date_input(
            "To Date",
            value=end_date,
            key="activity_end_date"
        )
    
    # Reset pagination when filters change
    current_filters = (search_term, record_type_filter, status_filter, start_date, end_date)
    if 'activity_last_filters' not in st.session_state:
        st.session_state.activity_last_filters = current_filters
    elif st.session_state.activity_last_filters != current_filters:
        st.session_state.activity_current_page = 1
        st.session_state.activity_last_filters = current_filters
    
    # Get data with pagination
    page_size = 10
    current_page = st.session_state.activity_current_page
    
    notes, total_count = get_notes_from_database(
        page=current_page,
        page_size=page_size,
        search_term=search_term if search_term else None,
        record_type=record_type_filter,
        status_filter=status_filter,
        start_date=start_date,
        end_date=end_date
    )
    
    if total_count == 0:
        st.info("No activity found for the selected filters.")
        return
    
    # Activity summary
    st.markdown("### 📈 Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    total_pages = (total_count + page_size - 1) // page_size
    
    with col1:
        st.metric("Total Records", total_count)
    
    with col2:
        st.metric("Current Page", f"{current_page}/{total_pages}")
    
    with col3:
        unique_records = len(set(n['record_id'] for n in notes))
        st.metric("Records on Page", unique_records)
    
    with col4:
        status_changes = len(set(n['new_status'] for n in notes))
        st.metric("Different Statuses", status_changes)
    
    # Pagination controls
    st.markdown("### 📄 Page Navigation")
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    with col1:
        if st.button("⏮️ First", disabled=current_page <= 1):
            st.session_state.activity_current_page = 1
            st.rerun()
    
    with col2:
        if st.button("◀️ Prev", disabled=current_page <= 1):
            st.session_state.activity_current_page = current_page - 1
            st.rerun()
    
    with col3:
        st.write(f"Page {current_page} of {total_pages}")
    
    with col4:
        if st.button("Next ▶️", disabled=current_page >= total_pages):
            st.session_state.activity_current_page = current_page + 1
            st.rerun()
    
    with col5:
        if st.button("Last ⏭️", disabled=current_page >= total_pages):
            st.session_state.activity_current_page = total_pages
            st.rerun()
    
    # Display notes
    st.markdown("### Activity Records")
    
    for note in notes:
        record_info = get_record_info(note['record_id'], note['record_type'])
        
        with st.expander(
            f"{get_status_color(note['new_status'])} {note['record_type'].title()} #{record_info.get('number', 'N/A')} - {note['old_status']} → {note['new_status']} "
            f"({note['change_date'].strftime('%m/%d %H:%M')})"
        ):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Record Type:** {note['record_type'].title()}")
                st.write(f"**Record Number:** {record_info.get('number', 'N/A')}")
                if 'customer' in record_info:
                    st.write(f"**Customer:** {record_info['customer']}")
                if 'vendor' in record_info:
                    st.write(f"**Vendor:** {record_info['vendor']}")
                st.write(f"**Status Change:** {note['old_status']} → {note['new_status']}")
            
            with col2:
                st.write(f"**Changed By:** {note['changed_by']}")
                st.write(f"**Date & Time:** {note['change_date'].strftime('%Y-%m-%d %H:%M:%S')}")
                if note['notes']:
                    st.write(f"**Notes:** {note['notes']}")
                if note['additional_data']:
                    st.write(f"**Additional Data:** {note['additional_data']}")
    
    # Export option
    st.markdown("---")
    if st.button("📤 Export Current Page"):
        export_data = []
        for note in notes:
            record_info = get_record_info(note['record_id'], note['record_type'])
            export_data.append({
                'Date': note['change_date'].strftime('%Y-%m-%d %H:%M:%S'),
                'Record Type': note['record_type'].title(),
                'Record Number': record_info.get('number', 'N/A'),
                'Customer/Vendor': record_info.get('customer', record_info.get('vendor', 'N/A')),
                'Old Status': note['old_status'],
                'New Status': note['new_status'],
                'Changed By': note['changed_by'],
                'Notes': note['notes'],
                'Additional Data': str(note['additional_data'])
            })
        
        if export_data:
            df = pd.DataFrame(export_data)
            csv = df.to_csv(index=False)
            st.download_button(
                label="📁 Download Page CSV",
                data=csv,
                file_name=f"activity_page_{current_page}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

def show_status_history_tab():
    """Show status history for specific records"""
    st.subheader("🔍 Record Status History")
    
    # Record selection
    record_type = static_selectbox(
        "Select Record Type",
        ["Booking", "Quotation", "Invoice", "Vehicle", "Bill"],
        key="history_record_type"
    )
    
    # Get records list based on type
    records_list = []
    if record_type == "Booking":
        records_list = [(b['id'], f"{b['booking_number']} - {b.get('customer', 'N/A')}") 
                       for b in st.session_state.get('bookings', [])]
    elif record_type == "Quotation":
        records_list = [(q['id'], f"{q['quotation_number']} - {q.get('customer', 'N/A')}") 
                       for q in st.session_state.get('quotations', [])]
    elif record_type == "Invoice":
        records_list = [(i['id'], f"{i['invoice_number']} - {i.get('customer', 'N/A')}") 
                       for i in st.session_state.get('invoices', [])]
    elif record_type == "Vehicle":
        records_list = [(v['id'], f"{v.get('registration_number', 'N/A')} - {v.get('make', '')} {v.get('model', '')}") 
                       for v in st.session_state.get('vehicles', [])]
    elif record_type == "Bill":
        records_list = [(b['id'], f"{b.get('bill_number', 'N/A')} - {b.get('vendor_name', 'N/A')}") 
                       for b in st.session_state.get('vendor_bills', [])]
    
    if not records_list:
        st.warning(f"No {record_type.lower()}s found.")
        return
    
    # Record selection
    record_options = [f"{display}" for _, display in records_list]
    selected_record_display = searchable_selectbox(
        f"Select {record_type}",
        record_options,
        key="history_record_select"
    )
    
    if selected_record_display:
        # Find the selected record ID
        selected_record_id = next(
            (record_id for record_id, display in records_list if display == selected_record_display), 
            None
        )
        
        if selected_record_id:
            show_status_timeline(selected_record_id, record_type.lower())

def show_search_records():
    """Search and filter records by status changes"""
    st.subheader("🔎 Search Records by Activity")
    
    # Search filters
    col1, col2 = st.columns(2)
    
    with col1:
        search_term = st.text_input(
            "Search by Record Number or Customer Name",
            key="search_term",
            help="Enter booking number, invoice number, customer name, etc."
        )
    
    with col2:
        search_status = static_selectbox(
            "Filter by Status",
            ["All", "Created", "Confirmed", "Dispatched", "Delivered", "Generated", "Paid", "Cancelled", "Overdue"],
            key="search_status"
        )
    
    # Date range
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "From Date",
            value=datetime.date.today() - datetime.timedelta(days=30),
            key="search_start_date"
        )
    
    with col2:
        end_date = st.date_input(
            "To Date",
            value=datetime.date.today(),
            key="search_end_date"
        )
    
    if st.button("Search", key="search_button"):
        # Get all notes
        all_notes = get_all_notes()
        
        # Filter by date range
        filtered_notes = [
            note for note in all_notes 
            if start_date <= note['change_date'].date() <= end_date
        ]
        
        # Filter by status
        if search_status != "All":
            filtered_notes = [
                note for note in filtered_notes 
                if note['new_status'] == search_status
            ]
        
        # Filter by search term
        if search_term:
            search_results = []
            for note in filtered_notes:
                record_info = get_record_info(note['record_id'], note['record_type'])
                
                # Search in record number, customer name, vendor name
                search_fields = [
                    record_info.get('number', ''),
                    record_info.get('customer', ''),
                    record_info.get('vendor', ''),
                    note['notes']
                ]
                
                if any(search_term.lower() in str(field).lower() for field in search_fields):
                    search_results.append(note)
            
            filtered_notes = search_results
        
        # Display results
        if not filtered_notes:
            st.info("No records found matching your search criteria.")
        else:
            st.success(f"Found {len(filtered_notes)} records")
            
            for note in filtered_notes:
                record_info = get_record_info(note['record_id'], note['record_type'])
                
                with st.expander(
                    f"{get_status_color(note['new_status'])} {note['record_type'].title()} "
                    f"#{record_info.get('number', 'N/A')} - {note['old_status']} → {note['new_status']}"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Record:** {note['record_type'].title()} #{record_info.get('number', 'N/A')}")
                        if 'customer' in record_info:
                            st.write(f"**Customer:** {record_info['customer']}")
                        if 'route' in record_info:
                            st.write(f"**Route:** {record_info['route']}")
                        st.write(f"**Status Change:** {note['old_status']} → {note['new_status']}")
                    
                    with col2:
                        st.write(f"**Date:** {note['change_date'].strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Changed By:** {note['changed_by']}")
                        if note['notes']:
                            st.write(f"**Notes:** {note['notes']}")
                        if note['additional_data']:
                            st.write(f"**Additional Info:** {note['additional_data']}")

def show_add_manual_note():
    """Add manual notes for records"""
    st.subheader("➕ Add Manual Note")
    
    st.info("Use this to add manual notes or corrections to status tracking.")
    
    # Record selection
    record_type = static_selectbox(
        "Record Type",
        ["Booking", "Quotation", "Invoice", "Vehicle", "Bill"],
        key="manual_record_type"
    )
    
    # Get records list
    records_list = []
    if record_type == "Booking":
        records_list = [(b['id'], f"{b['booking_number']} - {b.get('customer', 'N/A')}", b['status']) 
                       for b in st.session_state.get('bookings', [])]
    elif record_type == "Quotation":
        records_list = [(q['id'], f"{q['quotation_number']} - {q.get('customer', 'N/A')}", q['status']) 
                       for q in st.session_state.get('quotations', [])]
    elif record_type == "Invoice":
        records_list = [(i['id'], f"{i['invoice_number']} - {i.get('customer', 'N/A')}", i['status']) 
                       for i in st.session_state.get('invoices', [])]
    elif record_type == "Vehicle":
        records_list = [(v['id'], f"{v['registration_number']}", v.get('status', 'Active')) 
                       for v in st.session_state.get('vehicles', [])]
    elif record_type == "Bill":
        records_list = [(b['id'], f"{b.get('bill_number', 'N/A')} - {b.get('vendor_name', 'N/A')}", b.get('status', 'Unpaid')) 
                       for b in st.session_state.get('vendor_bills', [])]
    
    if not records_list:
        st.warning(f"No {record_type.lower()}s found.")
        return
    
    # Record selection
    record_options = [f"{display} (Current: {status})" for _, display, status in records_list]
    selected_record_display = searchable_selectbox(
        f"Select {record_type}",
        record_options,
        key="manual_record_select"
    )
    
    if selected_record_display:
        # Find selected record
        selected_index = record_options.index(selected_record_display)
        selected_record_id, _, current_status = records_list[selected_index]
        
        col1, col2 = st.columns(2)
        
        with col1:
            old_status = st.text_input(
                "Previous Status",
                value=current_status,
                key="manual_old_status"
            )
        
        with col2:
            new_status = st.text_input(
                "New Status",
                key="manual_new_status"
            )
        
        notes = st.text_area(
            "Notes",
            help="Describe the reason for this status change",
            key="manual_notes"
        )
        
        changed_by = st.text_input(
            "Changed By",
            value="Admin (Manual Entry)",
            key="manual_changed_by"
        )
        
        if st.button("Add Note", key="add_manual_note"):
            if new_status:
                add_status_note(
                    record_id=selected_record_id,
                    record_type=record_type.lower(),
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=changed_by,
                    notes=notes
                )
                st.success("Manual note added successfully!")
                # Clear the form by resetting keys in session state
                if 'manual_new_status' in st.session_state:
                    del st.session_state['manual_new_status']
                if 'manual_notes' in st.session_state:
                    del st.session_state['manual_notes']
                # Refresh notes data
                st.session_state.notes_data_loaded = False
            else:
                st.error("Please enter a new status.")

# Helper function to integrate with existing modules
def track_status_change(record_id: str, record_type: str, old_status: str, new_status: str, 
                       notes: str = "", changed_by: str = "Admin", additional_data: Dict = None):
    """
    Helper function to be called from other modules when status changes
    
    This function should be imported and called whenever a status change occurs
    """
    add_status_note(record_id, record_type, old_status, new_status, changed_by, notes, additional_data)

# Integration examples for other modules:
"""
Example integration in bookings.py:

from .notes import track_status_change

# When dispatching a booking:
track_status_change(
    record_id=booking['id'],
    record_type='booking',
    old_status=booking['status'],
    new_status='Dispatched',
    notes='Booking dispatched to driver',
    changed_by='Admin'
)

# When generating POD:
track_status_change(
    record_id=booking['id'],
    record_type='booking',
    old_status='Dispatched',
    new_status='POD Generated',
    notes='Proof of delivery generated',
    additional_data={'pod_date': datetime.datetime.now().isoformat()}
)
"""