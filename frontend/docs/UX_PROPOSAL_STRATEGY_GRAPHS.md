# UX Proposal: Strategy Graphs Unified Visualization

**Document:** UX architecture for graph-based strategy clarity  
**Scope:** UI only — backend separation unchanged  
**Tone:** Professional trading system, dense but readable

---

## 1. High-Level Unified Visualization Concept

### Core Mental Model (Conceptual — not literal UI)

The ASCII below illustrates *relationships*, not final pixels. **UI must not look like documentation.**

```
  [telegram_listener]  [fetch_ps3838_fixtures]  [fetch_ps3838_odds]
  timer 60s            timer 60s                timer 60s
        \                     |                        /
         \                    v                       /
          \___________  State Cache  _______________/
                                    |
                                    v
                    ┌───────────────────────────────┐
                    │     DECISION GRAPH            │  ← dominant, critical nucleus
                    │     (hot path)                │
                    └───────────────────────────────┘
```

### UI Principles (Terminal-Grade)

| Principle | Implementation |
|-----------|----------------|
| **More air** | Generous padding between elements; no cramming. |
| **Minimalism** | No outer box wrapping the diagram. Surfaces implied, not drawn. |
| **Fewer borders** | No thick frames. Hairlines only when separation is essential. |
| **Implicit hierarchy** | Decision Graph dominates by weight, contrast, width — not boxes. |
| **State Cache = infrastructure** | Never looks like a graph node. Background tint, centered text, no border, no shadow. |

### Key Invariants to Communicate

| Concept | Internal Name | UI Label | User Takeaway |
|---------|---------------|----------|---------------|
| Support Graphs | `support_graphs` | **External Data Modules** | Data providers. Run on triggers. Write to cache. |
| State Cache | — | State Cache | Shared data layer. Bus. Not a node. |
| Decision Graph | `decision_graph` | Decision Graph | Critical nucleus. Reads cache. Emits intents. |
| Data flow | — | — | Unidirectional: Providers → Cache → Decision |

---

## 2. UX Implementation Options

### Option A: Unified Meta-Canvas

**Description:** Single React Flow canvas showing a simplified architecture diagram. Flow Summary above. External Data Modules as compact pills; State Cache as infrastructure bar (not a node); Decision Graph as dominant block. Edges labeled by flow type.

**Pros:**
- One place to see everything
- Clear spatial relationship
- Can double-click a group to drill into full graph

**Cons:**
- Meta-canvas is a different abstraction than the actual graphs
- Risk of visual overload if many Support Graphs
- Requires custom React Flow node type for "group/subgraph"

**Best for:** Strategies with 2–4 Support Graphs.

---

### Option B: Contextual Relationship Diagram Above Tabs

**Description:** Flow Summary (one sentence) + compact diagram above the existing tabbed content. No React Flow. Shows:
- Flow Summary: "N External Data Modules write to State Cache. Decision Graph reads cache and emits execution intents."
- Row 1: External Data Modules as floating pills, each with trigger hint (secondary weight)
- Row 2: State Cache as infrastructure bar (tint, no border, full-width)
- Row 3: Decision Graph as dominant block (more weight, contrast, width)
- Arrows: dashed, muted

**Pros:**
- Lightweight, always visible
- No change to existing graph editors
- Easy to implement (SVG or simple div layout)

**Cons:**
- Conceptual only; not interactive
- Doesn't show internal node structure

**Best for:** Quick orientation. Minimal implementation cost.

---

### Option C: Hybrid with Collapsible Relationship Panel

**Description:** 
- Collapsible panel at top of Graph tab: "Data Flow"
- When expanded: Flow Summary + Option B diagram (pills, infrastructure bar, dominant block) + legend
- When collapsed: Flow Summary only (one sentence)
- Below: existing Decision Graph (primary) + External Data Modules (stacked, secondary)

**Pros:**
- Balances context with density
- Power users can collapse; new users expand
- Preserves current graph editing UX

**Cons:**
- Extra UI element to maintain

**Best for:** Production default. Recommended.

---

## 3. Flow Summary (Cognitive Load Reduction)

**Add a one-line textual summary above the diagram.** Ultra clear. No marketing.

> *3 External Data Modules write to State Cache. Decision Graph reads cache and emits execution intents.*

- Dynamic: Replace `3` with actual count. If 0: *Decision Graph reads cache and emits execution intents.*
- Single sentence. No bullets. No jargon beyond "State Cache" and "execution intents".
- Typography: `text-body` or `text-body-lg`, `text-muted-foreground`. Slightly dimmer than diagram labels.
- Position: Directly above the diagram, with a small gap (e.g. 8–12px).

This reduces cognitive load before the user parses the visual.

---

## 4. User Understanding Goals & Visual Metaphors

### What the User Should Understand in 5 Seconds

1. **Flow Summary** delivers the mental model in one sentence.
2. **External Data Modules** (Data Providers) feed a shared layer.
3. **Decision Graph** is the critical nucleus — dominant visually and conceptually.

### Visual Metaphors to Use

| Concept | Metaphor | Rationale |
|---------|----------|-----------|
| State Cache | **Data bus** — infrastructure, not a node | Shared medium; many producers, one consumer. |
| External Data Modules | Floating pills / secondary elements | Data providers; explicitly secondary. |
| Decision Graph | **Dominant block** — nucleus | Critical path. More weight, contrast, width. |
| Edges (data) | Dotted or muted | Different from execution edges (solid). |

### Visual Metaphors to Avoid

| Avoid | Reason |
|-------|--------|
| Funnels, funnels charts | Implies aggregation; misrepresents flow. |
| Circular/cycle diagrams | Suggests feedback loops; Decision Graph is read-only on cache. |
| Generic "cloud" for State Cache | Vague; "cache" is concrete. |
| Emojis, playful icons | Trading system tone. |
| Thick bordered "cards" | Boxitis; use subtle separation. |
| Literal ASCII diagram aesthetic | Feels like docs; not terminal-grade UI. |

### State Cache: Infrastructure, Not a Node

**Critical:** State Cache must not feel like a graph element. It is infrastructure.

| Property | Treatment |
|----------|-----------|
| **Background** | Slight tint (muted surface, 1–2% different from page). Full-width or near-full. |
| **Text** | Centered. "State Cache" — primary. Subtitle optional: "L1/L2 · parsed_tips, fixtures, odds". |
| **Border** | None. |
| **Shadow** | None or imperceptible. |
| **Shape** | Horizontal bar. Not a pill, not a box. Like a bus. |
| **Visual weight** | Lighter than Decision Graph; heavier than air. Implicit, not emphatic. |

---

## 5. Concrete UI Structure Proposal

### Layout Blocks (Graph Tab)

**No outer box.** Surfaces implied. Maximum air.

```
[▼] Data Flow                              (collapsible, default: expanded)

3 External Data Modules write to State Cache. Decision Graph reads cache and emits execution intents.

    [telegram_listener]   [fetch_ps3838_fixtures]   [fetch_ps3838_odds]
    timer 60s             timer 60s                 timer 60s
          \                      |                        /
           \                     v                       /
            \__________   State Cache   _______________/
                                      |
                                      v
    ┌─────────────────────────────────────────────────────────────────────┐
    │                     Decision Graph                                  │  ← full width, dominant
    └─────────────────────────────────────────────────────────────────────┘

    dashed = data flow

────────────────────────────────────────────────────────────────────────────

Decision Graph
[React Flow canvas - existing GraphBuilder]

External Data Modules
  telegram_listener  [expand/collapse]
  [React Flow canvas]
  fetch_ps3838_fixtures  [expand/collapse]
  [React Flow canvas - collapsed by default]
```

### Visual Hierarchy — Decision Graph as Nucleus

| Element | Weight | Treatment |
|---------|--------|-----------|
| **Flow Summary** | Light | text-body, text-muted-foreground. One sentence. |
| **External Data Modules (pills)** | Secondary | text-body, font-medium. Muted contrast. Compact. |
| **Trigger hints** | Tertiary | text-caption, foreground-helper |
| **State Cache bar** | Infrastructure | Full-width tint. No border. Centered text. text-body, muted. |
| **Decision Graph (in diagram)** | **Dominant** | text-h2 or text-body-lg, font-semibold. Higher contrast. More width. Spatial dominance. |
| Graph canvases | Primary | Existing GraphBuilder, no change |
| Legend | Caption | text-caption, 1 line |

**Hierarchy rule:** Decision Graph must have more typographic weight, more contrast, and more visual width than External Data Modules. Support modules feel secondary; Decision Graph feels like the nucleus.

### Minimal Diagram Specification (React Flow Compatible — Option A only)

If implementing Option A (meta-canvas) with React Flow:

**Node types:**
- `architecture-module`: Support Graph as compact pill. Data: `{ name, trigger }`.
- `architecture-cache`: State Cache bar. Single node, wide.
- `architecture-decision`: Decision Graph placeholder. Single node.

**Edge types:**
- `data-write`: Support → Cache. Dashed, muted. Optional label "writes".
- `data-read`: Cache → Decision. Dashed, muted. Optional label "reads".
- No `trigger` edges in diagram (trigger is metadata on the node).

**Positioning:**
- Support modules: Top row, horizontal spread.
- State Cache: Center, below Support.
- Decision Graph: Below Cache.
- Layout: Vertical flow, no overlaps.

**Alternative (recommended for Option B/C):** CSS flex/grid + SVG arrows. Simpler, no zoom/pan. Sufficient. Avoids literal "diagram nodes" — use floating pills, infrastructure bar, dominant block.

---

## 6. Edge & Label Conventions

| Edge Type | Line | Label | When to Show |
|-----------|------|-------|--------------|
| **Data (write)** | Dashed, 1px, muted | "writes" or none | Support → Cache |
| **Data (read)** | Dashed, 1px, muted | "reads" or none | Cache → Decision |
| **Execution** | Solid, 1px | "next", "true", "false" | Inside a graph (existing) |
| **Trigger** | Not an edge | Shown on node: "timer 60s" | Metadata on Support node |

**Recommendation:** Omit edge labels in the architecture diagram if the direction + dashed style is clear. Add a one-line legend: "Dashed = data flow".

---

## 7. Implementation Priority

1. **Phase 1 (Low effort):** Option B or C — Flow Summary + contextual diagram above existing content. No React Flow changes.
2. **Phase 2 (If needed):** Collapsible panel, Support Graph accordions.
3. **Phase 3 (Optional):** Option A — Unified meta-canvas with drill-down.

---

## 8. Acceptance Criteria

- [ ] Flow Summary visible above diagram. One sentence. Dynamic count.
- [ ] User understands relationship External Data Modules → State Cache → Decision Graph within 5 seconds.
- [ ] No thick borders, no outer box, no boxitis. Surfaces implied.
- [ ] State Cache reads as infrastructure (tint, no border, no shadow) — not a graph node.
- [ ] Decision Graph has clear visual dominance (weight, contrast, width).
- [ ] External Data Modules feel secondary (pills, muted).
- [ ] Trigger type visible per module.
- [ ] Existing graph editors unchanged; diagram is additive.
- [ ] Works in dark mode with existing palette (foreground, muted-foreground, foreground-helper).
