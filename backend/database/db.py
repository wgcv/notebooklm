import sqlalchemy
from datetime import datetime
import databases
from pydantic import BaseModel

DATABASE_URL = "sqlite:///./database.db"

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

documents = sqlalchemy.Table(
    "documents",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("thread_id", sqlalchemy.String),
    sqlalchemy.Column("documentUrl", sqlalchemy.String),
    sqlalchemy.Column("documentName", sqlalchemy.String),
    sqlalchemy.Column(
        "createdAt",
        sqlalchemy.DateTime(timezone=True),
        nullable=False,
        server_default=sqlalchemy.func.now(),
    ),
    sqlalchemy.Column(
        "updatedAt",
        sqlalchemy.DateTime(timezone=True),
        nullable=False,
        server_default=sqlalchemy.func.now(),
        onupdate=sqlalchemy.func.now(),
    ),
)


engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)


class documentAdd(BaseModel):
    thread_id: str
    documentUrl: str
    documentName: str
    

class document(BaseModel):
    id: int
    thread_id: str
    documentUrl: str
    documentName: str
    createdAt: datetime
    updatedAt: datetime
