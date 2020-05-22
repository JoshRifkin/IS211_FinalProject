DROP TABLE IF EXISTS books;

CREATE TABLE books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    isbn13 INTEGER NOT NULL,
    pages INTEGER,
    rating REAL,
    description TEXT
);

