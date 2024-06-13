from pydantic import BaseModel

class MemberBase(BaseModel):
    Id: str
    Name: str
    
class MemberCreate(MemberBase):
    Password: str

class Member(MemberBase):
    Idx: int

    class Config:
        orm_mode = True
