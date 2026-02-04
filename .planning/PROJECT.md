# SANS Webapp

## What This Is

A Streamlit-based web application for Small-Angle Neutron Scattering (SANS) data analysis. It provides interactive model fitting using sasmodels and AI-assisted analysis via OpenAI integration.

## Core Value

Scientists can fit SANS data to physical models and get AI-powered insights to guide their analysis.

## Requirements

### Validated

- Existing SANS data fitting with sasmodels
- Interactive parameter adjustment with polydispersity support
- AI chat assistant for analysis guidance
- Data visualization (log-log plots)
- CSV data import/export

### Active

- [ ] Fix polydispersity state inconsistency when switching models
- [ ] Fix temporary file cleanup on error

### Out of Scope

- Major feature additions (separate milestone)
- Performance optimizations (not blocking users)

## Context

Brownfield codebase with existing functionality. This milestone focuses on bug fixes identified in codebase analysis.

See: `.planning/codebase/` for full codebase analysis.

## Constraints

- **Stack**: Python/Streamlit — existing architecture must be preserved
- **Dependencies**: sasmodels, OpenAI SDK — maintain compatibility

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fix bugs before features | Stability first | — Pending |

---
*Last updated: 2026-02-04 after initialization*
