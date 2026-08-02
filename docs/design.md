# Lenny's Growth Assistant — Design System

## 1. Overview

Lenny's Growth Assistant is a single-page AI chat interface for product and growth
practitioners — querying a corpus of ~180 Lenny's Podcast episodes. The visual
personality is **dark, functional, and deliberately restrained**: near-pure black
backgrounds, white-only accents, fine monochrome borders, and a strict four-color
semantic category system for skill types. The UI is a tool, not a marketing site —
information density takes priority over decoration, and every color choice either
communicates hierarchy or carries semantic meaning (category coding).

---

## 2. Colors

### Background levels (dark → light)
| Token | Hex | Role |
|---|---|---|
| `bg-base` | `#0D0D0D` | App canvas — near-pure black |
| `bg-surface` | `#141414` | Sidebar, artifact pane, card surfaces |
| `bg-elevated` | `#1C1C1C` | Hover states, inputs, dropdowns |
| `bg-user-msg` | `#1F1F1F` | User chat bubble |

### Borders
| Token | Hex | Role |
|---|---|---|
| `border` DEFAULT | `#262626` | Standard — buttons, panels |
| `border-subtle` | `#1E1E1E` | Quiet dividers — sidebar edge |

### Text
| Token | Hex | Role |
|---|---|---|
| `text-primary` | `#F2F2F2` | Headings, primary content |
| `text-secondary` | `#888888` | Session titles, descriptions |
| `text-muted` | `#555555` | Timestamps, placeholders, meta |

### Accent
White `#FFFFFF` is the sole accent — avatar squares, active pill bg, send button.

### Skill category colors (semantic, not decorative)
| Skill | Hex | Config token |
|---|---|---|
| Q&A | `#5B8DEF` | `skill-qa` |
| Essay | `#8B6EE8` | `skill-ship30` |
| Artifact | `#4CAF82` | `skill-artifact` |
| Multi | `#F5A623` | inline in SkillBadge |
| Research | `#F97316` | inline in SkillBadge |
| Follow-up | `#9E9E9E` | inline in SkillBadge |

---

## 3. Typography

Fonts loaded in `index.css` via Google Fonts:
- **Inter** (variable 300–700 + italic) — all UI text currently
- **JetBrains Mono** (400, 500) — only inside `.prose-chat code/pre`

Gap: timestamps, model name, episode count footer use Inter but should use mono
(machine data vs human content — see Do's and Don'ts).

---

## 4. Elevation

Depth via background steps and borders only — no drop shadows in the main layout.

| Layer | Technique |
|---|---|
| Base → Surface | `#0D0D0D` → `#141414` step |
| Surface → Elevated | hover lifts to `#1C1C1C` |
| Panel edges | 1px `border-subtle` |
| Artifact pane edge | `border-l-2 border-white/10` + left-shadow (only shadow in main UI) |
| Active session | 2px white left bar |
| Dropdowns | `shadow-xl shadow-black/40` over elevated bg |

---

## 5. Components

### Chat bubble — User
Right-aligned, `bg-user-msg`, `border border-white/10`, `rounded-2xl rounded-br-md`,
with "U" avatar circle on the right.

### Chat bubble — Assistant
Left-aligned up to 760px, "L" white square avatar, `.prose-chat` prose, hover-revealed
action bar (copy, retry, artifact link), always-visible skill badge below.

### Sidebar session row
`text-xs` truncated title + `timeAgo`, active state = `bg-elevated` + white left bar,
3-dot menu with rename/delete.

### Skill badge (SkillBadge)
`rounded-full` border-only pill, 10px text, dot indicator. No fill — border at 25%
opacity, text at 80%, dot at 100% of skill color.

### Suggestion / prompt card (EmptyState)
`rounded-xl` card, `bg-surface border-border`, category label in 9px uppercase
tracking-widest in skill color, body in `text-secondary`.

### Provider toggle (ProviderToggle)
`bg-elevated border-border rounded-lg` container, active option `bg-white text-black` +
green dot, inactive `text-muted`.

### Artifact pane (ArtifactPane)
Full-height right drawer, `bg-surface`, separated by `border-l-2 border-white/10` +
shadow. Preview/Code tabs via Radix UI.

---

## 6. Do's and Don'ts

### Do
- Keep the 4-color category system (Q&A / Essay / Artifact / Multi) — functional, not decorative.
- Use JetBrains Mono for machine/system text: timestamps, model names, stats, counts.
- Use white as the sole accent — keep the "monochrome + category touches" language.
- Use background steps for elevation, not shadows (except floating elements).

### Don't
- **Don't use red** — banned, full stop. Use amber (`#D97706` range) or neutral gray for errors/warnings.
- Don't use gradients (background fills, button fills — flat only).
- Don't use nested cards.
- Don't use default Tailwind saturated hues — all category colors are hand-tuned desaturated variants.
- Don't use drop shadows for primary content separation — use borders instead.
