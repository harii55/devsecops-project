from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["available", "borrowed"]


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    genre: str = Field(min_length=1, max_length=60)


class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    author: str | None = Field(None, min_length=1, max_length=120)
    genre: str | None = Field(None, min_length=1, max_length=60)
    status: Status | None = None
    borrower: str | None = Field(None, min_length=1, max_length=120)


class BookOut(BookCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: Status
    borrower: str | None
