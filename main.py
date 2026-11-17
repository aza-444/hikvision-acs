"""
Hikvision Turniket Boshqaruv Tizimi (Access Control System)
iVMS-4200 analogi - Xodimlar kirish-chiqishini nazorat qilish va Telegram bot integratsiyasi
"""
import sys
import os
import threading
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QMessageBox,
    QStatusBar, QDialog, QTextBrowser
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont

# Loyiha modullari
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import (
    init_database, get_all_devices, update_device_status,
    add_access_event, get_employee_by_card, get_employee_by_no,
    get_all_employees, add_employee
)
from services.hikvision_api import HikvisionDevice, EventPoller
from services.telegram_bot import TelegramNotifier
from ui.dashboard import DashboardPage
from ui.employees import EmployeesPage
from ui.events import EventsPage
from ui.reports import ReportsPage
from ui.settings import SettingsPage


class HelpDialog(QDialog):
    """Foydalanuvchi uchun tushunarli o'zbek tilidagi qo'llanma dialogi"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📖 Dasturdan Foydalanish Qo'llanmasi")
        self.resize(750, 550)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml("""
        <h2 style="color: #60a5fa;">🛡️ Hikvision Turniket Nazorati — Oddiy Qo'llanma</h2>
        <p>Ushbu dastur orqali xodimlarning ishga kelib-ketish vaqtini osonlik bilan nazorat qilishingiz mumkin.</p>
        
        <hr style="border: 1px solid #334155;"/>

        <h3 style="color: #34d399;">1️⃣ Turniketni dasturga qanday ulayman?</h3>
        <ul>
            <li>Chap menyudagi <b>⚙️ Sozlamalar</b> bo'limiga kiring.</li>
            <li><b>"🔍 Tarmoqdan avtomatik qidirish (SADP)"</b> tugmasini bosing. Dastur kompyuteringiz ulangan tarmoqdagi barcha Hikvision turniketlarini o'zi topadi.</li>
            <li>Turniket parolini kiritib, <b>"Saqlash"</b> tugmasini bosing.</li>
        </ul>

        <h3 style="color: #34d399;">2️⃣ Kirish-chiqish xabarlarini Telegramga qanday ulayman?</h3>
        <ul>
            <li>Telegramda <b>@BotFather</b> botiga kirib, <code>/newbot</code> orqali yangi bot yarating va <b>Token</b> oling.</li>
            <li>Dasturda <b>⚙️ Sozlamalar -> ✈️ Telegram Bot</b> bo'limiga o'ting.</li>
            <li>Katakchani yoqing, Token va o'z Telegram ID raqamingizni (yoki guruh ID) kiriting.</li>
            <li><b>"📩 Botga sinov xabari yuborish"</b> tugmasi orqali tekshiring. Endi har bir o'tish Telegramga real-time boradi!</li>
        </ul>

        <h3 style="color: #34d399;">3️⃣ Xodimlarni qanday ro'yxatga olaman?</h3>
        <ul>
            <li><b>👥 Xodimlar</b> bo'limiga kiring va <b>"➕ Yangi xodim"</b> tugmasini bosing.</li>
            <li>Ism, familiya, bo'lim va xodimga berilgan karta raqamini kiriting.</li>
        </ul>

        <h3 style="color: #34d399;">4️⃣ Oylik hisobot va Excel tabel qayerda?</h3>
        <ul>
            <li><b>📈 Hisobotlar</b> bo'limiga kiring.</li>
            <li>Kerakli sana oralig'ini tanlab, <b>"📥 Excel"</b> tugmasini bosing. Barcha kelgan-ketgan vaqtlar va ishlagan soatlar chiroyli Excel faylga tushadi.</li>
        </ul>

        <h3 style="color: #f87171;">5️⃣ Turniketni shoshilinch ochish kerak bo'lsa:</h3>
        <ul>
            <li>Chap tomonda yashil <b>"🔓 Turniketni ochish"</b> tugmasi bor. Uni bossangiz, turniket darhol masofadan ochiladi.</li>
        </ul>
        """)
        layout.addWidget(browser)

        btn_close = QPushButton("Tushundim, rahmat!")
        btn_close.setFixedHeight(36)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


class DeviceSyncManager(QObject):
    """Qurilmalar bilan fonda doimiy ishlovchi va voqealarni yetkazuvchi menejer"""
    event_received = pyqtSignal(dict)
    device_status_changed = pyqtSignal(int, bool)

    def __init__(self):
        super().__init__()
        self.pollers = []
        self.running = True

    def start(self):
        devices = get_all_devices()
        for dev in devices:
            self._start_worker(dev)

    def _start_worker(self, dev):
        hk = HikvisionDevice(dev["ip_address"], dev["port"], dev["username"], dev["password"])

        def on_event_callback(parsed_event):
            emp_no = parsed_event.get("employee_no")
            card_no = parsed_event.get("card_no")

            emp = None
            if emp_no:
                emp = get_employee_by_no(emp_no)
            elif card_no:
                emp = get_employee_by_card(card_no)

            emp_name = f"{emp['first_name']} {emp['last_name']}" if emp else parsed_event.get("employee_name") or "Noma'lum"
            emp_id = emp["id"] if emp else None

            record = {
                "employee_id": emp_id,
                "employee_no": emp_no or (emp["employee_no"] if emp else ""),
                "employee_name": emp_name,
                "device_id": dev["id"],
                "device_name": dev["name"],
                "event_type": parsed_event.get("event_type", "entry"),
                "access_method": parsed_event.get("access_method", "card"),
                "card_no": card_no or (emp["card_no"] if emp else ""),
                "event_time": parsed_event.get("event_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "status": parsed_event.get("status", "granted"),
                "temperature": parsed_event.get("temperature", 0),
                "photo_url": "",
                "raw_data": str(parsed_event.get("raw", ""))
            }

            add_access_event(record)
            self.event_received.emit(record)
            TelegramNotifier.notify_access_event(record)

        poller = EventPoller(hk, on_event_callback, interval=4)
        poller.start()
        self.pollers.append(poller)


class MainWindow(QMainWindow):
    """Asosiy dastur oynasi"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hikvision Turniket Nazorat Tizimi - (iVMS Pro)")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 650)

        self._init_ui()
        self.dashboard_page.load_today_events()

        self.sync_manager = DeviceSyncManager()
        self.sync_manager.event_received.connect(self._on_live_event)
        self.sync_manager.device_status_changed.connect(self._on_device_status)
        self.sync_manager.start()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Yon panel (Sidebar)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(8)

        logo_layout = QHBoxLayout()
        logo_icon = QLabel("🛡️")
        logo_icon.setFont(QFont("Segoe UI Emoji", 22))
        logo_layout.addWidget(logo_icon)

        logo_title = QLabel("HIK-ACCESS\nPRO")
        logo_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        logo_title.setStyleSheet("color: #60a5fa; line-height: 1.1;")
        logo_layout.addWidget(logo_title)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)

        sidebar_layout.addSpacing(20)

        self.btn_dashboard = QPushButton("  📊  Dashboard")
        self.btn_dashboard.setObjectName("sidebarBtn")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)
        self.btn_dashboard.clicked.connect(lambda: self._switch_page(0))
        sidebar_layout.addWidget(self.btn_dashboard)

        self.btn_employees = QPushButton("  👥  Xodimlar")
        self.btn_employees.setObjectName("sidebarBtn")
        self.btn_employees.setCheckable(True)
        self.btn_employees.clicked.connect(lambda: self._switch_page(1))
        sidebar_layout.addWidget(self.btn_employees)

        self.btn_events = QPushButton("  📋  Jurnal")
        self.btn_events.setObjectName("sidebarBtn")
        self.btn_events.setCheckable(True)
        self.btn_events.clicked.connect(lambda: self._switch_page(2))
        sidebar_layout.addWidget(self.btn_events)

        self.btn_reports = QPushButton("  📈  Hisobotlar")
        self.btn_reports.setObjectName("sidebarBtn")
        self.btn_reports.setCheckable(True)
        self.btn_reports.clicked.connect(lambda: self._switch_page(3))
        sidebar_layout.addWidget(self.btn_reports)

        self.btn_settings = QPushButton("  ⚙️  Sozlamalar")
        self.btn_settings.setObjectName("sidebarBtn")
        self.btn_settings.setCheckable(True)
        self.btn_settings.clicked.connect(lambda: self._switch_page(4))
        sidebar_layout.addWidget(self.btn_settings)

        self.nav_buttons = [
            self.btn_dashboard, self.btn_employees,
            self.btn_events, self.btn_reports, self.btn_settings
        ]

        sidebar_layout.addStretch()

        # Yordam tugmasi
        btn_help = QPushButton("  ❓  Yordam / Qo'llanma")
        btn_help.setObjectName("btnOutline")
        btn_help.clicked.connect(self._show_help)
        sidebar_layout.addWidget(btn_help)

        # Turniketni ochish tugmasi
        btn_open_turnstile = QPushButton("🔓 Turniketni ochish")
        btn_open_turnstile.setObjectName("btnSuccess")
        btn_open_turnstile.setToolTip("Turniketni darhol masofadan ochish")
        btn_open_turnstile.clicked.connect(self._remote_open_turnstile)
        sidebar_layout.addWidget(btn_open_turnstile)

        main_layout.addWidget(sidebar)

        # 2. O'ng tomon
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.pages = QStackedWidget()
        self.dashboard_page = DashboardPage(self)
        self.employees_page = EmployeesPage(self)
        self.events_page = EventsPage(self)
        self.reports_page = ReportsPage(self)
        self.settings_page = SettingsPage(self)

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.employees_page)
        self.pages.addWidget(self.events_page)
        self.pages.addWidget(self.reports_page)
        self.pages.addWidget(self.settings_page)

        content_layout.addWidget(self.pages)
        main_layout.addWidget(content_container)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("🟢 Tizim faol | ISAPI & AlertStream ulandi")

    def _switch_page(self, index: int):
        self.pages.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        if index == 0:
            self.dashboard_page.refresh_stats()
        elif index == 1:
            self.employees_page.refresh_table()
        elif index == 2:
            self.events_page._load_events()

    def _show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def _on_live_event(self, event_data: dict):
        self.dashboard_page.new_event_signal.emit(event_data)
        emp_name = event_data.get("employee_name", "Noma'lum")
        typ = "Kirdi" if event_data.get("event_type") == "entry" else "Chiqdi"
        self.status_bar.showMessage(f"⚡ Yangi yozuv: {emp_name} - {typ} ({event_data.get('event_time')})", 6000)

    def _on_device_status(self, dev_id: int, is_online: bool):
        self.dashboard_page.refresh_stats()

    def _remote_open_turnstile(self):
        devices = get_all_devices()
        if not devices:
            QMessageBox.warning(self, "Qurilma topilmadi", "Hozirda birorta ham turniket qo'shilmagan!\nSozlamalar bo'limidan turniketni ulang.")
            return

        success_count = 0
        for dev in devices:
            try:
                hk = HikvisionDevice(dev["ip_address"], dev["port"], dev["username"], dev["password"])
                res = hk.open_door(door_no=1)
                if res and "error" not in res:
                    success_count += 1
            except Exception:
                pass

        if success_count > 0:
            QMessageBox.information(self, "Bajarildi", f"{success_count} ta turniketga ochish signali yuborildi!")
        else:
            QMessageBox.warning(self, "Turniket aloqasi", "Turniket qurilmasiga ulanib bo'lmadi.\nIP manzil va tarmoqni tekshiring.")


def seed_demo_data_if_empty():
    employees = get_all_employees(active_only=False)
    if not employees:
        demo_staff = [
            {"employee_no": "1001", "first_name": "Alisher", "last_name": "Navoiy", "department": "Rahbariyat", "position": "Bosh direktor", "phone": "+998 90 123 45 67", "email": "director@company.uz", "card_no": "A1B2C3D4", "photo_path": ""},
            {"employee_no": "1002", "first_name": "Bobur", "last_name": "Zahiriddin", "department": "IT bo'limi", "position": "Senior Developer", "phone": "+998 90 234 56 78", "email": "bobur@company.uz", "card_no": "B2C3D4E5", "photo_path": ""},
            {"employee_no": "1003", "first_name": "Zulfiya", "last_name": "Isroilova", "department": "HR", "position": "HR Menejer", "phone": "+998 90 345 67 89", "email": "hr@company.uz", "card_no": "C3D4E5F6", "photo_path": ""},
            {"employee_no": "1004", "first_name": "Ulug'bek", "last_name": "Mirzo", "department": "IT bo'limi", "position": "Tizim Administratori", "phone": "+998 90 456 78 90", "email": "admin@company.uz", "card_no": "D4E5F6A7", "photo_path": ""},
            {"employee_no": "1005", "first_name": "Nodira", "last_name": "Komilova", "department": "Buxgalteriya", "position": "Bosh buxgalter", "phone": "+998 90 567 89 01", "email": "finance@company.uz", "card_no": "E5F6A7B8", "photo_path": ""}
        ]
        for staff in demo_staff:
            add_employee(staff)


def main():
    init_database()
    seed_demo_data_if_empty()

    app = QApplication(sys.argv)
    app.setApplicationName("Hikvision Access Control Pro")

    style_path = os.path.join(os.path.dirname(__file__), "resources", "styles", "dark_theme.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
