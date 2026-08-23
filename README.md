# NetBalance — Group Expense Tracker

A full-stack expense splitting app with a debt-settlement engine that minimises group payments to the mathematically lowest number of transactions.

---

## Tech Stack

**Backend:** Python 3.11 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL · pytest  
**Frontend:** React 18 · TypeScript · Tailwind CSS · Axios · React Router v6  
**Infrastructure:** Docker · GitHub Actions · Render

---

## Features

- Create groups and invite members via shareable invite codes
- Add expenses with equal, exact, or percentage-based splits
- Net balance calculation across all group expenses
- Greedy settlement algorithm (O(N log N)) that minimises payments to at most N−1 transactions
- JWT auth with refresh token rotation and reuse detection
- Versioned REST API (`/v1/`) with pagination, rate limiting, and structured logging
- 90+ pytest cases covering circular debts, rounding edge cases, and large-group stress tests

---

## Getting Started

```bash
git clone https://github.com/yourusername/netbalance.git
cd netbalance

cp .env.example .env
# Generate a secret key and paste it into .env:
# openssl rand -hex 32

docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## Running Tests

```bash
cd backend
pytest -m "not postgres" -v
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key — generate with `openssl rand -hex 32` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `VITE_API_URL` | Backend URL (frontend build-time variable) |

---

## Project Structure

```
netbalance/
├── backend/
│   ├── app/
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── routers/v1/    # Versioned route handlers
│   │   ├── services/      # Business logic + settlement algorithm
│   │   ├── middleware/    # Logging and error handling
│   │   └── utils/         # JWT, hashing, rate limiting
│   ├── tests/             # 90+ pytest cases
│   └── alembic/           # Database migrations
└── frontend/
    └── src/
        ├── pages/         # Route-level components
        ├── components/    # Reusable UI components
        ├── services/      # Axios API client
        ├── context/       # Auth state (React Context)
        └── types/         # TypeScript interfaces
```

---

