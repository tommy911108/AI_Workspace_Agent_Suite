# Refund Agent 中文說明

這份文件簡單說明目前 Refund Agent 的功能、流程、模式差異與測試重點。

## 1. 這個 agent 是做什麼的

```text
Refund Agent
  ->
Search Gmail
  ->
Read emails
  ->
Classify
  ->
Send reply / Create draft / Skip
  ->
Summary
```

它的目標是處理 Gmail 裡和客服相關的信件，特別是：
- refund
- return
- complaint

## 2. 目前有哪些檔案

### `run_refund_agent.py`
- CLI 入口
- 啟動 agent
- 選擇 `auto` 或 `chat`

### `ai_workspace_agent_suite/agents/refund_agent.py`
- Refund Agent 主邏輯
- 載入 Gmail tools
- 建立 prompt
- 建立 graph
- 執行 auto / chat 對應流程

## 3. 目前流程

```text
python run_refund_agent.py
  ->
load .env
  ->
build model
  ->
connect workspace-mcp
  ->
load Gmail tools
  ->
run refund agent
```

Agent 內部流程：

```text
search_gmail_messages
  ->
get_gmail_message_content
  ->
classify
  ->
send / draft / skip
  ->
summary
```

## 4. 目前有什麼功能

目前這版已經可以：

- 搜尋 refund / return / complaint 相關郵件
- 讀取郵件內容
- 分類：
  - `REFUND_REQUEST`
  - `RETURN_REQUEST`
  - `COMPLAINT`
  - `OTHER`
- 清楚案件直接寄出
- 不確定案件建立草稿
- 不相關郵件跳過
- 回覆保留 thread
- 最後輸出 summary

## 5. Auto mode 跟 Chat mode 差別

### Auto mode

```text
固定任務
  ->
自動搜尋 unread refund-related emails
  ->
自動分類
  ->
clear case -> send
unclear case -> draft
  ->
summary
```

適合：
- 展示完整 workflow
- 一次跑完整流程

### Chat mode

```text
你自己輸入 prompt
  ->
agent 根據你的要求處理
```

適合：
- 測試
- demo
- 查詢
- 控制不要寄信 / 只草稿 / 只摘要

## 6. 目前的署名設定

現在寄信署名會從 `.env` 讀：

```env
REFUND_AGENT_SENDER_NAME=yenyu
```

如果你想改名字，只要改 `.env` 再重跑即可。

## 7. 怎麼執行

### Auto mode
```bash
python run_refund_agent.py --mode auto
```

### Chat mode
```bash
python run_refund_agent.py --mode chat
```

## 8. 測試重點

建議至少測這幾種：

```text
1. Retrieval-only
   ->
只搜尋 / 只摘要 / 不寄信

2. Draft-only
   ->
只建立草稿 / 不直接寄出

3. Real send
   ->
clear case 直接寄出

4. No-result case
   ->
沒有符合信件時要正常回報
```

## 9. 常見狀況

### 為什麼有時找不到測試信？

最常見原因是：

```text
測試信已不是 unread
  ->
agent 的搜尋條件通常偏向 unread
  ->
所以重新 demo 時可能抓不到
```

這不是因為 agent 記住以前的結果。  
重開程式後，它不會記住「之前處理過哪些信」，只是 Gmail 狀態變了。

## 10. 一句話總結

目前 Refund Agent 已經是一個可以展示的第一版：

```text
Search
  ->
Read
  ->
Classify
  ->
Send / Draft / Skip
  ->
Summary
```

下一步主要是完成 Calendar Agent。
