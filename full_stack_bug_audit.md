# Full-Stack Bug Audit & Specification Document
**Project:** Lenny's Growth Assistant (FastAPI + React/Vite + Supabase pgvector)  
**Document Version:** 1.0  
**Scope:** Deep-dive analysis combining User POV Examples, Code Trace Snippets, Technical Root Cause Analysis, and Recommended Fixes across all 11 identified issues.

---

## Executive Summary Matrix

| # | Bug Title | User Impact | Technical Root Cause | Severity |
|---|---|---|---|---|
| **1** | [First Message Disappears / Wipes Streaming Chat](#bug-1-first-message-disappears--wipes-streaming-chat) | Chat screen clears out mid-stream on first query | React `useEffect([activeSessionId])` race condition overwrites `messages` state with empty DB fetch | **CRITICAL** |
| **2** | [Cross-Session Stream Bleeding](#bug-2-cross-session-stream-bleeding) | Switching chats mid-stream streams tokens into wrong session | Missing session ID checks in stream callbacks & unhandled active stream cancellation | **CRITICAL** |
| **3** | [Insecure Iframe Sandboxing](#bug-3-insecure-iframe-sandboxing) | Security risk where iframe scripts escape sandbox | Combination of `allow-scripts` + `allow-same-origin` in iframe `sandbox` attribute | **CRITICAL** |
| **4** | [Historical Session Artifact Cards Vanish on Reload](#bug-4-historical-session-artifact-cards-vanish-on-reload) | Saved artifact buttons disappear after page refresh | Backend outputs `artifact_json`, but frontend expects `artifact` field in `MessageOut` | **CRITICAL** |
| **5** | [Duplicate Orphan Sessions on Fast Clicks](#bug-5-duplicate-orphan-sessions-on-fast-clicks) | Double clicking "+ New chat" spawns 2 sessions | Async `handleNewChat` lacks concurrency guard / button loading state | **HIGH** |
| **6** | [Raw Code Leak on Malformed Tags](#bug-6-raw-code-leak-on-malformed-tags) | Raw `<artifact>` tags leak into chat text | Strict regex parser fails on unclosed tags and falls back to raw text dump | **MEDIUM** |
| **7** | [Nonsense RAG Answers to Short Remarks](#bug-7-nonsense-rag-answers-to-short-remarks) | Typing "ok" or "thanks" triggers heavy podcast search | Followup router logic excludes generic conversational terms, falling through to `qa` | **MEDIUM** |
| **8** | [Global Provider Override Overwrites All Sessions](#bug-8-global-provider-override-overwrites-all-sessions) | Topbar model toggle forces all past chats to change model | Backend uses module global `_current_provider` instead of reading `session.llm_provider` | **MEDIUM** |
| **9** | [Research Agent Badges Vanish on Reload](#bug-9-research-agent-badges-vanish-on-reload) | Agent steps & confidence pills lost on refresh | `MessageOut` Pydantic model omits `agent_steps`, `confidence`, and `research_stats` fields | **MEDIUM** |
| **10** | [Uncancelled Backend Streams & Timestamp Inversion](#bug-10-uncancelled-backend-streams--timestamp-inversion) | Rapid message sends cause scrambled chat history | Frontend abort does not stop backend generator loop execution | **LOW** |
| **11** | [Mid-Stream Refresh Drops Assistant Response](#bug-11-mid-stream-refresh-drops-assistant-response) | Refreshing 2s into stream leaves user prompt unanswered | Assistant message DB insert occurs only at end of SSE stream generation | **LOW** |

---

## Detailed Bug Breakdown

### Bug 1: First Message Disappears / Wipes Streaming Chat

> [!CAUTION]
> **Severity:** CRITICAL (Breaks Core User Flow)

#### User POV & Example
* **What the user does:** Opens the web app with no chat selected (home empty screen). Types *"What did Brian Chesky say about culture?"* and hits Enter.
* **What the user experiences:** 
  1. The user bubble appears and the assistant starts typing tokens.
  2. Suddenly, 1 second later, the chat pane completely wipes out and reverts to the empty home screen ("How can I help you today?").
  3. The user thinks their message was lost. However, if they look at the sidebar, a session title has appeared. Clicking that session restores the message history.

#### Technical Analysis
* **File Location:** [App.jsx:135-142](file:///d:/Lenny's%20Growth%20Assistant/frontend/src/App.jsx#L135-L142) & [App.jsx:182-192](file:///d:/Lenny's%20Growth%20Assistant/frontend/src/App.jsx#L182-L192)
* **Code Trace:**
```javascript
// App.jsx — handleSend
let sessionId = activeSessionId;
if (!sessionId) {
  const session = await createSession('New chat', provider);
  setSessions(prev => [session, ...prev]);
  setActiveSessionId(session.id); // <--- Triggers useEffect([activeSessionId]) asynchronously!
  sessionId = session.id;
}
setMessages(prev => [...prev, userMsg, assistantMsg]); // Optimistic UI update

// App.jsx — useEffect
useEffect(() => {
  if (!activeSessionId) { setMessages([]); return; }
  setMessagesLoading(true);
  getMessages(activeSessionId) // <--- Backend returns [] because stream just started
    .then(setMessages)         // <--- OVERWRITES optimistic streaming state with []!
    .finally(() => setMessagesLoading(false));
}, [activeSessionId]);
```
* **Root Cause:** A state dependency race condition. `setActiveSessionId(session.id)` inside `handleSend` asynchronously triggers `useEffect([activeSessionId])`. The `useEffect` fires an HTTP GET to `/sessions/${session.id}/messages`. Because the streaming assistant response has not finished saving to DB yet, the API returns `[]`. `.then(setMessages)` overwrites the optimistic local state with `[]`.

#### Proposed Fix
```javascript
const skipNextFetchRef = useRef(false);
// In handleSend when creating session: skipNextFetchRef.current = true;
// In useEffect([activeSessionId]): if (skipNextFetchRef.current) { skipNextFetchRef.current = false; return; }
```

---

### Bug 2: Cross-Session Stream Bleeding

> [!CAUTION]
> **Severity:** CRITICAL (Data Pollution)

#### User POV & Example
* **What the user does:** Types a complex essay query in **Session A** (*"Write a 1000 word essay on retention"*). While Session A is actively streaming text, the user clicks **Session B** (*"Growth Metrics"*) in the sidebar to read an old answer.
* **What the user experiences:** 
  Tokens from Session A's essay start live-typing directly into Session B's message view! If an artifact finishes building, Session A's artifact pane pops open over Session B.

#### Technical Analysis
* **File Location:** [App.jsx:217-272](file:///d:/Lenny's%20Growth%20Assistant/frontend/src/App.jsx#L217-L272) & [App.jsx:304](file:///d:/Lenny's%20Growth%20Assistant/frontend/src/App.jsx#L304)
* **Code Trace:**
```javascript
// App.jsx — SessionSidebar invocation
<SessionSidebar
  onSelectSession={(id) => { setActiveSessionId(id); setArtifact(null); }} // Does NOT call abortRef.current?.abort()
/>

// App.jsx — streamChat callback inside handleSend
onToken: (token) => {
  setMessages(prev => prev.map(m =>
    m.id === assistantId ? { ...m, content: m.content + token } : m // Modifies whatever 'messages' state is currently active!
  ));
}
```
* **Root Cause:** 
  1. `onSelectSession` switches `activeSessionId` without aborting active SSE fetch streams (`abortRef.current?.abort()`).
  2. `onToken` and `onDone` stream callbacks do not check if `sessionId` matches the current `activeSessionId`.

#### Proposed Fix
```javascript
// In onSelectSession:
onSelectSession={(id) => {
  abortRef.current?.abort();
  setActiveSessionId(id);
  setArtifact(null);
}}
```

---

### Bug 3: Insecure Iframe Sandboxing

> [!CAUTION]
> **Severity:** CRITICAL (Security Vulnerability)

#### User POV & Example
* **What the user does:** Prompts the AI to create an interactive HTML dashboard: *"Build an HTML page with custom JavaScript."*
* **What the user experiences:** The preview renders fine, but any script embedded inside the generated HTML can access `window.parent`, inspect parent page memory, read cookies, or trigger actions in the main application UI.

#### Technical Analysis
* **File Location:** [ArtifactPane.jsx:106](file:///d:/Lenny's%20Growth%20Assistant/frontend/src/components/ArtifactPane.jsx#L106)
* **Code Trace:**
```html
<iframe
  id="artifact-iframe"
  srcDoc={artifact.content}
  sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
/>
```
* **Root Cause:** Combining `allow-scripts` AND `allow-same-origin` in an HTML iframe sandbox breaks the security boundary completely according to W3C specification. It allows the iframe script to execute in the same origin as the parent window, enabling it to reach `window.parent` and disable its own sandbox restrictions.

#### Proposed Fix
```html
sandbox="allow-scripts allow-forms allow-popups allow-modals"
<!-- Removed allow-same-origin to force null-origin execution isolation -->
```

---

### Bug 4: Historical Session Artifact Cards Vanish on Reload

> [!CAUTION]
> **Severity:** CRITICAL (Data Loss in UI)

#### User POV & Example
* **What the user does:** Generates an interactive chart or HTML document. An inline button *"Interactive HTML - Click to open preview →"* appears below the message. User refreshes the page or comes back to this chat tomorrow.
* **What the user experiences:** The chat text is saved, but the artifact preview button has vanished! There is no way to open the artifact pane for past sessions.

#### Technical Analysis
* **File Location:** [models.py:40](file:///d:/Lenny's%20Growth%20Assistant/backend/models.py#L40), [main.py:273-280](file:///d:/Lenny's%20Growth%20Assistant/backend/main.py#L273-L280), & [App.jsx:326](file:///d:/Lenny's%20Growth%20Assistant/frontend/src/App.jsx#L326)
* **Code Trace:**
```python
# models.py — MessageOut schema
class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    artifact_json: Optional[dict] = None # <--- Backend outputs key "artifact_json"

# App.jsx — ChatMessage rendering
<ChatMessage
  artifact={msg.artifact} // <--- Frontend expects key "artifact" (which is undefined on loaded history!)
/>
```
* **Root Cause:** Contract mismatch between backend Pydantic schema and frontend component prop expected key name. Backend returns `{ "artifact_json": {...} }` whereas frontend looks for `msg.artifact`.

#### Proposed Fix
```python
# In models.py or main.py response mapper:
class MessageOut(BaseModel):
    artifact: Optional[dict] = Field(None, alias="artifact_json")
```

---

### Bug 5: Duplicate Orphan Sessions on Fast Clicks

> [!WARNING]
> **Severity:** HIGH (UX Polish)

#### User POV & Example
* **What the user does:** Clicks the **"+ New chat"** button twice quickly.
* **What the user experiences:** Two separate "New chat" entries are created at the top of the sidebar. One of them becomes an orphaned empty chat session.

#### Technical Analysis
* **File Location:** [App.jsx:145-155](file:///d:/Lenny's%20Growth%20Assistant/frontend/src/App.jsx#L145-L155)
* **Root Cause:** `handleNewChat` is an async function without an execution lock or button disabled state during API call resolution.

---

### Bug 6: Raw Code Leak on Malformed Tags

> [!WARNING]
> **Severity:** MEDIUM

#### User POV & Example
* **What the user does:** Asks for an HTML artifact on Ollama (`qwen3:4b`).
* **What the user experiences:** Instead of a clean card, raw text like `<artifact type="html"> <!DOCTYPE html> ...` is dumped straight into the main chat bubble.

#### Technical Analysis
* **File Location:** [artifact.py:148-164](file:///d:/Lenny's%20Growth%20Assistant/backend/skills/artifact.py#L148-L164)
* **Root Cause:** `extract_artifact` regex `r'<artifact\s+type=["\'](\w+)["\']\s*>(.*?)</artifact>'` fails if the LLM output cuts off without `</artifact>`. The fallback logic treats the string as plain markdown, leaking code tags into text.

---

### Bug 7: Nonsense RAG Answers to Short Remarks

> [!WARNING]
> **Severity:** MEDIUM

#### User POV & Example
* **What the user does:** Types *"ok"*, *"thanks"*, or *"tell me more"*.
* **What the user experiences:** The assistant performs a full database search for "ok" and outputs a 300-word breakdown of podcast episodes instead of saying *"You're welcome!"*.

#### Technical Analysis
* **File Location:** [router.py:107-114](file:///d:/Lenny's%20Growth%20Assistant/backend/router.py#L107-L114)
* **Root Cause:** `_is_followup` fast path only detects specific pronouns (`"this"`, `"that"`, `"it"`). Short conversational remarks fall through to `_keyword_classify` -> returns `"qa"`, executing full vector retrieval.

---

### Bug 8: Global Provider Override Overwrites All Sessions

> [!WARNING]
> **Severity:** MEDIUM

#### User POV & Example
* **What the user does:** Switches Topbar toggle from **Local** to **Cloud**. Opens an old session created under Local.
* **What the user experiences:** The old session runs on Cloud instead of preserving its original provider setting.

#### Technical Analysis
* **File Location:** [main.py:63](file:///d:/Lenny's%20Growth%20Assistant/backend/main.py#L63) & [main.py:310](file:///d:/Lenny's%20Growth%20Assistant/backend/main.py#L310)
* **Root Cause:** `_current_provider` is a global module variable mutated by `/config/llm`. `main.py` ignores `session.llm_provider` stored in PostgreSQL.

---

### Bug 9: Research Agent Badges Vanish on Reload

> [!NOTE]
> **Severity:** MEDIUM

#### User POV & Example
* **What the user does:** Runs a query in 5-Agent Research Mode. Refreshes the page.
* **What the user experiences:** The step tracker badges (*🔍 Searching*, *🔧 Self-healing*) and confidence score pills vanish from history.

#### Technical Analysis
* **File Location:** [models.py:34-42](file:///d:/Lenny's%20Growth%20Assistant/backend/models.py#L34-L42)
* **Root Cause:** `MessageOut` Pydantic model omits `agent_steps`, `confidence`, and `research_stats` fields, stripping them from `GET /sessions/{id}/messages`.

---

### Bug 10: Uncancelled Backend Streams & Timestamp Inversion

> [!NOTE]
> **Severity:** LOW

#### User POV & Example
* **What the user does:** Types Message 1, hits Enter, then rapidly types Message 2 and hits Enter.
* **What the user experiences:** When reloading later, Message 1's response might appear *after* Message 2.

#### Technical Analysis
* **File Location:** [main.py:370-550](file:///d:/Lenny's%20Growth%20Assistant/backend/main.py#L370-L550)
* **Root Cause:** Disconnecting SSE HTTP connection on client does not stop Uvicorn generator loop, which continues inserting completion records to DB out of sync.

---

### Bug 11: Mid-Stream Refresh Drops Assistant Response

> [!NOTE]
> **Severity:** LOW

#### User POV & Example
* **What the user does:** Sends a query, then hits F5 2 seconds into streaming.
* **What the user experiences:** User prompt stays in sidebar, but no assistant answer exists on reload.

#### Technical Analysis
* **File Location:** [main.py:388-530](file:///d:/Lenny's%20Growth%20Assistant/backend/main.py#L388-L530)
* **Root Cause:** Assistant message `INSERT` statement only runs in final SSE block after completion stream closes.
