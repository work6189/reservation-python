from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, and_, text
from datetime import datetime, timedelta
from typing import List
from .database import SessionLocal, engine, get_db
from . import models, schema, auth

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

@app.post("/users/", response_model=schema.MemberBase)
def create_member(member: schema.MemberCreate, db: SessionLocal = Depends(get_db)):
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
def login_member(member: schema.MemberLogin, db: SessionLocal = Depends(get_db)):
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
    

@app.get("/exam/", response_model=List[schema.ExamWithReservationCount])
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

@app.post("/reservation/{idx}")
async def reservation_exam(idx: int, params: schema.Reservation, data: str = Depends(auth.verify_member_token), db: SessionLocal = Depends(get_db)):
    try:
        db_member = db.query(models.Member).filter(models.Member.MemberIdx == data).first()
        if not db_member :
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

        response = schema.responseModel(result=True, code=00, message="success")
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

        response = schema.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.put("/reservation/{idx}")
async def modify_reservation(idx: int, params: schema.Reservation, data: str = Depends(auth.verify_member_token), db: SessionLocal = Depends(get_db)):
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

        response = schema.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.get("/reservation/my", response_model=List[schema.ExamWithExamReservation])
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
 
@app.get("/admin/reservation/", response_model=List[schema.ExamWithExamReservation])
async def get_reservation(admin_idx: str = Depends(auth.verify_admin_token),db: SessionLocal = Depends(get_db)):
    try:
        # admin vertify
        db_admin = db.query(models.Admin).filter(models.Admin.AdminIdx == admin_idx).first()
        if not db_admin :
            raise HTTPException(status_code=400, detail="Not Admin Auth")
        
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

@app.delete("/admin/reservation/{examIdx}/{memberIdx}")
async def delete_reservation(examIdx: int, memberIdx: int, admin_idx: str = Depends(auth.verify_admin_token), db: SessionLocal = Depends(get_db)):
    try:
        # admin vertify
        db_admin = db.query(models.Admin).filter(models.Admin.AdminIdx == admin_idx).first()
        if not db_admin :
            raise HTTPException(status_code=400, detail="Not Admin Auth")

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

        response = schema.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.put("/admin/reservation/{examIdx}/{memberIdx}")
async def modify_reservation(examIdx: int, memberIdx: int, params: schema.AdminReservation, admin_idx: str = Depends(auth.verify_admin_token), db: SessionLocal = Depends(get_db)):
    try:
        # admin vertify
        db_admin = db.query(models.Admin).filter(models.Admin.AdminIdx == admin_idx).first()
        if not db_admin :
            raise HTTPException(status_code=400, detail="Not Admin Auth")
        
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

        response = schema.responseModel(result=True, code=00, message="success")
        return response
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Create Reservation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.post("/admin/users/", response_model=schema.AdminBase)
def create_admin(admin: schema.AdminCreate, db: SessionLocal = Depends(get_db)):
    try:
        db_admin = db.query(models.Admin).filter(models.Admin.Id == admin.Id).first()
        logger.info(f"Queried admin_member: {db_admin}")

        # 회원이 있는 경우
        if db_admin:
            raise HTTPException(status_code=400, detail="AdminID already registred")
        
        hashed_password = auth.hash_password(admin.Password)
        admin_member = models.Admin(Id=admin.Id, Name=admin.Name, Password=hashed_password)

        db.add(admin_member)
        db.commit()
        db.refresh(admin_member)
        return admin_member
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error creating Admin: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/admin/login")
def login_admin_member(admin: schema.AdminLogin, db: SessionLocal = Depends(get_db)):
    try:
        admin_member = db.query(models.Admin).filter(models.Admin.Id == admin.Id).first()
        logger.info(f"admin_member : {admin_member}")
        if not admin_member:
            raise HTTPException(status_code=400, detail="Invalid ID or password1")
        
        if admin_member.Password != auth.hash_password(admin.Password):
            raise HTTPException(status_code=400, detail="Invalid ID or password2")
        
        access_token = auth.create_access_token(
            data={"admin_data": admin_member.AdminIdx}
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException as http_exc:
        # HTTPException 발생 시 로깅 후 재발생
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error Login member: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.post("/admin/exam/")
def create_exam(exam: schema.ExamCreate, admin_idx: str = Depends(auth.verify_admin_token), db: SessionLocal = Depends(get_db)):
    try:
        # admin vertify
        db_admin = db.query(models.Admin).filter(models.Admin.AdminIdx == admin_idx).first()
        if not db_admin :
            raise HTTPException(status_code=400, detail="Not Admin Auth")
        
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
    