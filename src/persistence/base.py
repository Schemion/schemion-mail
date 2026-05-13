from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

mail_metadata = MetaData(schema="mail")


class Base(DeclarativeBase):
    metadata = mail_metadata
