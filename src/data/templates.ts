import { StreamlitTemplate } from '../types/streamlit';

export const TEMPLATES: StreamlitTemplate[] = [
  {
    id: 'starter',
    name: 'Standard Empty App',
    badge: 'Recommended',
    summary: 'Clean, deployment-ready starter with sidebar controls, metrics, and interactive widgets.',
    pythonCode: `import streamlit as st
import pandas as pd
import numpy as np

# Configure page settings
st.set_page_config(
    page_title="Streamlit Empty App",
    page_icon="🎈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# App Title & Description
st.title("🎈 Streamlit Empty Starter App")
st.write(
    "Welcome to your empty Streamlit application! This template is pre-configured "
    "for instant deployment on **Streamlit Community Cloud**."
)

# Sidebar with user inputs
with st.sidebar:
    st.header("⚙️ App Settings")
    user_name = st.text_input("Enter your name", value="Streamlit Developer")
    app_mode = st.selectbox(
        "Choose view",
        ["Overview", "Data Preview", "Cloud Deployment Guide"]
    )
    metric_multiplier = st.slider("Multiplier value", min_value=1, max_value=10, value=3)
    enable_balloons = st.checkbox("Celebrate launch with balloons", value=True)

# Main Content based on selection
if app_mode == "Overview":
    st.subheader(f"👋 Hello, {user_name}!")
    st.info("Edit \`streamlit_app.py\` to add your own Python logic, models, or data pipelines.")

    # KPI Metrics Row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Server Status", value="Online", delta="Healthy")
    with col2:
        st.metric(label="Python Version", value="3.11", delta="Standard")
    with col3:
        st.metric(label="Compute Factor", value=f"{metric_multiplier * 42} ops", delta=f"+{metric_multiplier}x")

    st.divider()

    # Interactive button demo
    if st.button("🚀 Click me to test interaction", type="primary"):
        st.success("Button clicked! Streamlit reruns your script top-to-bottom on every interaction.")
        if enable_balloons:
            st.balloons()

elif app_mode == "Data Preview":
    st.subheader("📊 Sample Dataset")
    st.write("Streamlit makes it effortless to display tables, dataframes, and charts.")

    # Create dummy data
    chart_data = pd.DataFrame(
        np.random.randn(20, 3) * metric_multiplier,
        columns=["Metric A", "Metric B", "Metric C"]
    )
    st.line_chart(chart_data)
    st.dataframe(chart_data, use_container_width=True)

elif app_mode == "Cloud Deployment Guide":
    st.subheader("☁️ Deploying to Streamlit Community Cloud")
    st.markdown("""
    1. **Push to GitHub**: Commit \`streamlit_app.py\` and \`requirements.txt\`.
    2. **Sign in**: Visit [share.streamlit.io](https://share.streamlit.io).
    3. **Deploy**: Select your repository, branch \`main\`, and file path \`streamlit_app.py\`.
    4. **Secrets**: Set any sensitive credentials in App Settings > Secrets.
    """)
    st.code("git init && git add . && git commit -m 'Initial commit'", language="bash")
`,
    requirements: `streamlit>=1.40.0
pandas>=2.2.0
numpy>=1.26.0
`,
    configToml: `[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#31333F"
font = "sans serif"

[server]
headless = true
enableCORS = false
port = 8501
`,
    secretsToml: `# Streamlit Community Cloud Secrets Template
# In local dev: stored in .streamlit/secrets.toml
# In Community Cloud: paste into App Settings -> Secrets

APP_ENVIRONMENT = "production"
# API_KEY = "your_secret_key_here"
# DATABASE_URL = "postgresql://user:pass@host:5432/db"
`,
    readme: `# Streamlit Community Cloud Empty App

A clean, production-ready starter template for [Streamlit Community Cloud](https://streamlit.io/cloud).

## 🚀 Quick Start (Local)

1. Clone or download this repository.
2. Create and activate a virtual environment:
   \`\`\`bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
   \`\`\`
3. Install dependencies:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`
4. Run the Streamlit app:
   \`\`\`bash
   streamlit run streamlit_app.py
   \`\`\`

## ☁️ Deploy to Streamlit Community Cloud

1. Push this repository to GitHub.
2. Head over to [share.streamlit.io](https://share.streamlit.io) and click **"New app"**.
3. Select your repository, set the branch to \`main\`, and set the file path to \`streamlit_app.py\`.
4. Click **"Deploy"**!
`,
    gitignore: `# Streamlit configuration and secrets
.streamlit/secrets.toml

# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
.venv/
env/
venv/
ENV/

# Distribution / packaging
dist/
build/
*.egg-info/

# Operating system files
.DS_Store
Thumbs.db
`
  },
  {
    id: 'minimal',
    name: 'Minimal Empty App',
    badge: 'Ultralight',
    summary: 'The simplest possible Streamlit app (~15 lines of pure code) with zero clutter.',
    pythonCode: `import streamlit as st

st.set_page_config(
    page_title="Minimal Streamlit App",
    page_icon="🎈",
    layout="centered"
)

st.title("🎈 Minimal Streamlit App")
st.write("This is an empty starter application ready for Streamlit Community Cloud.")

name = st.text_input("What is your name?", "World")
st.write(f"Hello, **{name}**!")

if st.button("Say Hello", type="primary"):
    st.success(f"Greetings, {name}! Your empty app is working.")
    st.balloons()
`,
    requirements: `streamlit>=1.40.0
`,
    configToml: `[theme]
primaryColor = "#FF4B4B"
`,
    secretsToml: `# Secrets for Streamlit Community Cloud
# Add your environment variables below:
`,
    readme: `# Minimal Streamlit Starter

The most lightweight empty starter for Streamlit Community Cloud.

## Run Locally
\`\`\`bash
pip install -r requirements.txt
streamlit run streamlit_app.py
\`\`\`
`,
    gitignore: `.streamlit/secrets.toml
__pycache__/
.venv/
`
  },
  {
    id: 'data',
    name: 'Data & Analytics Starter',
    badge: 'Data Science',
    summary: 'Starter app pre-configured with pandas data exploration, filtering, and chart visualization.',
    pythonCode: `import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Data Analytics Starter",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Data Analytics Starter")
st.caption("A baseline data-app template for Streamlit Community Cloud")

# Sidebar Filters
with st.sidebar:
    st.header("🔍 Data Filters")
    rows = st.slider("Number of records", 10, 100, 25)
    category = st.multiselect(
        "Filter Category",
        ["Engineering", "Marketing", "Sales", "Design"],
        default=["Engineering", "Sales"]
    )
    chart_type = st.radio("Chart Type", ["Line Chart", "Bar Chart", "Area Chart"])

# Generate sample dataset
np.random.seed(42)
data = pd.DataFrame({
    "Category": np.random.choice(["Engineering", "Marketing", "Sales", "Design"], size=rows),
    "Score": np.random.uniform(50, 100, size=rows).round(1),
    "Growth": np.random.uniform(-5, 25, size=rows).round(2),
    "Quarter": np.random.choice(["Q1", "Q2", "Q3", "Q4"], size=rows),
})

filtered_data = data[data["Category"].isin(category)] if category else data

# Summary Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Records", len(filtered_data))
col2.metric("Avg Score", f"{filtered_data['Score'].mean():.1f}" if len(filtered_data) else "N/A")
col3.metric("Max Growth", f"{filtered_data['Growth'].max():.1f}%" if len(filtered_data) else "N/A")
col4.metric("Active Categories", len(category))

st.divider()

# Charts
st.subheader("📈 Visual Breakdown")
if chart_type == "Line Chart":
    st.line_chart(filtered_data.groupby("Quarter")["Score"].mean())
elif chart_type == "Bar Chart":
    st.bar_chart(filtered_data.groupby("Category")["Score"].mean())
else:
    st.area_chart(filtered_data.groupby("Quarter")["Growth"].sum())

# Data Table
st.subheader("📋 Raw Data Explorer")
st.dataframe(filtered_data, use_container_width=True)

csv = filtered_data.to_csv(index=False).encode('utf-8')
st.download_button(
    "📥 Download CSV",
    data=csv,
    file_name="streamlit_sample_data.csv",
    mime="text/csv"
)
`,
    requirements: `streamlit>=1.40.0
pandas>=2.2.0
numpy>=1.26.0
`,
    configToml: `[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#31333F"
font = "sans serif"
`,
    secretsToml: `# Secrets configuration
`,
    readme: `# Data Analytics Streamlit App

Starter data analytics application ready for Streamlit Community Cloud.
`,
    gitignore: `.streamlit/secrets.toml
__pycache__/
.venv/
`
  },
  {
    id: 'chat',
    name: 'LLM & Chatbot Starter',
    badge: 'AI / Chat',
    summary: 'Starter app with conversational chat interface using st.chat_message and st.chat_input.',
    pythonCode: `import streamlit as st
import time

st.set_page_config(
    page_title="Streamlit Chat Starter",
    page_icon="💬",
    layout="centered"
)

st.title("💬 Chatbot Starter Template")
st.caption("A conversational Streamlit Community Cloud template")

# Check for API key in secrets or prompt user
api_key = st.secrets.get("API_KEY", "")
if not api_key:
    with st.sidebar:
        st.header("🔑 API Credentials")
        st.info("Tip: Set API_KEY in Streamlit Cloud Secrets so users don't need to enter it manually.")
        api_key = st.text_input("Enter API Key (optional):", type="password")

# Initialize chat history in session_state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am your Streamlit assistant. Ask me anything or test this chat starter."}
    ]

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Type your message here..."):
    # Display user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        sample_reply = f"Echo from Streamlit: You said '{prompt}'. Connect an LLM provider to power live answers!"
        
        # Simulate typing effect
        for chunk in sample_reply.split(" "):
            full_response += chunk + " "
            time.sleep(0.04)
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
        
    st.session_state.messages.append({"role": "assistant", "content": full_response})
`,
    requirements: `streamlit>=1.40.0
`,
    configToml: `[theme]
primaryColor = "#FF4B4B"
`,
    secretsToml: `# API keys and credentials for LLM apps
API_KEY = "your-api-key-here"
`,
    readme: `# Streamlit Chatbot Starter

A conversational chat app for Streamlit Community Cloud using \`st.chat_message\` and \`st.chat_input\`.
`,
    gitignore: `.streamlit/secrets.toml
__pycache__/
.venv/
`
  }
];
