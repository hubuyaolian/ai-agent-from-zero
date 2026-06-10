# Project 11 Agent Service Ops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `project_11_agent_service_ops`, a real FastAPI-based production service and operations course for Agent systems.

**Architecture:** Keep FastAPI as a thin delivery layer over pure Python modules for auth, rate limiting, model routing, cost tracking, metrics, tracing, and smoke evaluation. Tests should exercise pure logic without external LLM calls, and API tests should be skipped when FastAPI is not installed.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Pydantic, unittest.

---

### Task 1: Scaffold Project 11

**Files:**
- Create: `project_11_agent_service_ops/README.md`
- Create: `project_11_agent_service_ops/PROJECT_PLAN.md`
- Create: `project_11_agent_service_ops/DAY26.md`
- Create: `project_11_agent_service_ops/DAY27.md`
- Create: `project_11_agent_service_ops/__init__.py`

- [ ] Add the project folder and course documents.
- [ ] Keep the project positioned as Day26-Day27.
- [ ] Explain that FastAPI is the real service layer, while tests avoid real network and model calls.

### Task 2: Implement Core Runtime Modules

**Files:**
- Create: `project_11_agent_service_ops/config.py`
- Create: `project_11_agent_service_ops/gateway/model_gateway.py`
- Create: `project_11_agent_service_ops/gateway/cost_tracker.py`
- Create: `project_11_agent_service_ops/security/auth.py`
- Create: `project_11_agent_service_ops/security/rate_limiter.py`
- Create: `project_11_agent_service_ops/observability/tracing.py`
- Create: `project_11_agent_service_ops/observability/metrics.py`
- Create: `project_11_agent_service_ops/evaluation/smoke_eval.py`

- [ ] Add dataclasses and deterministic logic for model routing, fallback, budget checks, auth, token bucket rate limiting, trace events, metrics snapshots, and smoke eval.
- [ ] Do not call real LLM providers in tests.

### Task 3: Implement FastAPI Layer

**Files:**
- Create: `project_11_agent_service_ops/api/schemas.py`
- Create: `project_11_agent_service_ops/api/routes.py`
- Create: `project_11_agent_service_ops/api/app.py`
- Create: `project_11_agent_service_ops/main.py`

- [ ] Expose `/health`, `/chat`, `/stream`, `/metrics`, and `/eval/smoke`.
- [ ] Use API Key auth and rate limit checks on protected endpoints.
- [ ] Return deterministic demo responses through the model gateway.

### Task 4: Add Tests

**Files:**
- Create: `project_11_agent_service_ops/tests/test_gateway.py`
- Create: `project_11_agent_service_ops/tests/test_security.py`
- Create: `project_11_agent_service_ops/tests/test_observability.py`
- Create: `project_11_agent_service_ops/tests/test_api_contract.py`

- [ ] Test model fallback and budget rejection.
- [ ] Test auth and rate limiting.
- [ ] Test trace and metrics recording.
- [ ] Test FastAPI contracts when FastAPI is installed; skip API tests otherwise.

### Task 5: Update Course Entrypoints

**Files:**
- Modify: `requirements.txt`
- Modify: `README.md`
- Modify: `LEARNING_PLAN.md`

- [ ] Add FastAPI and Uvicorn dependencies.
- [ ] Update total course scope to 11 projects / 27 days.
- [ ] Add project_11 commands, docs index, and structure references.

### Task 6: Verify

**Commands:**
- `conda run -n agent_env python -m unittest discover project_11_agent_service_ops/tests -v`
- `conda run -n agent_env python -m compileall project_11_agent_service_ops`
- `git diff --check -- README.md LEARNING_PLAN.md requirements.txt project_11_agent_service_ops docs/superpowers/plans`

- [ ] Report whether FastAPI-specific tests ran or were skipped due to missing dependency.
