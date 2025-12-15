# Stranz Transport Management System

A comprehensive transport management system built with Streamlit for managing quotations, bookings, invoicing, payments, and vehicle operations.

## Features

### Core Modules
- **Quotations Management** - Create and manage customer quotations with approval workflow
- **Bookings Management** - Convert quotations to bookings, track delivery status
- **Invoicing** - Generate GST, Cash, and Contract invoices with movement type selection
- **Customer Payments** - Record payments, allocation to invoices, aging analysis
- **Vendor Management** - Track vendor bills and payments with category breakdown
- **Company Expenses** - Monitor operational expenses across multiple categories
- **Vehicle Master** - Manage vehicles, drivers, fuel logs, and odometer readings
- **Dashboard** - Real-time KPIs, charts, and performance analytics
- **Audit Exports** - Comprehensive data exports for audit purposes

### Key Business Rules
- Unique number sequences for bookings, invoices, quotations, and DSR
- Financial year-based numbering (resets every April)
- Cash invoices use booking numbers as invoice numbers
- POD capture required before invoice generation
- Payment allocation with outstanding tracking
- Overdue highlighting with color coding (Green/Yellow/Red)

### Number Formatting
- **Booking**: STZB2526-00001
- **Invoice**: 2526STZ-00001 (except Cash invoices)
- **Quotation**: STZQ2526-00001
- **DSR**: DSR251100001

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd TransportManagement
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

## Usage

1. **Start with Quotations** - Create customer quotations with pricing details
2. **Approve and Convert** - Approve quotations and convert to bookings
3. **Track Delivery** - Monitor booking status from creation to POD capture
4. **Generate Invoices** - Create invoices after POD capture with movement type selection
5. **Record Payments** - Track customer payments and allocate to invoices
6. **Monitor Operations** - Use dashboard for real-time insights

### Customer Payment Flow
1. Invoice Generated → Outstanding Balance Created
2. Customer Payment Entry → Allocation to Invoices (or mark as unallocated)
3. Monthly Statement Generation with aging analysis

### Vehicle Operations
- Record fuel consumption and odometer readings
- Track monthly vehicle metrics (KMPL, efficiency)
- Flag overutilization (>20% deviation from baseline)

## Data Storage
The application uses Streamlit session state for data persistence during the session. For production use, integrate with a proper database system.

## Export Capabilities
- Customer statements (PDF/Excel/CSV)
- Vendor ledgers
- Vehicle reports
- Comprehensive audit exports
- Outstanding and aging reports

## Business Intelligence
- Revenue vs Collections tracking
- Vehicle utilization analysis
- Category-wise expense monitoring
- Customer outstanding management
- Operational KPI dashboard

## Architecture
```
app.py                 # Main application entry point
modules/
├── quotations.py      # Quotation management
├── bookings.py        # Booking operations
├── invoicing.py       # Invoice generation
├── customer_payments.py # Payment processing
├── vendor_management.py # Vendor operations
├── company_expenses.py # Expense tracking
├── vehicle_master.py  # Vehicle and driver management
├── dashboard.py       # Analytics dashboard
└── audit_exports.py   # Export functionality
```

## Support
For technical support or queries, contact: admin@stranz.in

---
**Stranz Transport Management System v1.0**  
*Prepared by: Saran S P, Head of Digital Transformation*