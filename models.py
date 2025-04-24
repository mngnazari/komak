from datetime import datetime
from sqlalchemy import ForeignKey, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    DECIMAL,
    Text,
    Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
from config import Config

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    inviter_id = Column(Integer, ForeignKey('users.id'))
    remaining_invites = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_admin = Column(Boolean, default=False)

    # Relationships
    inviter = relationship("User", remote_side=[id], back_populates="invitees")
    invitees = relationship("User", back_populates="inviter")
    files = relationship("File", back_populates="user")
    referrals = relationship("Referral", back_populates="referrer")
    invited_users = relationship("InvitedUser", foreign_keys="[InvitedUser.referrer_id]", back_populates="referrer")
    wallet = relationship("Wallet", uselist=False, back_populates="user")
    referrals = relationship("Referral", back_populates="referrer")


class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100))
    file_id = Column(String(255), unique=True, nullable=False)
    file_unique_id = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    quantity = Column(Integer, default=1)
    description = Column(Text)
    status = Column(String(50), default='در حال انجام')
    notes = Column(Text)

    user = relationship("User", back_populates="files")


class Referral(Base):
    __tablename__ = 'referrals'

    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey('users.id'))
    referral_code = Column(String(20), unique=True)
    used_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime)
    is_admin = Column(Boolean, default=False)
    usage_limit = Column(Integer, default=-1)  # -1 برای نامحدود
    referrer = relationship("User", back_populates="referrals")


class InvitedUser(Base):
    __tablename__ = 'invited_users'

    referrer_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    invited_user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    invited_full_name = Column(String(255), nullable=False)
    invited_phone = Column(String(20), nullable=False)
    invited_at = Column(DateTime, server_default=func.now())

    referrer = relationship(
        "User",
        foreign_keys=[referrer_id],
        back_populates="invited_users"
    )

    user = relationship(
        "User",
        foreign_keys=[invited_user_id]
    )


class Wallet(Base):
    __tablename__ = 'wallets'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    balance = Column(DECIMAL(10, 2), default=0.00)
    discount = Column(DECIMAL(10, 2), default=0.00)

    user = relationship("User", back_populates="wallet")


# Indexes

Index('ix_referrals_code', Referral.referral_code)
Index('ix_files_created_at', File.created_at)
Index('ix_referrals_expires', Referral.expires_at)

# Database engine configuration
engine = create_engine(
    f"mysql+pymysql://{Config.DB_USER}:{Config.DB_PASS}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "connect_timeout": 15,
        "read_timeout": 30,
        "write_timeout": 30
    }
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)