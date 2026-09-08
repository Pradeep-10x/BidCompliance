---
version: alpha
name: "PRAMAAN"
description: "An evidence-first procurement compliance workspace for review officers."
colors:
  background: "oklch(1 0 0)"
  foreground: "oklch(0.145 0 0)"
  primary: "oklch(0.205 0 0)"
  primary-foreground: "oklch(0.985 0 0)"
  muted: "oklch(0.97 0 0)"
  muted-foreground: "oklch(0.556 0 0)"
  border: "oklch(0.922 0 0)"
  destructive: "oklch(0.577 0.245 27.325)"
  focus-ring: "oklch(0.708 0 0)"
typography:
  sans:
    fontFamily: "Geist Variable, sans-serif"
  heading:
    fontFamily: "Geist Variable, sans-serif"
rounded:
  DEFAULT: "0.625rem"
  card: "0.75rem"
spacing:
  control-gap: "0.375rem"
  card-padding: "1rem"
  page-gutter: "1rem"
components:
  button:
    backgroundColor: "oklch(0.205 0 0)"
    textColor: "oklch(0.985 0 0)"
    rounded: "0.625rem"
    height: "2rem"
  card:
    backgroundColor: "oklch(1 0 0)"
    textColor: "oklch(0.145 0 0)"
    rounded: "0.75rem"
    padding: "1rem"
  sidebar:
    backgroundColor: "oklch(0.985 0 0)"
    textColor: "oklch(0.145 0 0)"
---

# PRAMAAN Design System

## Overview

### Creative North Star

PRAMAAN should feel like an officer's evidence register translated into a calm
digital control room: compact, traceable, and visibly serious without imitating
paper forms. Evidence, status, and the next review action carry the hierarchy.

### Product context and register

- **Audience and primary job:** Indian public-procurement review officers who
  compare bidder evidence, investigate risk, and record accountable decisions.
- **Target market and evidence:** India, based on the PRAMAAN tender, Udyam,
  GST, MCA, BIS, DPIIT, and debarment domain implemented by the API and ML layer.
- **Locale and language policy:** The current UI is English (`en`). Domain codes
  and Indian number/currency conventions remain intact; future translations must
  not translate identifiers or evidence values.
- **Usage scene:** Desktop-first, repeated operational use with dense tables and
  time-sensitive review queues; narrow screens retain every action through the
  established responsive sidebar and table overflow patterns.
- **Register:** Product/admin throughout authenticated routes.
- **Memorable signature:** Evidence-backed status—scores, risk, sources, and
  audit references remain visually close to every recommendation.
- **Restraint:** Authentication, forms, tables, and officer decisions use familiar
  controls and quiet surfaces. Decoration never competes with evidence.
- **Anti-references:** Consumer-finance gamification, neon AI dashboards, and
  ceremonial government motifs; each would weaken review clarity or trust.
- **Token ownership/runtime mapping:** Existing Tailwind v4 variables in
  `frontend/src/index.css` are canonical. This file mirrors their accepted
  semantic values; shared primitives consume the mapped utilities.

## Colors

The palette is deliberately near-neutral. `primary` carries principal actions;
`destructive` is reserved for irreversible or disqualifying actions. Muted and
border tones establish hierarchy without extra shadows. Focus always uses the
shared `focus-ring` value. Dark mode remaps the same semantic roles in
`frontend/src/index.css` rather than changing their meaning.

## Typography

Geist Variable owns headings, body copy, controls, and numeric data. Hierarchy
comes from size and weight rather than decorative type. Identifiers, percentages,
and timestamps use tabular numerals where the component already supports them.

## Layout

Authenticated screens use the canonical sidebar shell, a compact 48px header,
16px page gutters that expand at larger breakpoints, and card/table regions that
own their overflow. The login route remains centered and narrow. Async content
must not change the position of primary controls.

## Elevation & Depth

Static surfaces use tonal contrast and one-pixel rings. Overlays may use the
existing shared primitive shadows; ordinary cards do not add decorative depth.

## Shapes

Controls use the shared 10px radius family, cards use 12px, and dense controls
may use the smaller derived runtime radius. Pills are limited to status badges.

## Components

### Foundational visual states

Shared components own hover, focus-visible, active, disabled, invalid, and dark
states. Busy actions retain their dimensions and block duplicate submission.
Status is always expressed with text or an icon in addition to color.

### Buttons and actions

Use the shared `Button`. Default is the primary safe action, outline/ghost are
secondary utilities, and destructive is reserved for consequential actions.
Labels use explicit verbs such as “Log out”, “Accept”, or “Run assessment”.

### Navigation and data display

The sidebar owns primary navigation. Tables use the shared table components and
keep risk/status values readable at a glance. Charts supplement, never replace,
textual totals and statuses.

### Forms and overlays

Fields use shared Input, Label, Form, Select, Dialog, and Drawer primitives.
Validation is inline and actionable. Product forms own validation messaging,
prevent duplicate submission, and keep entered non-sensitive values on failure.

### Iconography

Lucide is canonical, using outline icons at the shared component size. Important
actions retain text labels; icons do not carry compliance meaning alone.

### Motion

Motion communicates state using the existing short transitions. Reduced-motion
preferences remove nonessential transforms and preserve immediate feedback.

### Content and data visualization

Copy uses plain officer-facing verbs and names the document, bidder, rule, or
decision involved. Scores show units, audit records retain actor and timestamp,
and error copy explains the next recovery action without exposing raw internals.

## Do's and Don'ts

- **Do:** Keep evidence provenance and officer actions explicit and adjacent.
- **Do:** Reuse semantic tokens and shared primitives across every route.
- **Don't:** imply that mock verification is an official registry response.
- **Don't:** add decorative color, animation, or elevation that obscures risk.
