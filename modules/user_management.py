"""
User Management Module for Stranz Transport Management System
Handles user creation, management, and authentication
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    create_user, get_all_users, toggle_user_status, delete_user, 
    generate_random_password, load_data_when_needed, reset_user_password
)

def show():
    """Display the User Management interface"""
    
    # Check if user is admin
    if st.session_state.get('user_role') != 'Administrator':
        st.error("🚫 Access Denied: Only administrators can manage users")
        return
    
    st.markdown("### 👥 User Management")
    
    # Create two tabs: User List and Create User
    tab1, tab2 = st.tabs(["👥 User List", "➕ Create New User"])
    
    with tab2:
        show_create_user_form()
    
    with tab1:
        show_user_list()

def show_create_user_form():
    """Show the create user form"""
    st.markdown("#### ➕ Create New User")
    
    # Initialize session state for form data persistence
    form_keys = ['form_username', 'form_first_name', 'form_last_name', 'form_email', 'form_mobile', 'form_role']
    for key in form_keys:
        if key not in st.session_state:
            st.session_state[key] = ""
    
    if 'form_role_index' not in st.session_state:
        st.session_state.form_role_index = 0
    
    # Create user form
    with st.form("create_user_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username*", value=st.session_state.form_username, placeholder="Enter username")
            first_name = st.text_input("First Name*", value=st.session_state.form_first_name, placeholder="Enter first name")
            email = st.text_input("Email Address*", value=st.session_state.form_email, placeholder="Enter email address")
            role = st.selectbox("Role", ["User", "Manager", "Administrator"], index=st.session_state.form_role_index)
        
        with col2:
            mobile_number = st.text_input("Mobile Number", value=st.session_state.form_mobile, placeholder="Enter mobile number")
            last_name = st.text_input("Last Name*", value=st.session_state.form_last_name, placeholder="Enter last name")
            
            # Password generation section
            st.markdown("##### 🔒 Password")
            col_pass1, col_pass2 = st.columns([2, 1])
            
            with col_pass1:
                if 'generated_password' not in st.session_state:
                    st.session_state.generated_password = ""
                
                # Show password field - always use default type to show generated password clearly
                password = st.text_input(
                    "Password", 
                    value=st.session_state.generated_password,
                    type="default",
                    placeholder="Click Generate to create password"
                )
            
            with col_pass2:
                generate_button = st.form_submit_button("🎲 Generate", type="secondary")
                
        # Form submission
        submitted = st.form_submit_button("✅ Create User", type="primary", use_container_width=True)
        
        # Handle password generation
        if generate_button:
            # Store form data in session state
            st.session_state.form_username = username
            st.session_state.form_first_name = first_name
            st.session_state.form_last_name = last_name
            st.session_state.form_email = email
            st.session_state.form_mobile = mobile_number
            st.session_state.form_role_index = ["User", "Manager", "Administrator"].index(role)
            
            # Generate password
            st.session_state.generated_password = generate_random_password()
            st.rerun()
        
        if submitted:
            # Validate required fields
            if not all([username, first_name, last_name, email, password]):
                st.error("❌ Please fill in all required fields marked with *")
                return
            
            # Validate email format
            if "@" not in email or "." not in email:
                st.error("❌ Please enter a valid email address")
                return
            
            # Create user data
            user_data = {
                'username': username.strip(),
                'first_name': first_name.strip(),
                'last_name': last_name.strip(),
                'email': email.strip(),
                'mobile_number': mobile_number.strip(),
                'role': role,
                'password': password,
                'created_by': st.session_state.get('user_full_name', 'Admin')
            }
            
            # Create user
            success, message = create_user(user_data)
            
            if success:
                st.success(f"✅ {message}")
                st.info(f"🔑 **Temporary Password:** {password}")
                st.info("📝 **Note:** User will be asked to change password on first login")
                
                # Clear form data
                for key in form_keys:
                    st.session_state[key] = ""
                st.session_state.form_role_index = 0
                st.session_state.generated_password = ""
                
                # Refresh user list
                if 'users' in st.session_state:
                    del st.session_state['users']
                
                st.rerun()
            else:
                st.error(f"❌ {message}")

def show_user_list():
    """Show the list of all users"""
    st.markdown("#### 👥 User List")
    
    # Load users data
    users = get_all_users()
    
    if not users:
        st.info("📝 No users found. Create the first user using the 'Create New User' tab.")
        return
    
    # Convert to DataFrame for better display
    df_users = pd.DataFrame(users)
    
    # Format the data for display
    df_display = df_users.copy()
    df_display['Full Name'] = df_display['first_name'] + ' ' + df_display['last_name']
    df_display['Status'] = df_display['is_active'].apply(lambda x: '✅ Active' if x else '❌ Disabled')
    df_display['Password Status'] = df_display['password_changed'].apply(lambda x: '✅ Changed' if x else '🔄 Needs Change')
    df_display['Created Date'] = pd.to_datetime(df_display['created_date']).dt.strftime('%Y-%m-%d %H:%M')
    df_display['Last Login'] = pd.to_datetime(df_display['last_login']).dt.strftime('%Y-%m-%d %H:%M') if 'last_login' in df_display.columns else 'Never'
    
    # Select columns to display
    display_columns = ['Full Name', 'username', 'email', 'mobile_number', 'role', 'Status', 'Password Status', 'Created Date', 'Last Login']
    df_show = df_display[display_columns]
    
    # Display the dataframe
    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Full Name": st.column_config.TextColumn("Full Name", width="medium"),
            "username": st.column_config.TextColumn("Username", width="medium"),
            "email": st.column_config.TextColumn("Email", width="large"),
            "mobile_number": st.column_config.TextColumn("Mobile", width="medium"),
            "role": st.column_config.TextColumn("Role", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Password Status": st.column_config.TextColumn("Password", width="small"),
            "Created Date": st.column_config.TextColumn("Created", width="medium"),
            "Last Login": st.column_config.TextColumn("Last Login", width="medium")
        }
    )
    
    # User management actions
    st.markdown("#### 🛠️ User Management Actions")
    
    # Select user for actions
    user_options = {f"{user['first_name']} {user['last_name']} ({user['username']})": user for user in users}
    
    if user_options:
        selected_user_display = st.selectbox(
            "Select User for Action:",
            list(user_options.keys()),
            key="selected_user_for_action"
        )
        
        selected_user = user_options[selected_user_display]
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Toggle status button
            current_status = "Active" if selected_user['is_active'] else "Disabled"
            new_status = "Disable" if selected_user['is_active'] else "Enable"
            
            if st.button(f"🔄 {new_status} User", key="toggle_status"):
                success, message = toggle_user_status(selected_user['id'], not selected_user['is_active'])
                
                if success:
                    st.success(f"✅ {message}")
                    # Refresh user list
                    if 'users' in st.session_state:
                        del st.session_state['users']
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        with col2:
            # Reset password button
            if st.button("🔑 Reset Password", key="reset_password"):
                new_password = generate_random_password()
                
                # Update user password in database
                from database import update_user_password
                
                # Reset password and mark as needs change
                success, message = reset_user_password(selected_user['id'], new_password)
                
                if success:
                    # Store the new password and user info for popup
                    st.session_state['show_password_popup'] = True
                    st.session_state['reset_password_value'] = new_password
                    st.session_state['reset_user_name'] = f"{selected_user['first_name']} {selected_user['last_name']}"
                    
                    # Refresh user list
                    if 'users' in st.session_state:
                        del st.session_state['users']
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    # Password Reset Popup
    if st.session_state.get('show_password_popup', False):
        st.markdown("---")
        
        # Create a popup-like container
        with st.container():
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1.5rem;
                border-radius: 12px;
                margin: 1rem 0;
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
                border: 2px solid #667eea;
            ">
                <h3 style="color: white; margin: 0 0 1rem 0; text-align: center;">
                    🔑 Password Reset Successful
                </h3>
            </div>
            """, unsafe_allow_html=True)
            
            # User info and password display
            user_name = st.session_state.get('reset_user_name', 'User')
            new_password = st.session_state.get('reset_password_value', '')
            
            st.success(f"✅ Password reset successfully for **{user_name}**!")
            
            # Password display section with copy functionality
            col_pass, col_copy, col_close = st.columns([3, 1, 1])
            
            with col_pass:
                st.text_input(
                    "New Password:", 
                    value=new_password,
                    type="default",
                    disabled=True,
                    key="display_reset_password"
                )
            
            with col_copy:
                if st.button("📋 Copy", key="copy_password_btn", type="secondary"):
                    # JavaScript to copy to clipboard
                    st.markdown(f"""
                    <script>
                    navigator.clipboard.writeText('{new_password}').then(function() {{
                        console.log('Password copied to clipboard');
                    }});
                    </script>
                    """, unsafe_allow_html=True)
                    st.success("📋 Copied!")
            
            with col_close:
                if st.button("❌ Close", key="close_popup_btn", type="primary"):
                    # Clear popup state
                    st.session_state['show_password_popup'] = False
                    if 'reset_password_value' in st.session_state:
                        del st.session_state['reset_password_value']
                    if 'reset_user_name' in st.session_state:
                        del st.session_state['reset_user_name']
                    st.rerun()
            
            # Important notes
            st.info("📝 **Important Notes:**")
            st.markdown("""
            - Share this password securely with the user
            - User will be asked to change this password on next login
            - This password will not be shown again after closing this popup
            - Make sure to copy the password before closing
            """)
            
            # Auto-copy text for easy sharing
            st.code(f"Username: {selected_user['username']}\nTemporary Password: {new_password}")
        
        st.markdown("---")
        
        with col3:
            # View user details button
            if st.button("👁️ View Details", key="view_details"):
                show_user_details(selected_user)
        
        with col4:
            # Delete user button
            if st.button("🗑️ Delete User", key="delete_user", type="secondary"):
                show_delete_confirmation(selected_user)

def show_user_details(user):
    """Show detailed user information"""
    st.markdown(f"#### 👤 User Details: {user['first_name']} {user['last_name']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Username:** {user['username']}")
        st.markdown(f"**Email:** {user['email']}")
        st.markdown(f"**Role:** {user['role']}")
        st.markdown(f"**Status:** {'✅ Active' if user['is_active'] else '❌ Disabled'}")
    
    with col2:
        st.markdown(f"**Mobile:** {user.get('mobile_number', 'N/A')}")
        st.markdown(f"**Created By:** {user.get('created_by', 'N/A')}")
        st.markdown(f"**Password Changed:** {'✅ Yes' if user['password_changed'] else '🔄 No'}")
        
        created_date = pd.to_datetime(user['created_date']).strftime('%Y-%m-%d %H:%M:%S') if user['created_date'] else 'N/A'
        st.markdown(f"**Created Date:** {created_date}")

def show_delete_confirmation(user):
    """Show delete confirmation dialog"""
    if f"confirm_delete_{user['id']}" not in st.session_state:
        st.session_state[f"confirm_delete_{user['id']}"] = False
    
    if not st.session_state[f"confirm_delete_{user['id']}"]:
        if st.button(f"⚠️ Confirm Delete: {user['first_name']} {user['last_name']}", key=f"confirm_delete_btn_{user['id']}"):
            st.session_state[f"confirm_delete_{user['id']}"] = True
            st.rerun()
    else:
        st.warning(f"⚠️ **Are you sure you want to delete user '{user['first_name']} {user['last_name']}'?**")
        st.markdown("This action cannot be undone!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Yes, Delete", key=f"final_delete_{user['id']}", type="primary"):
                success, message = delete_user(user['id'])
                
                if success:
                    st.success(f"✅ {message}")
                    # Refresh user list
                    if 'users' in st.session_state:
                        del st.session_state['users']
                    # Clear confirmation state
                    del st.session_state[f"confirm_delete_{user['id']}"]
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        with col2:
            if st.button("❌ Cancel", key=f"cancel_delete_{user['id']}"):
                del st.session_state[f"confirm_delete_{user['id']}"]
                st.rerun()