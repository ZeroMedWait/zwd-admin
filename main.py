import streamlit as st
from supabase import create_client, Client
from openai import OpenAI
import asyncio
# Add this import
import invitation_api

# Role mapping
ROLE_MAPPING = {0: "doctor", 1: "physio", 2: "nurse"}


def get_role_name(role):
    """Convert role number to role name"""
    if isinstance(role, (int, str)):
        try:
            role_num = int(role)
            return ROLE_MAPPING.get(role_num, f"role_{role}")
        except ValueError:
            return str(role)
    return str(role)


# Get secret parameters for API keys
def get_secrets_params():
    supabase_url = st.secrets.get("supabase_url")
    supabase_key = st.secrets.get("supabase_key")
    or_api_key = st.secrets.get("or_api_key")
    return supabase_url, supabase_key, or_api_key


# Get API keys from secret parameters
supabase_url, supabase_service_key, openrouter_api_key = get_secrets_params()

# Supabase setup
if not supabase_service_key:
    st.error("Please provide supabase_key (service key) in app's secrets")
    st.stop()
if not supabase_url:
    st.error("Please provide supabase_url (db url) in app's secrets")
    st.stop()

supabase: Client = create_client(supabase_url, supabase_service_key)

# OpenRouter client setup (using OpenAI SDK)
if not openrouter_api_key:
    st.error("Please provide or_api_key (openrouter) in app's secrets")
    st.stop()

openai_client = OpenAI(
    api_key=openrouter_api_key, base_url="https://openrouter.ai/api/v1"
)


# Function to call OpenRouter GPT-4o using OpenAI SDK
def generate_report_with_gpt4o(transcript, prompt):
    try:
        response = openai_client.chat.completions.create(
            model="openai/gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Please analyze the following transcript:\n\n{transcript}",
                },
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating report: {str(e)}"


# Async function for parallel report generation
async def generate_report_async(transcript, prompt_text, role):
    try:
        # Create a new client for async usage
        async_client = OpenAI(
            api_key=openrouter_api_key, base_url="https://openrouter.ai/api/v1"
        )

        response = await async_client.chat.completions.create(
            model="openai/gpt-4o",
            messages=[
                {"role": "system", "content": prompt_text},
                {
                    "role": "user",
                    "content": f"Please analyze the following transcript:\n\n{transcript}",
                },
            ],
            temperature=0.7,
            max_tokens=2000,
        )

        return {
            "role": role,  # This will now be the mapped role name
            "report": response.choices[0].message.content,
        }
    except Exception as e:
        return {"role": role, "report": f"Error generating report: {str(e)}"}


# Fetch sessions from the database with transcript count
def fetch_sessions():
    try:
        # First try to get basic session info and see what's available
        response = supabase.table("sessions").select("*").execute()
        sessions = response.data

        # For each session, try to get its transcripts
        for session in sessions:
            try:
                transcript_response = (
                    supabase.table("transcripts")
                    .select("id, transcript")
                    .eq("session_id", session["id"])
                    .execute()
                )
                session["transcripts"] = transcript_response.data
            except Exception as e:
                # If transcripts table doesn't exist or has different structure, set empty
                session["transcripts"] = []

        return sessions
    except Exception as e:
        st.error(f"Error fetching sessions: {str(e)}")
        return []


# Fetch transcripts for a specific session
def fetch_session_transcripts(session_id):
    try:
        response = (
            supabase.table("transcripts")
            .select("*")
            .eq("session_id", session_id)
            .execute()
        )
        return response.data
    except Exception as e:
        st.error(f"Error fetching transcripts for session {session_id}: {str(e)}")
        return []


# Fetch prompts from the database
def fetch_prompts():
    response = supabase.table("soap_prompts").select("id, role, prompt").execute()
    return response.data


# Update a prompt in the database
def update_prompt(prompt_id, new_text):
    supabase.table("soap_prompts").update({"prompt": new_text}).eq(
        "id", prompt_id
    ).execute()


# Streamlit app layout
st.title("Admin Session and Prompt Manager")

# Fetch data
prompts = fetch_prompts()
sessions = fetch_sessions()

# Group prompts by role for easier display
prompts_by_role = {}
for prompt in prompts:
    role_name = get_role_name(prompt["role"])
    prompts_by_role[role_name] = prompt

st.header("Prompt Management")

# Create columns for prompts
prompt_updates = {}
for role, prompt_data in prompts_by_role.items():
    st.subheader(f"{role} Prompt")
    new_text = st.text_area(
        f"Prompt for {role}",
        value=prompt_data["prompt"],
        height=150,
        key=f"prompt_{role}",
    )
    prompt_updates[role] = {
        "id": prompt_data["id"],
        "text": new_text,
        "original": prompt_data["prompt"],
    }

    if st.button(f"Save {role} Prompt", key=f"save_{role}"):
        update_prompt(prompt_data["id"], new_text)
        st.success(f"{role} prompt updated successfully!")

st.divider()

# Session selection and report generation
st.header("Report Generation")

if sessions:
    # Prepare session options
    session_options = {}
    for session in sessions:
        # Count transcripts from the related transcripts data
        transcripts = session.get("transcripts", [])
        transcript_count = len(transcripts) if transcripts else 0
        option_text = f"{session.get('title', 'Untitled')} (ID: {session['id']}, Transcripts: {transcript_count})"
        session_options[session["id"]] = {"text": option_text, "data": session}

    # Session dropdown
    selected_session_id = st.selectbox(
        "Select Session",
        options=list(session_options.keys()),
        format_func=lambda x: session_options[x]["text"],
    )

    if selected_session_id:
        selected_session = session_options[selected_session_id]["data"]
        session_transcripts = selected_session.get("transcripts", [])

        st.subheader(f"Generate Reports for: {selected_session['title']}")

        if not session_transcripts:
            st.warning("No transcripts available for this session")
        else:
            # Transcript selection and viewing
            st.write("**Transcript Selection & Viewing:**")

            if len(session_transcripts) > 1:
                transcript_options = {
                    i: f"Transcript {i + 1} (ID: {t['id']})"
                    for i, t in enumerate(session_transcripts)
                }
                selected_transcript_idx = st.selectbox(
                    "Select Transcript",
                    options=list(transcript_options.keys()),
                    format_func=lambda x: transcript_options[x],
                )
                selected_transcript_data = session_transcripts[selected_transcript_idx]
            else:
                st.info(f"Using transcript ID: {session_transcripts[0]['id']}")
                selected_transcript_data = session_transcripts[0]

            selected_transcript = selected_transcript_data.get("transcript", "")

            # Display transcript content
            with st.expander("📄 View Transcript Content", expanded=False):
                if selected_transcript:
                    st.text_area(
                        "Transcript Content",
                        value=selected_transcript,
                        height=300,
                        disabled=True,
                        key="transcript_viewer",
                    )
                    st.caption(
                        f"Transcript ID: {selected_transcript_data.get('id', 'Unknown')} | "
                        f"Length: {len(selected_transcript)} characters"
                    )
                else:
                    st.warning("No transcript content available")

            st.divider()

            # Individual report generation
            st.write("**Individual Report Generation:**")
            cols = st.columns(len(prompts_by_role))

            for i, (role, prompt_data) in enumerate(prompts_by_role.items()):
                with cols[i]:
                    if st.button(f"Generate {role} Report", key=f"individual_{role}"):
                        with st.spinner(f"Generating {role} report..."):
                            current_prompt_text = prompt_updates[role]["text"]

                            if selected_transcript:
                                report = generate_report_with_gpt4o(
                                    selected_transcript, current_prompt_text
                                )

                                with st.expander(f"{role} Report", expanded=True):
                                    st.write(report)
                            else:
                                st.error("No transcript content available")

            st.divider()

            # Parallel report generation
            st.write("**Parallel Report Generation:**")
            if st.button("Generate All Reports in Parallel", key="parallel_all"):
                if selected_transcript:
                    with st.spinner("Generating all reports in parallel..."):
                        # Prepare async tasks
                        async def run_parallel_generation():
                            tasks = []
                            for role, prompt_data in prompts_by_role.items():
                                current_prompt_text = prompt_updates[role]["text"]
                                task = generate_report_async(
                                    selected_transcript, current_prompt_text, role
                                )
                                tasks.append(task)

                            results = await asyncio.gather(*tasks)
                            return results

                        # Run async tasks
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            results = loop.run_until_complete(run_parallel_generation())
                            loop.close()

                            # Display results
                            for result in results:
                                with st.expander(
                                    f"{result['role']} Report", expanded=True
                                ):
                                    st.write(result["report"])

                            st.success("All reports generated successfully!")

                        except Exception as e:
                            st.error(f"Error in parallel generation: {str(e)}")
                else:
                    st.error("No transcript available for this session")
else:
    st.warning("No sessions found in the database")

# User Invitation Management
st.header("User Invitation Management")

# Create tabs for different invitation functions
invite_tab1, invite_tab2, invite_tab3 = st.tabs(["Single Invitation", "Bulk Invitations", "User Management"])

with invite_tab1:
    st.subheader("Send Single Invitation")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        single_email = st.text_input("Email Address", placeholder="user@example.com")
    
    with col2:
        single_role = st.selectbox(
            "Role", 
            options=list(ROLE_MAPPING.keys()), 
            format_func=lambda x: f"{ROLE_MAPPING[x]} ({x})"
        )
    
    single_redirect = st.text_input(
        "Redirect URL (optional)", 
        value="https://app.zeromedwait.com/auth/sign-up",
        help="URL where user will be redirected after clicking invitation link"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send Invitation", type="primary"):
            if single_email:
                with st.spinner(f"Sending invitation to {single_email}..."):
                    # Use the same supabase client from main app
                    result = invitation_api.send_invitation(
                        single_email, 
                        single_role, 
                        supabase, 
                        single_redirect if single_redirect else None
                    )
                    
                    if result["success"]:
                        st.success(f"✅ {result['message']}")
                    else:
                        st.error(f"❌ {result['message']}")
            else:
                st.warning("Please enter an email address")
    
    with col2:
        if st.button("Delete User First, Then Invite"):
            if single_email:
                with st.spinner(f"Processing {single_email}..."):
                    # Delete first
                    delete_result = invitation_api.delete_user_by_email(single_email, supabase)
                    
                    if delete_result["success"]:
                        st.info(f"🗑️ {delete_result['message']}")
                    else:
                        st.warning(f"ℹ️ {delete_result['message']}")
                    
                    # Then invite
                    invite_result = invitation_api.send_invitation(
                        single_email, 
                        single_role, 
                        supabase, 
                        single_redirect if single_redirect else None
                    )
                    
                    if invite_result["success"]:
                        st.success(f"✅ {invite_result['message']}")
                    else:
                        st.error(f"❌ {invite_result['message']}")
            else:
                st.warning("Please enter an email address")

with invite_tab2:
    st.subheader("Bulk Invitations")
    
    # Bulk invitation input methods
    bulk_method = st.radio(
        "Choose input method:",
        ["Text Area (one email per line)", "CSV Format"]
    )
    
    if bulk_method == "Text Area (one email per line)":
        bulk_emails_text = st.text_area(
            "Email Addresses (one per line)",
            placeholder="user1@example.com\nuser2@example.com\nuser3@example.com",
            height=150
        )
        
        bulk_default_role = st.selectbox(
            "Default Role for all users", 
            options=list(ROLE_MAPPING.keys()), 
            format_func=lambda x: f"{ROLE_MAPPING[x]} ({x})"
        )
        
        if bulk_emails_text:
            email_list = [email.strip() for email in bulk_emails_text.split('\n') if email.strip()]
            st.info(f"Found {len(email_list)} email addresses")
            
            # Preview
            with st.expander("Preview Email List"):
                for i, email in enumerate(email_list, 1):
                    st.write(f"{i}. {email} → {ROLE_MAPPING[bulk_default_role]}")
    
    else:  # CSV Format
        bulk_emails_csv = st.text_area(
            "CSV Format (email,role)",
            placeholder="user1@example.com,0\nuser2@example.com,1\nuser3@example.com,2",
            help="Format: email,role (where role: 0=doctor, 1=physio, 2=nurse)",
            height=150
        )
        
        if bulk_emails_csv:
            email_list = []
            for line in bulk_emails_csv.split('\n'):
                line = line.strip()
                if line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        email = parts[0].strip()
                        try:
                            role = int(parts[1].strip())
                            email_list.append((email, role))
                        except ValueError:
                            st.warning(f"Invalid role for {email}, using default role 0")
                            email_list.append((email, 0))
                    elif len(parts) == 1:
                        email_list.append((parts[0].strip(), 0))
            
            st.info(f"Found {len(email_list)} email addresses")
            
            # Preview
            with st.expander("Preview Email List"):
                for i, (email, role) in enumerate(email_list, 1):
                    role_name = ROLE_MAPPING.get(role, f"role_{role}")
                    st.write(f"{i}. {email} → {role_name}")
    
    bulk_redirect = st.text_input(
        "Redirect URL for all invitations", 
        value="https://app.zeromedwait.com/auth/sign-up"
    )
    
    # Bulk actions
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send All Invitations", type="primary"):
            if 'email_list' in locals() and email_list:
                with st.spinner(f"Sending {len(email_list)} invitations..."):
                    if bulk_method == "Text Area (one email per line)":
                        result = invitation_api.bulk_invite(
                            email_list, 
                            bulk_default_role, 
                            supabase, 
                            bulk_redirect
                        )
                    else:
                        result = invitation_api.bulk_invite(
                            email_list, 
                            0,  # Default role (will be overridden by individual roles)
                            supabase, 
                            bulk_redirect
                        )
                    
                    # Display results
                    summary = result.get("summary", {})
                    st.success(f"✅ Completed: {summary.get('successful', 0)} successful, {summary.get('failed', 0)} failed")
                    
                    # Show detailed results
                    with st.expander("Detailed Results"):
                        for res in result.get("results", []):
                            status = "✅" if res.get("success") else "❌"
                            st.write(f"{status} {res['email']} (role: {ROLE_MAPPING.get(res.get('role', 0))}) - {res.get('message', 'No message')}")
            else:
                st.warning("Please enter email addresses")
    
    with col2:
        if st.button("Delete All Users First, Then Invite"):
            if 'email_list' in locals() and email_list:
                with st.spinner(f"Processing {len(email_list)} users..."):
                    # First delete all users
                    delete_results = []
                    for item in email_list:
                        email = item[0] if isinstance(item, tuple) else item
                        delete_result = invitation_api.delete_user_by_email(email, supabase)
                        delete_results.append({"email": email, **delete_result})
                    
                    # Then send all invitations
                    if bulk_method == "Text Area (one email per line)":
                        invite_result = invitation_api.bulk_invite(
                            email_list, 
                            bulk_default_role, 
                            supabase, 
                            bulk_redirect
                        )
                    else:
                        invite_result = invitation_api.bulk_invite(
                            email_list, 
                            0,
                            supabase, 
                            bulk_redirect
                        )
                    
                    # Display results
                    summary = invite_result.get("summary", {})
                    st.success(f"✅ Completed: {summary.get('successful', 0)} invitations sent, {summary.get('failed', 0)} failed")
                    
                    # Show detailed results
                    with st.expander("Detailed Results"):
                        st.write("**Deletion Results:**")
                        for res in delete_results:
                            status = "🗑️" if res.get("success") else "ℹ️"
                            st.write(f"{status} {res['email']} - {res.get('message', 'No message')}")
                        
                        st.write("**Invitation Results:**")
                        for res in invite_result.get("results", []):
                            status = "✅" if res.get("success") else "❌"
                            st.write(f"{status} {res['email']} (role: {ROLE_MAPPING.get(res.get('role', 0))}) - {res.get('message', 'No message')}")
            else:
                st.warning("Please enter email addresses")

with invite_tab3:
    st.subheader("User Management")
    
    if st.button("List All Users", type="secondary"):
        with st.spinner("Fetching all users..."):
            users = invitation_api.list_all_users(supabase)
            
            if users:
                st.success(f"Found {len(users)} users")
                
                # Display users in a nice format
                for i, user in enumerate(users, 1):
                    with st.expander(f"User {i}: {user.email}"):
                        st.json({
                            "id": user.id,
                            "email": user.email,
                            "created_at": str(user.created_at),
                            "last_sign_in_at": str(user.last_sign_in_at) if user.last_sign_in_at else "Never",
                            "email_confirmed_at": str(user.email_confirmed_at) if user.email_confirmed_at else "Not confirmed",
                            "user_metadata": user.user_metadata
                        })
            else:
                st.info("No users found")
    
    st.divider()
    
    st.subheader("Delete Individual User")
    delete_email = st.text_input("Email to delete", placeholder="user@example.com")
    
    if st.button("Delete User", type="secondary"):
        if delete_email:
            with st.spinner(f"Deleting user {delete_email}..."):
                result = invitation_api.delete_user_by_email(delete_email, supabase)
                
                if result["success"]:
                    st.success(f"✅ {result['message']}")
                else:
                    st.warning(f"ℹ️ {result['message']}")
        else:
            st.warning("Please enter an email address")

# Display usage instructions
with st.expander("Usage Instructions"):
    st.write("""
    **URL Parameters Required:**
    - `supabase_key`: Your Supabase service role key
    - `or_api_key`: Your OpenRouter API key

    **Example URL:**
    ```
    http://localhost:8501?supabase_key=YOUR_SERVICE_KEY&or_api_key=YOUR_OR_KEY
    ```

    **Features:**
    1. **Prompt Management**: Edit prompts for each role and save changes
    2. **Session Selection**: Choose from available sessions with metadata
    3. **Transcript Viewing**: Read transcript content before generating reports
    4. **Individual Reports**: Generate reports one role at a time
    5. **Parallel Reports**: Generate all role reports simultaneously
    """)

# Debug section to understand database structure
with st.expander("🔧 Debug Information", expanded=False):
    st.write("**Database Structure Debug:**")

    if sessions:
        st.write("**Sample Session Data:**")
        sample_session = sessions[0]
        st.json(sample_session)

        if sample_session.get("transcripts"):
            st.write("**Sample Transcript Data:**")
            st.json(sample_session["transcripts"][0])

    if prompts:
        st.write("**Sample Prompt Data:**")
        st.json(prompts[0])

    st.write("**URL Parameters:**")
    st.write(
        f"- Supabase Key: {'✅ Present' if supabase_service_key else '❌ Missing'}"
    )
    st.write(
        f"- OpenRouter Key: {'✅ Present' if openrouter_api_key else '❌ Missing'}"
    )
