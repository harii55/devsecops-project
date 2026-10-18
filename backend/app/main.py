from fastapi import Depends, FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Book
from app.schemas import BookCreate, BookOut, BookUpdate, Status

app = FastAPI(title="Library Book Tracker")
Instrumentator().instrument(app).expose(app)


def find_book(book_id: int, db: Session) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    return book


@app.get("/")
def home():
    return {"app": "Library Book Tracker", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "Database is not reachable")
    return {"status": "ready"}


@app.get("/api/books/stats")
def book_stats(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Book.status, func.count()).group_by(Book.status)).all())
    return {
        "total": sum(counts.values()),
        "available": counts.get("available", 0),
        "borrowed": counts.get("borrowed", 0),
    }


@app.get("/api/books", response_model=list[BookOut])
def list_books(status: Status | None = None, db: Session = Depends(get_db)):
    query = select(Book).order_by(Book.id)
    if status:
        query = query.where(Book.status == status)
    return db.scalars(query).all()


@app.get("/api/books/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    return find_book(book_id, db)


@app.post("/api/books", response_model=BookOut, status_code=201)
def add_book(data: BookCreate, db: Session = Depends(get_db)):
    book = Book(**data.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@app.put("/api/books/{book_id}", response_model=BookOut)
def update_book(book_id: int, data: BookUpdate, db: Session = Depends(get_db)):
    book = find_book(book_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(book, field, value)
    if book.status == "available":
        book.borrower = None
    elif not book.borrower:
        raise HTTPException(400, "Borrower name is required to borrow a book")
    db.commit()
    db.refresh(book)
    return book


@app.delete("/api/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    db.delete(find_book(book_id, db))
    db.commit()
