# Enterprise MCP Agent System

AI-powered assistant for project managers connecting to enterprise tools via Model Context Protocol (MCP) servers, orchestrated with LangGraph and Claude.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![React](https://img.shields.io/badge/React-18-61DAFB)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

A multi-agent orchestration system that connects to enterprise tools (GitHub, Jira, Calendar) through the Model Context Protocol. Features human-in-the-loop approvals for write operations, NeMo Guardrails for safety, and a comprehensive 30-task evaluation suite.

## Key Features

- **Multi-Tool Orchestration** -- Agent plans and executes across GitHub, Jira, and Calendar (26 tools)
- **Human-in-the-Loop** -- Write operations require approval via LangGraph interrupt
- **Streaming Responses** -- Real-time token streaming via WebSocket
- **Sub-Agents** -- Research and Triage agents for complex multi-step tasks
- **Guardrails** -- NeMo Guardrails + Presidio PII detection/redaction
- **Cost Tracking** -- Per-message token counting, session cost accumulator
- **Evaluation Suite** -- 30 tasks across 6 categories with automated scoring (>85% target)

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────┐
│   React UI  │────>│  FastAPI +   │────>│   LangGraph Agent   │
│  (Vite/TS)  │<────│  WebSocket   │<────│  (Claude-powered)   │
└─────────────┘     └──────────────┘     └──────────┬──────────┘
                           │                         │
                    ┌──────┴──────┐          ┌──────┴──────┐
                    │ PostgreSQL  │          │  MCP Servers │
                    │   + Redis   │          │  (3 servers) │
                    └─────────────┘          └─────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.12, SQLAlchemy (async), WebSocket |
| Agent | LangGraph, Claude (Sonnet/Haiku), AsyncPostgresSaver |
| MCP Servers | FastMCP (Python), JSON fixtures |
| Safety | NeMo Guardrails, Presidio PII detection |
| Infrastructure | Docker Compose, PostgreSQL 16, Redis 7 |
| Observability | LangSmith tracing, cost tracking |
| Evaluation | 30-task eval suite (>85% target) |

## Quick Start

```bash
cd enterprise-mcp-agent
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
make dev
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

See [enterprise-mcp-agent/README.md](enterprise-mcp-agent/README.md) for full documentation.

## License

MIT
