"""
Hikvision ISAPI xizmati - Turniket va terminallar bilan universal bog'lanish
HTTP va HTTPS ni avtomatik aniqlaydi, barcha Hikvision qurilmalari bilan barqaror ishlaydi.
"""
import requests
from requests.auth import HTTPDigestAuth, HTTPBasicAuth
import xmltodict
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable
import urllib3

# HTTPS sertifikat ogohlantirishlarini o'chirish
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HikvisionDevice:
    """Hikvision qurilmasi bilan universal aloqa klassi"""

    def __init__(self, ip: str, port: int = 80, username: str = "admin", password: str = ""):
        self.ip = ip.strip()
        self.port = int(port) if port else 80
        self.username = username.strip()
        self.password = password
        self.protocol = "https" if self.port == 443 else "http"
        self.base_url = f"{self.protocol}://{self.ip}:{self.port}"
        self.auth = HTTPDigestAuth(self.username, self.password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = False  # O'z-o'zidan imzolangan sertifikatlarga ruxsat berish
        self.timeout = 5
        self.is_connected = False
        self.last_error = ""

    def _request(self, method: str, path: str, data=None, headers=None, timeout=None):
        """Universal ISAPI so'rovi (HTTP va HTTPS avto-almashtirish bilan)"""
        t = timeout or self.timeout
        h = headers or {}

        # 1-urinish: standart protocol bilan
        res = self._do_http_request(self.protocol, method, path, data, h, t)
        if res and "error" not in res:
            return res

        # Agar HTTP da ulanib bo'lmasa, HTTPS orqali tekshirish
        alt_protocol = "https" if self.protocol == "http" else "http"
        res_alt = self._do_http_request(alt_protocol, method, path, data, h, t)
        if res_alt and "error" not in res_alt:
            self.protocol = alt_protocol
            self.base_url = f"{self.protocol}://{self.ip}:{self.port}"
            return res_alt

        return res

    def _do_http_request(self, proto: str, method: str, path: str, data, headers, timeout):
        url = f"{proto}://{self.ip}:{self.port}{path}"
        try:
            if method.upper() == "GET":
                resp = self.session.get(url, headers=headers, timeout=timeout)
            elif method.upper() == "PUT":
                resp = self.session.put(url, data=data, headers=headers, timeout=timeout)
            elif method.upper() == "POST":
                resp = self.session.post(url, data=data, headers=headers, timeout=timeout)
            elif method.upper() == "DELETE":
                resp = self.session.delete(url, headers=headers, timeout=timeout)
            else:
                return None

            if resp.status_code in (200, 201):
                content = resp.content
                if "application/json" in resp.headers.get("Content-Type", ""):
                    try:
                        return resp.json()
                    except Exception:
                        pass
                try:
                    return xmltodict.parse(content)
                except Exception:
                    try:
                        return json.loads(resp.text)
                    except Exception:
                        return {"raw": resp.text}
            elif resp.status_code == 401:
                # Basic Auth bilan sinab ko'rish (ba'zi eski firmwareda)
                basic_resp = requests.request(
                    method, url, data=data, headers=headers,
                    auth=HTTPBasicAuth(self.username, self.password),
                    timeout=timeout, verify=False
                )
                if basic_resp.status_code in (200, 201):
                    self.session.auth = HTTPBasicAuth(self.username, self.password)
                    try:
                        return xmltodict.parse(basic_resp.content)
                    except Exception:
                        return {"raw": basic_resp.text}
                self.last_error = "Parol yoki login xato! (HTTP 401 Unauthorized)"
                return {"error": "HTTP 401", "detail": "Parol yoki login noto'g'ri"}
            elif resp.status_code == 403:
                self.last_error = "Ruxsat berilmadi (HTTP 403 Forbidden - ISAPI o'chirilgan bo'lishi mumkin)"
                return {"error": "HTTP 403", "detail": self.last_error}
            else:
                self.last_error = f"HTTP xatosi: {resp.status_code}"
                return {"error": f"HTTP {resp.status_code}", "detail": resp.text}
        except requests.exceptions.ConnectTimeout:
            self.last_error = f"IP ga ulanib bo'lmadi ({self.ip}:{self.port}) - Timeout! Tarmoqni tekshiring."
            return {"error": "Timeout"}
        except requests.exceptions.ConnectionError as ce:
            self.last_error = f"Aloqa uzilgan yoki port yopiq ({self.ip}:{self.port})"
            return {"error": "ConnectionError"}
        except Exception as e:
            self.last_error = str(e)
            return {"error": str(e)}

    # ============================================================
    # Qurilma ma'lumotlari va diagnostika
    # ============================================================

    def check_connection(self) -> tuple[bool, str]:
        """Qurilma bilan aloqani tekshirish va batafsil natija qaytarish"""
        res = self._request("GET", "/ISAPI/System/deviceInfo")
        if res and "error" not in res:
            self.is_connected = True
            dev_info = res.get("DeviceInfo", {}) if isinstance(res, dict) else {}
            name = dev_info.get("deviceName", "Hikvision")
            model = dev_info.get("model", "")
            return True, f"Ulandi! Model: {model or name}"
        else:
            self.is_connected = False
            return False, self.last_error or "Qurilmaga ulanib bo'lmadi"

    def get_device_info(self) -> dict:
        return self._request("GET", "/ISAPI/System/deviceInfo")

    # ============================================================
    # Foydalanuvchilar (Xodimlar) va Kartalar
    # ============================================================

    def add_user(self, employee_no: str, name: str, card_no: str = "",
                 valid_from: str = "", valid_to: str = "") -> dict:
        if not valid_from:
            valid_from = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if not valid_to:
            valid_to = (datetime.now() + timedelta(days=3650)).strftime("%Y-%m-%dT%H:%M:%S")

        user_json = {
            "UserInfo": {
                "employeeNo": str(employee_no),
                "name": name,
                "userType": "normal",
                "closeDelayEnabled": False,
                "Valid": {
                    "enable": True,
                    "beginTime": valid_from,
                    "endTime": valid_to,
                    "timeType": "local",
                },
                "doorRight": "1",
                "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
            }
        }
        res = self._request(
            "POST",
            "/ISAPI/AccessControl/UserInfo/Record?format=json",
            data=json.dumps(user_json),
            headers={"Content-Type": "application/json"}
        )

        if res and "error" in res:
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <UserInfo version="2.0">
                <employeeNo>{employee_no}</employeeNo>
                <name>{name}</name>
                <userType>normal</userType>
                <Valid>
                    <enable>true</enable>
                    <beginTime>{valid_from}</beginTime>
                    <endTime>{valid_to}</endTime>
                    <timeType>local</timeType>
                </Valid>
                <doorRight>1</doorRight>
            </UserInfo>"""
            res = self._request("POST", "/ISAPI/AccessControl/UserInfo/Record", data=xml,
                                headers={"Content-Type": "application/xml"})

        if card_no and card_no.strip():
            self.add_card(employee_no=str(employee_no), card_no=card_no.strip())

        return res

    def add_card(self, employee_no: str, card_no: str, card_type: str = "normalCard") -> dict:
        card_json = {
            "CardInfo": {
                "employeeNo": str(employee_no),
                "cardNo": str(card_no),
                "cardType": card_type,
                "leaderCard": ""
            }
        }
        res = self._request(
            "POST",
            "/ISAPI/AccessControl/CardInfo/Record?format=json",
            data=json.dumps(card_json),
            headers={"Content-Type": "application/json"}
        )
        if res and "error" in res:
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <CardInfo version="2.0">
                <employeeNo>{employee_no}</employeeNo>
                <cardNo>{card_no}</cardNo>
                <cardType>{card_type}</cardType>
            </CardInfo>"""
            res = self._request("POST", "/ISAPI/AccessControl/CardInfo/Record", data=xml,
                                headers={"Content-Type": "application/xml"})
        return res

    def delete_user(self, employee_no: str) -> dict:
        data = {"UserInfoDelCond": {"EmployeeNoList": [{"employeeNo": str(employee_no)}]}}
        return self._request(
            "PUT",
            "/ISAPI/AccessControl/UserInfo/Delete?format=json",
            data=json.dumps(data),
            headers={"Content-Type": "application/json"}
        )

    # ============================================================
    # Turniketdan Xodimlar va Kartalarni Import Qilish
    # ============================================================

    def get_users_list(self, max_count: int = 500) -> list[dict]:
        """Qurilmadagi barcha ro'yxatdan o'tgan foydalanuvchilar (xodimlar) ro'yxati"""
        users = []
        pos = 0
        step = 50

        while pos < max_count:
            req_data = {
                "UserInfoSearchCond": {
                    "searchID": "1",
                    "searchResultPosition": pos,
                    "maxResults": step
                }
            }
            res = self._request(
                "POST",
                "/ISAPI/AccessControl/UserInfo/Search?format=json",
                data=json.dumps(req_data),
                headers={"Content-Type": "application/json"}
            )

            if not res or "error" in res:
                xml = f"""<?xml version="1.0" encoding="UTF-8"?>
                <UserInfoSearchCond version="2.0">
                    <searchID>1</searchID>
                    <searchResultPosition>{pos}</searchResultPosition>
                    <maxResults>{step}</maxResults>
                </UserInfoSearchCond>"""
                res = self._request("POST", "/ISAPI/AccessControl/UserInfo/Search", data=xml,
                                    headers={"Content-Type": "application/xml"})

            batch = []
            if isinstance(res, dict):
                search_res = res.get("UserInfoSearch", {}) or res.get("UserInfoSearchResult", {})
                if search_res:
                    user_info = search_res.get("UserInfo", [])
                    batch = [user_info] if isinstance(user_info, dict) else user_info

            if not batch:
                break

            for u in batch:
                emp_no = str(u.get("employeeNo", "")).strip()
                name = str(u.get("name", "")).strip()
                if emp_no:
                    users.append({
                        "employee_no": emp_no,
                        "name": name,
                        "user_type": u.get("userType", "normal")
                    })

            pos += len(batch)
            if len(batch) < step:
                break

        return users

    def get_cards_list(self, max_count: int = 500) -> dict[str, str]:
        """Qurilmadagi barcha kartalar ro'yxati (employeeNo -> cardNo)"""
        cards = {}
        pos = 0
        step = 50

        while pos < max_count:
            req_data = {
                "CardInfoSearchCond": {
                    "searchID": "1",
                    "searchResultPosition": pos,
                    "maxResults": step
                }
            }
            res = self._request(
                "POST",
                "/ISAPI/AccessControl/CardInfo/Search?format=json",
                data=json.dumps(req_data),
                headers={"Content-Type": "application/json"}
            )

            if not res or "error" in res:
                xml = f"""<?xml version="1.0" encoding="UTF-8"?>
                <CardInfoSearchCond version="2.0">
                    <searchID>1</searchID>
                    <searchResultPosition>{pos}</searchResultPosition>
                    <maxResults>{step}</maxResults>
                </CardInfoSearchCond>"""
                res = self._request("POST", "/ISAPI/AccessControl/CardInfo/Search", data=xml,
                                    headers={"Content-Type": "application/xml"})

            batch = []
            if isinstance(res, dict):
                search_res = res.get("CardInfoSearch", {}) or res.get("CardInfoSearchResult", {})
                if search_res:
                    card_info = search_res.get("CardInfo", [])
                    batch = [card_info] if isinstance(card_info, dict) else card_info

            if not batch:
                break

            for c in batch:
                emp_no = str(c.get("employeeNo", "")).strip()
                card_no = str(c.get("cardNo", "")).strip()
                if emp_no and card_no:
                    cards[emp_no] = card_no

            pos += len(batch)
            if len(batch) < step:
                break

        return cards

    def fetch_all_employees_with_cards(self, progress_callback=None) -> list[dict]:
        """Turniketdan xodimlar va ularga biriktirilgan kartalarni birlashtirib yuklash"""
        if progress_callback:
            progress_callback(10, "Turniketdan kartalar ro'yxati olinmoqda...")
        card_map = self.get_cards_list()

        if progress_callback:
            progress_callback(35, "Turniketdan xodimlar ma'lumotlari yuklanmoqda...")
        users = self.get_users_list()

        results = []
        total = len(users)
        for i, u in enumerate(users):
            full_name = u["name"].strip()
            parts = full_name.split(None, 1)
            first_name = parts[0] if parts else f"Xodim_{u['employee_no']}"
            last_name = parts[1] if len(parts) > 1 else ""

            emp_no = u["employee_no"]
            card_no = card_map.get(emp_no, "")

            results.append({
                "employee_no": emp_no,
                "first_name": first_name,
                "last_name": last_name,
                "department": "Umumiy",
                "position": "Xodim",
                "phone": "",
                "email": "",
                "card_no": card_no,
                "photo_path": ""
            })

            if progress_callback and total > 0:
                pct = 40 + int(((i + 1) / total) * 55)
                progress_callback(pct, f"Yuklandi: {i+1}/{total} - {first_name} {last_name}")

        return results

    # ============================================================
    # Turniketni Masofadan Boshqarish (Remote Control)
    # ============================================================

    def open_door(self, door_no: int = 1) -> dict:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <RemoteControlDoor version="2.0">
            <cmd>open</cmd>
        </RemoteControlDoor>"""
        return self._request("PUT", f"/ISAPI/AccessControl/RemoteControl/door/{door_no}",
                             data=xml, headers={"Content-Type": "application/xml"})

    def close_door(self, door_no: int = 1) -> dict:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <RemoteControlDoor version="2.0">
            <cmd>close</cmd>
        </RemoteControlDoor>"""
        return self._request("PUT", f"/ISAPI/AccessControl/RemoteControl/door/{door_no}",
                             data=xml, headers={"Content-Type": "application/xml"})

    # ============================================================
    # Kirish-chiqish voqealarini olish (Events)
    # ============================================================

    def get_access_events(self, start_time: str = "", end_time: str = "", max_results: int = 30) -> dict:
        if not start_time:
            start_time = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S")
        if not end_time:
            end_time = datetime.now().strftime("%Y-%m-%dT23:59:59")

        cond_json = {
            "AcsEventCond": {
                "searchID": "1",
                "searchResultPosition": 0,
                "maxResults": max_results,
                "major": 5,
                "startTime": start_time,
                "endTime": end_time
            }
        }
        res = self._request("POST", "/ISAPI/AccessControl/AcsEvent?format=json",
                            data=json.dumps(cond_json),
                            headers={"Content-Type": "application/json"})

        if res and "error" in res:
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <AcsEventCond version="2.0">
                <searchID>1</searchID>
                <searchResultPosition>0</searchResultPosition>
                <maxResults>{max_results}</maxResults>
                <major>5</major>
                <startTime>{start_time}</startTime>
                <endTime>{end_time}</endTime>
            </AcsEventCond>"""
            res = self._request("POST", "/ISAPI/AccessControl/AcsEvent",
                                data=xml, headers={"Content-Type": "application/xml"})
        return res

    def get_latest_events(self, count: int = 20) -> dict:
        now = datetime.now()
        start = (now - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S")
        end = now.strftime("%Y-%m-%dT%H:%M:%S")
        return self.get_access_events(start_time=start, end_time=end, max_results=count)

    # ============================================================
    # Real-time AlertStream
    # ============================================================

    def listen_alert_stream(self, callback: Callable, stop_event: threading.Event):
        url = f"{self.base_url}/ISAPI/Event/notification/alertStream"
        while not stop_event.is_set():
            try:
                with self.session.get(url, stream=True, timeout=60) as resp:
                    if resp.status_code != 200:
                        time.sleep(5)
                        continue

                    buffer = ""
                    for chunk in resp.iter_content(chunk_size=1024, decode_unicode=True):
                        if stop_event.is_set():
                            break
                        if chunk:
                            buffer += chunk
                            if "</EventNotificationAlert>" in buffer:
                                part = buffer[:buffer.find("</EventNotificationAlert>") + len("</EventNotificationAlert>")]
                                buffer = buffer[buffer.find("</EventNotificationAlert>") + len("</EventNotificationAlert>"):]
                                try:
                                    parsed = xmltodict.parse(part)
                                    callback(parsed)
                                except Exception:
                                    pass
                            elif "\r\n\r\n" in buffer and "Content-Type: application/json" in buffer:
                                lines = buffer.split("\r\n\r\n")
                                if len(lines) > 1:
                                    body = lines[1]
                                    try:
                                        data = json.loads(body)
                                        callback(data)
                                        buffer = ""
                                    except Exception:
                                        pass
            except Exception:
                time.sleep(4)


class EventPoller(threading.Thread):
    """Real-time monitoring oqimi va Online/Offline tekshiruvchisi"""

    def __init__(self, device: HikvisionDevice, device_id: int, on_event: Callable, on_status_change: Callable, interval: int = 3):
        super().__init__(daemon=True)
        self.device = device
        self.device_id = device_id
        self.on_event = on_event
        self.on_status_change = on_status_change
        self.interval = interval
        self._stop_event = threading.Event()
        self.last_handled_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.is_online = False

    def run(self):
        # 1. AlertStream ulanish
        stream_thread = threading.Thread(
            target=self.device.listen_alert_stream,
            args=(self._on_stream_alert, self._stop_event),
            daemon=True
        )
        stream_thread.start()

        # 2. Polling va Online holatini yangilab turish
        while not self._stop_event.is_set():
            try:
                ok, msg = self.device.check_connection()
                if ok != self.is_online:
                    self.is_online = ok
                    self.on_status_change(self.device_id, ok)

                if self.is_online:
                    events = self.device.get_latest_events(count=20)
                    if events and "error" not in events:
                        self._process_poll_events(events)
            except Exception:
                if self.is_online:
                    self.is_online = False
                    self.on_status_change(self.device_id, False)

            self._stop_event.wait(self.interval)

    def _on_stream_alert(self, alert_data):
        try:
            event = self._parse_generic_event(alert_data)
            if event:
                self.on_event(event)
        except Exception:
            pass

    def _process_poll_events(self, events_data):
        try:
            items = []
            if isinstance(events_data, dict):
                res1 = events_data.get("AcsEventSearchResult", {})
                if res1:
                    match_list = res1.get("MatchList", {}).get("AcsEventInfo", [])
                    items = [match_list] if isinstance(match_list, dict) else match_list
                res2 = events_data.get("AcsEvent", {})
                if res2:
                    info_list = res2.get("InfoList", [])
                    items = [info_list] if isinstance(info_list, dict) else info_list

            for item in items:
                t_str = item.get("time", "").replace("T", " ")[:19]
                if t_str and t_str > self.last_handled_time:
                    parsed = self._parse_generic_event(item)
                    if parsed:
                        self.last_handled_time = t_str
                        self.on_event(parsed)
        except Exception:
            pass

    def _parse_generic_event(self, item: dict) -> dict:
        emp_no = str(item.get("employeeNoString") or item.get("employeeNo") or "")
        card_no = str(item.get("cardNo") or "")
        name = item.get("name", "")

        minor = str(item.get("minor") or item.get("minorType") or "1")
        event_type = "exit" if minor in ("2", "0x02", "75") else "entry"

        v_mode = str(item.get("currentVerifyMode") or item.get("verifyMode") or "").lower()
        method = "card"
        if "face" in v_mode:
            method = "face"
        elif "finger" in v_mode:
            method = "fingerprint"
        elif "qr" in v_mode:
            method = "qr"
        elif card_no:
            method = "card"

        t_str = item.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")).replace("T", " ")[:19]

        return {
            "employee_no": emp_no,
            "employee_name": name,
            "card_no": card_no,
            "event_type": event_type,
            "event_time": t_str,
            "access_method": method,
            "status": "granted",
            "temperature": float(item.get("currTemperature", 0)),
            "raw": item
        }

    def stop(self):
        self._stop_event.set()
