"""
Hikvision Qurilmalarini Avtomatik Qidirish (SADP & IP Scan)
Lokal tarmoqdagi barcha Hikvision turniketlari, terminallari va kontrollerlarini avtomatik topadi
"""
import socket
import struct
import threading
import xmltodict
import time
import requests
from requests.auth import HTTPDigestAuth


SADP_MULTICAST_GROUP = "239.255.255.250"
SADP_PORT = 37020

# Hikvision SADP qidiruv paketi (Discovery probe XML)
SADP_PROBE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Probe>
    <Uuid>00000000-0000-0000-0000-000000000000</Uuid>
    <Types>inquiry</Types>
</Probe>"""


class DeviceDiscovery:
    """Tarmoqdagi Hikvision qurilmalarini aniqlash"""

    @staticmethod
    def search_via_sadp(timeout: float = 3.0) -> list[dict]:
        """SADP Multicast orqali Hikvision qurilmalarini topish"""
        devices = []
        found_ips = set()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.settimeout(timeout)

        try:
            # So'rov yuborish
            sock.sendto(SADP_PROBE_XML.encode("utf-8"), (SADP_MULTICAST_GROUP, SADP_PORT))
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(4096)
                    ip = addr[0]
                    if ip in found_ips:
                        continue

                    # Javobni parse qilish
                    text = data.decode("utf-8", errors="ignore")
                    if "<ProbeMatch>" in text:
                        parsed = xmltodict.parse(text)
                        match = parsed.get("ProbeMatch", {})
                        
                        dev_info = {
                            "ip_address": match.get("IPv4Address", ip),
                            "port": int(match.get("IPv4Port", 80)),
                            "name": match.get("DeviceDescription", "Hikvision Turnstile"),
                            "serial_number": match.get("DeviceSN", ""),
                            "device_type": match.get("DeviceType", "turnstile"),
                            "firmware": match.get("SoftwareVersion", ""),
                            "mac": match.get("MAC", "")
                        }
                        devices.append(dev_info)
                        found_ips.add(ip)
                except socket.timeout:
                    break
                except Exception:
                    continue
        except Exception as e:
            print(f"[Discovery Error] SADP xatosi: {e}")
        finally:
            sock.close()

        return devices

    @staticmethod
    def quick_scan_subnet(subnet_base: str = "192.168.1", start_ip: int = 1, end_ip: int = 254, timeout: float = 0.5) -> list[dict]:
        """
        SADP router orqali bloklangan hollarda (masalan, turli VLAN/subnets)
        Lokal IP diapazonni HTTP portlar orqali tekshirish
        """
        found = []
        threads = []
        lock = threading.Lock()

        def check_ip(ip):
            ports = [80, 8000]
            for port in ports:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(timeout)
                    result = s.connect_ex((ip, port))
                    s.close()
                    if result == 0:
                        # HTTP ISAPI orqali tekshirib ko'ramiz
                        try:
                            r = requests.get(f"http://{ip}:{port}/ISAPI/System/deviceInfo", timeout=1.0)
                            # Hikvision javobi 401 Unauthorized (Digest) yoki 200 qaytaradi va sarlavhada Hikvision bo'ladi
                            is_hik = False
                            auth_header = r.headers.get("Www-Authenticate", "")
                            server_header = r.headers.get("Server", "")
                            if "hikvision" in server_header.lower() or "digest" in auth_header.lower() or "isapi" in r.text.lower():
                                is_hik = True

                            if is_hik:
                                with lock:
                                    found.append({
                                        "ip_address": ip,
                                        "port": port,
                                        "name": f"Hikvision Device ({ip})",
                                        "serial_number": "",
                                        "device_type": "turnstile"
                                    })
                                break
                        except Exception:
                            pass
                except Exception:
                    pass

        # 254 ta IP ni parallel tekshirish
        for i in range(start_ip, end_ip + 1):
            ip = f"{subnet_base}.{i}"
            t = threading.Thread(target=check_ip, args=(ip,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=2.0)

        return found

    @staticmethod
    def discover_all_devices() -> list[dict]:
        """Avval SADP bilan qidiradi, agar topilmasa lokal subnetni tekshiradi"""
        devices = DeviceDiscovery.search_via_sadp(timeout=2.5)
        if devices:
            return devices

        # O'zimizning IP manzilimizni aniqlash
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            my_ip = s.getsockname()[0]
            s.close()
            parts = my_ip.split(".")
            subnet = f"{parts[0]}.{parts[1]}.{parts[2]}"
            devices = DeviceDiscovery.quick_scan_subnet(subnet_base=subnet, start_ip=1, end_ip=254)
        except Exception:
            devices = []

        return devices
