from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(120))
    genre: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="available")
    borrower: Mapped[str | None] = mapped_column(String(120))
