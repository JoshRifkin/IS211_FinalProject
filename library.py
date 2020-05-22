import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from contextlib import closing
import requests

app = Flask(__name__)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'library.db'),
    SECRET_KEY=os.urandom(24),
    USERNAME='admin',
    PASSWORD='password'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'db'):
        g.db = connect_db()
    return g.db


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.before_request
def before_request():
    """Opens the database at the beginning of the request"""
    g.db = connect_db()


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You\'ve been logged in successfully.')
            return redirect(url_for('dashboard'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('loggedIn', None)
    flash('You\'ve been logged out successfully.')
    return redirect(url_for('login'))


@app.route('/dashboard', methods=['GET'])
def dashboard():
    if not session.get('logged_in'):
        redirect(url_for('login'))
    db = get_db()
    books = db.execute('SELECT title, author, pages, rating, id FROM books').fetchall()

    return render_template('dashboard.html', books=books)


@app.route('/addBook', methods=['GET', 'POST'])
def addBook():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    if request.method == 'GET':
        return render_template('addBook.html')
    elif request.method == 'POST':
        url = 'https://www.googleapis.com/books/v1/volumes?q='
        searchTerm = request.form['search']
        searchURL = url + searchTerm
        r = requests.get(searchURL)
        book = r.json()['items'][0]['volumeInfo']
        try:
            bookInfo = {
                'title': book['title'],
                'description': book['description'],
                'author': book['authors'][0],
                'pages': book['pageCount'],
                'rating': book['averageRating'],
                'isbn13': book['industryIdentifiers'][0]['identifier']
            }
        except Exception:
            flash("Error parsing book information. Please search again.")
            return redirect(url_for('dashboard'))
        try:
            exists = db.execute('SELECT * FROM books WHERE isbn13 = ?', [bookInfo['isbn13']]).fetchone()
        except Exception:
            exists = True
        if exists:
            flash("That book is already in your library.")
            return redirect(url_for('dashboard'))
        else:
            db.execute(
                'INSERT INTO books (title, author, isbn13, pages, rating, description) VALUES (?, ?, ?, ?, ?, ?)',
                [bookInfo['title'], bookInfo['author'], bookInfo['isbn13'], bookInfo['pages'],
                 bookInfo['rating'], bookInfo['description'], ])
            db.commit()
            flash('Book added to library successfully.')
            return redirect(url_for('dashboard'))


@app.route('/delete/<id>', methods=['GET'])
def delete(id):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('DELETE FROM books WHERE id = ?', id)
    db.commit()
    flash("Book has been successfully removed from your library.")
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    init_db()
    app.run()

