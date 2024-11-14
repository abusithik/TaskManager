import streamlit as st
import re
from typing import Tuple
from database import TaskDB

class Auth:
    def __init__(self):
        self.db = TaskDB()

    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None

    def validate_password(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        return True, ""

    def login_page(self):
        """Display login page"""
        st.title("🔐 Login")
        
        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields")
                    return
                
                user = self.db.verify_user(email, password)
                if user:
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid email or password")

    def registration_page(self):
        """Display registration page"""
        st.title("📝 Register")
        
        with st.form("registration_form"):
            #Name = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            password_confirm = st.text_input("Confirm Password", type="password")
            
            submitted = st.form_submit_button("Register")
            
            if submitted:
                if not all([ email, password, password_confirm]):
                    st.error("Please fill in all fields")
                    return
                
                if not self.validate_email(email):
                    st.error("Please enter a valid email address")
                    return
                
                valid_password, msg = self.validate_password(password)
                if not valid_password:
                    st.error(msg)
                    return
                
                if password != password_confirm:
                    st.error("Passwords do not match!")
                    return
                
                if self.db.register_user(email,password):
                    st.success("Registration successful! Please login.")
                    st.session_state.show_login = True
                else:
                    st.error("Email already exists!")

    def logout(self):
        """Handle logout"""
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()
