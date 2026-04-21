# 🧠 PrepAI — AI-Powered Mock Interview Coach

> Practice interviews with AI interviewers that give specific, phrase-level feedback on every answer. Not generic advice — actionable insights that cite what you actually said.

[![Backend CI](https://github.com/your-org/prepai/actions/workflows/backend.yml/badge.svg)](https://github.com/your-org/prepai/actions/workflows/backend.yml)
[![Frontend CI](https://github.com/your-org/prepai/actions/workflows/frontend.yml/badge.svg)](https://github.com/your-org/prepai/actions/workflows/frontend.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                 │
│  Next.js 14 (App Router) · React 18 · Zustand · Socket.IO Client  │
│  Tailwind CSS · Recharts · Supabase Auth UI                        │
│  Hosted on: Vercel (free tier)                                     │
├─────────────────────────────────────────────────────────────────────┤
│                        GATEWAY LAYER                                │
│  FastAPI (Python 3.11) · Modular Monolith                          │
│  JWT Auth (Supabase) · Rate Limiting (Redis)                       │
│  Socket.IO (python-socketio) · Request ID Middleware               │
│  Hosted on: Railway (free tier)                                    │
├─────────────────────────────────────────────────────────────────────┤
│                       SERVICES LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Interview     │  │ Celery       │  │ WebSocket    │             │
│  │ Engine        │  │ Workers      │  │ Hub          │             │
│  │ (Adaptive Q)  │  │ (Async Eval) │  │ (Real-time)  │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
├─────────┼──────────────────┼──────────────────┼─────────────────────┤
│         │          AI LAYER│                  │                     │
│  ┌──────▼──────────────────▼──────────────────▼───────┐            │
│  │  LiteLLM Abstraction Layer                         │            │
│  │  Primary: Claude claude-sonnet-4-20250514 (Anthropic)              │            │
│  │  Fallback: GPT-4o-mini (OpenAI)                    │            │
│  │  Guardrails: Anti-generic validation + retry        │            │
│  └────────────────────────────────────────────────────┘            │
├─────────────────────────────────────────────────────────────────────┤
│                        DATA LAYER                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐    │
│  │ PostgreSQL  │  │ MongoDB    │  │ Redis      │  │ Supabase │    │
│  │ (Supabase)  │  │ (Atlas)    │  │ (Upstash)  │  │ Storage  │    │
│  │ Users,      │  │ Interview  │  │ Rate Limit │  │ Files    │    │
│  │ Interviews, │  │ Transcripts│  │ Sessions   │  │ Resumes  │    │
│  │ Scores      │  │ Full Turns │  │ Cost Track │  │          │    │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose | Free Tier |
|-------|-----------|---------|-----------|
| Frontend | Next.js 14, React 18, TypeScript | App Router, SSR | Vercel: Unlimited hobby |
| State | Zustand | Client state management | OSS |
| Styling | Tailwind CSS | Utility-first CSS | OSS |
| Charts | Recharts | Score visualization | OSS |
| Backend | FastAPI (Python 3.11) | REST API + WebSocket | Railway: $5/mo credit |
| Auth | Supabase Auth | JWT, Google OAuth | 50k MAU |
| Primary DB | PostgreSQL (Supabase) | Users, interviews, scores | 500MB |
| Transcript DB | MongoDB Atlas | Full interview transcripts | 512MB |
| Cache | Redis (Upstash) | Rate limiting, sessions | 10k req/day |
| Task Queue | Celery + Redis | Async AI evaluation | Same Redis |
| Real-time | Socket.IO (python-socketio) | Live interview events | OSS |
| Primary LLM | Claude claude-sonnet-4-20250514 (Anthropic) | Question gen, evaluation | $5 free credit |
| Fallback LLM | GPT-4o-mini (OpenAI) | Cost-effective fallback | Pay-as-you-go |
| LLM Router | LiteLLM | Model abstraction | OSS |
| Email | Resend | Transactional email | 3k emails/mo |
| CI/CD | GitHub Actions | Test, build, deploy | Free for public repos |

---

## Prerequisites

- **Node.js** 18+ ([download](https://nodejs.org))
- **Python** 3.11+ ([download](https://python.org))
- **Docker** & Docker Compose ([download](https://docker.com))
- **Git** ([download](https://git-scm.com))

### Required Accounts (all free tier)

| Service | Sign Up | What You Need |
|---------|---------|---------------|
| Anthropic | [console.anthropic.com](https://console.anthropic.com) | API key |
| Supabase | [supabase.com](https://supabase.com) | Project URL, Anon Key, JWT Secret, Service Key |
| MongoDB Atlas | [mongodb.com/atlas](https://www.mongodb.com/atlas) | Connection string |
| Upstash | [upstash.com](https://upstash.com) | Redis REST URL + Token |
| Vercel | [vercel.com](https://vercel.com) | Account for frontend deploy |
| Railway | [railway.app](https://railway.app) | Account for backend deploy |

---

## Local Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-org/prepai.git
cd prepai
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your API keys and service credentials
```

### 3. Start infrastructure (Postgres, Redis, MongoDB)

```bash
docker-compose up -d postgres redis mongo
```

### 4. Set up the backend

```bash
cd apps/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed interview roles
python -m apps.api.db.seed

# Start the API server
uvicorn apps.api.main:app --reload --port 8000
```

### 5. Start Celery worker (new terminal)

```bash
cd apps/api
source venv/bin/activate
celery -A apps.api.tasks.celery_app worker --loglevel=info
```

### 6. Set up the frontend

```bash
cd apps/web
npm install
npm run dev
```

### 7. Open the app

Visit [http://localhost:3000](http://localhost:3000)

---

## Free Tier Setup Guide

### Supabase (PostgreSQL + Auth)

1. Go to [supabase.com](https://supabase.com) → Sign up
2. Click **New Project** → Name it "prepai"
3. Wait for the database to provision (~2 minutes)
4. Go to **Settings → API**:
   - Copy **Project URL** → `SUPABASE_URL`
   - Copy **anon public** key → `SUPABASE_ANON_KEY`
   - Copy **service_role** key → `SUPABASE_SERVICE_KEY`
5. Go to **Settings → API → JWT Settings**:
   - Copy **JWT Secret** → `SUPABASE_JWT_SECRET`
6. Go to **Authentication → Providers**:
   - Enable **Google** (requires Google Cloud Console OAuth credentials)
7. Update `DATABASE_URL` with the Supabase Postgres connection string from **Settings → Database**

### MongoDB Atlas

1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas) → Sign up
2. Create a **free M0 cluster** (AWS, any region)
3. Create a database user with read/write access
4. Add `0.0.0.0/0` to the IP Access List (for development)
5. Click **Connect → Drivers** → Copy the connection string
6. Replace `<password>` and set as `MONGODB_URI`

### Upstash Redis

1. Go to [upstash.com](https://upstash.com) → Sign up
2. Create a new Redis database (free tier)
3. Copy the **REST URL** → `UPSTASH_REDIS_REST_URL`
4. Copy the **REST Token** → `UPSTASH_REDIS_REST_TOKEN`
5. Copy the **Redis URL** (redis://...) → `REDIS_URL`

### Anthropic API

1. Go to [console.anthropic.com](https://console.anthropic.com) → Sign up
2. Go to **API Keys** → Create a new key
3. Copy it → `ANTHROPIC_API_KEY`
4. New accounts get $5 free credit (~50-100 interviews)

---

## Environment Variables Reference

| Variable | Description | Where to Find | Required |
|----------|-------------|---------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | Anthropic Console → API Keys | ✅ |
| `OPENAI_API_KEY` | OpenAI API key (fallback) | OpenAI Platform → API Keys | ❌ |
| `SUPABASE_URL` | Supabase project URL | Supabase Settings → API | ✅ |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Supabase Settings → API | ✅ |
| `SUPABASE_JWT_SECRET` | JWT signing secret | Supabase Settings → API → JWT | ✅ |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Supabase Settings → API | ✅ |
| `DATABASE_URL` | PostgreSQL connection (async) | Supabase Settings → Database | ✅ |
| `MONGODB_URI` | MongoDB connection string | Atlas → Connect → Drivers | ✅ |
| `REDIS_URL` | Redis connection URL | Upstash → Database Details | ✅ |
| `UPSTASH_REDIS_REST_URL` | Upstash REST API URL | Upstash → Database Details | ❌ |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash REST API token | Upstash → Database Details | ❌ |
| `SECRET_KEY` | App secret (random 32 chars) | Generate yourself | ✅ |
| `ALLOWED_ORIGINS` | CORS allowed origins | Your frontend URL | ✅ |
| `ENVIRONMENT` | `development` / `production` | Set manually | ✅ |
| `RESEND_API_KEY` | Resend email API key | Resend Dashboard | ❌ |

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/health` | No | Health check |
| `GET` | `/api/v1/users/me` | Yes | Get current user profile |
| `PATCH` | `/api/v1/users/me` | Yes | Update profile |
| `GET` | `/api/v1/interviews/roles` | Yes | List available roles |
| `POST` | `/api/v1/interviews` | Yes | Create interview session |
| `GET` | `/api/v1/interviews` | Yes | List user's interviews |
| `GET` | `/api/v1/interviews/{id}` | Yes | Get interview details |
| `POST` | `/api/v1/interviews/{id}/start` | Yes | Start interview (get WS token) |
| `POST` | `/api/v1/interviews/{id}/abandon` | Yes | Abandon interview |
| `GET` | `/api/v1/interviews/{id}/report` | Yes | Get final report |
| `GET` | `/api/v1/feedback/skills` | Yes | Get skill snapshots |
| `GET` | `/api/v1/feedback/interview/{id}` | Yes | Get interview feedback |

---

## WebSocket Events Reference

| Event | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `join_interview` | Client → Server | `{interview_id, session_token}` | Join an interview room |
| `submit_answer` | Client → Server | `{interview_id, question_id, response_text, response_time_seconds}` | Submit answer |
| `question` | Server → Client | `{question_id, question_text, question_num, total_questions, question_type}` | New question delivered |
| `evaluation_complete` | Server → Client | `{question_id, scores, strengths, weaknesses}` | Answer evaluation ready |
| `interview_complete` | Server → Client | `{report_id}` | Interview finished, report available |
| `error` | Server → Client | `{code, message}` | Error occurred |

---

## Deployment Guide

### Backend → Railway

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Create project: `railway init`
4. Link to repo: `railway link`
5. Add environment variables in Railway dashboard
6. Deploy: `railway up --service prepai-api`
7. Note the deployment URL → update `NEXT_PUBLIC_API_URL`

### Frontend → Vercel

1. Install Vercel CLI: `npm install -g vercel`
2. Login: `vercel login`
3. Navigate to `apps/web`
4. Deploy: `vercel --prod`
5. Set environment variables in Vercel dashboard:
   - `NEXT_PUBLIC_API_URL` = Railway backend URL
   - `NEXT_PUBLIC_WS_URL` = Railway backend URL
   - `NEXT_PUBLIC_SUPABASE_URL` = Your Supabase URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = Your Supabase anon key

---

## Cost Breakdown

### Per Interview (~10 questions)
| Component | Tokens | Cost |
|-----------|--------|------|
| Question generation (10×) | ~8,000 input + 3,000 output | ~$0.069 |
| Answer evaluation (10×) | ~10,000 input + 4,000 output | ~$0.090 |
| Final report (1×) | ~4,000 input + 2,000 output | ~$0.042 |
| **Total per interview** | | **~$0.20** |

### Monthly Infrastructure

| Users/Month | 0 (dev) | 100 | 500 |
|-------------|---------|-----|-----|
| Supabase | Free | Free | Free |
| MongoDB Atlas | Free | Free | Free |
| Upstash Redis | Free | Free | ~$10 |
| Railway | Free ($5 credit) | ~$5 | ~$15 |
| Vercel | Free | Free | Free |
| LLM (Anthropic) | $0 | ~$20 | ~$100 |
| **Total** | **$0** | **~$25** | **~$125** |

> 💡 **Free until ~25 users/month** ($5 Anthropic credit ≈ 25 interviews)

---

## Roadmap

### Phase 1: MVP ✅ (Current)
- [x] 5 role specializations with expert personas
- [x] 10-question adaptive interviews
- [x] 5-dimension scoring (relevance, depth, clarity, communication, technical accuracy)
- [x] Phrase-level feedback with anti-generic guardrails
- [x] Real-time WebSocket interview flow
- [x] Dashboard with skill tracking
- [x] Free tier (3 interviews/month)

### Phase 2: Personalization
- [ ] Resume upload + parsing → personalized questions
- [ ] Vector search (Pinecone) for question bank
- [ ] Custom interview roles (user-created)
- [ ] Interview replay mode
- [ ] Detailed comparison with previous attempts

### Phase 3: Voice & Video
- [ ] Voice input (Whisper API)
- [ ] Voice output (text-to-speech for interviewer)
- [ ] Video recording for body language analysis
- [ ] Multi-modal feedback (verbal + non-verbal)

### Phase 4: Teams & Enterprise
- [ ] Team management dashboard
- [ ] Custom rubrics per company
- [ ] Interview sharing + coaching mode
- [ ] SSO integration
- [ ] Analytics for hiring managers

---

## Project Structure

```
prepai/
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── main.py                 # App entry point
│   │   ├── requirements.txt        # Python dependencies
│   │   ├── Dockerfile              # Backend container
│   │   ├── alembic/                # Database migrations
│   │   ├── interview/              # Interview module
│   │   │   ├── router.py           # API endpoints
│   │   │   ├── models.py           # SQLAlchemy models
│   │   │   ├── schemas.py          # Pydantic schemas
│   │   │   ├── service.py          # Business logic
│   │   │   └── engine.py           # InterviewEngine
│   │   ├── user/                   # User module
│   │   ├── feedback/               # Feedback module
│   │   ├── ai/                     # AI layer
│   │   │   ├── llm.py              # LiteLLM wrapper
│   │   │   ├── prompts.py          # Prompt templates
│   │   │   ├── evaluator.py        # Answer evaluator
│   │   │   └── guardrails.py       # Quality validation
│   │   ├── tasks/                  # Celery async tasks
│   │   ├── db/                     # Database setup
│   │   │   ├── postgres.py         # SQLAlchemy engine
│   │   │   ├── mongo.py            # Motor client
│   │   │   └── seed.py             # Seed data
│   │   ├── core/                   # Core utilities
│   │   │   ├── config.py           # Settings
│   │   │   ├── auth.py             # JWT + rate limit
│   │   │   └── websocket.py        # Socket.IO
│   │   └── tests/                  # Backend tests
│   └── web/                        # Next.js frontend
│       ├── app/                    # App Router pages
│       │   ├── page.tsx            # Landing page
│       │   ├── dashboard/          # Dashboard
│       │   ├── interview/          # Interview flow
│       │   └── auth/               # Login/signup
│       ├── components/             # React components
│       │   ├── interview/          # Chat, Input, Feedback
│       │   └── dashboard/          # Charts, History
│       ├── lib/                    # Utilities
│       │   ├── api.ts              # API client
│       │   ├── socket.ts           # WebSocket client
│       │   ├── store.ts            # Zustand store
│       │   └── supabase.ts         # Auth client
│       └── __tests__/              # Frontend tests
├── .github/workflows/              # CI/CD pipelines
├── docker-compose.yml              # Local dev infra
├── .env.example                    # Environment template
└── README.md                       # This file
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- **Python**: Type annotations on all functions, Pydantic v2 for validation
- **TypeScript**: Strict mode, no `any` types
- **Tests**: Maintain ≥70% coverage on backend
- **Commits**: Use conventional commits (`feat:`, `fix:`, `docs:`, etc.)
- **PRs**: Include description, test results, and screenshots for UI changes

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p>Built with ❤️ for interview preparation</p>
  <p>
    <a href="https://github.com/your-org/prepai/issues">Report Bug</a> ·
    <a href="https://github.com/your-org/prepai/issues">Request Feature</a>
  </p>
</div>
