"""
Hikvision ISAPI xizmati - Turniket va terminallar bilan universal bog'lanish
Hikvision DS-K1Txxx, DS-K2600, MinMoe, Face Recognition va barcha ISAPI turniketlari uchun moslashtirilgan.
"""
import requests
from requests.auth import HTTPDigestAuth
import xmltodict
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable


class HikvisionDevice:
    """Hikvision qurilmasi bilan universal aloqa klassi"""

    def __init__(self, ip: str, port: int = 80, username: str = "admin", password: str = ""):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"http://{ip}:{port}"
        self.auth = HTTPDigestAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.timeout = 8
        self.is_connected = False

    def _request(self, method: str, path: str, data=None, headers=None, timeout=None):
        """Universal ISAPI so'rovi (XML va JSON javoblarni qo'llab-quvvatlaydi)"""
        url = f"{self.base_url}{path}"
        t = timeout or self.timeout
        h = headers or {}
        try:
            if method.upper() == "GET":
                resp = self.session.get(url, headers=h, timeout=t)
            elif method.upper() == "PUT":
                resp = self.session.put(url, data=data, headers=h, timeout=t)
            elif method.upper() == "POST":
                resp = self.session.post(url, data=data, headers=h, timeout=t)
            elif method.upper() == "DELETE":
                resp = self.session.delete(url, headers=h, timeout=t)
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
            else:
                return {"error": f"HTTP {resp.status_code}", "detail": resp.text}
        except requests.exceptions.Timeout:
            return {"error": "Ulanish vaqti tugadi (Timeout)"}
        except requests.exceptions.ConnectionError:
            return {"error": f"Qurilmaga ulanib bo'lmadi: {self.ip}:{self.port}"}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # Qurilma ma'lumotlari
    # ============================================================

    def check_connection(self) -> bool:
        """Qurilma bilan aloqani tekshirish"""
        res = self._request("GET", "/ISAPI/System/deviceInfo")
        self.is_connected = res is not None and "error" not in res
        return self.is_connected

    def get_device_info(self) -> dict:
        """Qurilma ma'lumotlarini olish (Model, Seriya, Firmware)"""
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

    def always_open(self, door_no: int = 1) -> dict:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <RemoteControlDoor version="2.0">
            <cmd>alwaysOpen</cmd>
        </RemoteControlDoor>"""
        return self._request("PUT", f"/ISAPI/AccessControl/RemoteControl/door/{door_no}",
                             data=xml, headers={"Content-Type": "application/xml"})

    # ============================================================
    # Kirish-chiqish voqealarini olish (Events)
    # ============================================================

    def get_access_events(self, start_time: str = "", end_time: str = "", max_results: int = 30) -> dict:
        if not start_time:
            start_time = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
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
    # Real-time AlertStream (Instant kechikishsiz oqim)
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
    """Real-time monitoring oqimi (AlertStream + Polling zaxira)"""

    def __init__(self, device: HikvisionDevice, callback: Callable, interval: int = 4):
        super().__init__(daemon=True)
        self.device = device
        self.callback = callback
        self.interval = interval
        self._stop_event = threading.Event()
        self.last_handled_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def run(self):
        stream_thread = threading.Thread(
            target=self.device.listen_alert_stream,
            args=(self._on_stream_alert, self._stop_event),
            daemon=True
        )
        stream_thread.start()

        while not self._stop_event.is_set():
            try:
                events = self.device.get_latest_events(count=20)
                if events and "error" not in events:
                    self._process_poll_events(events)
            except Exception:
                pass
            self._stop_event.wait(self.interval)

    def _on_stream_alert(self, alert_data):
        try:
            event = self._parse_generic_event(alert_data)
            if event:
                self.callback(event)
        except Exception as e:
            print(f"[AlertStream Parse Error]: {e}")

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
                        self.callback(parsed)
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
