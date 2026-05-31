# AI Workspace Agent Suite 專案狀態

這份文件用簡單版本整理目前專案做到哪裡、現在的流程、以及接下來要做什麼。

## 1. 目前完成了什麼

目前專案已完成：

```text
[Shared Core]
config.py
  ->
llm.py
  ->
mcp_client.py
  ->
graph.py
```

以及第一個可執行 agent：

```text
[Refund Email Agent]
run_refund_agent.py
  ->
refund_agent.py
  ->
Gmail MCP tools
  ->
Search / Read / Classify / Reply or Draft / Summary
```

## 2. 目前有哪些主要檔案

### 共用模組
- `ai_workspace_agent_suite/config.py`
  - 讀 `.env`
  - 管理 OpenAI / Google OAuth / sender name 設定

- `ai_workspace_agent_suite/llm.py`
  - 建立模型

- `ai_workspace_agent_suite/mcp_client.py`
  - 建立 `workspace-mcp` client

- `ai_workspace_agent_suite/graph.py`
  - 建立 LangGraph ReAct loop

- `ai_workspace_agent_suite/prompts.py`
  - 放共用 prompt

- `ai_workspace_agent_suite/state.py`
  - 放 LangGraph message state

- `ai_workspace_agent_suite/utils.py`
  - 放共用小工具

### 已完成 agent
- `ai_workspace_agent_suite/agents/refund_agent.py`
  - Refund Email Agent 主邏輯

- `run_refund_agent.py`
  - Refund Agent CLI 執行入口

## 3. 現在的執行流程

### 整體流程

```text
.env
  ->
load_settings()
  ->
create_chat_model()
  ->
create_mcp_client()
  ->
load Gmail tools
  ->
build refund agent
  ->
run auto mode or chat mode
```

### Refund Agent 內部流程

```text
User task
  ->
LLM
  ->
search_gmail_messages
  ->
get_gmail_message_content
  ->
classify email
  ->
send_gmail_message or draft_gmail_message or skip
  ->
final summary
```

## 4. 目前 Refund Agent 可以做什麼

目前這個版本已經可以：

- 搜尋 Gmail 裡的 refund / return / complaint 相關信件
- 讀取信件內容
- 分類成：
  - `REFUND_REQUEST`
  - `RETURN_REQUEST`
  - `COMPLAINT`
  - `OTHER`
- 在 clear case 時直接寄出回信
- 在不確定時建立草稿
- 保留 thread reply
- 最後輸出 summary
- 支援寄件署名，從 `.env` 的 `REFUND_AGENT_SENDER_NAME` 讀取

## 5. Auto / Chat 差別

```text
[Auto Mode]
固定任務
  ->
自動搜尋
  ->
自動分類
  ->
清楚就直接寄
不確定就草稿
  ->
輸出 summary
```

```text
[Chat Mode]
你自己輸入 prompt
  ->
agent 根據你的要求動作
  ->
適合 demo / 測試 / 查詢 / 控制行為
```

## 6. 老師專案目前怎麼看

目前最合理的理解是：

```text
Project = 2 separate agents

1. Refund Email Agent
2. Calendar Agent
```

它們共用底層架構，但不是現在就一定要做成一個總 planner。

所以目前狀態可以理解成：

```text
AI Workspace Agent Suite
  ->
Shared Core 已完成
  ->
Refund Agent 已完成第一版
  ->
Calendar Agent 尚未完成
```

## 7. 接下來要做什麼

下一步最合理的是：

```text
Calendar Agent (MCP-only first)
  ->
run_calendar_agent.py
  ->
calendar_agent.py
  ->
查 calendars / 查 events / interactive mode / demo mode
```

之後再做：

```text
Calendar CLI layer
  ->
workspace-cli subprocess tools
```

## 8. 一句話總結

目前專案已經有一個可實際展示的 Refund Email Agent，接下來重點是完成第二個 Calendar Agent。
