from pydantic import BaseModel
from datetime import datetime

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