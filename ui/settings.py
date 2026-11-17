"""
Sozlamalar sahifasi - Qurilmalar, Telegram Bot va tizim parametrlari
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QDialog, QFormLayout, QComboBox, QMessageBox, QSpinBox,
    QFrame, QTabWidget, QGroupBox, QCheckBox, QProgressDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from models.database import (
    get_all_devices, add_device, update_device, delete_device,
    get_all_departments, add_department, delete_department,
    get_setting, set_setting
)
from services.hikvision_api import HikvisionDevice
from services.telegram_bot import TelegramNotifier
from services.device_discovery import DeviceDiscovery


class DeviceDialog(QDialog):
    """Qurilma qo'shish/tahrirlash"""
    def __init__(self, device=None, parent=None):
        super().__init__(parent)
        self.device = device
        self.setWindowTitle("Qurilma qo'shish" if not device else "Qurilma tahrirlash")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("🖥️  Qurilma sozlamalari")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Masalan: Asosiy kirish turniketi")
        form.addRow("Nomi *:", self.inp_name)
        self.inp_ip = QLineEdit()
        self.inp_ip.setPlaceholderText("192.168.1.100")
        form.addRow("IP manzil *:", self.inp_ip)
        self.inp_port = QSpinBox()
        self.inp_port.setRange(1, 65535)
        self.inp_port.setValue(80)
        form.addRow("Port:", self.inp_port)
        self.inp_username = QLineEdit()
        self.inp_username.setText("admin")
        form.addRow("Foydalanuvchi:", self.inp_username)
        self.inp_password = QLineEdit()
        self.inp_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Parol:", self.inp_password)
        self.inp_type = QComboBox()
        self.inp_type.addItems(["turnstile", "face_terminal", "door_controller", "card_reader"])
        form.addRow("Turi:", self.inp_type)
        self.inp_serial = QLineEdit()
        self.inp_serial.setPlaceholderText("Seriya raqami (ixtiyoriy)")
        form.addRow("Seriya №:", self.inp_serial)
        layout.addLayout(form)

        if self.device:
            self.inp_name.setText(self.device.get("name", ""))
            self.inp_ip.setText(self.device.get("ip_address", ""))
            self.inp_port.setValue(self.device.get("port", 80))
            self.inp_username.setText(self.device.get("username", "admin"))
            self.inp_password.setText(self.device.get("password", ""))
            idx = self.inp_type.findText(self.device.get("device_type", "turnstile"))
            if idx >= 0:
                self.inp_type.setCurrentIndex(idx)
            self.inp_serial.setText(self.device.get("serial_number", ""))

        btn_test = QPushButton("🔗 Ulanishni tekshirish")
        btn_test.setObjectName("btnWarning")
        btn_test.clicked.connect(self._test_connection)
        layout.addWidget(btn_test)

        layout.addStretch()
        bl = QHBoxLayout()
        bl.addStretch()
        bc = QPushButton("Bekor qilish")
        bc.setObjectName("btnSecondary")
        bc.clicked.connect(self.reject)
        bl.addWidget(bc)
        bs = QPushButton("💾  Saqlash")
        bs.clicked.connect(self._save)
        bl.addWidget(bs)
        layout.addLayout(bl)

    def _test_connection(self):
        ip = self.inp_ip.text().strip()
        port = self.inp_port.value()
        user = self.inp_username.text().strip()
        pwd = self.inp_password.text()
        if not ip:
            QMessageBox.warning(self, "Xatolik", "IP manzilni kiriting!")
            return
        try:
            dev = HikvisionDevice(ip, port, user, pwd)
            if dev.check_connection():
                info = dev.get_device_info()
                dev_info = info.get("DeviceInfo", {}) if isinstance(info, dict) else {}
                msg = (
                    f"✅ Ulanish muvaffaqiyatli!\n\n"
                    f"Qurilma: {dev_info.get('deviceName', 'Hikvision Device')}\n"
                    f"Model: {dev_info.get('model', 'N/A')}\n"
                    f"Seriya №: {dev_info.get('serialNumber', 'N/A')}\n"
                    f"Firmware: {dev_info.get('firmwareVersion', 'N/A')}"
                )
                if not self.inp_serial.text() and dev_info.get('serialNumber'):
                    self.inp_serial.setText(dev_info.get('serialNumber'))
                QMessageBox.information(self, "Natija", msg)
            else:
                QMessageBox.warning(self, "Xatolik", "❌ Qurilmaga ulanib bo'lmadi!\nIP, port va login/parolni tekshiring.")
        except Exception as e:
            QMessageBox.critical(self, "Xatolik", f"Ulanish xatosi:\n{e}")

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
            "device_type": self.inp_type.currentText(),
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
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("⚙️  Sozlamalar")
        title.setObjectName("title")
        layout.addWidget(title)

        tabs = QTabWidget()

        # === TAB 1: QURILMALAR ===
        dev_tab = QWidget()
        dl = QVBoxLayout(dev_tab)
        dt = QHBoxLayout()

        btn_scan = QPushButton("🔍 Tarmoqdan avtomatik qidirish (SADP)")
        btn_scan.setObjectName("btnSuccess")
        btn_scan.clicked.connect(self._auto_scan_devices)
        dt.addWidget(btn_scan)

        btn_add_dev = QPushButton("➕ Qo'lda qo'shish")
        btn_add_dev.clicked.connect(self._add_device)
        dt.addWidget(btn_add_dev)

        btn_edit_dev = QPushButton("✏️ Tahrirlash")
        btn_edit_dev.setObjectName("btnSecondary")
        btn_edit_dev.clicked.connect(self._edit_device)
        dt.addWidget(btn_edit_dev)

        btn_del_dev = QPushButton("🗑️ O'chirish")
        btn_del_dev.setObjectName("btnDanger")
        btn_del_dev.clicked.connect(self._delete_device)
        dt.addWidget(btn_del_dev)

        btn_test_all = QPushButton("🔗 Tekshirish")
        btn_test_all.setObjectName("btnWarning")
        btn_test_all.clicked.connect(self._test_all_devices)
        dt.addWidget(btn_test_all)
        dt.addStretch()
        dl.addLayout(dt)

        self.dev_table = QTableWidget()
        self.dev_table.setColumnCount(7)
        self.dev_table.setHorizontalHeaderLabels(["ID", "Nomi", "IP manzil", "Port", "Turi", "Seriya №", "Holat"])
        self.dev_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dev_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.dev_table.setColumnWidth(0, 50)
        self.dev_table.setAlternatingRowColors(True)
        self.dev_table.verticalHeader().setVisible(False)
        self.dev_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.dev_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.dev_table.setShowGrid(False)
        dl.addWidget(self.dev_table)
        tabs.addTab(dev_tab, "🖥️ Qurilmalar")

        # === TAB 2: TELEGRAM BOT ===
        tg_tab = QWidget()
        tgl = QVBoxLayout(tg_tab)

        tg_group = QGroupBox("Telegram Bot orqali real-time xabardor qilish")
        tg_form = QFormLayout(tg_group)
        tg_form.setSpacing(14)

        self.chk_tg_enable = QCheckBox("Telegram xabarnomalarini yoqish")
        self.chk_tg_enable.setChecked(get_setting("telegram_enabled", "0") == "1")
        tg_form.addRow("Holat:", self.chk_tg_enable)

        self.inp_tg_token = QLineEdit()
        self.inp_tg_token.setPlaceholderText("Masalan: 7123456789:AAHq_ABCDEF...")
        self.inp_tg_token.setText(get_setting("telegram_bot_token", ""))
        tg_form.addRow("Bot Token (BotFather):", self.inp_tg_token)

        self.inp_tg_chat = QLineEdit()
        self.inp_tg_chat.setPlaceholderText("Masalan: 123456789 yoki -100123456789 (guruh/kanal ID)")
        self.inp_tg_chat.setText(get_setting("telegram_chat_id", ""))
        tg_form.addRow("Chat ID / Guruh ID:", self.inp_tg_chat)

        self.chk_tg_entry = QCheckBox("Kirish hodisalarini yuborish (🟢 Kirish)")
        self.chk_tg_entry.setChecked(get_setting("telegram_notify_entries", "1") == "1")
        tg_form.addRow("", self.chk_tg_entry)

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
        btn_save_tg.clicked.connect(self._save_telegram_settings)
        tgl.addWidget(btn_save_tg)
        tgl.addStretch()
        tabs.addTab(tg_tab, "✈️ Telegram Bot")

        # === TAB 3: UMUMIY ===
        gen_tab = QWidget()
        gl = QVBoxLayout(gen_tab)

        company_group = QGroupBox("Kompaniya")
        cgl = QFormLayout(company_group)
        self.inp_company = QLineEdit()
        self.inp_company.setText(get_setting("company_name", "Kompaniya nomi"))
        cgl.addRow("Kompaniya nomi:", self.inp_company)
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
        self.dept_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.dept_table.setShowGrid(False)
        dpl.addWidget(self.dept_table)
        tabs.addTab(dept_tab, "🏢 Bo'limlar")

        layout.addWidget(tabs)

        self._refresh_devices()
        self._refresh_departments()

    def _auto_scan_devices(self):
        """Tarmoqdagi barcha Hikvision qurilmalarini avtomatik qidirish"""
        progress = QProgressDialog("Tarmoq skanerlanmoqda (SADP & IP scan)...", "Bekor qilish", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        progress.setValue(20)

        found = DeviceDiscovery.discover_all_devices()
        progress.setValue(100)
        progress.close()

        if not found:
            QMessageBox.information(
                self, "Natija",
                "Lokal tarmoqda Hikvision qurilmalari topilmadi.\n\n"
                "Iltimos, kompyuter va turniket bitta Wi-Fi yoki LAN switchga ulanganligini tekshiring."
            )
            return

        msg = f"Tarmoqda {len(found)} ta Hikvision qurilmasi topildi:\n\n"
        for i, d in enumerate(found, 1):
            msg += f"{i}. {d.get('name', 'Turniket')} — IP: {d['ip_address']}:{d['port']}\n"
        msg += "\nTopilgan birinchi qurilmani qo'shishni xohlaysizmi?"

        reply = QMessageBox.question(self, "Qurilmalar topildi", msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            target = found[0]
            dlg = DeviceDialog(parent=self)
            dlg.inp_name.setText(target.get("name", "Turniket"))
            dlg.inp_ip.setText(target.get("ip_address", ""))
            dlg.inp_port.setValue(target.get("port", 80))
            if target.get("serial_number"):
                dlg.inp_serial.setText(target.get("serial_number"))
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
            type_map = {"turnstile": "Turniket", "door_controller": "Eshik", "face_terminal": "Yuz terminal", "card_reader": "Karta o'quvchi"}
            self.dev_table.setItem(row, 4, QTableWidgetItem(type_map.get(dev["device_type"], dev["device_type"])))
            self.dev_table.setItem(row, 5, QTableWidgetItem(dev.get("serial_number", "")))
            st = "🟢 Online" if dev.get("is_online") else "🔴 Offline"
            self.dev_table.setItem(row, 6, QTableWidgetItem(st))

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
                QMessageBox.information(self, "Tayyor", "Qurilma qo'shildi!")
            except Exception as e:
                QMessageBox.critical(self, "Xatolik", str(e))

    def _edit_device(self):
        rows = self.dev_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Diqqat", "Qurilmani tanlang!")
            return
        from models.database import get_device
        dev_id = int(self.dev_table.item(rows[0].row(), 0).text())
        dev = get_device(dev_id)
        if not dev:
            return
        dlg = DeviceDialog(device=dev, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            update_device(dev_id, dlg.get_data())
            self._refresh_devices()

    def _delete_device(self):
        rows = self.dev_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Diqqat", "Qurilmani tanlang!")
            return
        reply = QMessageBox.question(self, "Tasdiqlash", "Qurilmani o'chirmoqchimisiz?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            dev_id = int(self.dev_table.item(rows[0].row(), 0).text())
            delete_device(dev_id)
            self._refresh_devices()

    def _test_all_devices(self):
        from models.database import update_device_status
        devices = get_all_devices()
        results = []
        for dev in devices:
            try:
                hk = HikvisionDevice(dev["ip_address"], dev["port"], dev["username"], dev["password"])
                ok = hk.check_connection()
                update_device_status(dev["id"], ok)
                results.append(f"{'✅' if ok else '❌'} {dev['name']} ({dev['ip_address']})")
            except Exception as e:
                update_device_status(dev["id"], False)
                results.append(f"❌ {dev['name']}: {e}")
        self._refresh_devices()
        QMessageBox.information(self, "Natija", "\n".join(results) if results else "Qurilma yo'q")

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
