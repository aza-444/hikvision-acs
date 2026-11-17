"""
Hisobotlar sahifasi - Davomat, kech kelganlar, bo'lim statistikasi
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QDateEdit, QComboBox, QTabWidget, QFileDialog, QMessageBox
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from models.database import (
    get_all_employees, get_employee_attendance, get_department_stats,
    get_late_arrivals
)
from utils.helpers import format_date, format_time, calculate_work_hours, is_late


class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("📊  Hisobotlar")
        title.setObjectName("title")
        layout.addWidget(title)

        tabs = QTabWidget()

        # === Tab 1: Davomat ===
        att_tab = QWidget()
        al = QVBoxLayout(att_tab)
        af = QHBoxLayout()
        af.addWidget(QLabel("📅 Dan:"))
        self.att_date_from = QDateEdit()
        self.att_date_from.setCalendarPopup(True)
        self.att_date_from.setDate(QDate.currentDate().addDays(-30))
        self.att_date_from.setDisplayFormat("dd.MM.yyyy")
        af.addWidget(self.att_date_from)
        af.addWidget(QLabel("📅 Gacha:"))
        self.att_date_to = QDateEdit()
        self.att_date_to.setCalendarPopup(True)
        self.att_date_to.setDate(QDate.currentDate())
        self.att_date_to.setDisplayFormat("dd.MM.yyyy")
        af.addWidget(self.att_date_to)
        af.addWidget(QLabel("Xodim:"))
        self.att_employee = QComboBox()
        self.att_employee.addItem("Barcha xodimlar", 0)
        for emp in get_all_employees():
            self.att_employee.addItem(f"{emp['first_name']} {emp['last_name']} ({emp['employee_no']})", emp["id"])
        self.att_employee.setMinimumWidth(250)
        af.addWidget(self.att_employee)
        btn_att = QPushButton("📊 Hisobot")
        btn_att.clicked.connect(self._generate_attendance)
        af.addWidget(btn_att)
        btn_att_ex = QPushButton("📥 Excel")
        btn_att_ex.setObjectName("btnSuccess")
        btn_att_ex.clicked.connect(self._export_attendance)
        af.addWidget(btn_att_ex)
        af.addStretch()
        al.addLayout(af)

        self.att_table = QTableWidget()
        self.att_table.setColumnCount(7)
        self.att_table.setHorizontalHeaderLabels(["Xodim", "Sana", "Kelgan vaqt", "Ketgan vaqt", "Ish soati", "Kirishlar", "Holat"])
        self.att_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.att_table.setAlternatingRowColors(True)
        self.att_table.verticalHeader().setVisible(False)
        self.att_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.att_table.setShowGrid(False)
        al.addWidget(self.att_table)
        tabs.addTab(att_tab, "📋 Davomat")

        # === Tab 2: Kech kelganlar ===
        late_tab = QWidget()
        ll = QVBoxLayout(late_tab)
        lf = QHBoxLayout()
        lf.addWidget(QLabel("📅 Sana:"))
        self.late_date = QDateEdit()
        self.late_date.setCalendarPopup(True)
        self.late_date.setDate(QDate.currentDate())
        self.late_date.setDisplayFormat("dd.MM.yyyy")
        lf.addWidget(self.late_date)
        btn_late = QPushButton("🔍 Ko'rsatish")
        btn_late.clicked.connect(self._show_late_arrivals)
        lf.addWidget(btn_late)
        lf.addStretch()
        ll.addLayout(lf)
        self.late_table = QTableWidget()
        self.late_table.setColumnCount(5)
        self.late_table.setHorizontalHeaderLabels(["Xodim", "Bo'lim", "Kelgan vaqt", "Ish vaqti", "Kechikish"])
        self.late_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.late_table.setAlternatingRowColors(True)
        self.late_table.verticalHeader().setVisible(False)
        self.late_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.late_table.setShowGrid(False)
        ll.addWidget(self.late_table)
        tabs.addTab(late_tab, "⏰ Kech kelganlar")

        # === Tab 3: Bo'limlar ===
        dept_tab = QWidget()
        dl = QVBoxLayout(dept_tab)
        df = QHBoxLayout()
        df.addWidget(QLabel("📅 Dan:"))
        self.dept_date_from = QDateEdit()
        self.dept_date_from.setCalendarPopup(True)
        self.dept_date_from.setDate(QDate.currentDate().addDays(-7))
        self.dept_date_from.setDisplayFormat("dd.MM.yyyy")
        df.addWidget(self.dept_date_from)
        df.addWidget(QLabel("📅 Gacha:"))
        self.dept_date_to = QDateEdit()
        self.dept_date_to.setCalendarPopup(True)
        self.dept_date_to.setDate(QDate.currentDate())
        self.dept_date_to.setDisplayFormat("dd.MM.yyyy")
        df.addWidget(self.dept_date_to)
        btn_dept = QPushButton("📊 Ko'rsatish")
        btn_dept.clicked.connect(self._show_dept_stats)
        df.addWidget(btn_dept)
        df.addStretch()
        dl.addLayout(df)
        self.dept_table = QTableWidget()
        self.dept_table.setColumnCount(4)
        self.dept_table.setHorizontalHeaderLabels(["Bo'lim", "Xodimlar", "Kirishlar", "Chiqishlar"])
        self.dept_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dept_table.setAlternatingRowColors(True)
        self.dept_table.verticalHeader().setVisible(False)
        self.dept_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.dept_table.setShowGrid(False)
        dl.addWidget(self.dept_table)
        tabs.addTab(dept_tab, "🏢 Bo'limlar")

        layout.addWidget(tabs)

    def _generate_attendance(self):
        df = self.att_date_from.date().toString("yyyy-MM-dd") + " 00:00:00"
        dt = self.att_date_to.date().toString("yyyy-MM-dd") + " 23:59:59"
        emp_id = self.att_employee.currentData()
        self.att_table.setRowCount(0)
        emps = get_all_employees()
        if emp_id and emp_id > 0:
            emps = [e for e in emps if e["id"] == emp_id]
        for emp in emps:
            att = get_employee_attendance(emp["id"], df, dt)
            for day in att:
                row = self.att_table.rowCount()
                self.att_table.insertRow(row)
                self.att_table.setItem(row, 0, QTableWidgetItem(f"{emp['first_name']} {emp['last_name']}"))
                self.att_table.setItem(row, 1, QTableWidgetItem(format_date(day["date"])))
                self.att_table.setItem(row, 2, QTableWidgetItem(format_time(day["first_entry"]) if day["first_entry"] else "-"))
                self.att_table.setItem(row, 3, QTableWidgetItem(format_time(day["last_exit"]) if day["last_exit"] else "-"))
                wh = calculate_work_hours(day["first_entry"], day["last_exit"]) if day["first_entry"] and day["last_exit"] else 0
                self.att_table.setItem(row, 4, QTableWidgetItem(f"{wh:.1f} soat"))
                self.att_table.setItem(row, 5, QTableWidgetItem(str(day.get("entries", 0))))
                late = is_late(day["first_entry"]) if day["first_entry"] else False
                si = QTableWidgetItem("⚠️ Kech kelgan" if late else "✅ Normal")
                si.setForeground(QColor("#f59e0b" if late else "#22c55e"))
                self.att_table.setItem(row, 6, si)

    def _show_late_arrivals(self):
        date = self.late_date.date().toString("yyyy-MM-dd")
        lates = get_late_arrivals(date)
        self.late_table.setRowCount(0)
        for emp in lates:
            row = self.late_table.rowCount()
            self.late_table.insertRow(row)
            self.late_table.setItem(row, 0, QTableWidgetItem(f"{emp['first_name']} {emp['last_name']}"))
            self.late_table.setItem(row, 1, QTableWidgetItem(emp.get("department", "")))
            self.late_table.setItem(row, 2, QTableWidgetItem(format_time(emp.get("arrival_time", ""))))
            self.late_table.setItem(row, 3, QTableWidgetItem("09:00"))
            try:
                arr = emp.get("arrival_time", "")
                fmt = "%Y-%m-%dT%H:%M:%S" if "T" in arr else "%Y-%m-%d %H:%M:%S"
                t = datetime.strptime(arr[:19], fmt)
                s = t.replace(hour=9, minute=0, second=0)
                lm = int((t - s).total_seconds() / 60)
                li = QTableWidgetItem(f"{lm} daqiqa")
                li.setForeground(QColor("#ef4444"))
                self.late_table.setItem(row, 4, li)
            except (ValueError, TypeError):
                self.late_table.setItem(row, 4, QTableWidgetItem("-"))

    def _show_dept_stats(self):
        df = self.dept_date_from.date().toString("yyyy-MM-dd") + " 00:00:00"
        dt = self.dept_date_to.date().toString("yyyy-MM-dd") + " 23:59:59"
        stats = get_department_stats(df, dt)
        self.dept_table.setRowCount(0)
        for s in stats:
            row = self.dept_table.rowCount()
            self.dept_table.insertRow(row)
            self.dept_table.setItem(row, 0, QTableWidgetItem(s.get("department", "Belgilanmagan")))
            self.dept_table.setItem(row, 1, QTableWidgetItem(str(s.get("total_employees", 0))))
            self.dept_table.setItem(row, 2, QTableWidgetItem(str(s.get("total_entries", 0))))
            self.dept_table.setItem(row, 3, QTableWidgetItem(str(s.get("total_exits", 0))))

    def _export_attendance(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            path, _ = QFileDialog.getSaveFileName(self, "Excelga saqlash", f"davomat_{datetime.now().strftime('%Y%m%d')}.xlsx", "Excel Files (*.xlsx)")
            if not path:
                return
            wb = Workbook()
            ws = wb.active
            ws.title = "Davomat"
            headers = ["Xodim", "Sana", "Kelgan vaqt", "Ketgan vaqt", "Ish soati", "Kirishlar", "Holat"]
            for col, h in enumerate(headers, 1):
                c = ws.cell(row=1, column=col, value=h)
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
                c.alignment = Alignment(horizontal="center")
            for row in range(self.att_table.rowCount()):
                for col in range(self.att_table.columnCount()):
                    item = self.att_table.item(row, col)
                    v = item.text() if item else ""
                    for e in ["⚠️", "✅"]:
                        v = v.replace(e, "").strip()
                    ws.cell(row=row + 2, column=col + 1, value=v)
            wb.save(path)
            QMessageBox.information(self, "Tayyor!", f"Fayl saqlandi:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Xatolik", f"Eksport xatosi:\n{e}")
