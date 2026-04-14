# Enterprise MCP Agent System

AI-powered assistant for project managers connecting to enterprise tools via Model Context Protocol (MCP) servers, orchestrated with LangGraph and Claude.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────┐
│   React UI  │────▶│  FastAPI +   │────▶│   LangGraph Agent   │
│  (Vite/TS)  │◀────│  WebSocket   │◀────│  (Claude-powered)   │
└─────────────┘     └──────────────┘     └──────────┬──────────┘
                           │                         │
                    ┌──────┴──────┐          ┌──────┴──────┐
                    │ PostgreSQL  │          │  MCP Servers │
                    │   + Redis   │          │             │
                    └─────────────┘          ├─ GitHub     │
                                             ├─ Project Mgmt│
                                             └─ Calendar   │
                                             └─────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.12, SQLAlchemy (async), WebSocket |
| Agent | LangGraph, Claude (Sonnet/Haiku), AsyncPostgresSaver |
| MCP Servers | FastMCP (Python), JSON fixtures |
| Safety | NeMo Guardrails, Presidio PII detection |
| Infrastructure | Docker Compose, PostgreSQL 16, Redis 7 |
| Observability | LangSmith tracing, cost tracking |
| Evaluation | 30-task eval suite (>85% target) |

## Features

- **Multi-tool orchestration**: Agent plans and executes across GitHub, Jira, and Calendar
- **Human-in-the-loop**: Write operations require approval via LangGraph interrupt
- **Streaming responses**: Real-time token streaming via WebSocket
- **Sub-agents**: Research and Triage agents for complex multi-step tasks
- **Guardrails**: Input validation, PII detection/redaction, topic boundaries
- **Cost tracking**: Per-message token counting, session cost accumulator
- **Evaluation suite**: 30 tasks across 6 categories with automated scoring

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Python 3.12+
- Anthropic API key

### Setup

1. **Clone and configure:**
   ```bash
   cd enterprise-mcp-agent
   cp .env.example .env
   # Edit .env and set ANTHROPIC_API_KEY
   ```

2. **Start all services:**
   ```bash
   make dev
   ```

3. **Access the app:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Demo Accounts

| Email | Password | Role |
|-------|----------|------|
| admin@acme.com | admin123 | Admin |
| user@acme.com | user123 | User |

## Project Structure

```
enterprise-mcp-agent/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── agent/           # LangGraph agent (graph, nodes, subagents)
│   │   ├── api/             # REST + WebSocket endpoints
│   │   ├── guardrails/      # NeMo Guardrails + Presidio PII
│   │   ├── mcp/             # MCP client manager + registry
│   │   ├── models/          # SQLAlchemy ORM + Pydantic schemas
│   │   ├── services/        # Business logic layer
│   │   ├── middleware/      # Auth, logging, error handling
│   │   ├── db/              # Database + Redis connections
│   │   └── observability/   # LangSmith tracing + metrics
│   └── tests/               # Unit, integration, eval suite
├── mcp_servers/             # 3 MCP servers with mock data
│   ├── github_server/       # 10 tools (PRs, issues, commits, CI)
│   ├── project_management_server/  # 11 tools (sprints, tickets, velocity)
│   ├── calendar_server/     # 5 tools (meetings, availability, notes)
│   └── shared/              # Base server, error simulator, types
├── frontend/                # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── components/      # Chat, sidebar, approvals, common
│       ├── stores/          # Zustand state management
│       ├── hooks/           # WebSocket, auto-scroll, streaming
│       ├── services/        # API client, WebSocket service
│       ├── pages/           # Chat, Approvals, History, Settings
│       └── types/           # TypeScript type definitions
└── docker/                  # Docker Compose + DB init
```

## MCP Tools (26 total)

### GitHub Server (10 tools)
- `list_pull_requests`, `get_pr_details`, `get_pr_diff`
- `list_issues`, `get_issue_details`
- `list_commits`, `get_ci_status`
- `create_issue` ✏️, `add_comment` ✏️, `add_labels` ✏️

### Project Management Server (11 tools)
- `list_sprints`, `get_sprint_details`
- `list_tickets`, `get_ticket_details`
- `get_velocity`, `get_backlog`, `get_assignments`
- `update_ticket_priority` ✏️, `update_ticket_assignee` ✏️, `update_ticket_labels` ✏️, `move_ticket` ✏️

### Calendar Server (5 tools, read-only)
- `list_meetings`, `get_meeting_details`, `get_attendees`
- `check_availability`, `get_meeting_notes`

✏️ = Write operation (requires human approval)

## Agent Graph

```
START → guardrails_input → router
                              ├── needs_tools → planner → tool_executor
                              │                              ├── write? → approval_gate → INTERRUPT
                              │                              └── read → synthesizer
                              ├── complex → delegate (subagent) → synthesizer
                              └── direct → synthesizer
                                              → guardrails_output → END

Error path: error_handler → retry (2x) | fallback → synthesizer
```

## Development

```bash
make dev          # Start all services (dev mode with hot reload)
make test         # Run pytest suite
make eval         # Run 30-task evaluation suite
make lint         # Run ruff + eslint
make clean        # Stop services and remove volumes
make db-migrate   # Run Alembic migrations
make mcp-test     # Test MCP servers individually
```

## Evaluation Suite

30 tasks across 6 categories targeting >85% completion:

| Category | Count | Scoring | Examples |
|----------|-------|---------|----------|
| Status Reports | 5 | Rubric | "What happened over the weekend?" |
| Ticket Triage | 5 | Exact match | "Triage the unassigned bugs" |
| Meeting Prep | 5 | Rubric | "Prepare me for sprint planning" |
| Cross-Tool Queries | 5 | Factual | "Why is the payment feature delayed?" |
| Error Recovery | 5 | Pass/fail | Tool timeout, rate limit scenarios |
| Guardrail Enforcement | 5 | Pass/fail | PII, off-topic, prompt injection |

## License

MIT
