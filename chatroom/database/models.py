
from sqlalchemy import Column, DateTime, String, Integer, func, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    middle_name = Column(String)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # One-to-many: User can create many chatrooms
    chatrooms = relationship("Chatroom", back_populates="creator")
    # Many-to-many: User is member of many chatrooms
    member_of = relationship("RoomMembers", back_populates="user")


class Chatroom(Base):
    __tablename__ = "chatroom"

    id = Column(Integer, primary_key=True, autoincrement=True)
    roomname = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_private = Column(Boolean, nullable=False)
    is_deleted = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Creator of the room
    creator = relationship("User", back_populates="chatrooms")
    # Members of the room
    members = relationship("RoomMembers", back_populates="chatroom")


class RoomMembers(Base):
    __tablename__ = "room_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("chatroom.id"), nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    joined_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="member_of")
    chatroom = relationship("Chatroom", back_populates="members")
