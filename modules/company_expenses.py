import streamlit as st
import pandas as pd
import datetime
import uuid
from typing import Dict, List

def format_datetime(date_field):
    """Safely format datetime from various formats"""
    if not date_field:
        return "Not set"
    
    if isinstance(date_field, str):
        try:
            # Try parsing ISO format with timezone
            dt = datetime.datetime.fromisoformat(date_field.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            try:
                # Try parsing standard format
                dt = datetime.datetime.strptime(date_field, '%Y-%m-%d %H:%M:%S')
                return dt.strftime('%Y-%m-%d %H:%M')
            except:
                try:
                    # Try parsing date only
                    dt = datetime.datetime.strptime(date_field, '%Y-%m-%d')
                    return dt.strftime('%Y-%m-%d')
                except:
                    return str(date_field)  # Return as is if can't parse
    elif hasattr(date_field, 'strftime'):
        return date_field.strftime('%Y-%m-%d %H:%M')
    else:
        return str(date_field)

def show():
    """Display the company expenses module"""
    # Load data when needed
    from database import load_data_when_needed
    load_data_when_needed('expenses')
    
    st.header("🏢 Company Expenses Tracking")
    
    tab1, tab2 = st.tabs(["Record Expense", "View Expenses"])
    
    with tab1:
        record_expense()
    
    with tab2:
        view_expenses()

def record_expense():
    """Record a new company expense"""
    st.subheader("Record New Expense")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        expense_date = st.date_input("Expense Date*", value=datetime.datetime.now().date(), key="expense_date")
        expense_category = st.selectbox(
            "Category*",
            [
                "Employee welfare", "Vehicle inauguration", "Stationery and office supplies",
                "Printer and equipment maintenance", "Office rent", "Vehicle loans and EMI",
                "Vehicle insurance premiums", "Permits and documentation",
                "Utility bills", "Travel and conveyance", "Professional fees",
                "Bank charges", "Miscellaneous expenses"
            ],
            key="expense_category"
        )
    
    with col2:
        expense_amount = st.number_input("Amount (₹)*", min_value=0.0, value=0.0, key="expense_amount")
        payment_method = st.selectbox(
            "Payment Method*",
            ["Cash", "Bank Transfer", "Card", "Cheque", "UPI"],
            key="expense_payment_method"
        )
    
    with col3:
        receipt_reference = st.text_input("Receipt Reference/Bill Number", key="expense_receipt")
        
    description = st.text_area("Description*", key="expense_description", 
                              placeholder="Detailed description of the expense")
    
    remarks = st.text_area("Remarks", key="expense_remarks", 
                          placeholder="Additional notes or comments")
    
    if st.button("Record Expense", type="primary"):
        if not expense_date or not expense_category or expense_amount <= 0 or not description:
            st.error("Date, category, amount, and description are required")
            return
        
        expense = {
            'id': str(uuid.uuid4()),
            'expense_date': expense_date,
            'category': expense_category,
            'description': description,
            'amount': expense_amount,
            'payment_method': payment_method,
            'receipt_reference': receipt_reference,
            'remarks': remarks,
            'created_date': datetime.datetime.now(),
            'created_by': 'Admin'
        }
        
        # Save to database
        from app import save_expense
        if save_expense(expense):
            # Refresh expenses data from database
            from database import load_data_when_needed
            st.session_state.expenses = []  # Clear cache to force reload
            load_data_when_needed('expenses')
            
            # Add to session state for immediate display
            if 'expenses' not in st.session_state:
                st.session_state.expenses = []
            st.session_state.expenses.append(expense)
            
            st.success(f"Expense of ₹{expense_amount:,.2f} recorded successfully!")
            
            # Clear form
            for key in st.session_state.keys():
                if key.startswith('expense_'):
                    del st.session_state[key]
            
            st.rerun()
        else:
            st.error("Failed to save expense. Please try again.")

def view_expenses():
    """View and analyze expenses"""
    st.subheader("View Company Expenses")
    
    if not st.session_state.expenses:
        st.info("No expenses recorded yet.")
        return
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        category_filter = st.selectbox(
            "Filter by Category",
            ["All"] + list(set([exp['category'] for exp in st.session_state.expenses])),
            key="expense_category_filter"
        )
    
    with col2:
        payment_method_filter = st.selectbox(
            "Filter by Payment Method",
            ["All"] + list(set([exp['payment_method'] for exp in st.session_state.expenses])),
            key="expense_method_filter"
        )
    
    with col3:
        from_date = st.date_input(
            "From Date",
            value=datetime.datetime.now() - datetime.timedelta(days=30),
            key="expense_from_date"
        )
    
    with col4:
        to_date = st.date_input(
            "To Date",
            value=datetime.datetime.now().date(),
            key="expense_to_date"
        )
    
    # Filter expenses
    filtered_expenses = st.session_state.expenses
    
    if category_filter != "All":
        filtered_expenses = [exp for exp in filtered_expenses if exp['category'] == category_filter]
    
    if payment_method_filter != "All":
        filtered_expenses = [exp for exp in filtered_expenses if exp['payment_method'] == payment_method_filter]
    
    filtered_expenses = [exp for exp in filtered_expenses if from_date <= exp['expense_date'] <= to_date]
    
    # Summary metrics
    total_expenses = len(filtered_expenses)
    total_amount = sum(exp['amount'] for exp in filtered_expenses)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Expenses", total_expenses)
    with col2:
        st.metric("Total Amount", f"₹{total_amount:,.2f}")
    with col3:
        avg_expense = total_amount / total_expenses if total_expenses > 0 else 0
        st.metric("Average Expense", f"₹{avg_expense:,.2f}")
    
    # Category breakdown
    if filtered_expenses:
        st.markdown("---")
        st.markdown("### Category Breakdown")
        
        category_summary = {}
        for expense in filtered_expenses:
            category = expense['category']
            if category not in category_summary:
                category_summary[category] = {'count': 0, 'amount': 0}
            category_summary[category]['count'] += 1
            category_summary[category]['amount'] += expense['amount']
        
        category_data = []
        for category, data in category_summary.items():
            category_data.append({
                'Category': category,
                'Count': data['count'],
                'Total Amount': f"₹{data['amount']:,.2f}",
                'Average': f"₹{data['amount']/data['count']:,.2f}"
            })
        
        df_categories = pd.DataFrame(category_data)
        st.dataframe(df_categories, use_container_width=True)
        
        # Monthly trend
        st.markdown("### Monthly Expense Trend")
        
        monthly_summary = {}
        for expense in filtered_expenses:
            month_key = expense['expense_date'].strftime('%Y-%m')
            if month_key not in monthly_summary:
                monthly_summary[month_key] = 0
            monthly_summary[month_key] += expense['amount']
        
        if monthly_summary:
            monthly_data = pd.DataFrame([
                {'Month': month, 'Amount': amount} 
                for month, amount in sorted(monthly_summary.items())
            ])
            st.line_chart(monthly_data.set_index('Month'))
    
    st.markdown("---")
    st.markdown("### Expense Details")
    
    # Display expenses
    for expense in filtered_expenses:
        with st.expander(f"₹{expense['amount']:,.2f} - {expense['category']} - {expense['expense_date']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Date:** {expense['expense_date']}")
                st.write(f"**Category:** {expense['category']}")
                st.write(f"**Amount:** ₹{expense['amount']:,.2f}")
                st.write(f"**Payment Method:** {expense['payment_method']}")
                if expense.get('receipt_reference'):
                    st.write(f"**Receipt Reference:** {expense['receipt_reference']}")
            
            with col2:
                st.write(f"**Description:** {expense['description']}")
                if expense.get('remarks'):
                    st.write(f"**Remarks:** {expense['remarks']}")
                st.write(f"**Recorded:** {format_datetime(expense.get('created_date'))}")
            
            # Delete expense
            if st.button(f"Delete", key=f"delete_expense_{expense['id']}"):
                # Delete from database
                from database import delete_from_database
                if delete_from_database('expenses', expense['id']):
                    # Remove from session state
                    st.session_state.expenses = [exp for exp in st.session_state.expenses if exp['id'] != expense['id']]
                    st.success("Expense deleted successfully!")
                else:
                    st.error("Failed to delete expense from database")
                st.rerun()
    
    # Export options
    st.markdown("---")
    if st.button("Export Expenses to CSV"):
        export_data = []
        for exp in filtered_expenses:
            export_data.append({
                'Date': exp['expense_date'],
                'Category': exp['category'],
                'Description': exp['description'],
                'Amount': exp['amount'],
                'Payment Method': exp['payment_method'],
                'Receipt Reference': exp.get('receipt_reference', ''),
                'Remarks': exp.get('remarks', ''),
                'Recorded Date': format_datetime(exp.get('created_date'))
            })
        
        df = pd.DataFrame(export_data)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"expenses_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )