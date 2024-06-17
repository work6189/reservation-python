from pydantic import BaseModel

class AdminBase(BaseModel):
    Id: str
    Name: str

class AdminCreate(AdminBase):
    Id: str
    Name: str
    Password: str

class Admin(AdminBase):
    AdminIdx: int

    class Config:
        from_attributes = True

class AdminLogin(BaseModel):
    Id: str
    Password: str