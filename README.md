# AI Workspace Agent Suite

This project implements two Google Workspace agents on top of a shared LangGraph + MCP architecture:

```text
AI Workspace Agent Suite
  ->
Shared Core
  ->
1. Refund Email Agent
2. Calendar Agent
```

## 1. Project Structure

```text
.env
  ->
ai_workspace_agent_suite/config.py
  ->
ai_workspace_agent_suite/llm.py
  ->
ai_workspace_agent_suite/mcp_client.py
  ->
ai_workspace_agent_suite/graph.py
```

Shared core:

- `config.py`
  - loads `.env`
  - stores OpenAI / Google / timezone settings
- `llm.py`
  - creates the chat model
- `mcp_client.py`
  - starts the local `workspace-mcp` connection
- `graph.py`
  - builds the shared LangGraph ReAct loop
- `prompts.py`
  - stores shared agent prompts
- `utils.py`
  - helper functions

Agents:

- `run_refund_agent.py`
  - CLI entry point for the Gmail refund agent
- `ai_workspace_agent_suite/agents/refund_agent.py`
  - refund search / classify / reply workflow
- `run_calendar_agent.py`
  - CLI entry point for the calendar agent
- `ai_workspace_agent_suite/agents/calendar_agent.py`
  - calendar read / create / update / delete workflow
- `ai_workspace_agent_suite/tools/calendar_cli.py`
  - lightweight `workspace-cli` read tools for calendar lookups

## 2. Overall Flow

```text
User
  ->
CLI entry point
  ->
load_settings()
  ->
create_chat_model()
  ->
create_mcp_client()
  ->
load tools
  ->
build LangGraph agent
  ->
run task
```

## 3. Refund Agent Flow

```text
Search Gmail
  ->
Read email
  ->
Classify
  - REFUND_REQUEST
  - RETURN_REQUEST
  - COMPLAINT
  - OTHER
  ->
Send / Draft / Skip
  ->
Summary
```

Modes:

- `--mode auto`
  - fixed autonomous workflow
  - sends directly for clear cases
  - drafts only when uncertain
- `--mode chat`
  - interactive prompt-based workflow

Run:

```bash
python run_refund_agent.py --mode auto
python run_refund_agent.py --mode chat
```

## 4. Calendar Agent Flow

```text
User request
  ->
Calendar Agent
  ->
Simple read
  ->
workspace-cli tools

or

Create / Update / Delete / RSVP / FreeBusy
  ->
Calendar MCP tools
```

Calendar agent uses Taiwan time by default:

```text
LOCAL_TIMEZONE=Asia/Taipei
```

Modes:

- `--mode demo`
  - runs a few fixed calendar queries
- `--mode chat`
  - interactive calendar assistant

Run:

```bash
python run_calendar_agent.py --mode demo
python run_calendar_agent.py --mode chat
```

## 5. Environment Variables

Required `.env` values:

```env
OPENAI_KEY=...
OPENAI_BASE=...
OPENAI_MODEL=gpt-4o

GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
OAUTHLIB_INSECURE_TRANSPORT=1

USER_GOOGLE_EMAIL=your_google_account
REFUND_AGENT_SENDER_NAME=yenyu
LOCAL_TIMEZONE=Asia/Taipei
WORKSPACE_MCP_PORT=8000
WORKSPACE_MCP_HTTP_PORT=8001
```

## 6. Setup Notes

This repo depends on both Python packages and Google Cloud / OAuth setup.

You still need:

1. A conda environment
2. `workspace-mcp` installed
3. Google OAuth client configured
4. Gmail API enabled
5. Google Calendar API enabled
6. Your Google account added as a test user if the OAuth app is still in testing mode

## 7. Reproducibility

```bash
conda run -n ai-workspace-agent-suite python -m pip freeze
```

To recreate a similar environment:

```bash
conda create -n ai-workspace-agent-suite python=3.11 -y
conda activate ai-workspace-agent-suite
pip install -r requirements.txt
```

## 8. Test Files

Prompt collections:

- `REFUND_AGENT_TEST_PROMPTS.txt`
- `CALENDAR_AGENT_TEST_PROMPTS.txt`

Status / notes:

- `PROJECT_STATUS_ZH.md`
- `REFUND_AGENT_ZH.md`
- `ARCHITECTURE_ZH.md`

## 9. Current Status

```text
Shared Core
  ->
Refund Agent completed
  ->
Calendar Agent completed
```

This version is suitable for local demo, course presentation, and iterative extension.
