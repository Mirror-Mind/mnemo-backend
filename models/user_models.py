import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    emailVerified = Column(Boolean, default=False)
    image = Column(String, nullable=True)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    phoneNumber = Column(String, nullable=True, index=True)
    phoneNumberVerified = Column(Boolean, nullable=True, default=False)
    lang = Column(String, nullable=True)

    sessions = relationship("Session", back_populates="user")
    accounts = relationship("Account", back_populates="user")
    user_thread = relationship("UserThread", back_populates="user", uselist=False)


class Session(Base):
    __tablename__ = "session"

    id = Column(String, primary_key=True, index=True)
    expiresAt = Column(DateTime)
    token = Column(String, unique=True, index=True)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    ipAddress = Column(String, nullable=True)
    userAgent = Column(String, nullable=True)
    userId = Column(String, ForeignKey("user.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="sessions")


class Account(Base):
    __tablename__ = "account"

    id = Column(String, primary_key=True, index=True)
    accountId = Column(String, index=True)
    providerId = Column(String, index=True)
    userId = Column(String, ForeignKey("user.id", ondelete="CASCADE"))
    accessToken = Column(String, nullable=True)
    refreshToken = Column(String, nullable=True)
    idToken = Column(String, nullable=True)
    accessTokenExpiresAt = Column(DateTime, nullable=True)
    refreshTokenExpiresAt = Column(DateTime, nullable=True)
    scope = Column(String, nullable=True)
    password = Column(String, nullable=True)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="accounts")


class Verification(Base):
    __tablename__ = "verification"

    id = Column(String, primary_key=True, index=True)
    identifier = Column(String, index=True)
    value = Column(String)
    expiresAt = Column(DateTime)
    createdAt = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=True
    )
    updatedAt = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )


class UserThread(Base):
    __tablename__ = "user_thread"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    userId = Column(String, ForeignKey("user.id", ondelete="CASCADE"), unique=True)
    threadId = Column(String, index=True)
    checkpoint = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="user_thread")


class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    email = Column(String, unique=True, index=True)
    phoneNumber = Column(String, index=True)
    countryCode = Column(String)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
