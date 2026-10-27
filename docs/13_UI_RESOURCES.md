# 13 — UI/UX Resources for Claude Code (free, accounts OK)

Prepared 27 Oct 2026. Goal: a polished, intentional UI that does **not** look like a generic AI template (the finale
briefing says UI/UX carries marks). Planning material: what to install and how to work on the day; no app code here.

Stack constraint (CLAUDE.md): React + TypeScript + Vite, Tailwind, TanStack Query, **ECharts**. Prefer resources that fit it.

---

## 1. Design direction (decide before the day)

Use the plant-operations world's own design language instead of a startup-dashboard template:

- **High-performance HMI (ISA-101) principles** used in control rooms: light-grey neutral background, flat 2-D
  graphics, and **colour reserved for abnormal states and alarms**; a display hierarchy from plant overview down to
  diagnostics; moving-bar indicators with alarm limits [R1][R2]. This maps directly onto our three lenses
  (CFO = overview, Ops = area/unit, Engineer = diagnostics).
- **Colour carries meaning only** (docs/01 §5): controllable vs uncontrollable vs residual vs recovered; status colours
  always paired with an icon and a label.
- **Numbers are the hero**: tabular figures in tables, units always shown, provenance badges (measured / modeled / synthetic).
- **Light theme** (also recommended by the organizers for projection).
- Avoid the generic AI look: purple gradients, glassmorphism, oversized hero sections, emoji icons, default Inter-everywhere,
  identical card grids, decorative charts with no decision behind them [R3].

Write these as a short **design brief** in the dev repo's CLAUDE.md on the day (template in §6).

---

## 2. Claude Code plugins / MCP servers worth installing

| Tool | What it does for us | Cost / account | Install (verify on the day) | Verdict |
|---|---|---|---|---|
| **Anthropic `frontend-design` plugin** | Official Claude Code skill that pushes Claude to commit to a distinct aesthetic and avoid generic AI UI | Free | `/plugin marketplace add anthropics/claude-code` then `/plugin install frontend-design@claude-code-plugins` [R3] | **Install** |
| **Playwright MCP** (Microsoft) | Lets Claude open the running app, take full-page/element screenshots and read the accessibility tree → it can *see* and fix its own layout bugs | Free, needs Node ≥ 20 | `claude mcp add playwright -- npx @playwright/mcp@latest` [R4] | **Install** (the Claude desktop app's built-in browser is an alternative) |
| **Context7 MCP** (Upstash) | Pulls current, version-specific docs (ECharts, TanStack Query, Tailwind, React Router) so generated code uses real APIs | Free; optional free key for higher limits | `npx @upstash/context7-mcp` (local) or remote endpoint [R5] | **Install** |
| **shadcn/ui MCP** (official) | Browse/search/install shadcn components (accessible Radix primitives styled with Tailwind) by prompt | Free | `pnpm dlx shadcn@latest mcp init --client claude` [R6] | **Install** if we use shadcn primitives (tables, dialogs, selects, tabs) |
| **Figma remote MCP** | Claude reads frames/variables from a Figma file and implements them | Figma says the remote server works on all plans [R7]; third-party guides disagree — check with your account | `claude mcp add --transport http figma https://mcp.figma.com/mcp` [R7] | **Optional**: only if a teammate designs screens in Figma first |
| **21st.dev Magic MCP** | Generates shadcn/Tailwind components from a prompt | Account + API key; free tier is a small daily allowance, then paywall [R8] | `npx @21st-dev/cli@latest install claude --api-key …` | **Optional / use sparingly** — its outputs are exactly the "template look" judges penalise; use for a starting skeleton only |
| Refero MCP | Real product screens and design systems as references for the agent | **Paid (Pro required)** [R9] | — | Skip (paid) |
| shadcn.io MCP | Third-party registry | **Paid Pro** [R10] | — | Skip (paid) |

Recommended minimum set: **frontend-design + Playwright + Context7 (+ shadcn MCP)**. All free.

---

## 3. Component and chart libraries (free)

| Library | Use it for | Notes |
|---|---|---|
| **shadcn/ui** (Radix + Tailwind) | Accessible primitives: table, tabs, dialog, select, dropdown, tooltip, sheet | Copy-in components, fully restylable → easy to make *ours* |
| **Tremor** (now Vercel, MIT) | Dashboard layout blocks and KPI patterns for reference | 35+ components, 300+ blocks/templates now free and open source [R11]. Its charts use Recharts — we keep **ECharts** for charts, borrow layouts only |
| **Apache ECharts examples** (echarts.apache.org/examples) | Waterfall (stacked transparent base), heatmap, custom series, mark lines for limits/guarantees | Already in the stack |
| **lucide-react** | Icons | Already in use; consistent stroke style |
| **@fontsource/ibm-plex-sans / ibm-plex-mono** | Self-hosted fonts (works offline) | Industrial, legible; avoids the default Inter look |

---

## 4. Design inspiration (browse before the day — references, not code)

| Source | Search for | Cost |
|---|---|---|
| **Dribbble** (dribbble.com) | "SCADA", "energy dashboard", "solar monitoring", "control room", "power plant UI" | Free to browse |
| **ISA-101 / high-performance HMI white papers** (Emerson, process-industry guides) | Grey backgrounds, alarm colour rules, analog bars | Free [R1][R2] |
| **Vendor product pages** (Power Factors, meteocontrol VCOM, Prescinto) | How incumbents present portfolio → site → inverter drill-down | Free (marketing pages) |
| **Mobbin / Godly / Land-book** | General layout patterns | Free browsing tiers vary — check; not verified |

Save 5–10 screenshots per lens (CFO, Ops, Engineer) into a `design-refs/` folder of the dev repo **on the day** and point
Claude at them ("match the density and hierarchy of these, not their colours").

---

## 5. On-the-day UI workflow with Claude Code

1. **Brief first** — paste the design brief (§6) into CLAUDE.md before any UI prompt.
2. **Tokens before pages** — ask for Tailwind theme tokens (neutrals, one accent, status colours, chart roles) and a
   type scale; review once; never let pages invent colours.
3. **One component kit** — KPI tile, panel, status pill, provenance badge, data table, empty/loading states. Build and
   review these before pages.
4. **Page by page with screenshots** — after each page, have Claude open it via Playwright at 1440×900 and 1280×720
   (projector size), screenshot, and critique against the checklist (§7). Fix, re-shoot.
5. **Real data early** — render real API data as soon as possible; layout problems (long numbers, empty months) only
   appear with real values.
6. **Projector check** — light background, ≥ 13 px body text, chart labels readable from 3 m; test once on the actual
   projector resolution if possible.

## 6. Design brief to paste into the dev CLAUDE.md (template)

```
UI brief — TriNexus
Audience: plant engineer, O&M manager, CFO. Each screen answers ONE decision (stated in the page header).
Style: industrial control-room clarity (ISA-101 spirit). Light neutral background, white panels, hairline borders,
one control-room blue accent, colour ONLY for state (ok / watch / alarm) and loss meaning
(controllable / uncontrollable / residual / recovered). Status colour always with icon + label.
Type: IBM Plex Sans (UI), IBM Plex Mono (ids, codes, table numbers). Tabular numbers in tables.
Never: gradients, glassmorphism, emoji, purple, decorative illustrations on data pages, cards with no decision.
Charts: ECharts only; legend for ≥2 series; units in subtitles; thin marks; recessive grid.
Every number shows unit + provenance (measured / modeled / synthetic / derived).
No arithmetic on metrics in React — the API sends display-ready values.
```

## 7. Review checklist (use on every screenshot)
- Can a judge tell in 3 seconds what decision this page supports?
- Is colour used only for state or meaning? Any status colour without an icon/label?
- Do long numbers fit without wrapping at 1280 px?
- Units on every number and axis? Provenance visible?
- Empty, loading and error states designed (not blank)?
- Same component looks the same on every page?
- Anything that looks like a stock template (gradient hero, emoji, generic illustration)? Remove it.

---

## Sources
- [R1] Emerson, "Up Your Productivity and Safety with High Performance HMI Design" (white paper) — https://www.emersonautomationexperts.com/2023/discrete-automation/up-your-productivity-and-safety-with-high-performance-hmi-design-white-paper/
- [R2] Open Exam Prep, "HMI & High-Performance Graphics Design (ISA-101)" — https://open-exam-prep.com/study-guides/isa-cap/system-design-hmi-alarms-enterprise/hmi-design-isa101
- [R3] ClaudeLog, "What is the Frontend Design Skill in Claude Code" — https://claudelog.com/faqs/what-is-frontend-design-skill-in-claude-code/ ; source in github.com/anthropics/claude-code (plugins/frontend-design)
- [R4] ClaudeLog, "Playwright MCP" — https://claudelog.com/claude-code-mcps/playwright-mcp
- [R5] Context7 MCP (Upstash) — https://upstash.com/blog/context7-mcp.md ; https://mcpservers.org/remote-mcp-servers/context7
- [R6] shadcn/ui, "MCP Server" docs — https://ui.shadcn.com/docs/mcp
- [R7] Figma Help Center, MCP server guide — https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Dev-Mode-MCP-Server ; https://github.com/figma/mcp-server-guide
- [R8] 21st.dev Magic — https://21st.dev/magic (free tier: daily allowance; see https://21st.dev/pricing)
- [R9] Refero MCP docs — https://doc.refero.design/mcp/getting-started
- [R10] shadcn.io MCP for Claude Code — https://www.shadcn.io/mcp/claude-code
- [R11] Vercel, "Vercel acquires Tremor" — https://vercel.com/blog/vercel-acquires-tremor ; https://tremor.so/
