"""
KeChat - 可聊 轻量即时通讯系统
数据库模型定义
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kechat.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    display_name = Column(String(100), default="")
    password_hash = Column(String(200), nullable=False)
    avatar_url = Column(String(500), default="")
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    msg_type = Column(String(20), default="text")  # text, image, file
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)


class Conversation(Base):
    """记录用户之间的会话关系，用于显示最近联系人"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    peer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    last_message = Column(Text, default="")
    last_message_time = Column(DateTime, default=datetime.utcnow)
    unread_count = Column(Integer, default=0)


def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)
