from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, groups, expenses, balances, settlements   # ← add

app = FastAPI(title="Splitwise Clone API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(expenses.router)
app.include_router(balances.router)
app.include_router(settlements.router)    # ← register


@app.get("/health")
def health_check():
    return {"status": "ok"}