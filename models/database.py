"""
Ma'lumotlar bazasi modeli - SQLite
Xodimlar, qurilmalar va kirish-chiqish yozuvlari
"""
import sqlite3
import os
from datetime import datetime, timedelta


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "access_control.db")


def get_connection():
    """Ma'lumotlar bazasiga ulanish"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """Ma'lumotlar bazasini yaratish"""
    conn = get_connection()
    cursor = conn.cursor()

    # Xodimlar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_no TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            department TEXT DEFAULT '',
            position TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            card_no TEXT DEFAULT '',
            photo_path TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # Bo'limlar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # Qurilmalar jadvali (turniketlar)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            port INTEGER DEFAULT 80,
            username TEXT DEFAULT 'admin',
            password TEXT DEFAULT '',
            device_type TEXT DEFAULT 'turnstile',
            serial_number TEXT DEFAULT '',
            is_online INTEGER DEFAULT 0,
            last_heartbeat TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # Kirish-chiqish yozuvlari
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            employee_no TEXT,
            employee_name TEXT DEFAULT '',
            device_id INTEGER,
            device_name TEXT DEFAULT '',
            event_type TEXT NOT NULL,  -- 'entry' yoki 'exit'
            access_method TEXT DEFAULT 'card',  -- 'card', 'face', 'fingerprint', 'qr'
            card_no TEXT DEFAULT '',
            event_time TEXT NOT NULL,
            status TEXT DEFAULT 'granted',  -- 'granted', 'denied'
            temperature REAL DEFAULT 0,
            photo_url TEXT DEFAULT '',
            raw_data TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (employee_id) REFERENCES employees(id),
            FOREIGN KEY (device_id) REFERENCES devices(id)
        )
    """)

    # Ish vaqti jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_time TEXT NOT NULL,  -- '09:00'
            end_time TEXT NOT NULL,    -- '18:00'
            late_threshold INTEGER DEFAULT 15,  -- daqiqa
            early_leave_threshold INTEGER DEFAULT 15,
            is_default INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # Dastur sozlamalari
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Indekslar
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON access_events(event_time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_employee ON access_events(employee_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON access_events(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_no ON employees(employee_no)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_card ON employees(card_no)")

    # Standart ma'lumotlar
    cursor.execute("SELECT COUNT(*) FROM departments")
    if cursor.fetchone()[0] == 0:
        departments = [
            ("IT bo'limi", "Axborot texnologiyalari"),
            ("Buxgalteriya", "Moliyaviy hisob-kitob"),
            ("HR", "Kadrlar bo'limi"),
            ("Xavfsizlik", "Xavfsizlik xizmati"),
            ("Rahbariyat", "Boshqaruv"),
        ]
        cursor.executemany("INSERT INTO departments (name, description) VALUES (?, ?)", departments)

    cursor.execute("SELECT COUNT(*) FROM work_schedules")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO work_schedules (name, start_time, end_time, late_threshold, early_leave_threshold, is_default)
            VALUES ('Standart', '09:00', '18:00', 15, 15, 1)
        """)

    # Standart sozlamalar
    default_settings = {
        "company_name": "Kompaniya nomi",
        "auto_refresh_interval": "10",
        "event_poll_interval": "5",
        "language": "uz",
        "theme": "dark",
    }
    for key, value in default_settings.items():
        cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    conn.commit()
    conn.close()


# ============================================================
# Xodimlar bilan ishlash
# ============================================================

def get_all_employees(active_only=True):
    conn = get_connection()
    if active_only:
        rows = conn.execute(
            "SELECT * FROM employees WHERE is_active=1 ORDER BY last_name, first_name"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM employees ORDER BY last_name, first_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_employee(employee_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_employee_by_card(card_no):
    conn = get_connection()
    row = conn.execute("SELECT * FROM employees WHERE card_no=? AND is_active=1", (card_no,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_employee_by_no(employee_no):
    conn = get_connection()
    row = conn.execute("SELECT * FROM employees WHERE employee_no=? AND is_active=1", (employee_no,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_employee(data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO employees (employee_no, first_name, last_name, department, position, phone, email, card_no, photo_path)
        VALUES (:employee_no, :first_name, :last_name, :department, :position, :phone, :email, :card_no, :photo_path)
    """, data)
    conn.commit()
    emp_id = cursor.lastrowid
    conn.close()
    return emp_id


def update_employee(employee_id, data: dict):
    conn = get_connection()
    data["id"] = employee_id
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE employees SET
            employee_no=:employee_no, first_name=:first_name, last_name=:last_name,
            department=:department, position=:position, phone=:phone, email=:email,
            card_no=:card_no, photo_path=:photo_path, updated_at=:updated_at
        WHERE id=:id
    """, data)
    conn.commit()
    conn.close()


def upsert_employee_from_device(data: dict) -> tuple[int, bool]:
    """
    Turniketdan import qilingan xodimni bazaga kiritish yoki yangilash.
    Qaytaradi: (employee_id, is_new: bool)
    """
    conn = get_connection()
    emp_no = str(data.get("employee_no", "")).strip()
    if not emp_no:
        conn.close()
        return 0, False

    row = conn.execute("SELECT id, first_name, last_name, card_no, department FROM employees WHERE employee_no=?", (emp_no,)).fetchone()
    if row:
        emp_id = row["id"]
        new_card = data.get("card_no") or row["card_no"]
        new_first = data.get("first_name") or row["first_name"]
        new_last = data.get("last_name") or row["last_name"]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute("""
            UPDATE employees SET
                first_name=?, last_name=?, card_no=?, is_active=1, updated_at=?
            WHERE id=?
        """, (new_first, new_last, new_card, now, emp_id))
        conn.commit()
        conn.close()
        return emp_id, False
    else:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO employees (employee_no, first_name, last_name, department, position, phone, email, card_no, photo_path)
            VALUES (:employee_no, :first_name, :last_name, :department, :position, :phone, :email, :card_no, :photo_path)
        """, data)
        conn.commit()
        emp_id = cursor.lastrowid
        conn.close()
        return emp_id, True


def delete_employee(employee_id):
    conn = get_connection()
    conn.execute("UPDATE employees SET is_active=0 WHERE id=?", (employee_id,))
    conn.commit()
    conn.close()


def search_employees(query):
    conn = get_connection()
    q = f"%{query}%"
    rows = conn.execute("""
        SELECT * FROM employees WHERE is_active=1
        AND (first_name LIKE ? OR last_name LIKE ? OR employee_no LIKE ? OR card_no LIKE ? OR department LIKE ?)
        ORDER BY last_name, first_name
    """, (q, q, q, q, q)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_employee_count():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM employees WHERE is_active=1").fetchone()[0]
    conn.close()
    return count


# ============================================================
# Qurilmalar bilan ishlash
# ============================================================

def get_all_devices():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM devices ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_device(device_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM devices WHERE id=?", (device_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_device(data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO devices (name, ip_address, port, username, password, device_type, serial_number)
        VALUES (:name, :ip_address, :port, :username, :password, :device_type, :serial_number)
    """, data)
    conn.commit()
    dev_id = cursor.lastrowid
    conn.close()
    return dev_id


def update_device(device_id, data: dict):
    conn = get_connection()
    data["id"] = device_id
    conn.execute("""
        UPDATE devices SET
            name=:name, ip_address=:ip_address, port=:port,
            username=:username, password=:password,
            device_type=:device_type, serial_number=:serial_number
        WHERE id=:id
    """, data)
    conn.commit()
    conn.close()


def delete_device(device_id):
    conn = get_connection()
    conn.execute("DELETE FROM devices WHERE id=?", (device_id,))
    conn.commit()
    conn.close()


def update_device_status(device_id, is_online):
    conn = get_connection()
    conn.execute(
        "UPDATE devices SET is_online=?, last_heartbeat=? WHERE id=?",
        (1 if is_online else 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), device_id),
    )
    conn.commit()
    conn.close()


# ============================================================
# Kirish-chiqish yozuvlari
# ============================================================

def add_access_event(data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO access_events
            (employee_id, employee_no, employee_name, device_id, device_name,
             event_type, access_method, card_no, event_time, status, temperature, photo_url, raw_data)
        VALUES
            (:employee_id, :employee_no, :employee_name, :device_id, :device_name,
             :event_type, :access_method, :card_no, :event_time, :status, :temperature, :photo_url, :raw_data)
    """, data)
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    return event_id


def get_access_events(date_from=None, date_to=None, employee_id=None,
                       event_type=None, limit=500):
    conn = get_connection()
    query = "SELECT * FROM access_events WHERE 1=1"
    params = []

    if date_from:
        query += " AND event_time >= ?"
        params.append(date_from)
    if date_to:
        query += " AND event_time <= ?"
        params.append(date_to)
    if employee_id:
        query += " AND employee_id = ?"
        params.append(employee_id)
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)

    query += " ORDER BY event_time DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_today_events():
    today = datetime.now().strftime("%Y-%m-%d")
    return get_access_events(date_from=f"{today} 00:00:00", date_to=f"{today} 23:59:59", limit=1000)


def get_today_summary():
    """Bugungi statistika"""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")

    total_entries = conn.execute(
        "SELECT COUNT(*) FROM access_events WHERE event_type='entry' AND event_time LIKE ?",
        (f"{today}%",),
    ).fetchone()[0]

    total_exits = conn.execute(
        "SELECT COUNT(*) FROM access_events WHERE event_type='exit' AND event_time LIKE ?",
        (f"{today}%",),
    ).fetchone()[0]

    unique_employees = conn.execute(
        "SELECT COUNT(DISTINCT employee_id) FROM access_events WHERE event_time LIKE ? AND employee_id IS NOT NULL",
        (f"{today}%",),
    ).fetchone()[0]

    denied = conn.execute(
        "SELECT COUNT(*) FROM access_events WHERE status='denied' AND event_time LIKE ?",
        (f"{today}%",),
    ).fetchone()[0]

    conn.close()
    return {
        "total_entries": total_entries,
        "total_exits": total_exits,
        "unique_employees": unique_employees,
        "denied": denied,
        "currently_inside": total_entries - total_exits,
    }


def get_employee_attendance(employee_id, date_from, date_to):
    """Xodimning davomati"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT DATE(event_time) as date, MIN(event_time) as first_entry, MAX(event_time) as last_exit,
               COUNT(CASE WHEN event_type='entry' THEN 1 END) as entries,
               COUNT(CASE WHEN event_type='exit' THEN 1 END) as exits
        FROM access_events
        WHERE employee_id=? AND event_time BETWEEN ? AND ?
        GROUP BY DATE(event_time)
        ORDER BY date
    """, (employee_id, date_from, date_to)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# Bo'limlar
# ============================================================

def get_all_departments():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM departments ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_department(name, description=""):
    conn = get_connection()
    conn.execute("INSERT INTO departments (name, description) VALUES (?, ?)", (name, description))
    conn.commit()
    conn.close()


def delete_department(dept_id):
    conn = get_connection()
    conn.execute("DELETE FROM departments WHERE id=?", (dept_id,))
    conn.commit()
    conn.close()


# ============================================================
# Sozlamalar
# ============================================================

def get_setting(key, default=""):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


# ============================================================
# Hisobot uchun
# ============================================================

def get_department_stats(date_from, date_to):
    """Bo'limlar bo'yicha statistika"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.department,
               COUNT(DISTINCT e.id) as total_employees,
               COUNT(CASE WHEN ae.event_type='entry' THEN 1 END) as total_entries,
               COUNT(CASE WHEN ae.event_type='exit' THEN 1 END) as total_exits
        FROM employees e
        LEFT JOIN access_events ae ON e.id = ae.employee_id
            AND ae.event_time BETWEEN ? AND ?
        WHERE e.is_active=1
        GROUP BY e.department
        ORDER BY e.department
    """, (date_from, date_to)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_late_arrivals(date, schedule_start="09:00"):
    """Kech kelganlar"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.*, MIN(ae.event_time) as arrival_time
        FROM employees e
        JOIN access_events ae ON e.id = ae.employee_id
        WHERE ae.event_type='entry' AND DATE(ae.event_time)=?
        GROUP BY e.id
        HAVING TIME(MIN(ae.event_time)) > ?
        ORDER BY arrival_time
    """, (date, schedule_start)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
