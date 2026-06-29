from fastapi import APIRouter
from app.api.v1 import auth, animals, paddocks, devices, alerts, dashboard
from app.api.v1 import establishments, health, reproduction, weights, noc, import_data, lora, provision

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(animals.router)
api_router.include_router(paddocks.router)
api_router.include_router(devices.router)
api_router.include_router(alerts.router)
api_router.include_router(dashboard.router)
api_router.include_router(establishments.router)
api_router.include_router(health.router)
api_router.include_router(reproduction.router)
api_router.include_router(weights.router)
api_router.include_router(noc.router)
api_router.include_router(import_data.router)
api_router.include_router(lora.router)
api_router.include_router(provision.router)
