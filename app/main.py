from fastapi import FastAPI
from .database import engine
from . import models
from app.router.v1 import member_router, exam_router, reservation_router, admin_router
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

# v1 API
app.include_router(member_router.router, prefix="/v1")
app.include_router(exam_router.router, prefix="/v1")
app.include_router(reservation_router.router, prefix="/v1")
app.include_router(admin_router.router, prefix="/v1")

