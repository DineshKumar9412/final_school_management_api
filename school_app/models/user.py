# models/user.py
from sqlalchemy import Column, Integer, String
from database.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(100))
