from __future__ import annotations

import os
import secrets
import csv
import io
from datetime import date, datetime, time, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, make_response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

if not os.environ.get("SPORTCENTER_CLOUDFLARE_WORKER"):
    import sqlite3
else:
    sqlite3 = None

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("SPORTCENTER_DB", BASE_DIR / "instance" / "sportcenter.db"))
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
secret_key = os.environ.get("SPORTCENTER_SECRET")
if not os.environ.get("SPORTCENTER_CLOUDFLARE_WORKER") and not secret_key:
    secret_key = secrets.token_urlsafe(48)
app.config.update(SECRET_KEY=secret_key, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")


@app.template_filter("datetime")
def format_datetime(value, fmt="%d.%m.%Y · %H:%M"):
    try:
        return datetime.fromisoformat(value).strftime(fmt)
    except (TypeError, ValueError):
        return value


def db():
    if "db" not in g:
        if app.config.get("CLOUDFLARE_D1"):
            from cloudflare_d1 import D1Connection
            workers_env = request.environ.get("workers.env")
            if workers_env is None:
                raise RuntimeError("Cloudflare Worker environment is missing")
            g.db = D1Connection(workers_env.DB)
        else:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'client', phone TEXT DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS classes (
      id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL,
      description TEXT NOT NULL DEFAULT '', coach TEXT NOT NULL, starts_at TEXT NOT NULL,
      duration INTEGER NOT NULL DEFAULT 60, capacity INTEGER NOT NULL DEFAULT 12,
      room TEXT NOT NULL DEFAULT 'Зал 1'
    );
    CREATE TABLE IF NOT EXISTS bookings (
      id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, class_id)
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute("INSERT INTO users(name,email,password_hash,role,phone) VALUES(?,?,?,?,?)",
                     ("Администратор", "admin@sportcenter.local", generate_password_hash("admin123"), "admin", ""))
    if conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0] == 0:
        samples = [
            ("Йога: баланс и дыхание", "Йога", "Мягкая практика для гибкости, осанки и спокойствия.", "Алия Садыкова", 9, 60, 14, "Зал Mind"),
            ("Силовая: full body", "Фитнес", "Силовая тренировка на всё тело для любого уровня.", "Данияр Ахметов", 11, 55, 12, "Зал Energy"),
            ("Бокс: техника", "Бокс", "Работа над стойкой, движением и базовыми комбинациями.", "Тимур Касенов", 14, 60, 10, "Зал Fight"),
            ("Пилатес: здоровая спина", "Пилатес", "Контроль движения и укрепление мышц корпуса.", "Алия Садыкова", 17, 50, 14, "Зал Mind"),
            ("Функциональная тренировка", "Кроссфит", "Интервальная работа над силой и выносливостью.", "Данияр Ахметов", 19, 60, 12, "Зал Energy"),
            ("Йога: вечернее восстановление", "Йога", "Спокойная растяжка после насыщенного дня.", "Мадина Нурланова", 20, 60, 16, "Зал Mind"),
        ]
        base = datetime.combine(date.today(), time.min)
        for title, cat, desc, coach, hour, duration, cap, room in samples:
            starts = base + timedelta(days=1 if hour < datetime.now().hour + 1 else 0, hours=hour)
            conn.execute("INSERT INTO classes(title,category,description,coach,starts_at,duration,capacity,room) VALUES(?,?,?,?,?,?,?,?)",
                         (title, cat, desc, coach, starts.isoformat(timespec="minutes"), duration, cap, room))
        # Keep one event on the next day even when the schedule is opened late.
        for offset, hour in [(1, 10), (1, 18), (2, 12)]:
            starts = datetime.combine(date.today() + timedelta(days=offset), time(hour))
            conn.execute("INSERT INTO classes(title,category,description,coach,starts_at,duration,capacity,room) VALUES(?,?,?,?,?,?,?,?)",
                         ("Открытая тренировка", "Фитнес", "Знакомство с программой и тренером.", "Данияр Ахметов", starts.isoformat(timespec="minutes"), 45, 16, "Зал Energy"))
    conn.commit()


@app.before_request
def load_user():
    g.user = db().execute("SELECT * FROM users WHERE id=?", (session.get("user_id"),)).fetchone() if session.get("user_id") else None


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not g.user:
            flash("Войдите, чтобы продолжить.", "info")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapped


def class_rows(where="", params=()):
    return db().execute(f"""SELECT c.*, (SELECT COUNT(*) FROM bookings b WHERE b.class_id=c.id) AS booked,
      (SELECT COUNT(*) FROM bookings b WHERE b.class_id=c.id AND b.user_id=?) AS joined
      FROM classes c {where} ORDER BY c.starts_at""", (g.user["id"] if g.user else 0, *params)).fetchall()


@app.route("/")
def home():
    upcoming = class_rows("WHERE c.starts_at >= ?", (datetime.now().isoformat(timespec="minutes"),))
    my_next = None
    if g.user:
        my_next = db().execute("""SELECT c.* FROM classes c JOIN bookings b ON b.class_id=c.id
        WHERE b.user_id=? AND c.starts_at>=? ORDER BY c.starts_at LIMIT 1""",
        (g.user["id"], datetime.now().isoformat(timespec="minutes"))).fetchone()
    return render_template("home.html", classes=upcoming[:3], my_next=my_next)


@app.route("/schedule")
def schedule():
    category = request.args.get("category", "")
    rows = class_rows("WHERE c.starts_at >= ?" + (" AND c.category=?" if category else ""),
                      (datetime.now().isoformat(timespec="minutes"), *((category,) if category else ())))
    categories = [r[0] for r in db().execute("SELECT DISTINCT category FROM classes ORDER BY category")]
    return render_template("schedule.html", classes=rows, categories=categories, selected=category)


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("home"))
    if request.method == "POST":
        name, email, phone, password = (request.form.get(k, "").strip() for k in ("name", "email", "phone", "password"))
        if not name or "@" not in email or len(password) < 6:
            flash("Укажите имя, корректный email и пароль минимум из 6 символов.", "error")
        else:
            try:
                cur = db().execute("INSERT INTO users(name,email,password_hash,phone) VALUES(?,?,?,?)",
                                   (name, email.lower(), generate_password_hash(password), phone))
                db().commit()
                session["user_id"] = cur.lastrowid
                flash("Аккаунт создан. Добро пожаловать!", "success")
                return redirect(url_for("home"))
            except Exception as error:
                duplicate_email = (
                    (sqlite3 is not None and isinstance(error, sqlite3.IntegrityError))
                    or "unique constraint failed" in str(error).lower()
                )
                if not duplicate_email:
                    raise
                flash("Этот email уже зарегистрирован.", "error")
    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("home"))
    if request.method == "POST":
        user = db().execute("SELECT * FROM users WHERE email=?", (request.form.get("email", "").strip().lower(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(request.args.get("next") or url_for("home"))
        flash("Неверный email или пароль.", "error")
    return render_template("auth.html", mode="login")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.post("/book/<int:class_id>")
@login_required
def book(class_id):
    conn = db()
    workout = conn.execute("SELECT * FROM classes WHERE id=?", (class_id,)).fetchone()
    if not workout:
        abort(404)
    if datetime.fromisoformat(workout["starts_at"]) < datetime.now():
        flash("Запись на прошедшее занятие закрыта.", "error")
    elif conn.execute("SELECT 1 FROM bookings WHERE user_id=? AND class_id=?", (g.user["id"], class_id)).fetchone():
        flash("Вы уже записаны на это занятие.", "info")
    elif conn.execute("SELECT COUNT(*) FROM bookings WHERE class_id=?", (class_id,)).fetchone()[0] >= workout["capacity"]:
        flash("Свободных мест больше нет.", "error")
    else:
        conn.execute("INSERT INTO bookings(user_id,class_id) VALUES(?,?)", (g.user["id"], class_id))
        conn.commit()
        flash("Вы записаны! Занятие появилось в разделе «Мои тренировки».", "success")
    return redirect(request.referrer or url_for("schedule"))


@app.post("/cancel/<int:class_id>")
@login_required
def cancel(class_id):
    db().execute("DELETE FROM bookings WHERE user_id=? AND class_id=?", (g.user["id"], class_id))
    db().commit()
    flash("Запись отменена.", "info")
    return redirect(request.referrer or url_for("my_bookings"))


@app.route("/my")
@login_required
def my_bookings():
    rows = db().execute("""SELECT c.*, (SELECT COUNT(*) FROM bookings x WHERE x.class_id=c.id) booked,
      1 joined FROM classes c JOIN bookings b ON b.class_id=c.id
      WHERE b.user_id=? ORDER BY c.starts_at""", (g.user["id"],)).fetchall()
    return render_template("schedule.html", classes=rows, categories=[], selected="", mine=True)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name, phone = request.form.get("name", "").strip(), request.form.get("phone", "").strip()
        if not name:
            flash("Имя не может быть пустым.", "error")
        else:
            db().execute("UPDATE users SET name=?,phone=? WHERE id=?", (name, phone, g.user["id"]))
            db().commit()
            flash("Профиль обновлён.", "success")
            return redirect(url_for("profile"))
    return render_template("profile.html")


@app.route("/admin")
@admin_required
def admin():
    conn = db()
    if request.args.get("export") == "bookings":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["Участник", "Email", "Тренировка", "Дата и время", "Тренер"])
        for row in conn.execute("""SELECT u.name,u.email,c.title,c.starts_at,c.coach FROM bookings b
          JOIN users u ON u.id=b.user_id JOIN classes c ON c.id=b.class_id ORDER BY c.starts_at"""):
            writer.writerow(row)
        response = make_response("\ufeff" + output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = "attachment; filename=sportcenter-bookings.csv"
        return response
    stats = {"users": conn.execute("SELECT COUNT(*) FROM users WHERE role='client'").fetchone()[0],
             "classes": conn.execute("SELECT COUNT(*) FROM classes WHERE starts_at>=?", (datetime.now().isoformat(timespec="minutes"),)).fetchone()[0],
             "bookings": conn.execute("SELECT COUNT(*) FROM bookings b JOIN classes c ON c.id=b.class_id WHERE c.starts_at>=?", (datetime.now().isoformat(timespec="minutes"),)).fetchone()[0]}
    bookings = conn.execute("""SELECT u.name,u.email,c.title,c.starts_at,c.coach FROM bookings b
    JOIN users u ON u.id=b.user_id JOIN classes c ON c.id=b.class_id ORDER BY c.starts_at LIMIT 100""").fetchall()
    classes = conn.execute("SELECT * FROM classes ORDER BY starts_at").fetchall()
    users = conn.execute("SELECT id,name,email,phone,role,created_at FROM users ORDER BY created_at DESC").fetchall()
    return render_template("admin.html", stats=stats, bookings=bookings, classes=classes, users=users)


@app.post("/admin/class")
@admin_required
def create_class():
    form = request.form
    try:
        starts = datetime.fromisoformat(form.get("starts_at", ""))
        title, category, coach = (form.get(k, "").strip() for k in ("title", "category", "coach"))
        duration, capacity = int(form.get("duration", 60)), int(form.get("capacity", 12))
        if not title or not category or not coach or starts < datetime.now() or duration < 15 or not 1 <= capacity <= 100:
            raise ValueError
        db().execute("INSERT INTO classes(title,category,description,coach,starts_at,duration,capacity,room) VALUES(?,?,?,?,?,?,?,?)",
            (title, category, form.get("description", "").strip(), coach, starts.isoformat(timespec="minutes"), duration, capacity, form.get("room", "Зал 1").strip() or "Зал 1"))
        db().commit()
        flash("Занятие добавлено в расписание.", "success")
    except (ValueError, TypeError):
        flash("Проверьте поля занятия, время и вместимость.", "error")
    return redirect(url_for("admin") + "#classes")


@app.post("/admin/class/<int:class_id>/delete")
@admin_required
def delete_class(class_id):
    db().execute("DELETE FROM classes WHERE id=?", (class_id,))
    db().commit()
    flash("Занятие и связанные записи удалены.", "info")
    return redirect(url_for("admin") + "#classes")


@app.post("/admin/user/<int:user_id>")
@admin_required
def update_user(user_id):
    name, phone = request.form.get("name", "").strip(), request.form.get("phone", "").strip()
    if not name:
        flash("Имя пользователя не может быть пустым.", "error")
    elif user_id == g.user["id"] and request.form.get("role") == "client":
        flash("Нельзя снять роль администратора у текущей учётной записи.", "error")
    else:
        role = "admin" if request.form.get("role") == "admin" else "client"
        cursor = db().execute("UPDATE users SET name=?,phone=?,role=? WHERE id=?", (name, phone, role, user_id))
        db().commit()
        if not cursor.rowcount:
            abort(404)
        flash("Данные пользователя сохранены.", "success")
    return redirect(url_for("admin") + "#users")


@app.route("/health")
def health():
    return {"status": "ok"}


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="Этот раздел доступен только администратору."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="Такой страницы или занятия нет."), 404


if not os.environ.get("SPORTCENTER_CLOUDFLARE_WORKER"):
    with app.app_context():
        init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
