from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import auth, transactions, transfers, statistics, settings, admin, debts, groups, workers
from database.session import close_db, init_db

app = FastAPI(
    title="Expenses Bot Mini App API",
    description="Backend API for Telegram Mini App",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production указать конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(transfers.router, prefix="/api/transfers", tags=["Transfers"])
# Debts router already has '/debts' prefix; include under /api to avoid double prefix.
app.include_router(debts.router, prefix="/api", tags=["Debts"])
app.include_router(groups.router, prefix="/api", tags=["Groups"])
app.include_router(workers.router, prefix="/api", tags=["Workers"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["Statistics"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

@app.get("/")
async def root():
    return {"message": "Expenses Bot Mini App API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
