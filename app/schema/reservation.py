from pydantic import BaseModel
from datetime import datetime


class Reservation(BaseModel):
    Memo: str = None

class AdminReservation(BaseModel):
    Memo: str = None
    ConfirmDatetime: datetime = None
