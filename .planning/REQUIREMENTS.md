# Requirements: SANS-webapp MCP Integration

**Defined:** 2026-02-05
**Core Value:** AI-driven state changes must be immediately visible in the UI

## v1 Requirements

Requirements for completing MCP state synchronization. Each maps to roadmap phases.

### State Synchronization

- [ ] **SYNC-01**: `set-model` tool clears old parameter widgets and updates model flags
- [ ] **SYNC-02**: `set-parameter` tool updates corresponding UI widget state (`value_`, `min_`, `max_`, `vary_` keys)
- [ ] **SYNC-03**: `set-multiple-parameters` tool updates all affected UI widgets atomically
- [ ] **SYNC-04**: `run-fit` tool updates fit result display and triggers plot refresh
- [ ] **SYNC-05**: `enable-polydispersity` tool updates PD widget state
- [ ] **SYNC-06**: Structure factor tools (`set-structure-factor`, `remove-structure-factor`) update model configuration

### Infrastructure

- [ ] **INFRA-01**: Extend SessionStateBridge with parameter widget setters
- [ ] **INFRA-02**: All state-modifying tools use bridge methods instead of direct state access
- [ ] **INFRA-03**: Automatic UI rerun after tool execution completes

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Robustness

- **ROBUST-01**: Validate parameter values before applying (bounds checking, NaN handling)
- **ROBUST-02**: Rollback capability if tool execution fails mid-operation
- **ROBUST-03**: Error recovery with clear user feedback

### Testing

- **TEST-01**: End-to-end tests for tool -> UI sync
- **TEST-02**: Integration tests for multi-tool sequences

## Out of Scope

| Feature | Reason |
|---------|--------|
| Persistent fit history | Session-only scope for this milestone |
| Async/background fitting | Fitting is fast enough for interactive use |
| Multi-user support | Single-user desktop application |
| Real-time collaboration | Not needed for solo analysis workflow |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| SYNC-01 | Phase 2 | Pending |
| SYNC-02 | Phase 2 | Pending |
| SYNC-03 | Phase 2 | Pending |
| SYNC-04 | Phase 3 | Pending |
| SYNC-05 | Phase 3 | Pending |
| SYNC-06 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0

---
*Requirements defined: 2026-02-05*
*Last updated: 2026-02-05 after roadmap creation*
