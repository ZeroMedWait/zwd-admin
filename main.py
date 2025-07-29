import streamlit as st
from supabase import create_client, Client
from openai import OpenAI
import asyncio

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


# Get URL parameters for API keys
def get_url_params():
    supabase_url = st.query_params.get("supabase_url")
    supabase_key = st.query_params.get("supabase_key")
    or_api_key = st.query_params.get("or_api_key")
    print(supabase_key, or_api_key)
    return supabase_url, supabase_key, or_api_key


# Get API keys from URL parameters
supabase_url, supabase_service_key, openrouter_api_key = get_url_params()

# Supabase setup
if not supabase_service_key:
    st.error("Please provide supabase_key (service key) in URL parameters")
    st.stop()
if not supabase_url:
    st.error("Please provide supabase_url (db url) in URL parameters")
    st.stop()

supabase: Client = create_client(supabase_url, supabase_service_key)

# OpenRouter client setup (using OpenAI SDK)
if not openrouter_api_key:
    st.error("Please provide or_api_key (openrouter) in URL parameters")
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
