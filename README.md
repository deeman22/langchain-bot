# LangChain Bot

A Streamlit-based AI chatbot built with LangChain, OpenAI, and SQLite.

The project is being developed incrementally to learn:

- LangChain fundamentals
- LCEL (LangChain Expression Language)
- Prompt Templates
- Conversation memory
- Authentication
- Multi-thread conversations
- LangGraph
- Checkpointers
- RAG (Retrieval-Augmented Generation)
- Tool Calling
- Agentic AI Patterns

---

## Prompt Pipeline (LCEL)

The application uses LCEL:

```python
prompt | llm
```

Pipeline flow:

```text
User Input
     ↓
ChatPromptTemplate
     ↓
ChatOpenAI
     ↓
AIMessage
```

Prompt structure:

```text
System Message
      ↓
Conversation History
      ↓
Current User Input
      ↓
LLM
```

---

## Authentication

Authentication logic is isolated in:

```text
src/langchain_bot/auth.py
```

Uses SQLite and parameterized queries.

Supported users:

| Email | Password | Role |
|---------|----------|---------|
| sivaprasad.valluru@gmail.com | siva@123 | customer |
| bob@example.com | bob123 | customer |
| admin@example.com | admin123 | admin |

Authentication returns:

```python
{
    "email": "...",
    "full_name": "...",
    "role": "..."
}
```

or

```python
None
```

for invalid credentials.

---

# Project Structure

```text
langchain-bot/
│
├── pyproject.toml
├── README.md
├── ecommerce.db
├── ecommerce_setup.sql
│
├── src/
│   └── langchain_bot/
│       ├── __init__.py
│       ├── auth.py
│       └── db_init.py
│
└── app.py
```

---

# Database Initialization

File:

```text
src/langchain_bot/db_init.py
```

Responsibilities:

- Locate project root
- Read `ecommerce_setup.sql`
- Create `ecommerce.db`
- Execute schema and seed data

Run:

```bash
uv run python src/langchain_bot/db_init.py
```

Expected:

```text
Database initialized at:
.../ecommerce.db
```

---

# Authentication Module

File:

```text
src/langchain_bot/auth.py
```

Responsibilities:

- Login validation
- User lookup
- Role validation
- Database access abstraction

Example:

```python
user = authenticate_user(
    email="admin@example.com",
    password="admin123",
    role="admin"
)
```

---

# Running the Application

## Install Dependencies

```bash
uv add streamlit \
langchain \
langchain-openai \
openai \
python-dotenv \
langgraph \
langgraph-checkpoint-sqlite \
langchain-community \
chromadb \
langchain-text-splitters \
google-auth-oauthlib \
google-auth-httplib2 \
google-api-python-client
```

---

## Configure Environment

Create:

```text
.env
```

```env
OPENAI_API_KEY=your_api_key
```

---

## Start Applications

### 1. Start Customer Chat Application

Run the customer-facing chatbot:

```bash
uv run streamlit run app.py
```

Default URL:

```text
http://localhost:8501
```

---

### 2. Start Admin Application

Run the admin dashboard/application:

```bash
uv run streamlit run admin_app.py
```

Default URL:

```text
http://localhost:8502
```

If running both applications simultaneously:

```bash
uv run streamlit run app.py --server.port 8501

uv run streamlit run admin_app.py --server.port 8502
```

---

## Gmail Integration Setup

The application uses Gmail OAuth for email-related tools.

### 1. Create Google Cloud Project

1. Open Google Cloud Console.
2. Create a new project.
3. Enable the Gmail API.
4. Configure OAuth Consent Screen.
5. Add your Google account as a test user.

---

### 2. Create OAuth Credentials

Navigate to:

```text
APIs & Services
    → Credentials
    → Create Credentials
    → OAuth Client ID
```

Choose:

```text
Application Type: Desktop App
```

Download the OAuth credentials JSON file.

Rename it to:

```text
credentials.json
```

Place it in the project root:

```text
langchain-bot/
├── credentials.json
├── app.py
├── admin_app.py
└── ...
```

---

### 3. Required Gmail Scopes

Typical scopes used:

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]
```

For full Gmail access:

```python
SCOPES = [
    "https://mail.google.com/"
]
```

Use the least-privileged scope required by your application.

---

### 4. First-Time Authentication

Run the Gmail authentication flow:

```bash
uv run python gmail_auth.py
```

A browser window will open asking you to:

1. Sign in to Google.
2. Grant Gmail permissions.
3. Complete OAuth authorization.

---

### 5. Generated Token

After successful authentication:

```text
token.pickle
```

will be created automatically.

Project structure:

```text
langchain-bot/
├── credentials.json
├── token.pickle
├── app.py
├── admin_app.py
└── ...
```

---

## Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key
MODEL_NAME=gpt-xxx
MODEL_PROVIDER=openai
TAVILY_API_KEY=tavily_api_key_for_web_search
OPENWEATHERMAP_API_KEY=openweather_api_key
```

---

## Complete Startup Flow

```bash
# Install dependencies
uv sync

# Initialize database
uv run python src/langchain_bot/db_init.py

# Authenticate Gmail (one-time setup)
uv run python gmail_auth.py

# Start customer application
uv run streamlit run app.py

# Start admin application
uv run streamlit run admin_app.py --server.port 8502
```
---

### Package Management

- uv

### Language

- Python 3.13