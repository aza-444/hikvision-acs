"""
Yordamchi funksiyalar
"""
import os
from datetime import datetime


def format_datetime(dt_str, fmt="%d.%m.%Y %H:%M:%S"):
    """Vaqtni formatlash"""
    if not dt_str:
        return ""
    try:
        if "T" in dt_str:
            dt = datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")
        else:
            dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime(fmt)
    except (ValueError, TypeError):
        return str(dt_str)


def format_time(dt_str):
    """Faqat vaqtni olish"""
    return format_datetime(dt_str, "%H:%M:%S")


def format_date(dt_str):
    """Faqat sanani olish"""
    return format_datetime(dt_str, "%d.%m.%Y")


def get_resource_path(filename):
    """Resurs faylining to'liq yo'li"""
    base = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base, "resources", filename)


def calculate_work_hours(first_entry, last_exit):
    """Ish soatlarini hisoblash"""
    try:
        if "T" in first_entry:
            t1 = datetime.strptime(first_entry[:19], "%Y-%m-%dT%H:%M:%S")
        else:
            t1 = datetime.strptime(first_entry[:19], "%Y-%m-%d %H:%M:%S")

        if "T" in last_exit:
            t2 = datetime.strptime(last_exit[:19], "%Y-%m-%dT%H:%M:%S")
        else:
            t2 = datetime.strptime(last_exit[:19], "%Y-%m-%d %H:%M:%S")

        diff = t2 - t1
        hours = diff.total_seconds() / 3600
        return round(hours, 2)
    except (ValueError, TypeError):
        return 0


def is_late(entry_time, schedule_start="09:00"):
    """Kech kelganmi?"""
    try:
        if "T" in entry_time:
            t = datetime.strptime(entry_time[:19], "%Y-%m-%dT%H:%M:%S")
        else:
            t = datetime.strptime(entry_time[:19], "%Y-%m-%d %H:%M:%S")
        start_h, start_m = map(int, schedule_start.split(":"))
        return t.hour > start_h or (t.hour == start_h and t.minute > start_m)
    except (ValueError, TypeError):
        return False


def sanitize_card_number(card_no: str) -> str:
    """Karta raqamini tozalash"""
    return card_no.strip().upper().replace(" ", "")
