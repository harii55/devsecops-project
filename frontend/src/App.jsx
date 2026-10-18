import { useEffect, useState } from "react";

const emptyForm = { title: "", author: "", genre: "" };
const filters = ["all", "available", "borrowed"];

async function request(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

export default function App() {
  const [books, setBooks] = useState([]);
  const [stats, setStats] = useState({ total: 0, available: 0, borrowed: 0 });
  const [filter, setFilter] = useState("all");
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadBooks() {
    try {
      const query = filter === "all" ? "" : `?status=${filter}`;
      const [bookList, bookStats] = await Promise.all([request(`/api/books${query}`), request("/api/books/stats")]);
      setBooks(bookList);
      setStats(bookStats);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBooks();
  }, [filter]);

  async function run(action) {
    try {
      await action();
      await loadBooks();
    } catch (err) {
      setError(err.message);
    }
  }

  function addBook(event) {
    event.preventDefault();
    run(async () => {
      await request("/api/books", { method: "POST", body: JSON.stringify(form) });
      setForm(emptyForm);
    });
  }

  function updateBook(book, changes) {
    run(() => request(`/api/books/${book.id}`, { method: "PUT", body: JSON.stringify(changes) }));
  }

  function borrowBook(book) {
    const borrower = window.prompt(`Who is borrowing "${book.title}"?`)?.trim();
    if (borrower) updateBook(book, { status: "borrowed", borrower });
  }

  function deleteBook(book) {
    if (window.confirm(`Delete "${book.title}"?`)) run(() => request(`/api/books/${book.id}`, { method: "DELETE" }));
  }

  return (
    <div className="page">
      <header>
        <h1>Library Book Tracker</h1>
        <p>Keep track of every book in the library and who has borrowed it.</p>
      </header>

      <section className="stats">
        <div className="card"><span>Total books</span><strong>{stats.total}</strong></div>
        <div className="card"><span>Available</span><strong>{stats.available}</strong></div>
        <div className="card"><span>Borrowed</span><strong>{stats.borrowed}</strong></div>
      </section>

      <form className="add-form" onSubmit={addBook}>
        <input placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        <input placeholder="Author" value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} required />
        <input placeholder="Genre" value={form.genre} onChange={(e) => setForm({ ...form, genre: e.target.value })} required />
        <button type="submit">Add book</button>
      </form>

      <div className="filters">
        {filters.map((name) => (
          <button key={name} className={filter === name ? "active" : ""} onClick={() => setFilter(name)}>
            {name}
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="message">Loading books...</p>
      ) : books.length === 0 ? (
        <p className="message">No books here yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Title</th><th>Author</th><th>Genre</th><th>Status</th><th>Borrower</th><th></th></tr>
            </thead>
            <tbody>
              {books.map((book) => (
                <tr key={book.id}>
                  <td>{book.title}</td>
                  <td>{book.author}</td>
                  <td>{book.genre}</td>
                  <td><span className={`badge ${book.status}`}>{book.status}</span></td>
                  <td>{book.borrower ?? "-"}</td>
                  <td className="actions">
                    {book.status === "available" ? (
                      <button onClick={() => borrowBook(book)}>Borrow</button>
                    ) : (
                      <button onClick={() => updateBook(book, { status: "available" })}>Return</button>
                    )}
                    <button className="delete" onClick={() => deleteBook(book)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
