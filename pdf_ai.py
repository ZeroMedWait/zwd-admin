from pathlib import Path
import streamlit as st
from openai import OpenAI
import PyPDF2
import requests
import base64
from datetime import datetime


# ============================================================
# PASSWORD PROTECTION
# ============================================================
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


# =============================================================
# GITHUB UPLOAD FUNCTIONALITY
# =============================================================
def upload_to_github(file_content, filename, github_token, repo_name, branch="main"):
    """
    Upload a file to GitHub repository's public folder.
    
    Args:
        file_content: Binary content of the file
        filename: Name of the file
        github_token: GitHub personal access token
        repo_name: Repository in format 'owner/repo'
        branch: Branch name (default: 'main')
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Encode file content to base64
        content_base64 = base64.b64encode(file_content).decode('utf-8')
        
        # GitHub API URL for creating/updating files
        url = f"https://api.github.com/repos/{repo_name}/contents/public/{filename}"
        
        # Check if file already exists
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Try to get existing file (to get its SHA if it exists)
        response = requests.get(url, headers=headers)
        sha = None
        if response.status_code == 200:
            sha = response.json().get('sha')
        
        # Prepare the data for upload
        data = {
            "message": f"Upload PDF: {filename} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_base64,
            "branch": branch
        }
        
        # If file exists, include SHA for update
        if sha:
            data["sha"] = sha
        
        # Upload the file
        response = requests.put(url, json=data, headers=headers)
        
        if response.status_code in [200, 201]:
            file_url = response.json().get('content', {}).get('html_url', '')
            return True, f"Successfully uploaded to GitHub! [View file]({file_url})"
        else:
            return False, f"Failed to upload: {response.status_code} - {response.text}"
            
    except Exception as e:
        return False, f"Error uploading to GitHub: {str(e)}"


# ============================================================
# STREAMLIT UI
# ============================================================
st.title("📄 PDF Upload to GitHub")
st.write("Upload PDF files and push them to your GitHub repository's public folder")

# GitHub configuration
st.sidebar.header("⚙️ GitHub Configuration")
github_token = st.sidebar.text_input(
    "GitHub Token",
    type="password",
    help="Your GitHub Personal Access Token with repo permissions",
    value=st.secrets.get("github_token", "")
)
repo_name = st.sidebar.text_input(
    "Repository",
    help="Format: owner/repo (e.g., username/my-repo)",
    value=st.secrets.get("github_repo", "")
)
branch = st.sidebar.text_input(
    "Branch",
    value="main",
    help="Branch to upload to (default: main)"
)

# File uploader
st.header("Upload PDF")
uploaded_file = st.file_uploader(
    "Choose a PDF file",
    type=['pdf'],
    help="Drag and drop or click to browse"
)

# Display file information and upload button
if uploaded_file is not None:
    st.success(f"✅ File selected: {uploaded_file.name}")
    
    # Display file details
    col1, col2 = st.columns(2)
    with col1:
        st.metric("File Name", uploaded_file.name)
    with col2:
        file_size = len(uploaded_file.getvalue()) / 1024  # Size in KB
        st.metric("File Size", f"{file_size:.2f} KB")
    
    # Preview PDF info
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        num_pages = len(pdf_reader.pages)
        st.info(f"📖 PDF has {num_pages} page(s)")
        uploaded_file.seek(0)  # Reset file pointer
    except Exception as e:
        st.warning(f"Could not read PDF info: {str(e)}")
    
    # Confirmation and upload
    st.markdown("---")
    st.subheader("Confirm Upload")
    
    if not github_token or not repo_name:
        st.error("⚠️ Please configure GitHub Token and Repository in the sidebar first!")
    else:
        st.write(f"**Destination:** `{repo_name}/public/{uploaded_file.name}`")
        st.write(f"**Branch:** `{branch}`")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🚀 Upload to GitHub", type="primary"):
                with st.spinner("Uploading to GitHub..."):
                    # Read file content
                    file_content = uploaded_file.getvalue()
                    
                    # Upload to GitHub
                    success, message = upload_to_github(
                        file_content,
                        uploaded_file.name,
                        github_token,
                        repo_name,
                        branch
                    )
                    
                    if success:
                        st.success(message)
                        st.balloons()
                    else:
                        st.error(message)
        
        with col2:
            if st.button("❌ Cancel"):
                st.rerun()

else:
    st.info("👆 Please upload a PDF file to get started")


