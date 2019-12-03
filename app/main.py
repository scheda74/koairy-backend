from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .api.routes import router as api_router
from .db.mongodb_utils import connect_to_mongo, close_mongo_connection


app = FastAPI(title="KoAirY API", docs_url="/koairy/api/docs", openapi_url="/koairy/api/openapi.json")

app.add_middleware(CORSMiddleware, allow_origins="*", allow_methods=["*"], allow_headers=["*"])

app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

app.include_router(api_router, prefix="/koairy/api")

