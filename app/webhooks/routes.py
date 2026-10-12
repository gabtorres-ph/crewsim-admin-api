from fastapi import APIRouter

from app.webhooks.telcovision import router as telcovision_router

router = APIRouter(prefix="/webhooks")
router.include_router(telcovision_router)
