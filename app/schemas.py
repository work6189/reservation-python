from pydantic import BaseModel
from datetime import datetime, time, timedelta

class MemberLogin(BaseModel):
    Id: str
    Password: str

class MemberBase(BaseModel):
    Id: str
    Name: str
    
class MemberCreate(MemberBase):
    Password: str

class Member(MemberBase):
    MemberIdx: int

    class Config:
        from_attributes = True

class ExamSearch(BaseModel):
    Title: str = None
    StartDatetime: datetime = None
    EndDatetime: datetime = None
    page: int = 1
    limit: int = 10
    class Config:
        orm_mode = True

class ExamList(BaseModel):
    ExamIdx: int 
    Title: str 
    ExamDatetime: datetime
    PersonnelCount: int
    class Config:
        from_attributes=True

class ExamBase(BaseModel):
    Title: str
    ExamDatetime: datetime
    PersonnelCount: int = 50000
    
class ExamCreate(ExamBase):
    Title: str
    ExamDatetime: datetime
    PersonnelCount: int = 50000    

class Exam(ExamBase):
    Idx: int
    class Config:
        from_attributes = True

class ExamWithReservationCount(ExamList):
    ReservationCount: int

class ExamWithExamReservation(ExamList):
    MemberIdx: int
    Memo: str
    ConfirmDatetime: datetime
    RegDatetime: datetime 

class Reservation(BaseModel):
    Memo: str = None

class AdminReservation(BaseModel):
    Memo: str = None
    ConfirmDatetime: datetime = None

class AdminBase(BaseModel):
    Id: str
    Name: str

class Admin(AdminBase):
    AdminIdx: int

    class Config:
        from_attributes = True

class responseModel(BaseModel):
    result: bool
    code: int
    message: str

