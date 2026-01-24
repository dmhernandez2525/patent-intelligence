from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.routes import health, patents, search, expiration, analysis, ideas, watchlist
from src.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("app.starting", version=settings.app_version)
    yield
    logger.info("app.shutting_down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered patent intelligence platform for discovering expiring patents, "
    "white space opportunities, and innovation ideas from 200M+ global patents.",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(patents.router, prefix="/api/patents", tags=["Patents"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(expiration.router, prefix="/api/expiration", tags=["Expiration"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(ideas.router, prefix="/api/ideas", tags=["Ideas"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["Watchlist"])
