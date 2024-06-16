from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from typing import List
from .database import SessionLocal, engine, get_db
from . import models, schemas, auth

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/users/", response_model=schemas.MemberBase)
def create_member(member: schemas.MemberCreate, db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.Id == member.Id).first()
        logger.info(f"Queried db_member: {db_member}")

        # 회원이 있는 경우
        if db_member:
            raise HTTPException(status_code=400, detail="ID already registred")
        
        hashed_password = auth.hash_password(member.Password)
        db_member = models.Member(Id=member.Id, Name=member.Name, Password=hashed_password)

        db.add(db_member)
        db.commit()
        db.refresh(db_member)
        return db_member
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error creating member: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/login")
def login_member(member: schemas.MemberLogin, db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.Id == member.Id).first()
        if not db_member:
            raise HTTPException(status_code=400, detail="Invalid ID or password")
        
        if db_member.Password != auth.hash_password(member.Password):
            raise HTTPException(status_code=400, detail="Invalid ID or password")
        
        access_token = auth.create_access_token(
            data={"data": db_member.MemberIdx}
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Login member: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/users/my")
def get_member_info(data: str = Depends(auth.verify_member_token),  db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.MemberIdx == data).first()
        if not db_member :
            raise HTTPException(status_code=400, detail="Empty Member")
        return db_member
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Login member: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.post("/exam/")
def create_exam(exam: schemas.ExamCreate, db: SessionLocal = Depends(get_db)):
    try:
        db_exam = db.query(models.Exam).filter(models.Exam.Title == exam.Title).filter(models.Exam.ExamDatetime == exam.ExamDatetime).first()
        if db_exam:
            raise HTTPException(status_code=400, detail="already registred Exam Data")

        db_exam = models.Exam(ExamDatetime=exam.ExamDatetime, Title=exam.Title, PersonnelCount=exam.PersonnelCount)
        
        db.add(db_exam)
        db.commit()
        db.refresh(db_exam)
        return db_exam
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error creating exam: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.get("/exam/", response_model=List[schemas.ExamWithReservationCount])
def search_exams(params: schemas.ExamSearch, db: SessionLocal = Depends(get_db)):
    try:
        logger.info(f"params:{params}")
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
            # .filter(models.ExamReservation.ConfirmDatetime == None)
            .group_by(models.Exam.ExamIdx)
        )
        if(params.Title):
            query = query.filter(models.Exam.Title.contains(params.Title))
        if(params.StartDatetime and params.EndDatetime):
            query = query.filter(models.Exam.ExamDatetime >= params.StartDatetime).filter(models.Exam.ExamDatetime <= params.EndDatetime)
        db_result = query.offset((params.page - 1) * params.limit).limit(params.limit).all()

        # 실제 실행되는 SQL 쿼리 출력
        # logger.info(str(query))
        # logger.info(f"query : {query}")
        # logger.info(f"db_result : {db_result}")

        response = []
        for exam in db_result:
            # logger.info(f"exam : {exam}")
            # logger.info(f"ReservationCount : {ReservationCount}")
            # exam_data = schemas.ExamList.from_orm(exam)
            response.append(
                schemas.ExamWithReservationCount(
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

@app.post("/reservation/{idx}")
async def reservation_exam(idx: int, params: schemas.Reservation, data: str = Depends(auth.verify_member_token), db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.MemberIdx == data).first()
        if not db_member :
            # response = schemas.responseModel(result=False, code=91, message="Empty Member")
            raise HTTPException(status_code=400, detail="Empty Member")
        
        db_exam = db.query(models.Exam).filter(models.Exam.ExamIdx == idx).first()
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

        response = schemas.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")  
   
@app.delete("/reservation/{idx}")
async def delete_reservation(idx: int, data: str = Depends(auth.verify_member_token), db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.MemberIdx == data).first()
        if not db_member :
            # response = schemas.responseModel(result=False, code=91, message="Empty Member")
            raise HTTPException(status_code=400, detail="Empty Member")
        
        db_exam = db.query(models.Exam).filter(models.Exam.ExamIdx == idx).first()
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

        response = schemas.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.put("/reservation/{idx}")
async def modify_reservation(idx: int, params: schemas.Reservation, data: str = Depends(auth.verify_member_token), db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.MemberIdx == data).first()
        if not db_member :
            # response = schemas.responseModel(result=False, code=91, message="Empty Member")
            raise HTTPException(status_code=400, detail="Empty Member")
        
        db_exam = db.query(models.Exam).filter(models.Exam.ExamIdx == idx).first()
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

        response = schemas.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.get("/reservation/my", response_model=List[schemas.ExamWithExamReservation])
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
                schemas.ExamWithExamReservation(
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
 
@app.get("/admin/reservation/", response_model=List[schemas.ExamWithExamReservation])
async def get_reservation(db: SessionLocal = Depends(get_db)):
    try:
        # admin vertify
        
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
            .join(models.ExamReservation, 
                models.Exam.ExamIdx == models.ExamReservation.ExamIdx)
            .all()
        )

        response = []
        if db_result:
            for exam in db_result:
                logger.info(f"exam : {exam}")
                response.append(
                    schemas.ExamWithExamReservation(
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

@app.delete("/admin/reservation/{examIdx}/{memberIdx}")
async def delete_reservation(examIdx: int, memberIdx: int, db: SessionLocal = Depends(get_db)):
    try:
        # admin vertify

        db_exam = db.query(models.Exam).filter(models.Exam.ExamIdx == examIdx).first()
        if not db_exam:
            raise HTTPException(status_code=400, detail="Not Exists Exam Data")
        
        db_reservation = (
            db.query(models.ExamReservation)
            .filter(models.ExamReservation.ExamIdx == db_exam.ExamIdx)
            .filter(models.ExamReservation.MemberIdx == memberIdx)
            .first()
        )
        if not db_reservation:
            raise HTTPException(status_code=400, detail="Not Exists Registred Exam")
        
        db.delete(db_reservation)
        db.commit()

        response = schemas.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.put("/admin/reservation/{examIdx}/{memberIdx}")
async def modify_reservation(examIdx: int, memberIdx: int, params: schemas.AdminReservation, db: SessionLocal = Depends(get_db)):
    try:
        # db_member = db.query(models.Member).filter(models.Member.MemberIdx == data).first()
        # if not db_member :
        #     # response = schemas.responseModel(result=False, code=91, message="Empty Member")
        #     raise HTTPException(status_code=400, detail="Empty Member")
        
        db_exam = db.query(models.Exam).filter(models.Exam.ExamIdx == examIdx).first()
        if not db_exam:
            raise HTTPException(status_code=400, detail="Not Exists Exam Data")
        
        db_reservation = (
            db.query(models.ExamReservation)
            .filter(models.ExamReservation.MemberIdx == memberIdx)
            .filter(models.ExamReservation.ExamIdx == db_exam.ExamIdx)
            .first()
        )
        if not db_reservation:
            raise HTTPException(status_code=400, detail="Not Exists Registred Exam")
        
        if params.Memo:
            db_reservation.Memo = params.Memo
        if params.ConfirmDatetime:
            db_reservation.ConfirmDatetime = params.ConfirmDatetime
        db.commit()

        response = schemas.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
