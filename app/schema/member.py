from pydantic import BaseModel

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