from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, relationship

from src.persistence.base import Base


class MailOutbox(Base):
    __tablename__ = "outbox"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    mail_from = Column(Text, nullable=False)
    rcpt_tos = Column(ARRAY(Text), nullable=False)
    raw_message = Column(LargeBinary, nullable=False)
    status = Column(Text, nullable=False, server_default="queued")
    attempts = Column(Integer, nullable=False, server_default="0")
    max_attempts = Column(Integer, nullable=False, server_default="5")
    next_attempt_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)

    delivery_attempts: Mapped[list["MailDeliveryAttempt"]] = relationship(back_populates="email", cascade="all, delete-orphan")


class MailDeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email_id = Column(BigInteger, ForeignKey("mail.outbox.id", ondelete="CASCADE"), nullable=False, index=True)
    mx_host = Column(Text, nullable=True)
    smtp_code = Column(Integer, nullable=True)
    smtp_response = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False,server_default="false")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,server_default=func.now())

    email: Mapped[MailOutbox] = relationship(back_populates="delivery_attempts")
