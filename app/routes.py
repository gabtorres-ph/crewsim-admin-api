from fastapi import APIRouter

from app.accounts.routes import router as accounts_router
from app.esims.routes import account_router as account_esims_router
from app.esims.routes import router as esims_router
from app.esims.routes import user_router as user_esims_router
from app.routers.favorites import router as favorites_router
from app.users.routes import router as users_router

api_router = APIRouter()
api_router.include_router(accounts_router)
api_router.include_router(account_esims_router)
api_router.include_router(users_router)
api_router.include_router(user_esims_router)
api_router.include_router(esims_router)
api_router.include_router(favorites_router)

__all__ = ["api_router"]
