from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, and_, text
from typing import List
from ...database import SessionLocal, get_db
from ... import models, schema
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/exam", response_model=List[schema.ExamWithReservationCount])
def search_exams(params: schema.ExamSearch, db: SessionLocal = Depends(get_db)):
    try:
        future_time = func.now() + text("INTERVAL '3 HOURS'")
        query = (
            db.query(
                models.Exam.ExamIdx,
                models.Exam.Title,
                models.Exam.ExamDatetime,
                models.Exam.PersonnelCount,
                func.count(models.ExamReservation.MemberIdx).label("ReservationCount")
            )
            .outerjoin(models.ExamReservation, and_(
                models.Exam.ExamIdx == models.ExamReservation.ExamIdx,
                models.ExamReservation.ConfirmDatetime == None,
            ))
            .filter(models.Exam.ExamDatetime >= future_time)
            .group_by(models.Exam.ExamIdx)
        )
        if(params.Title):
            query = query.filter(models.Exam.Title.contains(params.Title))
        if(params.StartDatetime and params.EndDatetime):
            query = query.filter(models.Exam.ExamDatetime >= params.StartDatetime).filter(models.Exam.ExamDatetime <= params.EndDatetime)
        db_result = query.offset((params.page - 1) * params.limit).limit(params.limit).all()

        response = []
        for exam in db_result:
            response.append(
                schema.ExamWithReservationCount(
                    ExamIdx= exam.ExamIdx,
                    Title= exam.Title,
                    ExamDatetime= exam.ExamDatetime,
                    PersonnelCount= exam.PersonnelCount,
                    ReservationCount=exam.ReservationCount
                )
            )
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error get Exam : {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
