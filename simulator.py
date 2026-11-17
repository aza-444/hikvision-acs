"""
Hikvision Turniket Simulyatori (Testlash uchun)
Haqiqiy turniket yo'q bo'lganda yoki test o'tkazish uchun virtual kirish-chiqish voqealari yaratadi
va Telegram botga ham xabar yuborishni tekshiradi.
"""
import sys
import os
import time
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import init_database, get_all_employees, add_access_event
from services.telegram_bot import TelegramNotifier


def run_simulator(interval_seconds=4):
    print("=" * 65)
    print("  HIKVISION TURNIKET SIMULYATORI ISHGA TUSHDI")
    print("  Har bir necha soniyada xodimlar kirib-chiqishini simulyatsiya qiladi")
    print("  Telegram bot ulangan bo'lsa, xabarlar Telegramga ham boradi")
    print("=" * 65)

    init_database()
    employees = get_all_employees()

    if not employees:
        print("[!] Xodimlar topilmadi. Avval dasturni bir marta ishga tushiring yoki xodim qo'shing.")
        return

    methods = ["card", "face", "fingerprint", "qr"]
    types = ["entry", "exit"]
    turnstiles = ["Turniket 1 (Asosiy kirish)", "Turniket 2 (Orqa eshik)"]

    print(f"Bazada mavjud xodimlar: {len(employees)} ta")
    print(f"Interval: {interval_seconds} soniya. To'xtatish uchun: Ctrl + C\n")

    try:
        while True:
            emp = random.choice(employees)
            ev_type = random.choice(types)
            method = random.choice(methods)
            turnstile = random.choice(turnstiles)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            event_record = {
                "employee_id": emp["id"],
                "employee_no": emp["employee_no"],
                "employee_name": f"{emp['first_name']} {emp['last_name']}",
                "device_id": 1,
                "device_name": turnstile,
                "event_type": ev_type,
                "access_method": method,
                "card_no": emp.get("card_no", "12345678"),
                "event_time": now_str,
                "status": "granted",
                "temperature": round(random.uniform(36.2, 36.8), 1),
                "photo_url": "",
                "raw_data": '{"simulated": true}'
            }

            add_access_event(event_record)

            # Telegram xabar
            TelegramNotifier.notify_access_event(event_record)

            icon = "🟢 KIRISH" if ev_type == "entry" else "🔴 CHIQISH"
            print(f"[{now_str}] {icon} | {emp['first_name']} {emp['last_name']} ({emp['employee_no']}) | Usul: {method} | {turnstile}")

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nSimulyator to'xtatildi.")


if __name__ == "__main__":
    interval = 4
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            pass
    run_simulator(interval)
