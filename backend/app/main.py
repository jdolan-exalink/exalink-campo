import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from app.core.config import settings
from app.api.v1.router import api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_mqtt_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mqtt_task
    from app.services.mqtt_consumer import run_mqtt_consumer
    _mqtt_task = asyncio.create_task(run_mqtt_consumer())
    logger.info("Exalink Campo API iniciada")
    yield
    if _mqtt_task:
        _mqtt_task.cancel()
        try:
            await _mqtt_task
        except asyncio.CancelledError:
            pass
    logger.info("Exalink Campo API detenida")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plataforma Ganadera Inteligente Multi-Tenant",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION, "env": settings.ENVIRONMENT}
