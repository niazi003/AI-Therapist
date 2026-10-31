# Personal AI Wellbeing Companion

A mental wellbeing companion application using AI to provide supportive conversations with PostgreSQL-backed memory. Built with FastAPI, React, LangGraph, and Groq.

## ⚠️ Important Disclaimer

This is an **educational software project**, not a licensed therapy or mental health service. It does not:
- Provide clinical mental health treatment
- Diagnose mental health conditions
- Replace professional medical care

If you're experiencing a mental health crisis, contact your local emergency services or visit the nearest emergency department. Users can optionally request an approximate country estimate through ipwho.is via the backend; the user's public IP address is forwarded to that service, and the user confirms the result before the country is stored locally and sent with chat messages. The urgent workflow uses the Koko helplines API for a confirmed or explicitly stated country when available, and links to [Find A Helpline](https://findahelpline.com/) if the lookup is unavailable. The app does not guess emergency numbers.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│                    http://localhost:5173                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                            │
│                    http://localhost:8000                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ Safety Review│  │   Consent    │  │   User Management    │ │
│  │   (Groq)     │  │  Management  │  │                      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
  ┌─────────────────────┐ ┌────────────┐ ┌─────────────────┐
  │   LangGraph         │ │ PostgreSQL │ │     Groq AI     │
  │  Therapy Graph      │ │  Database  │ │   (Inference)   │
  │  (Multi-Agent +     │ │            │ │                 │
  │   Memory Store)     │ │            │ │                 │
  └─────────────────────┘ └────────────┘ └─────────────────┘
```

### LangGraph Multi-Agent Therapy Graph

```
┌──────────────────────────────────────────────────────────────────┐
│                     LangGraph Therapy Graph                      │
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐   │
│  │   Intake    │───▶│   Active     │───▶│   Memory          │   │
│  │  Evaluator  │    │  Therapist   │    │  Consolidation    │   │
│  │  (safety)   │    │  (response)  │    │  (summarization)  │   │
│  └──────┬──────┘    └──────────────┘    └───────────────────┘   │
│         ├── URGENT ─────────▶ Emergency Referral                 │
│         ├── FOLLOW-UP ──────▶ Clarifying question                │
│         ├── REFERRAL ───────▶ Professional Referral               │
│         └── REVIEW ERROR ───▶ Safe unavailable response           │
│                                                                  │
│  State: TherapyState (TypedDict)                                │
│  Checkpointer: AsyncPostgresSaver (short-term per-thread)        │
│  Store: AsyncPostgresStore (long-term cross-thread)              │
└──────────────────────────────────────────────────────────────────┘
```

### Memory Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Short-term (per-thread) | LangGraph AsyncPostgresSaver | Conversation state within a session |
| Long-term (cross-thread) | LangGraph AsyncPostgresStore | Clinical profiles, session summaries, distress events, mood |

**Store Namespace Hierarchy:**
```
["patient", {user_id}, "clinical_profile"]     → goals, challenges, triggers, preferences
["patient", {user_id}, "distress_events"]      → timestamped crisis records
["patient", {user_id}, "session_summaries"]     → compressed conversation insights
["patient", {user_id}, "mood_tracker"]          → mood over time
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------| 
| Backend | Python + FastAPI | REST API, business logic |
| Frontend | React + TypeScript + Vite | User interface |
| AI Model | Groq (LLM inference) | Language model inference |
| Agent Framework | LangGraph | Multi-agent orchestration + memory |
| Database | PostgreSQL | Application data storage |
| Containers | Docker Compose | Deployment & orchestration |

---

## Prerequisites

1. **Docker & Docker Compose** - [Install Docker](https://docs.docker.com/get-docker/)
2. **Groq API Key** - Get free key at [console.groq.com](https://console.groq.com/keys)
3. **Terminal/Command Prompt** - For running commands

---

## Quick Start

### 1. Clone and Setup

```bash
cd "c:\Users\PC\Desktop\AI Therapist"
```

### 2. Configure Environment

Copy `.env.example` to `.env` and add your credentials:

```bash
# Generate a secure secret key
openssl rand -hex 32  # Use output for SECRET_KEY

# Edit .env file with your Groq API key
GROQ_API_KEY=your-groq-api-key
SECRET_KEY=your-generated-secret
```

### 3. Start All Services

```bash
# From project root
docker-compose up --build
```

This starts:
- **PostgreSQL** (port 5432)
- **Backend API** (port 8000)
- **Frontend** (port 5173)

### 4. Verify Services

Open your browser:
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/api/v1/docs

---

## Development Commands

### Backend (Python/FastAPI)

```bash
cd backend

# Install dependencies
uv sync

# Run development server
uv run uvicorn app.main:app --reload

# Run tests
uv run --extra test pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=html
```

### Frontend (React/Vite)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

### Docker

```bash
# Start all services
docker-compose up

# Stop all services (keep data)
docker-compose down

# Stop and remove volumes (delete data)
docker-compose down -v

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
```

---

## Project Structure

```
personal-wellbeing-companion/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── core/              # Configuration, security, logging
│   │   ├── db/                # Database models and sessions
│   │   ├── routers/           # API endpoints
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── services/          # Business logic
│   │   │   ├── groq_client.py         # Groq LLM client
│   │   │   ├── graph_state.py         # TypedDict/Pydantic state definitions
│   │   │   ├── graph_store.py         # LangGraph Store + namespace helpers
│   │   │   ├── langgraph_therapy.py   # Multi-agent therapy graph
│   │   │   ├── conversation_service.py # Graph invocation service
│   │   │   ├── memory_service.py      # Deprecated (replaced by LangGraph Store)
│   │   │   └── appointment_service.py # Provider bookings
│   │   └── main.py            # FastAPI application
│   ├── tests/                 # Unit and integration tests
│   ├── alembic/               # Database migrations
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/                   # React + TypeScript frontend
│   ├── src/
│   │   ├── api/               # API client
│   │   ├── components/        # Reusable UI components
│   │   ├── hooks/             # React hooks (auth, chat)
│   │   ├── pages/             # Page components
│   │   ├── types/             # TypeScript types
│   │   └── styles/            # CSS styles
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml         # Container orchestration
├── .env.example              # Environment template
└── README.md                  # This file
```

---

## API Endpoints

### Health
- `GET /api/v1/health` - Check service status (Groq, LangGraph, DB)

### Authentication
- `POST /api/v1/register` - Create account
- `POST /api/v1/login` - Login (returns JWT)
- `GET /api/v1/me` - Get current user

### Consent
- `GET /api/v1/consent` - Get user consent records
- `PUT /api/v1/consent` - Update consent
- `GET /api/v1/consent/required` - List required consents

### Chat
- `POST /api/v1/chat` - Send message to AI companion
- `GET /api/v1/chat/history` - Get conversation history

### Memory
- `GET /api/v1/memory` - Get stored profile, summary, distress, and mood memories
- `DELETE /api/v1/memory` - Delete all long-term memory and short-term conversation state
- `POST /api/v1/memory/end-conversation` - Clear short-term conversation state while retaining long-term memory

### Appointments (Simulated)
- `GET /api/v1/providers` - Search providers
- `GET /api/v1/providers/{id}/slots` - Get available slots
- `POST /api/v1/appointments` - Book appointment
- `GET /api/v1/appointments` - List appointments
- `POST /api/v1/appointments/{id}/cancel` - Cancel appointment

---

## Safety Workflow

The application uses a multi-agent safety review via LangGraph:

1. **Load Context** - Hydrate state with long-term clinical memory
2. **Intake Evaluator** - Classify message safety level
3. **Routing:**
   - **Routine** → Active Therapist → (optional Memory Consolidation) → Response
   - **Follow-up** → Ask clarifying question
   - **Professional referral** → Search for current therapist-finding resources, or recommend medical assessment for persistent physical symptoms
   - **Urgent** → Emergency Referral with crisis resources
   - **Safety review unavailable or invalid** → Stop safely; do not route to the therapist agent
4. **Memory Consolidation** - Periodic compression of conversation history into Store

The intake evaluator uses `GROQ_SAFETY_MODEL`; response generation and memory consolidation use `GROQ_CHAT_MODEL`. If the safety model is unavailable or its result is invalid, chat is paused and the user is asked to retry rather than treating the message as routine. The emergency-referral node calls the server-side `fetch_koko_helplines` tool with a validated country name. It uses Koko's `GET /crisis_helplines?country=...` endpoint; the request Origin is the configured application origin (`KOKO_API_ORIGIN`, or the first `CORS_ORIGINS` value), never a Koko-owned origin. Koko must allowlist the application's actual origin. If lookup fails or returns no resources, the response says so and links to Find A Helpline instead of inventing contact numbers. No emergency-number fallback is hardcoded.

The optional IP country estimate is requested only after the user clicks the location control, because it discloses their public IP address to ipwho.is through the backend. The user must confirm the returned country. Only the country code is stored in browser local storage and sent with chat requests; users can forget it at any time.

Therapist referrals use Groq's hosted browser-search tool to look for current public-health, regulator, or reputable directory starting points for the confirmed country. The search request is limited to the country and a generic therapist-finding topic; it does not include the user's message or conversation history. The response can link to search findings but does not verify individual clinicians, credentials, availability, or prices. If web search fails, the app falls back to general directory guidance. Provider search and booking endpoints still use clearly marked simulated data; there is no live-provider directory or booking API connected.

---

## Database Migrations

```bash
cd backend

# Create a new migration
uv run alembic revision --autogenerate -m "description"

# Run migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

---

## Testing

```bash
cd backend

# Run all tests
uv run pytest

# Run specific test file
uv run --extra test pytest tests/unit/test_langgraph.py

# Run with coverage
uv run --extra test pytest --cov=app --cov-report=term-missing
```

### Test Categories

- **Unit tests** - Test individual functions without external services
- **Safety tests** - Test safety workflow scenarios via mocked LangGraph graph
- **Integration tests** - Test API endpoints with real services

---

## Troubleshooting

### Services won't start

```bash
# Check if ports are in use
netstat -ano | findstr "5432 8000 5173"

# Check Docker status
docker-compose ps

# View error logs
docker-compose logs
```

### Database connection errors

```bash
# Wait for database to be ready
docker-compose logs app-db

# Restart backend
docker-compose restart backend
```

### 502 Bad Gateway on the frontend

A 502 means the frontend proxy could not get a response from the backend. Check
that the backend is running and inspect its startup logs:

```bash
docker-compose ps
docker-compose logs --tail=100 backend
```

Check the API directly at `http://localhost:8000/api/v1/health`. If it is
unavailable, resolve the backend startup error in the logs and restart it with
`docker-compose restart backend`.

### Groq API errors

Ensure your API key is set in `.env`:
```
GROQ_API_KEY=your-key-here
```

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | API key from console.groq.com |
| `GROQ_CHAT_MODEL` | No | Model for therapy chat (default: openai/gpt-oss-120b) |
| `GROQ_SAFETY_MODEL` | No | Model for safety review (default: openai/gpt-oss-20b) |
| `SECRET_KEY` | Yes | JWT signing key (generate secure) |
| `POSTGRES_HOST` | No | Database host (default: localhost) |
| `POSTGRES_PORT` | No | Database port (default: 5432) |
| `POSTGRES_USER` | No | Database user (default: wellbeing) |
| `POSTGRES_PASSWORD` | No | Database password |
| `DEBUG` | No | Enable debug mode |

---

## Production Deployment Notes

Before deploying for real users, you MUST:

1. **Replace development authentication** - Current is for development only
2. **Configure HTTPS** - Use a reverse proxy (Caddy, Nginx)
3. **Set secure secrets** - Never use default values
4. **Review safety workflow** - Have clinical professionals evaluate
5. **Implement backup/restore** - For PostgreSQL data
6. **Add rate limiting** - Prevent abuse
7. **Enable audit logging** - Track access for compliance
8. **Review data retention and backups** - Conversation and wellbeing memory are stored in PostgreSQL; define retention, encryption, and restore policies before real-user deployment.

---

## License

This project is for educational purposes. See LICENSE for details.