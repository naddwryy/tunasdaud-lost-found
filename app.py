import os
from datetime import date
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-before-deployment")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))

def connect():
    if USE_POSTGRES:
        if psycopg is None:
            raise RuntimeError("Paket psycopg belum terpasang.")
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    import sqlite3
    db = sqlite3.connect(os.environ.get("SQLITE_PATH", "lost_found.db"))
    db.row_factory = sqlite3.Row
    return db

def execute(db, sql, params=()):
    # SQL placeholders are adapted for PostgreSQL.
    if USE_POSTGRES:
        sql = sql.replace("?", "%s")
    return db.execute(sql, params)

def init_db():
    with connect() as db:
        if USE_POSTGRES:
            execute(db, """CREATE TABLE IF NOT EXISTS items (
                id SERIAL PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
                color TEXT, location TEXT NOT NULL, found_date TEXT NOT NULL,
                description TEXT, status TEXT NOT NULL DEFAULT 'Belum diambil',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            execute(db, """CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY, name TEXT NOT NULL, category TEXT,
                color TEXT, last_seen TEXT NOT NULL, lost_date TEXT NOT NULL,
                description TEXT, contact TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Menunggu verifikasi',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        else:
            execute(db, """CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                category TEXT NOT NULL, color TEXT, location TEXT NOT NULL,
                found_date TEXT NOT NULL, description TEXT,
                status TEXT NOT NULL DEFAULT 'Belum diambil',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            execute(db, """CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                category TEXT, color TEXT, last_seen TEXT NOT NULL,
                lost_date TEXT NOT NULL, description TEXT, contact TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Menunggu verifikasi',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

init_db()

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            flash("Silakan login sebagai admin terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    with connect() as db:
        if q:
            like = f"%{q}%"
            items = execute(db, """SELECT * FROM items
                WHERE status = 'Belum diambil'
                AND (name LIKE ? OR category LIKE ? OR color LIKE ? OR location LIKE ?)
                ORDER BY id DESC""", (like, like, like, like)).fetchall()
        else:
            items = execute(db, """SELECT * FROM items
                WHERE status = 'Belum diambil' ORDER BY id DESC""").fetchall()
    return render_template("index.html", items=items, q=q)

@app.route("/lapor", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        last_seen = request.form.get("last_seen", "").strip()
        lost_date = request.form.get("lost_date", "").strip()
        contact = request.form.get("contact", "").strip()
        if not all([name, last_seen, lost_date, contact]):
            flash("Nama barang, lokasi terakhir, tanggal, dan kontak wajib diisi.", "danger")
            return render_template("laporan.html", today=date.today().isoformat())
        try:
            date.fromisoformat(lost_date)
        except ValueError:
            flash("Tanggal tidak valid.", "danger")
            return render_template("laporan.html", today=date.today().isoformat())
        with connect() as db:
            execute(db, """INSERT INTO reports
                (name, category, color, last_seen, lost_date, description, contact)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", (
                name, request.form.get("category", "").strip(),
                request.form.get("color", "").strip(), last_seen, lost_date,
                request.form.get("description", "").strip(), contact))
        flash("Laporan berhasil dikirim. Admin sekolah akan menindaklanjutinya.", "success")
        return redirect(url_for("report"))
    return render_template("laporan.html", today=date.today().isoformat())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = os.environ.get("ADMIN_USERNAME", "")
        password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
        supplied_user = request.form.get("username", "")
        supplied_password = request.form.get("password", "")
        if username and password_hash and supplied_user == username and check_password_hash(password_hash, supplied_password):
            session.clear()
            session["admin"] = True
            flash("Login berhasil.", "success")
            return redirect(url_for("dashboard"))
        flash("Username atau password salah. Periksa pengaturan admin di hosting.", "danger")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
@admin_required
def logout():
    session.clear()
    flash("Kamu sudah logout.", "success")
    return redirect(url_for("index"))

@app.route("/admin")
@admin_required
def dashboard():
    with connect() as db:
        items = execute(db, "SELECT * FROM items ORDER BY id DESC").fetchall()
        reports = execute(db, "SELECT * FROM reports ORDER BY id DESC").fetchall()
        total = execute(db, "SELECT COUNT(*) AS n FROM items").fetchone()["n"]
        available = execute(db, "SELECT COUNT(*) AS n FROM items WHERE status='Belum diambil'").fetchone()["n"]
        pending = execute(db, "SELECT COUNT(*) AS n FROM reports WHERE status='Menunggu verifikasi'").fetchone()["n"]
    return render_template("dashboard.html", items=items, reports=reports,
                           total=total, available=available, pending=pending)

@app.route("/admin/barang/tambah", methods=["POST"])
@admin_required
def add_item():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    location = request.form.get("location", "").strip()
    found_date = request.form.get("found_date", "").strip()
    if not all([name, category, location, found_date]):
        flash("Lengkapi nama, kategori, lokasi, dan tanggal ditemukan.", "danger")
        return redirect(url_for("dashboard"))
    try:
        date.fromisoformat(found_date)
    except ValueError:
        flash("Tanggal ditemukan tidak valid.", "danger")
        return redirect(url_for("dashboard"))
    with connect() as db:
        execute(db, """INSERT INTO items
            (name, category, color, location, found_date, description)
            VALUES (?, ?, ?, ?, ?, ?)""", (
            name, category, request.form.get("color", "").strip(), location,
            found_date, request.form.get("description", "").strip()))
    flash("Barang temuan berhasil ditambahkan.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/barang/<int:item_id>/status", methods=["POST"])
@admin_required
def update_item_status(item_id):
    status = request.form.get("status", "")
    if status not in ("Belum diambil", "Sudah diambil"):
        abort(400)
    with connect() as db:
        execute(db, "UPDATE items SET status=? WHERE id=?", (status, item_id))
    flash("Status barang diperbarui.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/barang/<int:item_id>/hapus", methods=["POST"])
@admin_required
def delete_item(item_id):
    with connect() as db:
        execute(db, "DELETE FROM items WHERE id=?", (item_id,))
    flash("Data barang dihapus.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/laporan/<int:report_id>/status", methods=["POST"])
@admin_required
def update_report_status(report_id):
    status = request.form.get("status", "")
    if status not in ("Menunggu verifikasi", "Sedang ditindaklanjuti", "Selesai"):
        abort(400)
    with connect() as db:
        execute(db, "UPDATE reports SET status=? WHERE id=?", (status, report_id))
    flash("Status laporan diperbarui.", "success")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
