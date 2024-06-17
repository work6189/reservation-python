from pydantic import BaseModel

class responseModel(BaseModel):
    result: bool
    code: int
    message: str
