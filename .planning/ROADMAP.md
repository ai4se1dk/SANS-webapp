# Roadmap: SANS-webapp MCP State Synchronization

## Overview

This roadmap delivers bidirectional state synchronization between Claude's MCP tools and the Streamlit UI. We start with infrastructure (SessionStateBridge extension), then implement core parameter/model sync, and finish with advanced tools (fit, polydispersity, structure factors). When complete, any state change made by Claude will be immediately visible to the user.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Infrastructure** - Extend SessionStateBridge and wire up auto-rerun
- [ ] **Phase 2: Core Sync** - Model and parameter tools update UI widgets
- [ ] **Phase 3: Advanced Sync** - Fit, polydispersity, and structure factor tools

## Phase Details

### Phase 1: Infrastructure
**Goal**: MCP tools have a clean API to sync state and trigger UI refresh
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. SessionStateBridge has methods to set individual parameter widgets (value, min, max, vary)
  2. SessionStateBridge has methods to clear all parameter widgets for model changes
  3. All state-modifying MCP tools use bridge methods (no direct st.session_state access in tools)
  4. After any state-modifying tool executes, the UI automatically reruns
**Plans**: 1 plan

Plans:
- [ ] 01-01-PLAN.md — Extend SessionStateBridge and refactor MCP tools to use bridge

### Phase 2: Core Sync
**Goal**: Users see model and parameter changes immediately when Claude modifies them
**Depends on**: Phase 1
**Requirements**: SYNC-01, SYNC-02, SYNC-03
**Success Criteria** (what must be TRUE):
  1. When Claude calls `set-model`, the model selector and parameter table update to show new model
  2. When Claude calls `set-parameter`, the corresponding value/min/max/vary widgets reflect the change
  3. When Claude calls `set-multiple-parameters`, all affected widgets update atomically
  4. No stale values visible after any parameter tool call
**Plans**: TBD

Plans:
- [ ] 02-01: [TBD - defined during plan-phase]

### Phase 3: Advanced Sync
**Goal**: Fit results, polydispersity, and structure factor tools sync to UI
**Depends on**: Phase 2
**Requirements**: SYNC-04, SYNC-05, SYNC-06
**Success Criteria** (what must be TRUE):
  1. When Claude calls `run-fit`, fit results display updates with chi-squared and parameters
  2. When Claude calls `run-fit`, the plot refreshes with the fitted curve
  3. When Claude calls `enable-polydispersity`, PD configuration widgets appear with correct values
  4. When Claude calls `set-structure-factor` or `remove-structure-factor`, model configuration UI updates
**Plans**: TBD

Plans:
- [ ] 03-01: [TBD - defined during plan-phase]

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure | 0/1 | Planned | - |
| 2. Core Sync | 0/? | Not started | - |
| 3. Advanced Sync | 0/? | Not started | - |

---
*Roadmap created: 2026-02-05*
*Phase 1 planned: 2026-02-05*
