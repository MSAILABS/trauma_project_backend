from fastapi import APIRouter

from router.routes import route_data

api_router = APIRouter()

api_router.include_router(route_data.router, prefix="/data", tags=["data"])
# api_router.include_router(route_migration.router, prefix="/migration", tags=["Migration"])