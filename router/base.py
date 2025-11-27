from fastapi import APIRouter

from router.routes import route_data, route_data_queue, route_login

api_router = APIRouter()

api_router.include_router(route_login.router, prefix="", tags=["auth"])
api_router.include_router(route_data.router, prefix="/data", tags=["data"])
# api_router.include_router(route_data_queue.router, prefix="/data_queue", tags=["data_queue"])
# api_router.include_router(route_migration.router, prefix="/migration", tags=["Migration"])