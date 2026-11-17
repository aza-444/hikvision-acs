"""
Telegram Bot integratsiyasi
Turniketdan kirish-chiqish sodir bo'lganda Telegram guruh yoki rahbar chatiga avtomatik xabar yuborish
"""
import requests
import threading
from datetime import datetime
from models.database import get_setting


class TelegramNotifier:
    """Telegram orqali xabarnoma yuboruvchi xizmat"""

    @staticmethod
    def send_message_async(text: str):
        """Xabarni asosiy oqimni (UI) qotirmaslik uchun alohida thread orqali yuborish"""
        threading.Thread(target=TelegramNotifier._send_message, args=(text,), daemon=True).start()

    @staticmethod
    def _send_message(text: str):
        token = get_setting("telegram_bot_token", "").strip()
        chat_id = get_setting("telegram_chat_id", "").strip()
        enabled = get_setting("telegram_enabled", "0") == "1"

        if not enabled or not token or not chat_id:
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"[Telegram Error] Xabar yuborishda xatolik: {e}")

    @staticmethod
    def notify_access_event(event: dict):
        """Turniket hodisasi haqida formatlangan xabar yuborish"""
        enabled = get_setting("telegram_enabled", "0") == "1"
        if not enabled:
            return

        # Filtrlash sozlamalari
        notify_entries = get_setting("telegram_notify_entries", "1") == "1"
        notify_exits = get_setting("telegram_notify_exits", "1") == "1"
        notify_late_only = get_setting("telegram_notify_late_only", "0") == "1"

        ev_type = event.get("event_type", "entry")
        if ev_type == "entry" and not notify_entries:
            return
        if ev_type == "exit" and not notify_exits:
            return

        emp_name = event.get("employee_name") or "Noma'lum shaxs"
        emp_no = event.get("employee_no") or "-"
        time_str = event.get("event_time", "")
        dev_name = event.get("device_name") or "Asosiy Turniket"
        method = event.get("access_method", "card")

        method_icons = {
            "card": "💳 Karta",
            "face": "👤 Yuzni tanish",
            "fingerprint": "👆 Barmoq izi",
            "qr": "📱 QR kod"
        }
        method_text = method_icons.get(method, "💳 Karta")

        # Kechikishni aniqlash
        is_late = False
        try:
            dt = datetime.strptime(time_str[:19], "%Y-%m-%d %H:%M:%S")
            time_formatted = dt.strftime("%H:%M:%S")
            date_formatted = dt.strftime("%d.%m.%Y")
            if ev_type == "entry" and (dt.hour > 9 or (dt.hour == 9 and dt.minute > 0)):
                is_late = True
        except Exception:
            time_formatted = time_str
            date_formatted = ""

        if notify_late_only and not is_late:
            return

        if ev_type == "entry":
            header = "🟢 <b>KIRISH QAYD ETILDI</b>"
            if is_late:
                header = "⚠️ <b>KECHIKIB KIRISH!</b>"
        else:
            header = "🔴 <b>CHIQISH QAYD ETILDI</b>"

        msg = (
            f"{header}\n\n"
            f"👤 <b>Xodim:</b> {emp_name}\n"
            f"🆔 <b>ID raqam:</b> <code>{emp_no}</code>\n"
            f"🚪 <b>Qurilma:</b> {dev_name}\n"
            f"🔑 <b>Usul:</b> {method_text}\n"
            f"⏰ <b>Vaqt:</b> {time_formatted} ({date_formatted})\n"
        )

        if event.get("temperature", 0) > 0:
            msg += f"🌡 <b>Harorat:</b> {event.get('temperature')} °C\n"

        TelegramNotifier.send_message_async(msg)

    @staticmethod
    def test_connection(token: str, chat_id: str) -> tuple[bool, str]:
        """Bot token va Chat ID to'g'riligini tekshirish"""
        if not token or not chat_id:
            return False, "Token va Chat ID bo'sh bo'lishi mumkin emas!"

        url = f"https://api.telegram.org/bot{token}/getMe"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return False, "Bot token noto'g'ri! BotFather bergan tokenni tekshiring."
            
            bot_info = resp.json().get("result", {})
            bot_name = bot_info.get("first_name", "Bot")

            # Chatga test xabar yuborish
            send_url = f"https://api.telegram.org/bot{token}/sendMessage"
            test_msg = {
                "chat_id": chat_id,
                "text": f"✅ <b>Hikvision Turniket Tizimi ulandi!</b>\n\nBot: @{bot_info.get('username')}\nTizim bildirishnomalari shu yerga keladi.",
                "parse_mode": "HTML"
            }
            send_resp = requests.post(send_url, json=test_msg, timeout=5)
            if send_resp.status_code == 200:
                return True, f"Muvaffaqiyatli! Bot: @{bot_info.get('username')}. Test xabar chatga yuborildi."
            else:
                return False, f"Bot topildi (@{bot_info.get('username')}), lekin chatga xabar yuborib bo'lmadi. Chat ID to'g'riligini tekshiring (Botga avval /start bosgan bo'lishingiz kerak)."
        except requests.exceptions.RequestException as e:
            return False, f"Internet yoki tarmoq xatosi: {e}"
