"""
Voqealar jurnali sahifasi
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QDateEdit, QComboBox, QFrame, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from datetime import datetime
from models.database import get_access_events
from utils.helpers import format_datetime


class EventsPage(QWidget):
    """Voqealar jurnali"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_events()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QHBoxLayout()
        title = QLabel("📋  Kirish-chiqish jurnali")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        self.count_label = QLabel()
        self.count_label.setObjectName("subtitle")
        header.addWidget(self.count_label)
        layout.addLayout(header)

        filter_frame = QFrame()
        filter_frame.setObjectName("cardFrame")
        fl = QHBoxLayout(filter_frame)
        fl.setSpacing(12)
        fl.addWidget(QLabel("📅 Dan:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        fl.addWidget(self.date_from)
        fl.addWidget(QLabel("📅 Gacha:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        fl.addWidget(self.date_to)
        fl.addWidget(QLabel("Turi:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(["Hammasi", "Kirish", "Chiqish"])
        fl.addWidget(self.type_filter)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Xodim qidirish...")
        self.search_input.setMaximumWidth(200)
        fl.addWidget(self.search_input)
        btn_search = QPushButton("🔍 Qidirish")
        btn_search.clicked.connect(self._load_events)
        fl.addWidget(btn_search)
        btn_export = QPushButton("📥 Excel export")
        btn_export.setObjectName("btnSuccess")
        btn_export.clicked.connect(self._export_excel)
        fl.addWidget(btn_export)
        layout.addWidget(filter_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["№", "Sana/Vaqt", "Xodim", "ID raqam", "Turi", "Usul", "Holat", "Qurilma"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)

    def _load_events(self):
        date_from = self.date_from.date().toString("yyyy-MM-dd") + " 00:00:00"
        date_to = self.date_to.date().toString("yyyy-MM-dd") + " 23:59:59"
        event_type = None
        if self.type_filter.currentText() == "Kirish":
            event_type = "entry"
        elif self.type_filter.currentText() == "Chiqish":
            event_type = "exit"
        events = get_access_events(date_from=date_from, date_to=date_to, event_type=event_type, limit=1000)
        search = self.search_input.text().strip().lower()
        if search:
            events = [e for e in events if search in (e.get("employee_name", "") or "").lower() or search in (e.get("employee_no", "") or "").lower()]

        self.table.setRowCount(0)
        for i, event in enumerate(events):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(format_datetime(event.get("event_time", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(event.get("employee_name", "Noma'lum")))
            self.table.setItem(row, 3, QTableWidgetItem(event.get("employee_no", "")))
            et = event.get("event_type", "entry")
            ti = QTableWidgetItem("🟢 Kirish" if et == "entry" else "🔴 Chiqish")
            ti.setForeground(QColor("#22c55e" if et == "entry" else "#ef4444"))
            self.table.setItem(row, 4, ti)
            mm = {"card": "💳 Karta", "face": "👤 Yuz", "fingerprint": "👆 Barmoq", "qr": "📱 QR"}
            self.table.setItem(row, 5, QTableWidgetItem(mm.get(event.get("access_method", "card"), "💳 Karta")))
            st = event.get("status", "granted")
            si = QTableWidgetItem("✅ Ruxsat" if st == "granted" else "❌ Rad")
            si.setForeground(QColor("#22c55e" if st == "granted" else "#ef4444"))
            self.table.setItem(row, 6, si)
            self.table.setItem(row, 7, QTableWidgetItem(event.get("device_name", "")))
        self.count_label.setText(f"Jami: {self.table.rowCount()} ta yozuv")

    def _export_excel(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            path, _ = QFileDialog.getSaveFileName(self, "Excelga saqlash", f"kirish_chiqish_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", "Excel Files (*.xlsx)")
            if not path:
                return
            wb = Workbook()
            ws = wb.active
            ws.title = "Kirish-Chiqish"
            headers = ["№", "Sana/Vaqt", "Xodim", "ID raqam", "Turi", "Usul", "Holat", "Qurilma"]
            hf = Font(bold=True, color="FFFFFF")
            hfill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
            for col, h in enumerate(headers, 1):
                c = ws.cell(row=1, column=col, value=h)
                c.font = hf
                c.fill = hfill
                c.alignment = Alignment(horizontal="center")
            for row in range(self.table.rowCount()):
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    v = item.text() if item else ""
                    for emoji in ["🟢", "🔴", "💳", "👤", "👆", "📱", "✅", "❌"]:
                        v = v.replace(emoji, "").strip()
                    ws.cell(row=row + 2, column=col + 1, value=v)
            for col_cells in ws.columns:
                ml = max(len(str(c.value or "")) for c in col_cells)
                ws.column_dimensions[col_cells[0].column_letter].width = min(ml + 4, 30)
            wb.save(path)
            QMessageBox.information(self, "Tayyor!", f"Fayl saqlandi:\n{path}")
        except ImportError:
            QMessageBox.warning(self, "Xatolik", "openpyxl o'rnatilmagan!\npip install openpyxl")
        except Exception as e:
            QMessageBox.critical(self, "Xatolik", f"Eksport xatosi:\n{e}")
