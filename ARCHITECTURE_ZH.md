# 整體架構簡述

```text
AI Workspace Agent Suite
  ->
Shared Core
  ->
2 Agents
    - Refund Email Agent
    - Calendar Agent
```

## Shared Core

```text
.env
  ->
config.py
  ->
llm.py
  ->
mcp_client.py
  ->
graph.py
```

- `config.py`
  - 讀取設定
- `llm.py`
  - 建立模型
- `mcp_client.py`
  - 建立 `workspace-mcp` 連線
- `graph.py`
  - 建立 LangGraph ReAct loop

## Refund Agent

```text
Search Gmail
  ->
Read Email
  ->
Classify
  ->
Send / Draft / Skip
  ->
Summary
```

## Calendar Agent

```text
User request
  ->
LLM decides tool
  ->
Simple read
  ->
workspace-cli tools

or

Create / Update / Delete / RSVP / FreeBusy
  ->
Calendar MCP tools
```

## Calendar Agent 的雙工具層

```text
Calendar Agent
  ->
CLI tools
  - cli_list_calendars
  - cli_today_events
  - cli_list_events
  - cli_get_event

Calendar Agent
  ->
MCP tools
  - list_calendars
  - get_events
  - manage_event
  - query_freebusy
```

## 一句話總結

```text
同一套 Shared Core
  ->
分別接 Gmail Agent 與 Calendar Agent
  ->
Calendar Agent 再多一層 CLI read tools
```
