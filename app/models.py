from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .database import Base

class Admin(Base):
    __tablename__ = "Admin"

    AdminIdx = Column(Integer, primary_key=True, autoincrement=True)
    Id = Column(String, unique=True, index=True)
    Name = Column(String, nullable=False)
    Password = Column(String, nullable=False)
    RegDatetime = Column(DateTime, server_default=func.now())

class Member(Base):
    __tablename__ = "Member"

    MemberIdx = Column(Integer, primary_key=True, autoincrement=True)
    Id = Column(String, unique=True, index=True)
    Name = Column(String, nullable=False)
    Password = Column(String, nullable=False)
    RegDatetime = Column(DateTime, server_default=func.now())

class Exam(Base):
    __tablename__ = "Exam"

    ExamIdx = Column(Integer, primary_key=True, autoincrement=True)
    ExamDatetime = Column(DateTime, nullable=False, index=True)
    Title = Column(String, nullable=False)
    PersonnelCount = Column(Integer, default=50000)
    RegDatetime = Column(DateTime, server_default=func.now())

class ExamReservation(Base):
    __tablename__ = "ExamReservation"

    MemberIdx = Column(Integer, ForeignKey("Member.MemberIdx"), primary_key=True)
    ExamIdx = Column(Integer, ForeignKey("Exam.ExamIdx"), primary_key=True)
    Memo = Column(String)
    ConfirmDatetime = Column(DateTime, nullable=True)
    RegDatetime = Column(DateTime,  server_default=func.now())

