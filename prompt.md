------------------------------------------------------------ 
TRANSPORT MANAGEMENT SYSTEM 
Functional Specification Document ------------------------------------------------------------ 
Prepared By: Saran S P 
Designation: Head of Digital Transformation 
Organization: Stranz 
Contact: admin@stranz.in 
Date: December 2025 
Version: 1.0 
Stranz Controlled Copy not to be reused or shared 
Page 1 | 17 
 
Stranz Controlled Copy not to be reused or shared 
Page 2 | 17 
 
 
 
Section Title 
1 Customer Payments, Outstandings, and Monthly Statement 
2 Vendor Payments and Ledger 
3 Company Expenses Tracking 
4 Vehicle Master and Tracking 
5 Dashboards 
6 Audit-Ready Exports 
7 Number Formatting 
8 Module and Screen Summary 
9 Key Data Objects 
10 Critical Business Rules Summary 
11 Overdue Highlighting Color Scheme 
 
 
 
 
TRANSPORT MANAGEMENT SYSTEM - FUNCTIONAL SPECIFICATION 
1. CUSTOMER PAYMENTS, OUTSTANDINGS, AND MONTHLY STATEMENT 
1.1 Flow 
Invoice generated (GST/Cash/Contract) → Outstanding balance created → Customer 
payment entry → Allocation to specific bills → Monthly statement export (PDF/Excel/CSV) 
1.2 Payment Types 
Full Payment with Allocation: Customer pays and specifies which invoices are covered. 
System allocates payment to those invoices and reduces outstanding accordingly. 
Partial Payment without Allocation: Customer pays an amount but does not specify 
which invoices it covers. System records payment and reduces total customer 
outstanding. A flag marks this payment as "Unallocated" or "Pending Allocation." Later, 
when customer provides bill details, user updates the allocation. Until allocated, individual 
invoice outstanding remains unchanged but total customer outstanding reflects the 
payment. 
1.3 Payment Terms 
Payment terms are set per customer after quotation approval. Examples: 30 days, 45 days, 
60 days, 90 days. Payment terms determine the due date for each invoice (Invoice Date + 
Payment Terms = Due Date). Payment terms are used for aging calculations and overdue 
highlighting. 
1.4 Monthly Statement Contents 
• Statement period and generation date 
• Customer details and payment terms 
• Count of movements (completed bookings) in period 
• Invoice list: Invoice number, booking number, date, due date, amount, paid, 
outstanding, days overdue 
• Payment list: Date, amount, reference, allocation status (allocated/unallocated), 
mapped invoices 
• Outstanding summary: Total and per-invoice breakdown 
• Aging buckets: 0-30, 31-60, 61-90, 90+ days 
Stranz Controlled Copy not to be reused or shared 
Page 3 | 17 
• Spend graph: Monthly spending trend (bar/line chart) 
1.5 Overdue Highlighting Rules 
When generating customer reports, each invoice row is color-coded based on how many 
days past the payment terms it remains unpaid: 
• Green: Within payment terms (not yet due) 
• Yellow: 1 to 15 days past due date 
• Red: More than 15 days past due date 
Example: Customer has 45-day payment terms. Invoice dated 01-Oct-2025 has due date 
15-Nov-2025. If unpaid on 20-Dec-2025 (35 days overdue), that row appears in red. 
1.6 Export Formats 
All customer reports and statements exportable as CSV and Excel. PDF available for formal 
statements. 
2. VENDOR PAYMENTS AND LEDGER 
2.1 Flow 
Vendor bill/expense entry → Vendor outstanding created → Vendor payment entry → 
Allocation to bills → Vendor monthly ledger export 
2.2 Vendor Ledger Contents 
• Period and vendor details 
• Bills raised: Count and total value 
• Payments made: Count and total value 
• Outstanding as of period end 
• Category breakdown (fuel, maintenance, tolls, office, loans, insurance, etc.) 
• Bills table with payment status 
• Payments table with allocation details 
2.3 Export Formats 
CSV and Excel for all vendor reports. 
Stranz Controlled Copy not to be reused or shared 
Page 4 | 17 
3. COMPANY EXPENSES TRACKING 
3.1 Purpose 
Track non-commercial and administrative expenses incurred for company operations that 
are not directly tied to vendors or vehicle operations. 
3.2 Expense Categories 
• Employee welfare (snacks, refreshments, celebrations) 
• Vehicle inauguration expenses (pooja, ceremonies) 
• Stationery and office supplies 
• Printer and equipment maintenance 
• Office rent 
• Vehicle loans and EMI payments 
• Vehicle insurance premiums 
• Permits and documentation fees 
• Utility bills (electricity, internet, phone) 
• Travel and conveyance 
• Professional fees (CA, legal) 
• Bank charges 
• Miscellaneous expenses 
3.3 Expense Entry Fields 
• Date of expense 
• Category (from list above) 
• Description 
• Amount 
• Payment method (cash/bank/card) 
• Receipt reference or bill number (if any) 
Stranz Controlled Copy not to be reused or shared 
Page 5 | 17 
• Remarks 
3.4 Expense Reports 
• Monthly expense summary by category 
• Category-wise trend over months 
• Export as CSV/Excel 
4. VEHICLE MASTER AND TRACKING 
4.1 Vehicle Master Data 
• Registration number 
• Vehicle length and type 
• Fuel type 
• Linked driver (name, license number, phone) 
4.2 Logs 
Fuel Log: Date, vehicle, liters, cost, source, odometer reading 
Odometer Log: Date, vehicle, kilometer reading 
On monthly basis or weekly or 15 days once  
4.3 Monthly Vehicle Metrics 
• Total kilometers run 
• Total fuel consumed 
• Kilometers per liter 
• Fuel per 100 kilometers 
• Overutilization flag (if fuel efficiency deviates more than 20% from vehicle baseline) 
Stranz Controlled Copy not to be reused or shared 
Page 6 | 17 
5. DASHBOARDS 
5.1 Filters 
Day-wise, Month-wise, Year-wise period selection 
5.2 Metrics Displayed 
• Bookings count 
• Invoices generated count 
• Pending billings count (delivered but not invoiced) 
• Total revenue (billed) 
• Total receipts (collected) 
• Revenue vs receipts comparison 
• Vehicle fuel consumption (monthly rollup) 
• Vehicle kilometers run (monthly rollup) 
• Cash and Carry movements  
5.3 Visuals 
• KPI cards for counts 
• Line/bar charts for trends 
6. AUDIT-READY EXPORTS 
6.1 Export Contents (Date Range Selectable) 
• Bookings with status and numbers 
• Invoices (GST, Contract) with templates used 
• Customer payments with allocation references 
• Vendor bills and payments 
• Company expenses 
• Vehicle fuel and odometer logs 
Stranz Controlled Copy not to be reused or shared 
Page 7 | 17 
• DSR reports for contract periods 
6.2 Export Formats 
Primary: CSV and Excel (easy to share and analyze) 
Secondary: PDF bundles for invoices and DSR documents 
7. NUMBER FORMATTING 
7.1 Booking Number 
Format: STZB2526-00001 
• STZB = Fixed prefix 
• 2526 = Financial year token (FY 2025-26) 
• 00001 = 5-digit sequence, resets each financial year 
7.2 Invoice Number 
Format: 2526STZ-00001 
• 2526 = Financial year token 
• STZ = Fixed prefix 
• 00001 = 5-digit sequence, resets each financial year 
Cash and Carry Exception: Invoice number equals booking number. No separate invoice 
number generated. 
7.3 DSR Number 
Format: DSR251100001 
• DSR = Fixed prefix 
• 25 = Year (2025) 
• 11 = Month (November) 
• 00001 = 5-digit sequence, resets each month 
Stranz Controlled Copy not to be reused or shared 
Page 8 | 17 
7.4 Quotation Number 
Format: STZQ2526-00001 
• STZQ = Fixed prefix 
• 2526 = Financial year token 
• 00001 = 5-digit sequence, resets each financial year 
7.5 Sequence Rules 
• Numbers never reused, even if document cancelled 
• Independent sequences per document type 
• Booking, invoice, quotation reset sequence each April (new FY) 
• DSR resets sequence each calendar month 
8. MODULE AND SCREEN SUMMARY 
8.1 Quotations 
• Create/edit quotation 
• Set per-customer base price 
• Set payment terms per customer 
• Convert approved quotation to booking 
8.2 Bookings 
• Create/edit booking 
• Assign vehicle and driver 
• Record appointment schedule (pickup/drop) 
• Track status (created → confirmed → dispatched → delivered → POD captured) 
• Cancel booking (closes without invoice) 
Stranz Controlled Copy not to be reused or shared 
Page 9 | 17 
8.3 Invoicing 
Before invoice generation: Select movement type (Local/Long) 
GST Invoice: New invoice number generated, standard GST template 
Cash and Carry Invoice: Booking number used as invoice number, separate non-GST 
template 
Contract Invoice: New invoice number generated, contract start/end dates shown, DSR 
attached 
8.4 Customer Payments 
• Record payment with date, amount, method, reference 
• Option to allocate immediately or mark as unallocated 
• Update allocation later when customer provides details 
• View customer outstanding 
• Generate monthly statement with overdue highlighting 
• Export as CSV/Excel 
8.5 Vendor Management 
• Record vendor bill with category 
• Record vendor payment 
• Allocate payments to bills 
• View vendor outstanding 
• Generate vendor ledger 
• Export as CSV/Excel 
8.6 Company Expenses 
• Record expense with category, date, amount, description 
• View expense summary by category and period 
• Export as CSV/Excel 
8.7 Vehicle Master 
• Manage vehicle and driver records 
Stranz Controlled Copy not to be reused or shared 
Page 10 | 17 
• Enter fuel log and odometer log 
• View monthly utilization metrics 
• Flag overutilization 
8.8 Dashboards 
• Day/month/year filters 
• KPI cards and charts 
• Bookings, billings, pending billings, revenue, receipts, vehicle metrics 
8.9 Audit Exports 
• Select date range 
• Choose export components 
• Download CSV/Excel files and PDF bundles 
9. KEY DATA OBJECTS 
• Booking 
• Quotation 
• Invoice (GST, Cash, Contract) 
• Customer Payment 
• Payment Allocation 
• Vendor Bill 
• Vendor Payment 
• Company Expense 
• Vehicle 
• Driver 
• Fuel Log 
• Odometer Log 
• DSR Entry 
Stranz Controlled Copy not to be reused or shared 
Page 11 | 17 
10. CRITICAL BUSINESS RULES SUMMARY 
1. Booking number generated at booking creation, never changes 
2. Cancelled bookings retain their number, marked cancelled, no invoice generated 
3. POD must be captured before invoice can be generated 
4. Cash and Carry invoices use booking number as invoice number 
5. Movement type (Local/Long) selected before invoice generation and stored on 
invoice 
6. Payment terms set per customer, used for due date calculation and overdue 
highlighting 
7. Partial payments without allocation reduce total outstanding but individual invoices 
remain marked unpaid until allocation updated 
8. Overdue invoices highlighted by color based on days past payment terms 
9. All exports available in CSV and Excel formats 
10. Number sequences never reuse numbers, maintain continuity 
11. OVERDUE HIGHLIGHTING COLOR SCHEME 
Days Past Due Date Color 
Not yet due 
Green 
1-15 days overdue Yellow 
15+ days overdue 
Red 
This applies to all customer reports, statements, and aging reports. 
Stranz Controlled Copy not to be reused or shared 
Page 12 | 17 
Process Flow Overview: Quotation to Invoice Generation 
This flowchart outlines the workflow from quotation creation to invoice generation, 
covering approvals, booking management, trip types, and invoice issuance (GST, Cash, or 
Contract). 
1. Quotation Stage 
• Quotation Details: Create a quotation with customer and pricing details. 
• Approval Check:  
o If not approved (No), the quotation is closed and the process ends. 
o If approved (Yes), it proceeds to booking details. 
2. Booking Stage 
• Booking Details: Record trip specifics (e.g., vehicle, dates, locations). 
• Save Booking: Confirm and save the booking. 
• Generate Booking Number: Auto-generate a unique booking reference (e.g., 
STZB2526-00001). 
• Cancellation Check:  
o If cancelled (Yes), the booking is closed without invoicing, and the process 
ends. 
o If not cancelled (No), proceed to booking type selection. 
3. Booking Type Selection 
• Regular Trip: For standard, one-time deliveries. 
• Contract Trip: For ongoing agreements (e.g., monthly contracts). 
4. Trip Completion 
• Regular Trip: Marked as "Delivery Done" when completed. 
Stranz Controlled Copy not to be reused or shared 
Page 13 | 17 
• Contract Trip: Marked as "Contract Done" when the agreed period ends. 
5. Movement Selection 
Both trip types converge here to select the movement type (e.g., local or long-distance), 
which affects routing or pricing. 
6. Invoice Generation 
Based on the invoice type chosen, the system generates one of three invoice types: 
A. GST Invoice (Standard) 
• Enter Details: Input billing specifics (e.g., taxes, amounts). 
• Generate Invoice: Auto-generate an invoice number (e.g., 2526STZ-00001). 
• Output: Generate a GST-compliant PDF invoice and end the process. 
B. Cash Invoice (Non-GST) 
• Non-GST Template: Use a simplified template (no GST details). 
• Invoice Rule: The invoice number matches the booking number (e.g., STZB2526
00001). 
• Output: Generate a cash receipt PDF and end the process. 
C. Contract Invoice 
• Contract Template: Use a contract-specific template with start/end dates. 
• Generate Contract Invoice (CN) + DSR: Create a contract invoice number and 
attach a Daily Service Record (DSR) for the period. 
• Output: Generate a contract invoice PDF with DSR and end the process. 
Key Notes: 
• Cancellation: Bookings can be cancelled before invoicing, avoiding unnecessary 
invoices. 
Stranz Controlled Copy not to be reused or shared 
Page 14 | 17 
• Invoice Types: GST invoices generate new numbers; Cash invoices reuse booking 
numbers. 
• Contract Invoices: Include DSRs for compliance and tracking. 
• Endpoints: Each path concludes with a PDF invoice (GST, Cash, or Contract). 
This flowchart ensures a structured, audit-friendly process from quotation to final billing, 
with clear distinctions for regular, cash, and contract transactions. 
Stranz Controlled Copy not to be reused or shared 
Page 15 | 17 
FLOW CHART 
Stranz Controlled Copy not to be reused or shared 
Page 16 | 17 
DOCUMENT INFORMATION 
Document Prepared By: Saran S P 
Designation: Head of Digital Transformation 
Organization: Stranz 
Contact: admin@stranz.in 
For any doubts, clarifications, or queries regarding this document, please reach out. 
Stranz Controlled Copy not to be reused or shared 
Page 17 | 17 