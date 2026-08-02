# Lensight (Lenny's Growth Assistant) — Design System

## 1. Overview

**Lensight** is a single-page AI chat interface for product and growth practitioners — querying a corpus of ~180 Lenny's Podcast episodes. The visual personality is **dark, functional, and restrained**: near-pure black backgrounds, white-only accents, fine monochrome borders, and a strict semantic category system for skill types. Information density takes priority over decoration, and every visual element communicates state or hierarchy.

---

## 2. Brand & Typography
 
### Brand Identity
- **Name:** Lensight
- **Sidebar Header:** `Lens` in primary white text + `ight` in lighter italic muted style (`font-style: italic`, `opacity: 0.7`).
- **Logo Badge:** Square `L` icon with pure white background and black bold typography.

### Typography & Fonts
- **Inter** (variable 300–700 + italic) — primary UI text font.
- **JetBrains Mono** — code blocks, execution metrics, timestamps, model indicators.

---

## 3. Colors & Tokens

### Background Levels
| Token | Hex / Value | Role |
|---|---|---|
| `bg-base` | `#0D0D0D` | App canvas — near-pure black |
| `bg-surface` | `#141414` | Sidebar, artifact pane, cards |
| `bg-elevated` | `#1C1C1C` | Hover states, inputs, dropdowns |
| `bg-user-msg` | `#1F1F1F` | User chat bubble |

### Text Tokens
| Token | Hex / Value | Role |
|---|---|---|
| `text-primary` | `#F2F2F2` | Headings, primary text |
| `text-secondary` | `#888888` | Secondary content, session titles |
| `text-muted` | `#555555` | Meta labels, timestamps, placeholders |

### Semantic Skill Colors
| Skill | Hex | Config token / Role |
|---|---|---|
| Q&A | `#5B8DEF` | `skill-qa` |
| Essay | `#8B6EE8` | `skill-ship30` |
| Artifact | `#4CAF82` | `skill-artifact` |
| Multi | `#F5A623` | `SkillBadge` orange accent |
| Research | `#F97316` | Research Mode toggle / stats |

---

## 4. Key UI Components

### 1. Capability Chips (Empty State)
Centered below the chat input when no messages exist in the active session and input draft is empty:
- **Essay:** `BookOpen` icon (`rgba(112,89,196,0.6)`)
- **Q&A:** `Lightbulb` icon (`rgba(78,122,199,0.6)`)
- **Insights:** `BarChart2` icon (`rgba(61,144,104,0.6)`)
- **Dashboard:** `Layers` icon (`rgba(196,133,26,0.6)`)

*Behavior:* Auto-hides when user types draft text or sends first query.

### 2. Monochrome AgentTracker (Research Mode)
Pipeline status indicator rendered above streaming responses in Research Mode:
- **Style:** Monochrome dark palette using opacities of white (`rgba(255,255,255,...)`), replacing bright decorative multi-colors.
- **States:**
  - `pending`: white/4 dot (`rgba(255,255,255,0.04)`)
  - `active`: white/12 background + spinning `Loader2`
  - `healing`: white/10 background + pulsing `Wrench` icon
  - `done`: white/8 background + subtle `Check` icon
- **Step Text:** Clean plain text (emojis automatically stripped via `cleanStep`).

### 3. AgentStatus Row (Classic Mode)
- Animated label (`Thinking...` → `Searching...` → `Generating...` → `Repairing...`).
- Styled in `text-text-muted italic` with three synchronized animated pulse dots.
- Emojis stripped defensively via `stripEmoji()` utility to maintain visual restraint.

### 4. Split-Pane Artifact Viewer
- Slides in from right when an HTML or Markdown artifact is active (420px width).
- Interactive tab switch: `Preview` (iframe sandbox) ↔ `Code` (syntax-highlighted raw source).
- Header includes artifact title, copy button, and close controls.
