"""
Dashboard sahifasi - Bosh ekran
Real-time monitoring, statistika va yangi foydalanuvchilar uchun tezkor qo'llanma
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from models.database import get_today_summary, get_today_events, get_employee_count, get_all_devices


class StatCard(QFrame):
    """Statistika kartochkasi"""
    def __init__(self, title, value="0", icon="", color="blue", parent=None):
        super().__init__(parent)
        self.color = color
        self._setup_ui(title, value, icon)

    def _setup_ui(self, title, value, icon):
        color_map = {
            "blue": "cardFrameBlue",
            "green": "cardFrameGreen",
            "red": "cardFrameRed",
            "yellow": "cardFrameYellow",
        }
        self.setObjectName(color_map.get(self.color, "cardFrame"))
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        header = QHBoxLayout()
        if icon:
            icon_label = QLabel(icon)
            icon_label.setFont(QFont("Segoe UI Emoji", 18))
            header.addWidget(icon_label)
        title_label = QLabel(title)
        title_label.setObjectName("statLabel")
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("statValue")
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(str(value))


class LiveEventTable(QTableWidget):
    """Real-time voqealar jadvali"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "Vaqt", "Xodim", "ID raqam", "Harakat", "Tekshiruv usuli", "Natija"
        ])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 90)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(3, 110)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(4, 130)
        self.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(5, 110)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setShowGrid(False)

    def add_event(self, event: dict, prepend=True):
        if prepend:
            self.insertRow(0)
            row = 0
        else:
            row = self.rowCount()
            self.insertRow(row)

        time_str = event.get("event_time", "")
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(time_str[:19], fmt)
                time_str = dt.strftime("%H:%M:%S")
                break
            except ValueError:
                continue

        self.setItem(row, 0, QTableWidgetItem(time_str))
        self.setItem(row, 1, QTableWidgetItem(event.get("employee_name", "Noma'lum")))
        self.setItem(row, 2, QTableWidgetItem(str(event.get("employee_no", "-"))))

        event_type = event.get("event_type", "entry")
        type_item = QTableWidgetItem("🟢 KIRISH" if event_type == "entry" else "🔴 CHIQISH")
        type_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        type_item.setForeground(QColor("#22c55e" if event_type == "entry" else "#ef4444"))
        self.setItem(row, 3, type_item)

        method_map = {
            "card": "💳 RFID Karta",
            "face": "👤 Yuzni tanish",
            "fingerprint": "👆 Barmoq izi",
            "qr": "📱 QR Kod"
        }
        self.setItem(row, 4, QTableWidgetItem(method_map.get(event.get("access_method", "card"), "💳 RFID Karta")))

        status = event.get("status", "granted")
        status_item = QTableWidgetItem("✅ Ruxsat berildi" if status == "granted" else "❌ Rad etildi")
        status_item.setForeground(QColor("#22c55e" if status == "granted" else "#ef4444"))
        self.setItem(row, 5, status_item)

        while self.rowCount() > 200:
            self.removeRow(self.rowCount() - 1)


class DashboardPage(QWidget):
    """Dashboard sahifasi"""
    new_event_signal = pyqtSignal(dict)
    open_settings_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.new_event_signal.connect(self._on_new_event)
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # 1. Sarlavha va Soat
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("📊  Jonli Monitoring va Nazorat Paneli")
        title.setObjectName("title")
        title_box.addWidget(title)

        subtitle = QLabel("Turniket orqali kirib-chiqayotgan xodimlarning real-time oqimi")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        clock_box = QVBoxLayout()
        clock_box.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #60a5fa;")
        clock_box.addWidget(self.time_label)

        self.date_label = QLabel()
        self.date_label.setObjectName("subtitle")
        clock_box.addWidget(self.date_label)
        header.addLayout(clock_box)
        layout.addLayout(header)

        # 2. Yangi boshlovchilar uchun qulay maslahat paneli (Onboarding Banner)
        self.guide_banner = QFrame()
        self.guide_banner.setObjectName("cardFrame")
        self.guide_banner.setStyleSheet(
            "background-color: #1e293b; border-left: 4px solid #3b82f6; border-radius: 8px; padding: 10px;"
        )
        banner_layout = QHBoxLayout(self.guide_banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        
        info_icon = QLabel("💡")
        info_icon.setFont(QFont("Segoe UI Emoji", 18))
        banner_layout.addWidget(info_icon)

        banner_text = QLabel(
            "<b>Tezkor boshlash:</b> 1️⃣ <i>Sozlamalar</i> bo'limidan turniketni ulang -> "
            "2️⃣ <i>Telegram Bot</i>ni faollashtiring -> 3️⃣ <i>Xodimlar</i> ro'yxatini to'ldiring."
        )
        banner_text.setStyleSheet("color: #e2e8f0; font-size: 13px;")
        banner_layout.addWidget(banner_text)
        banner_layout.addStretch()

        btn_close_banner = QPushButton("Tushunarli ✕")
        btn_close_banner.setObjectName("btnSecondary")
        btn_close_banner.setFixedHeight(28)
        btn_close_banner.clicked.connect(lambda: self.guide_banner.setVisible(False))
        banner_layout.addWidget(btn_close_banner)
        layout.addWidget(self.guide_banner)

        # 3. Statistika kartochkalari
        stats_layout = QGridLayout()
        stats_layout.setSpacing(14)
        self.card_entries = StatCard("BUGUN KIRGANLAR", "0", "🟢", "green")
        self.card_exits = StatCard("BUGUN CHIQQANLAR", "0", "🔴", "red")
        self.card_inside = StatCard("AYNI VAQTDA ICHKARIDA", "0", "🏢", "blue")
        self.card_employees = StatCard("JAMI XODIMLAR SONI", "0", "👥", "yellow")
        stats_layout.addWidget(self.card_entries, 0, 0)
        stats_layout.addWidget(self.card_exits, 0, 1)
        stats_layout.addWidget(self.card_inside, 0, 2)
        stats_layout.addWidget(self.card_employees, 0, 3)
        layout.addLayout(stats_layout)

        # 4. Turniketlar holati
        devices_header = QHBoxLayout()
        devices_title = QLabel("🖥️  Ulangan Turniketlar")
        devices_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        devices_header.addWidget(devices_title)
        devices_header.addStretch()
        layout.addLayout(devices_header)

        self.devices_layout = QHBoxLayout()
        self.devices_layout.setSpacing(12)
        layout.addLayout(self.devices_layout)

        # 5. Jonli voqealar jurnali
        events_header = QHBoxLayout()
        events_title = QLabel("⚡  Jonli Harakatlar Oqimi (Real-time)")
        events_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        events_header.addWidget(events_title)
        events_header.addStretch()

        self.event_count_label = QLabel("0 ta voqea")
        self.event_count_label.setObjectName("subtitle")
        events_header.addWidget(self.event_count_label)
        layout.addLayout(events_header)

        self.events_table = LiveEventTable()
        layout.addWidget(self.events_table, 1)

    def _setup_timer(self):
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.refresh_stats)
        self.stats_timer.start(5000)

        self._update_clock()
        self.refresh_stats()

    def _update_clock(self):
        now = datetime.now()
        self.time_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(now.strftime("%d-%B, %Y-yil"))

    def refresh_stats(self):
        try:
            summary = get_today_summary()
            self.card_entries.set_value(summary["total_entries"])
            self.card_exits.set_value(summary["total_exits"])
            self.card_inside.set_value(max(0, summary["currently_inside"]))
            self.card_employees.set_value(get_employee_count())
            self.event_count_label.setText(f"{summary['total_entries'] + summary['total_exits']} ta o'tish qayd etildi")
            self._update_devices()
        except Exception as e:
            print(f"Stats yangilash xatosi: {e}")

    def _update_devices(self):
        while self.devices_layout.count():
            item = self.devices_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        devices = get_all_devices()
        if not devices:
            lbl = QLabel("⚠️ Hali turniket ulanmagan. 'Sozlamalar' bo'limiga kirib turniket IP manzilini kiriting.")
            lbl.setStyleSheet("color: #f59e0b; padding: 6px;")
            self.devices_layout.addWidget(lbl)
            return

        for dev in devices:
            card = QFrame()
            card.setObjectName("cardFrame")
            card.setMinimumWidth(220)
            card.setMaximumWidth(320)
            cl = QVBoxLayout(card)
            cl.setSpacing(4)

            status_icon = "🟢" if dev.get("is_online") else "🔴"
            nl = QLabel(f"{status_icon}  <b>{dev['name']}</b>")
            cl.addWidget(nl)

            il = QLabel(f"IP: {dev['ip_address']}:{dev['port']}")
            il.setObjectName("subtitle")
            cl.addWidget(il)

            st = "Online (Bog'langan)" if dev.get("is_online") else "Offline (Aloqa yo'q)"
            sl = QLabel(st)
            sl.setStyleSheet(f"color: {'#22c55e' if dev.get('is_online') else '#ef4444'}; font-weight: bold; font-size: 11px;")
            cl.addWidget(sl)

            self.devices_layout.addWidget(card)

        self.devices_layout.addStretch()

    def _on_new_event(self, event: dict):
        self.events_table.add_event(event, prepend=True)
        self.refresh_stats()

    def load_today_events(self):
        events = get_today_events()
        self.events_table.setRowCount(0)
        for event in reversed(events):
            self.events_table.add_event(event, prepend=True)
