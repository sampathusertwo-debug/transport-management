# Notes & Status Tracking Module

## Overview
The Notes & Status Tracking module provides comprehensive tracking of all status changes across different entities in the transport management system. It automatically logs status changes for bookings, quotations, invoices, vehicles, and vendor bills.

## Features

### 1. Automatic Status Tracking
- **Booking Status Changes**: Created → Confirmed → Dispatched → POD Generated → Invoiced → Cancelled
- **Invoice Status Changes**: Generated → Sent → Partially Paid → Paid → Overdue  
- **Quotation Status Changes**: Draft → Sent → Approved → Rejected → Converted to Booking
- **Vehicle Status Changes**: Active → Maintenance → Inactive
- **Bill Status Changes**: Unpaid → Partially Paid → Paid

### 2. Activity Dashboard
- Recent activity overview with metrics
- Filter by record type, time period, and status
- Real-time updates showing latest status changes
- Export activity reports to CSV

### 3. Status History Timeline
- Complete status history for any record
- Visual timeline showing status progression
- Detailed notes and additional information for each change
- User information tracking (who made the change)

### 4. Search & Filter
- Search records by number, customer name, or vendor name
- Filter by date range and status
- Advanced search across all status notes

### 5. Manual Notes
- Add manual notes for corrections or additional tracking
- Support for all record types
- Custom status changes with detailed notes

## Technical Implementation

### Database Schema
```sql
CREATE TABLE notes (
    id UUID PRIMARY KEY,
    record_id UUID NOT NULL,
    record_type VARCHAR(50) NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100) DEFAULT 'Admin',
    notes TEXT,
    additional_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Integration with Existing Modules
The notes module automatically integrates with existing modules through the `track_status_change` function:

```python
from modules.notes import track_status_change

# Example: When dispatching a booking
track_status_change(
    record_id=booking['id'],
    record_type='booking',
    old_status='Confirmed',
    new_status='Dispatched',
    notes='Booking dispatched to driver',
    additional_data={'booking_number': booking['booking_number']}
)
```

### Current Integrations
- **Bookings Module**: Tracks creation, dispatch, POD generation, cancellation, and invoicing
- **Invoicing Module**: Tracks invoice generation and payment status updates
- **Payment System**: Automatic status updates when payments are recorded

## Usage Guide

### Viewing Activity Dashboard
1. Navigate to "Notes & Tracking" in the main menu
2. Use the "Activity Dashboard" tab
3. Apply filters for record type, time period, or status
4. View summary metrics and recent activity
5. Export activity reports if needed

### Checking Record History
1. Go to "Status History" tab
2. Select record type (Booking, Invoice, etc.)
3. Choose specific record from dropdown
4. View complete timeline of status changes

### Searching Records
1. Use "Search Records" tab
2. Enter search terms (record numbers, customer names)
3. Set date range and status filters
4. Click "Search" to view results

### Adding Manual Notes
1. Go to "Add Manual Note" tab
2. Select record type and specific record
3. Enter previous status, new status, and notes
4. Click "Add Note" to save

## Status Color Coding
- 🟡 Created/Draft - Initial status
- 🔵 Confirmed - Confirmed status
- 🟠 Dispatched - In progress
- 🟢 Delivered/Active - Completed/Active
- ✅ POD Generated/Paid - Finalized
- ❌ Cancelled/Rejected - Terminated
- ⚠️ Overdue - Needs attention
- 📄 Generated/Invoiced - Document created

## Benefits

### For Management
- Complete visibility into status progression
- Identify bottlenecks in workflow
- Track performance metrics
- Audit trail for all changes

### For Operations
- Quick status checks for any record
- Historical context for decision making
- Easy identification of stuck processes
- Better customer communication

### For Compliance
- Complete audit trail
- Time-stamped status changes
- User accountability
- Export capabilities for reporting

## Data Privacy & Security
- All status changes are logged with timestamps
- User identification for accountability
- Secure database storage
- Export capabilities for backup and analysis

## Future Enhancements
- Email notifications for status changes
- Workflow automation based on status
- Custom status definitions per record type
- Integration with external systems
- Advanced analytics and reporting
- Mobile app notifications

## API Integration
The notes module can be extended to work with external APIs:

```python
# Example webhook integration
def notify_external_system(record_id, record_type, new_status):
    webhook_url = "https://api.example.com/status-update"
    payload = {
        "record_id": record_id,
        "record_type": record_type,
        "status": new_status,
        "timestamp": datetime.datetime.now().isoformat()
    }
    requests.post(webhook_url, json=payload)
```

## Troubleshooting

### Common Issues
1. **Missing status history**: Ensure the notes module is properly imported in other modules
2. **Database errors**: Check database connection and table creation
3. **Performance issues**: Use pagination for large datasets
4. **Duplicate entries**: Implement proper status change validation

### Support
For technical support or feature requests, contact: admin@stranz.in