from fastapi import APIRouter, Depends
from starlette.responses import RedirectResponse

from .routers.data_routes import router as data_router
from .routers.prediction_routes import router as prediction_router
from .routers.simulation_routes import router as simulation_router

router = APIRouter()
router.include_router(data_router)
router.include_router(prediction_router)
router.include_router(simulation_router)

@router.get("/")
async def redirect():
    response = RedirectResponse(url='/koairy/api/docs')
    return response
