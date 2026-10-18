def add_book(client, title="Clean Code"):
    response = client.post("/api/books", json={"title": title, "author": "Robert Martin", "genre": "Programming"})
    assert response.status_code == 201
    return response.json()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_ready_checks_database(client):
    assert client.get("/ready").json() == {"status": "ready"}


def test_add_book(client):
    book = add_book(client)
    assert book["title"] == "Clean Code"
    assert book["status"] == "available"
    assert book["borrower"] is None


def test_add_book_without_title_fails(client):
    response = client.post("/api/books", json={"title": "", "author": "Someone", "genre": "Fiction"})
    assert response.status_code == 422


def test_get_book(client):
    book = add_book(client)
    assert client.get(f"/api/books/{book['id']}").json()["title"] == "Clean Code"


def test_get_missing_book_returns_404(client):
    assert client.get("/api/books/999").status_code == 404


def test_borrow_and_return_book(client):
    book = add_book(client)
    borrowed = client.put(f"/api/books/{book['id']}", json={"status": "borrowed", "borrower": "Hariny"}).json()
    assert borrowed["status"] == "borrowed"
    assert borrowed["borrower"] == "Hariny"

    returned = client.put(f"/api/books/{book['id']}", json={"status": "available"}).json()
    assert returned["status"] == "available"
    assert returned["borrower"] is None


def test_borrow_without_borrower_fails(client):
    book = add_book(client)
    response = client.put(f"/api/books/{book['id']}", json={"status": "borrowed"})
    assert response.status_code == 400


def test_filter_books_by_status(client):
    first = add_book(client, "Book One")
    add_book(client, "Book Two")
    client.put(f"/api/books/{first['id']}", json={"status": "borrowed", "borrower": "Hariny"})

    borrowed = client.get("/api/books?status=borrowed").json()
    assert [book["title"] for book in borrowed] == ["Book One"]
    assert client.get("/api/books/stats").json() == {"total": 2, "available": 1, "borrowed": 1}


def test_delete_book(client):
    book = add_book(client)
    assert client.delete(f"/api/books/{book['id']}").status_code == 204
    assert client.get(f"/api/books/{book['id']}").status_code == 404


def test_metrics_endpoint(client):
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
