"""
User Management Module for Stranz Transport Management System
Handles user creation, management, and authentication
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    create_user, get_all_users, toggle_user_status, delete_user, 
    generate_random_password, load_data_when_needed, reset_user_password, update_user
)

def show():
    """Display the User Management interface"""
    
    # Check if user is admin
    if st.session_state.get('user_role') != 'Administrator':
        st.error("Access Denied: Only administrators can manage users")
        return
    
    st.markdown("### 👥 User Management")
    
    # Create two tabs: User List and Create User
    tab1, tab2 = st.tabs(["User List", "Create New User"])
    
    with tab2:
        show_create_user_form()
    
    with tab1:
        show_user_list()

def show_create_user_form():
    """Show the create user form"""
    st.markdown("#### Create New User")
    
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
            st.markdown("##### Password")
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
        submitted = st.form_submit_button("Create User", type="primary", use_container_width=True)
        
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
                st.error("Please fill in all required fields marked with *")
                return
            
            # Validate email format
            if "@" not in email or "." not in email:
                st.error("Please enter a valid email address")
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
                st.info(f"**Temporary Password:** {password}")
                st.info("**Note:** User will be asked to change password on first login")
                
                # Additional success actions
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Create Another User", key="create_another_user", type="primary"):
                        # Keep the current form for creating another user
                        pass  # Form will be ready for next user
                with col2:
                    if st.button("👥 View User List", key="view_user_list"):
                        # Switch to user list tab
                        st.info("Switch to 'User List' tab to view all users")
                
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
    """Show the list of all users with integrated actions"""
    st.markdown("#### 👥 User List & Management")
    
    # Load users data
    users = get_all_users()
    
    if not users:
        st.info("No users found. Create the first user using the 'Create New User' tab.")
        return
    
    # User list with actions
    for i, user in enumerate(users):
        # Create a container for each user row
        with st.container():
            # Create columns for user info and actions
            col_info, col_actions = st.columns([3, 1])
            
            with col_info:
                # User information display
                status_icon = 'Active' if user['is_active'] else 'Disabled'
                password_icon = 'Changed' if user['password_changed'] else 'Needs Change'
                
                st.markdown(f"""
                **{user['first_name']} {user['last_name']}** {status_icon}
                
                - **Username:** {user['username']} | **Role:** {user['role']} 
                - **Email:** {user['email']} | **Mobile:** {user.get('mobile_number', 'N/A')}
                - **Password Status:** {password_icon} {'Changed' if user['password_changed'] else 'Needs Change'}
                - **Created:** {pd.to_datetime(user['created_date']).strftime('%Y-%m-%d %H:%M') if user['created_date'] else 'N/A'}
                """)
            
            with col_actions:
                # Action buttons for each user
                st.markdown("##### Actions")
                
                # Edit button
                if st.button(f"Edit", key=f"edit_user_{user['id']}", type="secondary", use_container_width=True):
                    st.session_state[f'editing_user_{user["id"]}'] = True
                    st.session_state['current_edit_user'] = user
                    st.rerun()
                
                # Toggle status button
                status_text = "Disable" if user['is_active'] else "Enable"
                status_icon = "🔄"
                if st.button(f"{status_icon} {status_text}", key=f"toggle_{user['id']}", use_container_width=True):
                    success, message = toggle_user_status(user['id'], not user['is_active'])
                    if success:
                        st.success(f"{message}")
                        if 'users' in st.session_state:
                            del st.session_state['users']
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                
                # Reset password button
                if st.button(f"Reset Pwd", key=f"reset_{user['id']}", use_container_width=True):
                    new_password = generate_random_password()
                    success, message = reset_user_password(user['id'], new_password)
                    if success:
                        st.session_state['show_password_popup'] = True
                        st.session_state['reset_password_value'] = new_password
                        st.session_state['reset_user_name'] = f"{user['first_name']} {user['last_name']}"
                        if 'users' in st.session_state:
                            del st.session_state['users']
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                
                # Delete button
                if st.button(f"Delete", key=f"delete_{user['id']}", type="secondary", use_container_width=True):
                    st.session_state[f'confirm_delete_{user["id"]}'] = True
                    st.rerun()
        
        # Show edit form if this user is being edited
        if st.session_state.get(f'editing_user_{user["id"]}', False):
            show_edit_user_form(user)
        
        # Show delete confirmation if requested
        if st.session_state.get(f'confirm_delete_{user["id"]}', False):
            show_delete_confirmation_inline(user)
        
        st.markdown("---")  # Separator between users
    
    # Password Reset Popup (if any)
    if st.session_state.get('show_password_popup', False):
        show_password_reset_popup()
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
            if st.button("View Details", key="view_details"):
                show_user_details(selected_user)
        
        with col4:
            # Delete user button
            if st.button("Delete User", key="delete_user", type="secondary"):
                show_delete_confirmation(selected_user)

def show_user_details(user):
    """Show detailed user information"""
    st.markdown(f"#### User Details: {user['first_name']} {user['last_name']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Username:** {user['username']}")
        st.markdown(f"**Email:** {user['email']}")
        st.markdown(f"**Role:** {user['role']}")
        st.markdown(f"**Status:** {'Active' if user['is_active'] else 'Disabled'}")
    
    with col2:
        st.markdown(f"**Mobile:** {user.get('mobile_number', 'N/A')}")
        st.markdown(f"**Created By:** {user.get('created_by', 'N/A')}")
        st.markdown(f"**Password Changed:** {'Yes' if user['password_changed'] else 'No'}")
        
        created_date = pd.to_datetime(user['created_date']).strftime('%Y-%m-%d %H:%M:%S') if user['created_date'] else 'N/A'
        st.markdown(f"**Created Date:** {created_date}")

def show_delete_confirmation(user):
    """Show delete confirmation dialog"""
    if f"confirm_delete_{user['id']}" not in st.session_state:
        st.session_state[f"confirm_delete_{user['id']}"] = False
    
    if not st.session_state[f"confirm_delete_{user['id']}"]:
        if st.button(f"Confirm Delete: {user['first_name']} {user['last_name']}", key=f"confirm_delete_btn_{user['id']}"):
            st.session_state[f"confirm_delete_{user['id']}"] = True
            st.rerun()
    else:
        st.warning(f"**Are you sure you want to delete user '{user['first_name']} {user['last_name']}'?**")
        st.markdown("This action cannot be undone!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Yes, Delete", key=f"final_delete_{user['id']}", type="primary"):
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
            if st.button("Cancel", key=f"cancel_delete_{user['id']}"):
                del st.session_state[f"confirm_delete_{user['id']}"]
                st.rerun()

def show_edit_user_form(user):
    """Show edit user form"""
    st.markdown(f"#### Edit User: {user['first_name']} {user['last_name']}")
    
    with st.form(f"edit_user_form_{user['id']}", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input("First Name*", value=user['first_name'])
            email = st.text_input("Email Address*", value=user['email'])
            role = st.selectbox("Role", ["User", "Manager", "Administrator"], 
                              index=["User", "Manager", "Administrator"].index(user['role']))
        
        with col2:
            last_name = st.text_input("Last Name*", value=user['last_name'])
            mobile_number = st.text_input("Mobile Number", value=user.get('mobile_number', ''))
        
        # Form buttons
        col_save, col_cancel = st.columns(2)
        
        with col_save:
            save_clicked = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
        
        with col_cancel:
            cancel_clicked = st.form_submit_button("Cancel", use_container_width=True)
        
        if save_clicked:
            # Validate required fields
            if not all([first_name, last_name, email]):
                st.error("❌ Please fill in all required fields marked with *")
                return
            
            # Validate email format
            if "@" not in email or "." not in email:
                st.error("❌ Please enter a valid email address")
                return
            
            # Prepare user data for update
            updated_data = {
                'first_name': first_name.strip(),
                'last_name': last_name.strip(),
                'email': email.strip(),
                'mobile_number': mobile_number.strip(),
                'role': role
            }
            
            # Update user
            success, message = update_user(user['id'], updated_data)
            
            if success:
                st.success(f"✅ {message}")
                
                # Clear editing state
                if f'editing_user_{user["id"]}' in st.session_state:
                    del st.session_state[f'editing_user_{user["id"]}']
                
                # Refresh user list
                if 'users' in st.session_state:
                    del st.session_state['users']
                
                st.rerun()
            else:
                st.error(f"❌ {message}")
        
        if cancel_clicked:
            # Clear editing state
            if f'editing_user_{user["id"]}' in st.session_state:
                del st.session_state[f'editing_user_{user["id"]}']
            st.rerun()

def show_delete_confirmation_inline(user):
    """Show inline delete confirmation for a specific user"""
    st.markdown(f"#### Delete User: {user['first_name']} {user['last_name']}")
    st.warning("Are you sure you want to delete this user? This action cannot be undone!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Yes, Delete", key=f"final_delete_inline_{user['id']}", type="primary", use_container_width=True):
            success, message = delete_user(user['id'])
            
            if success:
                st.success(f"✅ {message}")
                # Refresh user list
                if 'users' in st.session_state:
                    del st.session_state['users']
                # Clear confirmation state
                if f'confirm_delete_{user["id"]}' in st.session_state:
                    del st.session_state[f'confirm_delete_{user["id"]}']
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    with col2:
        if st.button("Cancel", key=f"cancel_delete_inline_{user['id']}", use_container_width=True):
            if f'confirm_delete_{user["id"]}' in st.session_state:
                del st.session_state[f'confirm_delete_{user["id"]}']
            st.rerun()

def show_password_reset_popup():
    """Show password reset popup"""
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
                Password Reset Successful
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # User info and password display
        user_name = st.session_state.get('reset_user_name', 'User')
        new_password = st.session_state.get('reset_password_value', '')
        
        st.success(f"Password reset successfully for **{user_name}**!")
        
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
            if st.button("Copy", key="copy_password_btn", type="secondary"):
                # JavaScript to copy to clipboard
                st.markdown(f"""
                <script>
                navigator.clipboard.writeText('{new_password}').then(function() {{
                    console.log('Password copied to clipboard');
                }});
                </script>
                """, unsafe_allow_html=True)
                st.success("Copied!")
        
        with col_close:
            if st.button("Close", key="close_popup_btn", type="primary"):
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
        st.code(f"Username: {st.session_state.get('current_reset_username', '')}\nTemporary Password: {new_password}")