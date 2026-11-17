"""
Sozlamalar sahifasi - Qurilmalar, Telegram Bot va tizim parametrlari
Intellektual SADP qidiruv, tarmoqdagi qurilmalarni ro'yxatdan tanlash va batafsil diagnostika
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QDialog, QFormLayout, QComboBox, QMessageBox, QSpinBox,
    QFrame, QTabWidget, QGroupBox, QCheckBox, QProgressBar,
    QRadioButton, QButtonGroup, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from models.database import (
    get_all_devices, add_device, update_device, delete_device,
    get_all_departments, add_department, delete_department,
    get_setting, set_setting, update_device_status
)
from services.hikvision_api import HikvisionDevice
from services.telegram_bot import TelegramNotifier
from services.device_discovery import DeviceDiscovery


class ScanThread(QThread):
    """Tarmoqdagi qurilmalarni fonda qidirish oqimi"""
    scan_completed = pyqtSignal(list)

    def run(self):
        devices = DeviceDiscovery.discover_all_devices()
        self.scan_completed.emit(devices)


class DiscoveredDevicesDialog(QDialog):
    """Tarmoqdagi topilgan barcha Hikvision turniketlarini ko'rsatish va tanlash oynasi"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Tarmoqdagi Hikvision Qurilmalari")
        self.resize(750, 480)
        self.selected_device = None
        self._init_ui()
        self._start_scan()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QVBoxLayout()
        title = QLabel("📡 Tarmoqdagi Hikvision Turniket va Terminallari")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.addWidget(title)

        subtitle = QLabel("Lokal tarmoqdagi barcha faol qurilmalar avtomatik aniqlanmoqda. Keraklisini tanlab 'Ushbu qurilmani qo'shish' tugmasini bosing.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        header.addWidget(subtitle)
        layout.addLayout(header)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Cheksiz animatsiya
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("🔎 Tarmoq skanerlanmoqda (SADP & Subnet)...")
        self.status_label.setStyleSheet("color: #60a5fa;")
        layout.addWidget(self.status_label)

        # Jadval
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Nomi / Model", "IP Manzil", "Port", "Seriya Raqami", "Amal"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 140)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 70)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 120)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)

        # Tugmalar
        bottom = QHBoxLayout()
        btn_rescan = QPushButton("🔄 Qaytadan qidirish")
        btn_rescan.setObjectName("btnSecondary")
        btn_rescan.clicked.connect(self._start_scan)
        bottom.addWidget(btn_rescan)
        bottom.addStretch()

        btn_cancel = QPushButton("Yopish")
        btn_cancel.setObjectName("btnOutline")
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)
        layout.addLayout(bottom)

    def _start_scan(self):
        self.progress_bar.setVisible(True)
        self.status_label.setText("🔎 Tarmoq skanerlanmoqda (SADP & Subnet)...")
        self.table.setRowCount(0)
        self.thread = ScanThread()
        self.thread.scan_completed.connect(self._on_scan_completed)
        self.thread.start()

    def _on_scan_completed(self, devices):
        self.progress_bar.setVisible(False)
        self.devices_list = devices

        if not devices:
            self.status_label.setText("⚠️ Tarmoqda Hikvision qurilmalari topilmadi. Kompyuter va turniket bitta tarmoqda ekanligini tekshiring.")
            self.status_label.setStyleSheet("color: #f59e0b;")
            return

        self.status_label.setText(f"✅ {len(devices)} ta Hikvision qurilmasi aniqlandi:")
        self.status_label.setStyleSheet("color: #22c55e;")

        self.table.setRowCount(0)
        for i, dev in enumerate(devices):
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(f"📹 {dev.get('name', 'Hikvision Turniket')}"))
            self.table.setItem(row, 1, QTableWidgetItem(dev.get("ip_address", "")))
            self.table.setItem(row, 2, QTableWidgetItem(str(dev.get("port", 80))))
            self.table.setItem(row, 3, QTableWidgetItem(dev.get("serial_number", "-")))

            btn_select = QPushButton("➕ Tanlash")
            btn_select.setObjectName("btnSuccess")
            btn_select.setFixedHeight(28)
            btn_select.clicked.connect(lambda checked, d=dev: self._choose_device(d))
            self.table.setCellWidget(row, 4, btn_select)

    def _choose_device(self, dev):
        self.selected_device = dev
        self.accept()


class DeviceDialog(QDialog):
    """Qurilma qo'shish va tahrirlash dialogi"""

    def __init__(self, device=None, prefill=None, parent=None):
        super().__init__(parent)
        self.device = device
        self.prefill = prefill
        self.setWindowTitle("🖥️ Qurilma Sozlash" if not device else "✏️ Qurilmani Tahrirlash")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # Sarlavha
        top_layout = QHBoxLayout()
        title = QLabel("Turniket / Terminal Sozlamalari")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        top_layout.addWidget(title)
        top_layout.addStretch()

        btn_find = QPushButton("🔍 Tarmoqdan tanlash")
        btn_find.setObjectName("btnSecondary")
        btn_find.clicked.connect(self._open_network_picker)
        top_layout.addWidget(btn_find)
        layout.addLayout(top_layout)

        form = QFormLayout()
        form.setSpacing(12)

        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Masalan: Asosiy kirish turniketi")
        form.addRow("Qurilma nomi *:", self.inp_name)

        # IP manzil
        self.inp_ip = QLineEdit()
        self.inp_ip.setPlaceholderText("Masalan: 192.168.1.100")
        form.addRow("IP Manzil *:", self.inp_ip)

        # Port va Protokol
        port_layout = QHBoxLayout()
        self.inp_port = QSpinBox()
        self.inp_port.setRange(1, 65535)
        self.inp_port.setValue(80)
        port_layout.addWidget(self.inp_port)

        btn_p80 = QPushButton("Port 80 (HTTP)")
        btn_p80.setObjectName("btnOutline")
        btn_p80.clicked.connect(lambda: self.inp_port.setValue(80))
        port_layout.addWidget(btn_p80)

        btn_p443 = QPushButton("Port 443 (HTTPS)")
        btn_p443.setObjectName("btnOutline")
        btn_p443.clicked.connect(lambda: self.inp_port.setValue(443))
        port_layout.addWidget(btn_p443)

        form.addRow("Port:", port_layout)

        # Login va Parol
        self.inp_username = QLineEdit()
        self.inp_username.setText("admin")
        form.addRow("Foydalanuvchi (Login):", self.inp_username)

        self.inp_password = QLineEdit()
        self.inp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_password.setPlaceholderText("Turniket admin paroli")
        form.addRow("Turniket paroli *:", self.inp_password)

        self.inp_type = QComboBox()
        self.inp_type.addItem("🚪 Turniket (Tripod / Flap barrier)", "turnstile")
        self.inp_type.addItem("👤 Yuzni tanish terminali (MinMoe)", "face_terminal")
        self.inp_type.addItem("🏢 Eshik kontrolleri (DS-K2600)", "door_controller")
        self.inp_type.addItem("💳 Karta o'quvchi terminal", "card_reader")
        form.addRow("Qurilma turi:", self.inp_type)

        self.inp_serial = QLineEdit()
        self.inp_serial.setPlaceholderText("Seriya raqami (ixtiyoriy)")
        form.addRow("Seriya №:", self.inp_serial)

        layout.addLayout(form)

        # Test natijasi oynasi
        self.test_result_box = QLabel()
        self.test_result_box.setStyleSheet("padding: 8px; border-radius: 6px; background-color: #1e293b; color: #94a3b8;")
        self.test_result_box.setWordWrap(True)
        self.test_result_box.setText("ℹ️ IP va parolni kiritgach, 'Ulanishni tekshirish' tugmasini bosing.")
        layout.addWidget(self.test_result_box)

        btn_test = QPushButton("🔗 Ulanishni tekshirish (Test)")
        btn_test.setObjectName("btnWarning")
        btn_test.setFixedHeight(34)
        btn_test.clicked.connect(self._test_connection)
        layout.addWidget(btn_test)

        # Prefill yoki mavjud qurilma
        if self.device:
            self.inp_name.setText(self.device.get("name", ""))
            self.inp_ip.setText(self.device.get("ip_address", ""))
            self.inp_port.setValue(self.device.get("port", 80))
            self.inp_username.setText(self.device.get("username", "admin"))
            self.inp_password.setText(self.device.get("password", ""))
            idx = self.inp_type.findData(self.device.get("device_type", "turnstile"))
            if idx >= 0:
                self.inp_type.setCurrentIndex(idx)
            self.inp_serial.setText(self.device.get("serial_number", ""))
        elif self.prefill:
            self.inp_name.setText(self.prefill.get("name", "Turniket"))
            self.inp_ip.setText(self.prefill.get("ip_address", ""))
            self.inp_port.setValue(self.prefill.get("port", 80))
            if self.prefill.get("serial_number"):
                self.inp_serial.setText(self.prefill.get("serial_number"))

        layout.addStretch()

        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_cancel = QPushButton("Bekor qilish")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Saqlash")
        btn_save.setFixedHeight(34)
        btn_save.clicked.connect(self._save)
        bottom.addWidget(btn_save)
        layout.addLayout(bottom)

    def _open_network_picker(self):
        picker = DiscoveredDevicesDialog(self)
        if picker.exec() == QDialog.DialogCode.Accepted and picker.selected_device:
            dev = picker.selected_device
            self.inp_name.setText(dev.get("name", "Turniket"))
            self.inp_ip.setText(dev.get("ip_address", ""))
            self.inp_port.setValue(dev.get("port", 80))
            if dev.get("serial_number"):
                self.inp_serial.setText(dev.get("serial_number"))

    def _test_connection(self):
        ip = self.inp_ip.text().strip()
        port = self.inp_port.value()
        user = self.inp_username.text().strip()
        pwd = self.inp_password.text()

        if not ip:
            self.test_result_box.setText("❌ IP manzilni kiriting!")
            self.test_result_box.setStyleSheet("background-color: rgba(220, 38, 38, 0.2); color: #f87171; padding: 8px;")
            return

        self.test_result_box.setText("⏳ Ulanish tekshirilmoqda...")
        self.test_result_box.setStyleSheet("background-color: #1e293b; color: #60a5fa; padding: 8px;")

        try:
            dev = HikvisionDevice(ip, port, user, pwd)
            ok, msg = dev.check_connection()
            if ok:
                info = dev.get_device_info()
                dev_info = info.get("DeviceInfo", {}) if isinstance(info, dict) else {}
                model = dev_info.get("model", "")
                serial = dev_info.get("serialNumber", "")
                if serial and not self.inp_serial.text():
                    self.inp_serial.setText(serial)

                res_text = f"✅ ULANISH MUVAFFAQIYATLI!\nModel: {model or 'Hikvision'}\nProtokol: {dev.protocol.upper()}"
                self.test_result_box.setText(res_text)
                self.test_result_box.setStyleSheet("background-color: rgba(34, 197, 94, 0.2); color: #4ade80; padding: 8px; font-weight: bold;")
            else:
                res_text = f"❌ ULANIB BO'LMADI!\nSababi: {msg}\nMaslahat: IP, port ({port}) va admin parolini qayta tekshiring."
                self.test_result_box.setText(res_text)
                self.test_result_box.setStyleSheet("background-color: rgba(220, 38, 38, 0.2); color: #f87171; padding: 8px;")
        except Exception as e:
            self.test_result_box.setText(f"❌ Xatolik: {e}")
            self.test_result_box.setStyleSheet("background-color: rgba(220, 38, 38, 0.2); color: #f87171; padding: 8px;")

    def _save(self):
        if not self.inp_name.text().strip():
            QMessageBox.warning(self, "Xatolik", "Qurilma nomini kiriting!")
            return
        if not self.inp_ip.text().strip():
            QMessageBox.warning(self, "Xatolik", "IP manzilni kiriting!")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.inp_name.text().strip(),
            "ip_address": self.inp_ip.text().strip(),
            "port": self.inp_port.value(),
            "username": self.inp_username.text().strip(),
            "password": self.inp_password.text(),
            "device_type": self.inp_type.currentData(),
            "serial_number": self.inp_serial.text().strip(),
        }


class SettingsPage(QWidget):
    """Sozlamalar sahifasi"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("⚙️  Tizim Sozlamalari")
        title.setObjectName("title")
        layout.addWidget(title)

        tabs = QTabWidget()

        # === TAB 1: QURILMALAR ===
        dev_tab = QWidget()
        dl = QVBoxLayout(dev_tab)
        dl.setSpacing(14)

        # Yuqori panel
        dt = QHBoxLayout()
        btn_scan = QPushButton("🔍 Tarmoqdan avtomatik qidirish (SADP)")
        btn_scan.setObjectName("btnSuccess")
        btn_scan.setFixedHeight(34)
        btn_scan.clicked.connect(self._auto_scan_devices)
        dt.addWidget(btn_scan)

        btn_add_dev = QPushButton("➕ Yangi qurilma qo'shish")
        btn_add_dev.setFixedHeight(34)
        btn_add_dev.clicked.connect(self._add_device)
        dt.addWidget(btn_add_dev)

        btn_test_all = QPushButton("🔄 Barchasini tekshirish")
        btn_test_all.setObjectName("btnWarning")
        btn_test_all.setFixedHeight(34)
        btn_test_all.clicked.connect(self._test_all_devices)
        dt.addWidget(btn_test_all)
        dt.addStretch()
        dl.addLayout(dt)

        # Jadval
        self.dev_table = QTableWidget()
        self.dev_table.setColumnCount(8)
        self.dev_table.setHorizontalHeaderLabels([
            "ID", "Nomi", "IP Manzil", "Port", "Turi", "Seriya №", "Aloqa Holati", "Amallar"
        ])
        self.dev_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dev_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.dev_table.setColumnWidth(0, 40)
        self.dev_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.dev_table.setColumnWidth(2, 130)
        self.dev_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.dev_table.setColumnWidth(3, 60)
        self.dev_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.dev_table.setColumnWidth(6, 110)
        self.dev_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.dev_table.setColumnWidth(7, 160)

        self.dev_table.setAlternatingRowColors(True)
        self.dev_table.verticalHeader().setVisible(False)
        self.dev_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.dev_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.dev_table.setShowGrid(False)
        dl.addWidget(self.dev_table)
        tabs.addTab(dev_tab, "🖥️ Turniket va Qurilmalar")

        # === TAB 2: TELEGRAM BOT ===
        tg_tab = QWidget()
        tgl = QVBoxLayout(tg_tab)

        tg_group = QGroupBox("Telegram Bot orqali kirish-chiqishlarni bildirish")
        tg_form = QFormLayout(tg_group)
        tg_form.setSpacing(14)

        self.chk_tg_enable = QCheckBox("Telegram xabarnomalarini yoqish")
        self.chk_tg_enable.setChecked(get_setting("telegram_enabled", "0") == "1")
        tg_form.addRow("Faollashtirish:", self.chk_tg_enable)

        self.inp_tg_token = QLineEdit()
        self.inp_tg_token.setPlaceholderText("Masalan: 7123456789:AAHq_ABCDEF...")
        self.inp_tg_token.setText(get_setting("telegram_bot_token", ""))
        tg_form.addRow("Bot Token (@BotFather):", self.inp_tg_token)

        self.inp_tg_chat = QLineEdit()
        self.inp_tg_chat.setPlaceholderText("Masalan: 123456789 yoki -100123456789 (Guruh ID)")
        self.inp_tg_chat.setText(get_setting("telegram_chat_id", ""))
        tg_form.addRow("Chat ID / Guruh ID:", self.inp_tg_chat)

        self.chk_tg_entry = QCheckBox("Kirish hodisalarini yuborish (🟢 Kirish)")
        self.chk_tg_entry.setChecked(get_setting("telegram_notify_entries", "1") == "1")
        tg_form.addRow("Filtr:", self.chk_tg_entry)

        self.chk_tg_exit = QCheckBox("Chiqish hodisalarini yuborish (🔴 Chiqish)")
        self.chk_tg_exit.setChecked(get_setting("telegram_notify_exits", "1") == "1")
        tg_form.addRow("", self.chk_tg_exit)

        self.chk_tg_late = QCheckBox("Faqat kechikkanlarni yuborish (09:00 dan keyin)")
        self.chk_tg_late.setChecked(get_setting("telegram_notify_late_only", "0") == "1")
        tg_form.addRow("", self.chk_tg_late)

        btn_tg_test = QPushButton("📩 Botga sinov xabari yuborish")
        btn_tg_test.setObjectName("btnWarning")
        btn_tg_test.clicked.connect(self._test_telegram)
        tg_form.addRow("", btn_tg_test)

        tgl.addWidget(tg_group)

        btn_save_tg = QPushButton("💾  Telegram sozlamalarini saqlash")
        btn_save_tg.setFixedHeight(34)
        btn_save_tg.clicked.connect(self._save_telegram_settings)
        tgl.addWidget(btn_save_tg)
        tgl.addStretch()
        tabs.addTab(tg_tab, "✈️ Telegram Bot")

        # === TAB 3: UMUMIY ===
        gen_tab = QWidget()
        gl = QVBoxLayout(gen_tab)

        company_group = QGroupBox("Tashkilot")
        cgl = QFormLayout(company_group)
        self.inp_company = QLineEdit()
        self.inp_company.setText(get_setting("company_name", "Kompaniya nomi"))
        cgl.addRow("Tashkilot nomi:", self.inp_company)
        gl.addWidget(company_group)

        time_group = QGroupBox("Monitoring parametrlari")
        tgl_form = QFormLayout(time_group)
        self.inp_refresh = QSpinBox()
        self.inp_refresh.setRange(2, 60)
        self.inp_refresh.setValue(int(get_setting("auto_refresh_interval", "5")))
        self.inp_refresh.setSuffix(" soniya")
        tgl_form.addRow("Statistika yangilash:", self.inp_refresh)
        gl.addWidget(time_group)

        btn_save_settings = QPushButton("💾  Umumiy sozlamalarni saqlash")
        btn_save_settings.setFixedHeight(34)
        btn_save_settings.clicked.connect(self._save_general_settings)
        gl.addWidget(btn_save_settings)
        gl.addStretch()
        tabs.addTab(gen_tab, "⚙️ Umumiy")

        # === TAB 4: BO'LIMLAR ===
        dept_tab = QWidget()
        dpl = QVBoxLayout(dept_tab)
        dpf = QHBoxLayout()
        self.inp_new_dept = QLineEdit()
        self.inp_new_dept.setPlaceholderText("Yangi bo'lim nomi")
        dpf.addWidget(self.inp_new_dept)
        btn_add_dept = QPushButton("➕ Qo'shish")
        btn_add_dept.clicked.connect(self._add_department)
        dpf.addWidget(btn_add_dept)
        btn_del_dept = QPushButton("🗑️ O'chirish")
        btn_del_dept.setObjectName("btnDanger")
        btn_del_dept.clicked.connect(self._delete_department)
        dpf.addWidget(btn_del_dept)
        dpf.addStretch()
        dpl.addLayout(dpf)

        self.dept_table = QTableWidget()
        self.dept_table.setColumnCount(3)
        self.dept_table.setHorizontalHeaderLabels(["ID", "Nomi", "Tavsif"])
        self.dept_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dept_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.dept_table.setColumnWidth(0, 50)
        self.dept_table.setAlternatingRowColors(True)
        self.dept_table.verticalHeader().setVisible(False)
        self.dept_table.setShowGrid(False)
        dpl.addWidget(self.dept_table)
        tabs.addTab(dept_tab, "🏢 Bo'limlar")

        layout.addWidget(tabs)

        self._refresh_devices()
        self._refresh_departments()

    def _auto_scan_devices(self):
        """Tarmoqdagi qurilmalarni qidirish dialogini ochish"""
        picker = DiscoveredDevicesDialog(self)
        if picker.exec() == QDialog.DialogCode.Accepted and picker.selected_device:
            dlg = DeviceDialog(prefill=picker.selected_device, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                add_device(dlg.get_data())
                self._refresh_devices()

    def _test_telegram(self):
        token = self.inp_tg_token.text().strip()
        chat_id = self.inp_tg_chat.text().strip()
        ok, res = TelegramNotifier.test_connection(token, chat_id)
        if ok:
            QMessageBox.information(self, "Muvaffaqiyat", res)
        else:
            QMessageBox.warning(self, "Xatolik", res)

    def _save_telegram_settings(self):
        set_setting("telegram_enabled", "1" if self.chk_tg_enable.isChecked() else "0")
        set_setting("telegram_bot_token", self.inp_tg_token.text().strip())
        set_setting("telegram_chat_id", self.inp_tg_chat.text().strip())
        set_setting("telegram_notify_entries", "1" if self.chk_tg_entry.isChecked() else "0")
        set_setting("telegram_notify_exits", "1" if self.chk_tg_exit.isChecked() else "0")
        set_setting("telegram_notify_late_only", "1" if self.chk_tg_late.isChecked() else "0")
        QMessageBox.information(self, "Tayyor", "Telegram sozlamalari saqlandi!")

    def _save_general_settings(self):
        set_setting("company_name", self.inp_company.text().strip())
        set_setting("auto_refresh_interval", str(self.inp_refresh.value()))
        QMessageBox.information(self, "Tayyor", "Umumiy sozlamalar saqlandi!")

    def _refresh_devices(self):
        devices = get_all_devices()
        self.dev_table.setRowCount(0)
        for dev in devices:
            row = self.dev_table.rowCount()
            self.dev_table.insertRow(row)

            self.dev_table.setItem(row, 0, QTableWidgetItem(str(dev["id"])))
            self.dev_table.setItem(row, 1, QTableWidgetItem(dev["name"]))
            self.dev_table.setItem(row, 2, QTableWidgetItem(dev["ip_address"]))
            self.dev_table.setItem(row, 3, QTableWidgetItem(str(dev["port"])))

            type_map = {
                "turnstile": "Turniket",
                "door_controller": "Eshik",
                "face_terminal": "Yuz terminal",
                "card_reader": "Karta terminal"
            }
            self.dev_table.setItem(row, 4, QTableWidgetItem(type_map.get(dev["device_type"], dev["device_type"])))
            self.dev_table.setItem(row, 5, QTableWidgetItem(dev.get("serial_number", "-")))

            st = "🟢 Online" if dev.get("is_online") else "🔴 Offline"
            st_item = QTableWidgetItem(st)
            st_item.setForeground(QColor("#22c55e" if dev.get("is_online") else "#ef4444"))
            self.dev_table.setItem(row, 6, st_item)

            # Har bir qatorda amallar tugmalari
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(6)

            btn_test = QPushButton("🔗")
            btn_test.setToolTip("Aloqani tekshirish")
            btn_test.setFixedSize(30, 26)
            btn_test.clicked.connect(lambda ch, d=dev: self._test_single_device(d))
            action_layout.addWidget(btn_test)

            btn_edit = QPushButton("✏️")
            btn_edit.setToolTip("Tahrirlash")
            btn_edit.setFixedSize(30, 26)
            btn_edit.clicked.connect(lambda ch, d=dev: self._edit_device_by_dict(d))
            action_layout.addWidget(btn_edit)

            btn_del = QPushButton("🗑️")
            btn_del.setObjectName("btnDanger")
            btn_del.setToolTip("O'chirish")
            btn_del.setFixedSize(30, 26)
            btn_del.clicked.connect(lambda ch, did=dev["id"]: self._delete_device_by_id(did))
            action_layout.addWidget(btn_del)

            self.dev_table.setCellWidget(row, 7, action_widget)

    def _test_single_device(self, dev):
        hk = HikvisionDevice(dev["ip_address"], dev["port"], dev["username"], dev["password"])
        ok, msg = hk.check_connection()
        update_device_status(dev["id"], ok)
        self._refresh_devices()
        if ok:
            QMessageBox.information(self, "Ulanish Muvaffaqiyatli", f"✅ {dev['name']} ({dev['ip_address']}) bilan aloqa o'rnatildi!")
        else:
            QMessageBox.warning(self, "Ulanib bo'lmadi", f"❌ {dev['name']} ({dev['ip_address']})\n\nSababi: {msg}")

    def _edit_device_by_dict(self, dev):
        dlg = DeviceDialog(device=dev, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            from models.database import update_device
            update_device(dev["id"], dlg.get_data())
            self._refresh_devices()

    def _delete_device_by_id(self, dev_id):
        reply = QMessageBox.question(self, "Tasdiqlash", "Qurilmani o'chirmoqchimisiz?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_device(dev_id)
            self._refresh_devices()

    def _refresh_departments(self):
        depts = get_all_departments()
        self.dept_table.setRowCount(0)
        for d in depts:
            row = self.dept_table.rowCount()
            self.dept_table.insertRow(row)
            self.dept_table.setItem(row, 0, QTableWidgetItem(str(d["id"])))
            self.dept_table.setItem(row, 1, QTableWidgetItem(d["name"]))
            self.dept_table.setItem(row, 2, QTableWidgetItem(d.get("description", "")))

    def _add_device(self):
        dlg = DeviceDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                add_device(dlg.get_data())
                self._refresh_devices()
            except Exception as e:
                QMessageBox.critical(self, "Xatolik", str(e))

    def _test_all_devices(self):
        devices = get_all_devices()
        results = []
        for dev in devices:
            try:
                hk = HikvisionDevice(dev["ip_address"], dev["port"], dev["username"], dev["password"])
                ok, msg = hk.check_connection()
                update_device_status(dev["id"], ok)
                icon = "✅" if ok else "❌"
                results.append(f"{icon} {dev['name']} ({dev['ip_address']}): {msg}")
            except Exception as e:
                update_device_status(dev["id"], False)
                results.append(f"❌ {dev['name']}: {e}")
        self._refresh_devices()
        QMessageBox.information(self, "Natija", "\n\n".join(results) if results else "Qurilma yo'q")

    def _add_department(self):
        name = self.inp_new_dept.text().strip()
        if not name:
            QMessageBox.warning(self, "Xatolik", "Bo'lim nomini kiriting!")
            return
        try:
            add_department(name)
            self.inp_new_dept.clear()
            self._refresh_departments()
        except Exception as e:
            QMessageBox.critical(self, "Xatolik", str(e))

    def _delete_department(self):
        rows = self.dept_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Diqqat", "Bo'limni tanlang!")
            return
        dept_id = int(self.dept_table.item(rows[0].row(), 0).text())
        delete_department(dept_id)
        self._refresh_departments()
