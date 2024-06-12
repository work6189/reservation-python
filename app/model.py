from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from .database import Base

class Member(Base):
    __tablename__ = "Member"

    MemberIdx = Column(Integer, primary_key=True, autoincrement=True)
    Id = Column(String, unique=True, index=True)
    Name = Column(String, nullable=False)
    Password = Column(String, nullable=False)
    RegDatetime = Column(DateTime)

class Reservation(Base):
    __tablename__ = "Reservation"

    Idx = Column(Integer, primary_key=True, autoincrement=True)
    Title = Column(String, nullable=False)
    StartDatetime = Column(DateTime)
    PersonnelNumber = Column(Integer, default=0)
    RegDatetime = Column(DateTime)

class ReservationMember(Base):
    __tablename__ = "ReservationMember"

    Idx = Column(Integer, ForeignKey("Reservation.Idx"))
    MemberIdx = Column(Integer, ForeignKey("Member.MemberIdx"))
    Confirmation = Column(Boolean, default=False)
    RegDatetime = Column(DateTime)



