import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from auth import Auth
from database import TaskDB
from typing import Optional
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel
import vertexai
from google.oauth2 import service_account


# Initialize authentication and database
auth = Auth()
db = TaskDB()

def init_vertex_ai():
    try:
        # Debug credentials
        if 'gcp_service_account' not in st.secrets:
            st.error("No GCP credentials found in secrets")
            return None
            
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        
        vertexai.init(
            project="tidal-repeater-441619-n3",
            location="us-central1",
            credentials=credentials
        )
        return GenerativeModel("gemini-1.5-pro")
    except Exception as e:
        st.error(f"Vertex AI initialization error: {e}")
        return None
    
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    return GenerativeModel("gemini-1.5-pro")

# Initialize session state
def init_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'show_login' not in st.session_state:
        st.session_state.show_login = True
    if 'active_tasks' not in st.session_state:
        st.session_state.active_tasks = []
    if 'completed_tasks' not in st.session_state:
        st.session_state.completed_tasks = []

def query_gemini(prompt):
    try:
        model = init_vertex_ai()
        st.write("Model initialized")  # Debug log
        
        response = model.generate_content(prompt)
        st.write("Response received")  # Debug log
        
        if not response or not response.text:
            st.error("Empty response from model")
            return None
            
        return response.text
    except Exception as e:
        st.error(f"Detailed error in query_gemini: {str(e)}")
        return None

def parse_task(note):
    """Parse a note into a structured task using Gemini"""
    system_prompt = """You are a task parsing assistant. Extract structured information from notes and return it in JSON format.
Return only a valid JSON object without any additional text or formatting.

Format your response exactly like this example:
{"task": "Send project report", "customer": "John", "due_date": "14-11-2024", "priority": "Medium"}

Rules:
- Task should be very brief and to the point
- To whom the job intended should be the customer name
- Convert the dates from words like today or tomorrow carefully from current date and return in DD-MM-YYYY format
- Return ONLY the JSON object, no other text
- If no date is mentioned, use tomorrow's date
- If no priority indicators, use "Medium"
- If no person is mentioned, use "Unspecified"
- Priority can only be "High", "Medium", or "Low"
- Date format must be DD-MM-YYYY
"""

    user_prompt = f"{system_prompt}\n\nNote to parse: {note}\n\nResponse (JSON only):"
    
    try:
        response = query_gemini(user_prompt)
        if not response:
            return None

        # Clean up the response
        response = response.strip()
        
        # Debug the raw response
        with st.expander("Debug Output", expanded=False):
            st.text("Raw Response:")
            st.code(response)
        
        # Extract JSON if it's wrapped in code blocks
        if "```" in response:
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip('`').strip()
        
        # Parse JSON
        parsed = json.loads(response)
        
        # Handle date format
        if parsed.get('due_date', '').lower() == 'tomorrow':
            tomorrow = datetime.now() + timedelta(days=1)
            parsed['due_date'] = tomorrow.strftime('%d-%m-%Y')
        
        # Validate required fields
        required_fields = ['task', 'customer', 'due_date', 'priority']
        if not all(field in parsed for field in required_fields):
            st.error("Missing required fields in response")
            return None
            
        return parsed
        
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON format: {e}")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def check_overdue(due_date_str):
    """Check if a task is overdue"""
    try:
        due = datetime.strptime(due_date_str, '%d-%m-%Y')
        return due.date() < datetime.now().date()
    except:
        return False

# Main function remains the same as your original code
def main():
    # Initialize session state
    init_session_state()
    
    if not st.session_state.authenticated:
        # Show login/registration pages
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            auth.login_page()
        with tab2:
            auth.registration_page()
        return  # Exit if not authenticated

    # Main app - only shown when authenticated
    st.sidebar.success(f"Welcome {st.session_state.user['email']}!")
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.title("📝 Smart Task Manager")

    # Task input form
    with st.form("task_form"):
        note_input = st.text_area(
            "Enter your task note:",
            placeholder="Example: Write an email to David on ABC project by tomorrow",
            help="Describe your task naturally. Include person name, due date, and priority if applicable."
        )
        
        submitted = st.form_submit_button("Add Task")
        
        if submitted and note_input:
            
            with st.spinner("Processing..."):
                parsed_task = parse_task(note_input)
                if parsed_task:
                    if db.save_task(st.session_state.user['id'], parsed_task):
                        st.success("Task added successfully!")
                        #st.session_state.note_input = ""  
                        #time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Error saving task")

    # Display tasks in tabs
    tab1, tab2 = st.tabs(["Active Tasks 📝", "Completed Tasks ✅"])
    
    try:
        # Fetch tasks
        user_id = st.session_state.user['id']
        active_tasks = db.get_tasks(user_id, status='active')
        completed_tasks = db.get_tasks(user_id, status='completed')
        
        with tab1:
            if active_tasks:
                # Table headers
                header_cols = st.columns([0.5, 2, 1, 1, 0.5])
                with header_cols[0]:
                    st.markdown("**Status**")
                with header_cols[1]:
                    st.markdown("**Task**")
                with header_cols[2]:
                    st.markdown("**Customer**")
                with header_cols[3]:
                    st.markdown("**Due Date**")
                with header_cols[4]:
                    st.markdown("**Action**")
                
                # Add a line after headers
                st.markdown("<hr style='margin: 5px 0; border: 1px solid #f0f2f6'>", unsafe_allow_html=True)
        
                for task in active_tasks:
                    col1, col2, col3, col4, col5 = st.columns([0.5, 2, 1, 1, 0.5])
                    
                    # Check if task is overdue
                    is_overdue = check_overdue(task['due_date'])
                    overdue_style = "color: red;" if is_overdue else ""
                    
                    with col1:
                        st.write("🚩" if is_overdue else "✅")
                    
                    with col2:
                        st.markdown(f"<span style='{overdue_style}'>{task['task']}</span>", 
                                  unsafe_allow_html=True)
                    
                    with col3:
                        st.write(task['customer'])
                    
                    with col4:
                        st.markdown(f"<span style='{overdue_style}'>{task['due_date']}</span>",
                                  unsafe_allow_html=True)
                    
                    with col5:
                        if st.button("✓", key=f"complete_{task['id']}"):
                            if db.complete_task(user_id, task['id']):
                                st.success("Task completed!")
                                st.rerun()
                    
                    st.markdown("---")
            else:
                st.info("No active tasks!")
        
        with tab2:
            if completed_tasks:
                # Table headers for completed tasks
                header_cols = st.columns([0.5, 2, 1, 1, 1])
                with header_cols[0]:
                    st.markdown("**Status**")
                with header_cols[1]:
                    st.markdown("**Task**")
                with header_cols[2]:
                    st.markdown("**Customer**")
                with header_cols[3]:
                    st.markdown("**Due Date**")
                with header_cols[4]:
                    st.markdown("**Completed On**")
        
                # Add a line after headers
                st.markdown("<hr style='margin: 5px 0; border: 1px solid #f0f2f6'>", unsafe_allow_html=True)
                for task in completed_tasks:
                    col1, col2, col3, col4, col5 = st.columns([0.5, 2, 1, 1, 1])
                    
                    with col1:
                        st.write("✓")
                    with col2:
                        st.write(task['task'])
                    with col3:
                        st.write(task['customer'])
                    with col4:
                        st.write(task['due_date'])
                    with col5:
                        st.write(f"Completed: {task['completion_date']}")
                    
                    st.markdown("---")
            else:
                st.info("No completed tasks!")

        # Sidebar statistics
        with st.sidebar:
            st.subheader("📊 Task Statistics")
            active_count = len(active_tasks)
            completed_count = len(completed_tasks)
            total_count = active_count + completed_count
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Active", active_count)
            with col2:
                st.metric("Completed", completed_count)
            
            if total_count > 0:
                completion_rate = (completed_count / total_count) * 100
                st.progress(completion_rate / 100)
                st.caption(f"Completion Rate: {completion_rate:.1f}%")
            
            # Show overdue tasks count
            overdue_count = sum(1 for task in active_tasks 
                              if check_overdue(task['due_date']))
            if overdue_count > 0:
                st.error(f"⚠️ Overdue Tasks: {overdue_count}")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        if st.button("Reset Session"):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()
