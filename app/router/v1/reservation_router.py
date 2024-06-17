from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from typing import List
from ...database import SessionLocal, get_db
from ... import models, schema, auth
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/reservation/{examIdx}")
async def reservation_exam(examIdx: int, params: schema.Reservation, data: str = Depends(auth.verify_member_token), db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.MemberIdx == data).first()
        if not db_member :
            raise HTTPException(status_code=400, detail="Empty Member")
        
        db_exam = db.query(models.Exam).filter(models.Exam.ExamIdx == examIdx).first()
        if not db_exam:
            raise HTTPException(status_code=400, detail="Not Exists Exam Data")
        
        db_reservation = (
            db.query(models.ExamReservation)
            .filter(models.ExamReservation.MemberIdx == db_member.MemberIdx)
            .filter(models.ExamReservation.ExamIdx == db_exam.ExamIdx)
            .first()
        )
        if db_reservation:
            raise HTTPException(status_code=400, detail="Already Registred Exam")
        
        db_reservation_count = (
            db.query(func.count(models.ExamReservation.MemberIdx))
            .filter(models.ExamReservation.ExamIdx == db_exam.ExamIdx)
            .filter(models.ExamReservation.ConfirmDatetime != None)
            .scalar()
        )

        if(db_reservation_count > db_exam.PersonnelCount):
            raise HTTPException(status_code=400, detail="Over Exam Personnel Count")
        
        db_reservation = models.ExamReservation(
            MemberIdx= db_member.MemberIdx, 
            ExamIdx=db_exam.ExamIdx,
            Memo= params.Memo
        )
        db.add(db_reservation)
        db.commit()

        response = schema.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")  
   
@router.delete("/reservation/{examIdx}")
async def delete_reservation(examIdx: int, data: str = Depends(auth.verify_member_token), db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.MemberIdx == data).first()
        if not db_member :
            raise HTTPException(status_code=400, detail="Empty Member")
        
        db_exam = db.query(models.Exam).filter(models.Exam.ExamIdx == examIdx).first()
        if not db_exam:
            raise HTTPException(status_code=400, detail="Not Exists Exam Data")
        
        db_reservation = (
            db.query(models.ExamReservation)
            .filter(models.ExamReservation.MemberIdx == db_member.MemberIdx)
            .filter(models.ExamReservation.ExamIdx == db_exam.ExamIdx)
            .filter(models.ExamReservation.ConfirmDatetime == None)
            .first()
        )
        if not db_reservation:
            raise HTTPException(status_code=400, detail="Not Exists Registred Exam")
        
        db.delete(db_reservation)
        db.commit()

        response = schema.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@router.put("/reservation/{examIdx}")
async def modify_reservation(examIdx: int, params: schema.Reservation, data: str = Depends(auth.verify_member_token), db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.MemberIdx == data).first()
        if not db_member :
            # response = schemas.responseModel(result=False, code=91, message="Empty Member")
            raise HTTPException(status_code=400, detail="Empty Member")
        
        db_exam = db.query(models.Exam).filter(models.Exam.ExamIdx == examIdx).first()
        if not db_exam:
            raise HTTPException(status_code=400, detail="Not Exists Exam Data")
        
        db_reservation = (
            db.query(models.ExamReservation)
            .filter(models.ExamReservation.MemberIdx == db_member.MemberIdx)
            .filter(models.ExamReservation.ExamIdx == db_exam.ExamIdx)
            .filter(models.ExamReservation.ConfirmDatetime == None)
            .first()
        )
        if not db_reservation:
            raise HTTPException(status_code=400, detail="Not Exists Registred Exam")
        
        db_reservation.Memo = params.Memo
        db.commit()

        response = schema.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@router.get("/reservation/my", response_model=List[schema.ExamWithExamReservation])
async def get_my_reservation(data: str = Depends(auth.verify_member_token), db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.MemberIdx == data).first()
        if not db_member :
            raise HTTPException(status_code=400, detail="Empty Member")
        
        db_result = (
            db.query(
                models.Exam.ExamIdx,
                models.Exam.Title,
                models.Exam.ExamDatetime,
                models.Exam.PersonnelCount,
                models.ExamReservation.MemberIdx,
                models.ExamReservation.Memo,
                models.ExamReservation.ConfirmDatetime,
                models.ExamReservation.RegDatetime
            )
            .outerjoin(models.ExamReservation, 
                models.Exam.ExamIdx == models.ExamReservation.ExamIdx)
            .filter(models.ExamReservation.MemberIdx == db_member.MemberIdx)
            .all()
        )

        logger.info(f"db_result : {db_result}")
        
        response = []
        for exam in db_result:
            logger.info(f"exam : {exam}")
            response.append(
                schema.ExamWithExamReservation(
                    ExamIdx= exam.ExamIdx,
                    Title= exam.Title,
                    ExamDatetime= exam.ExamDatetime,
                    PersonnelCount= exam.PersonnelCount,
                    MemberIdx= exam.MemberIdx,
                    Memo= exam.Memo,
                    ConfirmDatetime= exam.ConfirmDatetime,
                    RegDatetime= exam.RegDatetime
                )
            )
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
 