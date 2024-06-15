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

class ExamBase(BaseModel):
    Title: str
    ExamDatetime: datetime
    PersonnelNumber: int = 50000
    
class ExamCreate(ExamBase):
    Title: str
    ExamDatetime: datetime
    PersonnelNumber: int = 50000

class Exam(ExamBase):
    Idx: int

    class Config:
        from_attributes = True

# class AdminBase(BaseModel):
#     Id: str
#     Name: str
    
# class AdminCreate(AdminBase):
#     Password: str

# class Admin(AdminBase):
#     AdminIdx: int

#     class Config:
#         # orm_mode = True
#         from_attributes = True

class responseModel(BaseModel):
    result: bool
    code: int
    message: str

