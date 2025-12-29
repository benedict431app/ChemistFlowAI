import streamlit as st
import json
from datetime import datetime, timedelta
from database import init_db, create_admin_if_not_exists, UserRole
from auth import authenticate_user, create_user, get_admin_display_name, create_reset_token, reset_password_with_token
import sys

# Initialize database
init_db()
create_admin_if_not_exists()

# Page config - must be first Streamlit command
st.set_page_config(
    page_title="ChemistFlow - Pharmacy Management",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for mobile responsiveness
st.markdown("""
<style>
    /* Mobile-first responsive design */
    @media (max-width: 768px) {
        .stButton>button {
            width: 100%;
            margin-bottom: 10px;
        }
        .stDataFrame {
            font-size: 12px;
        }
    }
    
    /* Header styling */
    .pharmacy-header {
        background: linear-gradient(135deg, #1f77b4 0%, #2ca02c 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    
    /* Card styling */
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin-bottom: 10px;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #1f77b4;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        border: none;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #2ca02c;
        transform: translateY(-2px);
    }
    
    /* Notification badge */
    .notification-badge {
        background-color: #ff4b4b;
        color: white;
        border-radius: 50%;
        padding: 2px 8px;
        font-size: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'offline_mode' not in st.session_state:
    st.session_state.offline_mode = False

def logout():
    """Logout user"""
    st.session_state.user = None
    st.session_state.page = 'login'
    st.session_state.cart = []
    st.rerun()

def show_header():
    """Display header with pharmacy name"""
    pharmacy_name = get_admin_display_name()
    st.markdown(f"""
    <div class="pharmacy-header">
        <h1>💊 {pharmacy_name}</h1>
        <p>Your Complete Pharmacy Management Solution</p>
    </div>
    """, unsafe_allow_html=True)

def login_page():
    """Login page"""
    show_header()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Login")
        
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        col_login, col_register = st.columns(2)
        
        with col_login:
            if st.button("Login", use_container_width=True):
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user = {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'role': user.role.value,
                            'display_name': user.display_name
                        }
                        st.session_state.page = 'dashboard'
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials or account not approved")
                else:
                    st.warning("Please enter username and password")
        
        with col_register:
            if st.button("Register", use_container_width=True):
                st.session_state.page = 'register'
                st.rerun()
        
        if st.button("Forgot Password?", use_container_width=True):
            st.session_state.page = 'forgot_password'
            st.rerun()

def register_page():
    """Registration page"""
    show_header()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 📝 Register")
        
        role_choice = st.selectbox("Register as", ["Employee", "Customer"])
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.button("Register", use_container_width=True):
            if not all([username, email, password, confirm_password]):
                st.error("All fields are required")
            elif password != confirm_password:
                st.error("Passwords don't match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                role = UserRole.EMPLOYEE if role_choice == "Employee" else UserRole.CUSTOMER
                user, error = create_user(username, email, password, role)
                
                if user:
                    if role == UserRole.EMPLOYEE:
                        st.success("Registration successful! Please wait for admin approval.")
                    else:
                        st.success("Registration successful! You can now login.")
                    st.session_state.page = 'login'
                    st.rerun()
                else:
                    st.error(f"Registration failed: {error}")
        
        if st.button("Back to Login", use_container_width=True):
            st.session_state.page = 'login'
            st.rerun()

def forgot_password_page():
    """Forgot password page"""
    show_header()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔑 Reset Password")
        
        if 'reset_token' not in st.session_state:
            # Step 1: Request reset
            email = st.text_input("Enter your email address")
            
            if st.button("Send Reset Link", use_container_width=True):
                if email:
                    token, error = create_reset_token(email)
                    if token:
                        st.session_state.reset_token = token
                        st.success("Password reset instructions sent! Use the token below:")
                        st.code(token)
                        st.info("In production, this would be emailed to you.")
                        st.rerun()
                    else:
                        st.error(f"Error: {error}")
                else:
                    st.warning("Please enter your email")
        else:
            # Step 2: Reset with token
            token = st.text_input("Reset Token", value=st.session_state.reset_token)
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            if st.button("Reset Password", use_container_width=True):
                if new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    success, error = reset_password_with_token(token, new_password)
                    if success:
                        st.success("Password reset successful! You can now login.")
                        del st.session_state.reset_token
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error(f"Error: {error}")
        
        if st.button("Back to Login", use_container_width=True):
            if 'reset_token' in st.session_state:
                del st.session_state.reset_token
            st.session_state.page = 'login'
            st.rerun()

def main():
    """Main application"""
    if st.session_state.user is None:
        # Not logged in
        if st.session_state.page == 'login':
            login_page()
        elif st.session_state.page == 'register':
            register_page()
        elif st.session_state.page == 'forgot_password':
            forgot_password_page()
    else:
        # Logged in - import and show appropriate dashboard
        user_role = st.session_state.user['role']
        
        if user_role == 'admin':
            from pages import admin_dashboard
            admin_dashboard.show()
        elif user_role == 'employee':
            from pages import employee_dashboard
            employee_dashboard.show()
        elif user_role == 'customer':
            from pages import customer_dashboard
            customer_dashboard.show()

if __name__ == "__main__":
    main()
