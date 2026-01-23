import streamlit as st
from supabase import create_client, Client
from openai import OpenAI
import asyncio
from datetime import datetime
import time

# Password protection
def check_password():
    """Returns True if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if "password" in st.session_state:
            if st.session_state["password"] == st.secrets.get("app_password", ""):
                st.session_state["password_correct"] = True
                del st.session_state["password"]  # Don't store the password in session state
            else:
                st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state and not st.session_state.get("password_correct", False):
        st.error("😕 Password incorrect")
    return False

# Check password before running the rest of the app
if not check_password():
    st.stop()  # Do not continue if check_password is not True.