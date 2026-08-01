# Design: Lenny's Growth Assistant

**Version:** 0.1

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
```

**Rationale:** Black background with orange accent reads as warm intelligence rather than cold AI. The three skill colors give each mode a distinct visual identity at a glance.

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
└──────────┴──────────────────────────┴───────────────────────────┘
```

**Responsive:** On narrower viewports, artifact pane slides in as an overlay panel with a close button. Sidebar collapses to icon-only below 768px.

---

## Interaction Design

### Message States
- **Thinking:** animated pulsing dots (3-dot loader) while waiting for response
- **Skill badge:** each assistant message shows a small pill badge: `QA` (cyan) | `Essay` (purple) | `Artifact` (green)
- **Sources:** collapsed by default, expand on click — shows guest name + YouTube link

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

All components were built from scratch using React + Tailwind. No component library was used (prompt-kit/shadcn was considered but the shadcn/Vite setup overhead wasn't worth it for a 3-day build).

**Layout components:**
- `SessionSidebar` — session list, "New chat" button, relative timestamps, active indicator
- `ArtifactPane` — Radix UI Tabs (Preview/Source), sandboxed iframe for HTML, markdown renderer for MD, copy button

**Chat components:**
- `ChatMessage` — user/assistant bubbles, avatar, markdown rendering via `react-markdown` + `remark-gfm`, skill badge, sources accordion
- `ChatInput` — auto-resize textarea, suggestion chips, keyboard shortcuts (Enter to send, Shift+Enter newline)
- `ThinkingDots` — 3-dot bounce animation matching assistant avatar style

**UI components:**
- `SkillBadge` — colored pill with dot indicator: cyan (Q&A), purple (Essay), green (Artifact)
- `ProviderToggle` — segmented control: Local (Ollama) / Cloud (Anthropic)
- `SourcesAccordion` — collapsible list of cited sources with YouTube links

**External deps used:**
- `react-markdown` + `remark-gfm` — markdown rendering with GFM (tables, strikethrough)
- `@radix-ui/react-tabs` — accessible tabs in artifact pane
- `lucide-react` — icons
