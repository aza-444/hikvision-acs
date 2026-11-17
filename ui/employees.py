"""
Xodimlar boshqaruv sahifasi
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QDialog, QFormLayout, QComboBox, QMessageBox, QFileDialog,
    QFrame, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from models.database import (
    get_all_employees, add_employee, update_employee, delete_employee,
    search_employees, get_all_departments, get_employee
)


class EmployeeDialog(QDialog):
    """Xodim qo'shish/tahrirlash dialogi"""
    def __init__(self, employee=None, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.photo_path = employee.get("photo_path", "") if employee else ""
        self.setWindowTitle("Xodim qo'shish" if not employee else "Xodimni tahrirlash")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("👤 Xodim ma'lumotlari")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        # Rasm
        photo_layout = QHBoxLayout()
        self.photo_label = QLabel()
        self.photo_label.setFixedSize(100, 120)
        self.photo_label.setStyleSheet("background-color: #374151; border-radius: 8px; border: 2px dashed #6b7280;")
        self.photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_label.setText("📷")
        self.photo_label.setFont(QFont("Segoe UI Emoji", 24))
        if self.photo_path and self.photo_path.strip():
            pixmap = QPixmap(self.photo_path)
            if not pixmap.isNull():
                self.photo_label.setPixmap(pixmap.scaled(100, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        photo_layout.addWidget(self.photo_label)
        btn_choose = QPushButton("📁 Rasm tanlash")
        btn_choose.setObjectName("btnSecondary")
        btn_choose.clicked.connect(self._choose_photo)
        photo_layout.addWidget(btn_choose)
        photo_layout.addStretch()
        layout.addLayout(photo_layout)

        form = QFormLayout()
        form.setSpacing(12)
        self.inp_emp_no = QLineEdit()
        self.inp_emp_no.setPlaceholderText("Masalan: EMP001")
        form.addRow("Xodim raqami *:", self.inp_emp_no)
        self.inp_first_name = QLineEdit()
        self.inp_first_name.setPlaceholderText("Ism")
        form.addRow("Ism *:", self.inp_first_name)
        self.inp_last_name = QLineEdit()
        self.inp_last_name.setPlaceholderText("Familiya")
        form.addRow("Familiya *:", self.inp_last_name)
        self.inp_department = QComboBox()
        self.inp_department.setEditable(True)
        for d in get_all_departments():
            self.inp_department.addItem(d["name"])
        form.addRow("Bo'lim:", self.inp_department)
        self.inp_position = QLineEdit()
        self.inp_position.setPlaceholderText("Lavozim")
        form.addRow("Lavozim:", self.inp_position)
        self.inp_phone = QLineEdit()
        self.inp_phone.setPlaceholderText("+998 xx xxx xx xx")
        form.addRow("Telefon:", self.inp_phone)
        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText("email@example.com")
        form.addRow("Email:", self.inp_email)
        self.inp_card_no = QLineEdit()
        self.inp_card_no.setPlaceholderText("Karta raqami (turniket uchun)")
        form.addRow("Karta raqami:", self.inp_card_no)
        layout.addLayout(form)

        if self.employee:
            self.inp_emp_no.setText(self.employee.get("employee_no", ""))
            self.inp_first_name.setText(self.employee.get("first_name", ""))
            self.inp_last_name.setText(self.employee.get("last_name", ""))
            dept = self.employee.get("department", "")
            idx = self.inp_department.findText(dept)
            if idx >= 0:
                self.inp_department.setCurrentIndex(idx)
            else:
                self.inp_department.setEditText(dept)
            self.inp_position.setText(self.employee.get("position", ""))
            self.inp_phone.setText(self.employee.get("phone", ""))
            self.inp_email.setText(self.employee.get("email", ""))
            self.inp_card_no.setText(self.employee.get("card_no", ""))

        layout.addStretch()
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("Bekor qilish")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_save = QPushButton("💾  Saqlash")
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _choose_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Rasm tanlash", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.photo_path = path
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.photo_label.setPixmap(pixmap.scaled(100, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _save(self):
        if not self.inp_emp_no.text().strip():
            QMessageBox.warning(self, "Xatolik", "Xodim raqamini kiriting!")
            return
        if not self.inp_first_name.text().strip():
            QMessageBox.warning(self, "Xatolik", "Ismni kiriting!")
            return
        if not self.inp_last_name.text().strip():
            QMessageBox.warning(self, "Xatolik", "Familiyani kiriting!")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "employee_no": self.inp_emp_no.text().strip(),
            "first_name": self.inp_first_name.text().strip(),
            "last_name": self.inp_last_name.text().strip(),
            "department": self.inp_department.currentText().strip(),
            "position": self.inp_position.text().strip(),
            "phone": self.inp_phone.text().strip(),
            "email": self.inp_email.text().strip(),
            "card_no": self.inp_card_no.text().strip(),
            "photo_path": self.photo_path,
        }


class EmployeesPage(QWidget):
    """Xodimlar sahifasi"""
    employee_synced = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QHBoxLayout()
        title = QLabel("👥  Xodimlar ro'yxati")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        self.count_label = QLabel()
        self.count_label.setObjectName("subtitle")
        header.addWidget(self.count_label)
        layout.addLayout(header)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Xodim qidirish (ism, ID, karta raqami)...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)
        toolbar.addStretch()
        btn_add = QPushButton("➕  Yangi xodim")
        btn_add.clicked.connect(self._add_employee)
        toolbar.addWidget(btn_add)
        btn_edit = QPushButton("✏️  Tahrirlash")
        btn_edit.setObjectName("btnSecondary")
        btn_edit.clicked.connect(self._edit_employee)
        toolbar.addWidget(btn_edit)
        btn_delete = QPushButton("🗑️  O'chirish")
        btn_delete.setObjectName("btnDanger")
        btn_delete.clicked.connect(self._delete_employee)
        toolbar.addWidget(btn_delete)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "Xodim raqami", "Ism", "Familiya", "Bo'lim", "Lavozim", "Telefon", "Karta raqami"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self._edit_employee)
        layout.addWidget(self.table)

    def refresh_table(self, employees=None):
        if employees is None:
            employees = get_all_employees()
        self.table.setRowCount(0)
        for emp in employees:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(emp["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(emp["employee_no"]))
            self.table.setItem(row, 2, QTableWidgetItem(emp["first_name"]))
            self.table.setItem(row, 3, QTableWidgetItem(emp["last_name"]))
            self.table.setItem(row, 4, QTableWidgetItem(emp.get("department", "")))
            self.table.setItem(row, 5, QTableWidgetItem(emp.get("position", "")))
            self.table.setItem(row, 6, QTableWidgetItem(emp.get("phone", "")))
            self.table.setItem(row, 7, QTableWidgetItem(emp.get("card_no", "")))
        self.count_label.setText(f"Jami: {len(employees)} ta xodim")

    def _on_search(self, text):
        if text.strip():
            results = search_employees(text.strip())
        else:
            results = get_all_employees()
        self.refresh_table(results)

    def _get_selected_id(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Diqqat", "Avval xodimni tanlang!")
            return None
        return int(self.table.item(rows[0].row(), 0).text())

    def _add_employee(self):
        dlg = EmployeeDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                add_employee(data)
                self.refresh_table()
                QMessageBox.information(self, "Muvaffaqiyat", "Xodim muvaffaqiyatli qo'shildi!")
            except Exception as e:
                QMessageBox.critical(self, "Xatolik", f"Xodim qo'shishda xatolik:\n{e}")

    def _edit_employee(self):
        emp_id = self._get_selected_id()
        if emp_id is None:
            return
        emp = get_employee(emp_id)
        if not emp:
            return
        dlg = EmployeeDialog(employee=emp, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                update_employee(emp_id, data)
                self.refresh_table()
                QMessageBox.information(self, "Muvaffaqiyat", "Xodim ma'lumotlari yangilandi!")
            except Exception as e:
                QMessageBox.critical(self, "Xatolik", f"Tahrirlashda xatolik:\n{e}")

    def _delete_employee(self):
        emp_id = self._get_selected_id()
        if emp_id is None:
            return
        reply = QMessageBox.question(self, "Tasdiqlash", "Haqiqatan ham bu xodimni o'chirmoqchimisiz?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_employee(emp_id)
            self.refresh_table()
