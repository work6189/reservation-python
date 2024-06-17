from fastapi import APIRouter, Depends, HTTPException
from ...database import SessionLocal, get_db
from ... import models, schema, auth
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/users/", response_model=schema.MemberBase)
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

@router.post("/login")
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

@router.get("/users/my")
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
    