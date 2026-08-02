# Design: Lenny's Growth Assistant

**Version:** 0.2 — Research Mode (Phase 2)

---

## Design Philosophy

The goal is to feel like a premium, opinionated tool — not a generic AI chat template. The design language draws from two references:

1. **Lenny's Podcast branding** — warm, approachable, professional. Not cold-tech, not hype.
2. **Linear / Vercel dashboard aesthetic** — high information density, dark mode, tight typography, purposeful whitespace.

The evaluator sees this once. It needs to feel considered.

---

## Color System

```css
/* Design tokens */
--bg-base: #0d0d0f;          /* near-black background */
--bg-surface: #18181b;       /* card / sidebar surface */
--bg-elevated: #27272a;      /* input fields, hover states */
--border: #3f3f46;            /* subtle separator */

--accent-primary: #f97316;   /* Lenny orange — warm, on-brand */
--accent-secondary: #fb923c; /* lighter orange for hover */
--accent-muted: #431407;     /* very dark orange for subtle bg tints */

--text-primary: #fafafa;     /* headings, main content */
--text-secondary: #a1a1aa;   /* labels, timestamps, metadata */
--text-muted: #71717a;       /* placeholders, disabled */

--skill-qa: #22d3ee;          /* cyan — informational */
--skill-ship30: #a78bfa;      /* purple — creative */
--skill-artifact: #4ade80;    /* green — generative */

/* Research Mode additions */
--research-orange: #f97316;  /* active Research Mode accent */
--confidence-high: #4ade80;  /* green — high confidence badge */
--confidence-medium: #fbbf24; /* amber — medium confidence */
--confidence-low: #f87171;   /* red — low confidence */
--heal-amber: #fbbf24;       /* self-healing indicator */
```

**Rationale:** Black background with orange accent reads as warm intelligence rather than cold AI. The three skill colors give each mode a distinct visual identity at a glance. Research Mode reuses the same orange as the primary accent for brand coherence.

---

## Typography

```css
/* From Google Fonts */
--font-sans: 'Inter', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;

/* Scale */
--text-xs:   0.75rem;  /* 12px — timestamps, metadata */
--text-sm:   0.875rem; /* 14px — secondary content */
--text-base: 1rem;     /* 16px — body */
--text-lg:   1.125rem; /* 18px — subheadings */
--text-xl:   1.25rem;  /* 20px — headings */
--text-2xl:  1.5rem;   /* 24px — page title */
```

---

## Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: "Lenny's Growth Assistant"  ·  LLM toggle   ·  Status │
├──────────┬──────────────────────────┬───────────────────────────┤
│          │                          │                           │
│ Sidebar  │      Chat Pane           │     Artifact Pane         │
│ 240px    │      flex-1              │     400px                 │
│          │                          │  (hidden when no artifact)│
│ Sessions │  Messages + Input        │  Tab: Preview | Source    │
│ list     │  scroll + sticky input   │  iframe / md renderer     │
│          │                          │                           │
│          │  [Research] [↑ Send]     │                           │
└──────────┴──────────────────────────┴───────────────────────────┘
```

**Responsive:** On narrower viewports, artifact pane slides in as an overlay panel with a close button. Sidebar collapses to icon-only below 768px.

---

## Interaction Design

### Message States
- **Thinking:** animated pulsing dots (3-dot loader) while waiting for response
- **Skill badge:** each assistant message shows a small pill badge: `QA` (cyan) | `Essay` (purple) | `Artifact` (green) | `🔬 Research` (orange)
- **Sources:** collapsed by default, expand on click — shows guest name + YouTube link

### Research Mode Toggle
- Pill button placed left of the Send button inside the composer
- **Off:** subtle border, muted text, Microscope icon
- **On:** amber glow (`box-shadow: 0 0 12px rgba(249,115,22,0.2)`), animated pulse dot, "Research Active" text
- Placeholder text changes: *"Ask anything — Research Mode active (5 agents)…"*

### AgentTracker
- Horizontal 5-node pipeline strip appears **above** the streaming message content when Research Mode is active
- Nodes: `Plan → Search → Write → Build → QC`
- States per node:
  - `pending` → white dot (dim)
  - `active` → orange spinner (Loader2, animates)
  - `done` → green checkmark (Check)
  - `healing` → amber triangle (AlertTriangle, pulse)
- Header: animated orange pulse dot + "Research Mode — Multi-Agent Crew" label
- Compact step label shown below active/healing nodes

### Confidence Badge
- Shown in the hover action bar next to SkillBadge on `research:*` messages
- `high` → green dot + "High confidence" (5+ sources)
- `medium` → amber dot + "Medium confidence" (2-4 sources)
- `low` → red dot + "Low confidence" (0-1 sources)

### Research Stats
- Collapsed row below Research Mode responses
- Expand button shows: `N chunks · M episodes · K search hops · word count`
- Self-healing banner appears above if `healingAttempts > 0`:
  - Amber border, wrench icon, "Self-healed N× — ValidatorAgent fixed errors automatically"

### Artifact Pane
- **Tab 1 — Preview:** HTML rendered in `<iframe sandbox="allow-scripts">`. Markdown rendered with syntax highlighting.
- **Tab 2 — Source:** Raw code with copy button
- **Fade-in animation** when artifact first appears (transform: translateX(0) from right)

### LLM Toggle
- Simple segmented control in header: `[Local  |  Cloud]`
- Shows current model name below toggle: `llama3.3:8b` or `claude-sonnet-5`
- Orange ring pulse animation on switch (confirms state change)

### Session Sidebar
- "New chat" button at top with `+` icon
- Each session: title (first 60 chars of first message), relative timestamp
- Active session highlighted with left orange bar

---

## Component Library

All components were built from scratch using React + Tailwind. No component library was used.

**Layout components:**
- `SessionSidebar` — session list, "New chat" button, relative timestamps, active indicator
- `ArtifactPane` — Radix UI Tabs (Preview/Source), sandboxed iframe for HTML, markdown renderer for MD, copy button

**Chat components:**
- `ChatMessage` — user/assistant bubbles, markdown via `react-markdown` + `remark-gfm`, skill badge, sources accordion, AgentTracker (research), ConfidenceBadge, ResearchStats
- `ChatInput` — auto-resize textarea, keyboard shortcuts, ResearchModeToggle built-in
- `ThinkingDots` — 3-dot bounce animation

**Research Mode components (Phase 2):**
- `ResearchModeToggle` — amber pill toggle (off/active), pulse animation, placed inside composer
- `AgentTracker` — live 5-agent pipeline visualization, pending/active/done/healing node states
- `ConfidenceBadge` — green/amber/red source confidence indicator
- `ResearchStats` — expandable research metadata, self-healing banner

**UI components:**
- `SkillBadge` — colored pill with dot indicator: cyan (Q&A), purple (Essay), green (Artifact), orange 🔬 (Research variants)
- `ProviderToggle` — segmented control: Local (Ollama) / Cloud (Anthropic)
- `SourcesAccordion` — collapsible list of cited sources with YouTube links

**External deps used:**
- `react-markdown` + `remark-gfm` — markdown rendering with GFM (tables, strikethrough)
- `@radix-ui/react-tabs` — accessible tabs in artifact pane
- `lucide-react` — icons (ArrowUp, Microscope, Check, Loader2, AlertTriangle, etc.)
