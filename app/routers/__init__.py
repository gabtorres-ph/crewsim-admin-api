from fastapi import APIRouter

from app.routers.esims import router as esims_router
from app.routers.favorites import router as favorites_router
from app.routers.users import router as users_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(esims_router)
api_router.include_router(favorites_router)

__all__ = ["api_router"]
