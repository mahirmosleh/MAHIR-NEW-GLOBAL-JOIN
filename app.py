#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MAHIR SQUAD BOT — Join→Msg→Exit→Ghost (normal + recruit + group mode)
import subprocess, sys, importlib, os, ssl, json, time, random, asyncio, threading, gc, re, struct, base64, socket
from collections import deque
from datetime import datetime
import gzip, http.client, uuid, requests, urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import aiohttp, jwt
from rich.console import Console
from rich.panel import Panel
from cfonts import render
from protobuf_decoder.protobuf_decoder import Parser

from xC4 import (
    create_auth_token_chat, create_auth_token_online,
    yasser_Chat, Msg_Packet, yasser_quitcaht,
    Join_Sq, Join_By_RecruitCode, Join_By_RecruitCode_Alt,
    Join_Group_Packet,
    Ghost_Final_Packet, ExiT, GLobaL,
    send_craftland_share_sync, DeCode_PackEt, ArA_CoLor,
    # 🆕 NEW — auto_s2_invite + animation/bundle
    auto_s2_invite_async,
    mahir_animation_packet_async,
    Mahir_bundle_packet_async,
    Mahir_bundle_packet_2_async,
    ANIMATION_POOL,
    AUTO_BUNDLE_POOL,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
console = Console()

# ========== LOG BUFFER ==========
log_buffer = deque(maxlen=500)
log_lock = threading.Lock()
_orig_console_print = console.print

def _patched_console_print(*args, **kwargs):
    try: _orig_console_print(*args, **kwargs)
    except Exception: pass
    try:
        text = " ".join(str(a) for a in args)
        text = re.sub(r'\[/?[a-zA-Z0-9_#= ]+\]', '', text)
        ts = datetime.now().strftime("%H:%M:%S")
        with log_lock: log_buffer.append(f"[{ts}] {text}")
    except Exception: pass

console.print = _patched_console_print

# ================================================================
# AUTO UPDATE
# ================================================================
try:
    from google_play_scraper import app as _gps_app
    _GPS_AVAILABLE = True
except Exception:
    _GPS_AVAILABLE = False

DYNAMIC_SERVER_URL = CURRENT_OB = FREEFIRE_VERSION_NAME = STORE_VERSION = login_url = ob = version = ""

def AuToUpDaTE(max_retries=6, retry_delay=5):
    if not _GPS_AVAILABLE:
        console.print("[bold red]❌ google-play-scraper missing[/bold red]"); sys.exit(1)
    for attempt in range(1, max_retries + 1):
        try:
            data = _gps_app('com.dts.freefireth', lang="fr", country='CA')
            store_version = data.get("version")
            if not store_version: raise RuntimeError("Empty store version")
            api_url = f"https://version.ggwhitehawk.com/live/ver.php?version={store_version}&lang=fr&device=android&channel=android"
            r = requests.get(api_url, timeout=20)
            if r.status_code != 200: raise RuntimeError(f"HTTP {r.status_code}")
            j = r.json()
            su, obv, rp = j.get('server_url'), j.get('latest_release_version'), j.get('remote_version')
            if not all([su, obv, rp]): raise RuntimeError("Missing fields")
            return str(su).strip(), str(obv).strip(), str(rp).strip(), str(store_version).strip()
        except Exception as e:
            console.print(f"[yellow]⚠ Attempt {attempt}: {e}[/yellow]")
            if attempt < max_retries: time.sleep(retry_delay)
            else: sys.exit(1)

_tmp = AuToUpDaTE()
DYNAMIC_SERVER_URL    = _tmp[0].rstrip('/')
CURRENT_OB            = _tmp[1]
FREEFIRE_VERSION_NAME = _tmp[2]
STORE_VERSION         = _tmp[3]
login_url = DYNAMIC_SERVER_URL
ob = CURRENT_OB
version = FREEFIRE_VERSION_NAME

console.print(f"""
[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 LIVE DATA LOADED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 OB         : [white]{CURRENT_OB}[/white]
🛒 Store Ver  : [white]{STORE_VERSION}[/white]
🎮 Remote Ver : [white]{FREEFIRE_VERSION_NAME}[/white]
🌐 Server     : [white]{DYNAMIC_SERVER_URL}[/white]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

TIMEOUT = aiohttp.ClientTimeout(total=30)
WEB_CONFIG_FILE = "web_config.json"
ACCOUNTS_FILE = "accounts.txt"
RECRUIT_FILE = "RECRUITS.txt"

# ========== JWT DECODE ==========
def decode_jwt_noverify(token):
    try:
        parts = token.split(".")
        if len(parts) < 2: return None
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64).decode())
    except Exception: return None

# ========== TRACKING ==========
running_bots = set()
running_bots_lock = threading.Lock()
bot_status = {}
bot_lock = threading.Lock()
online_count = 0
total_accounts = 0
active_accounts = []
active_lock = threading.Lock()

current_mode = "normal"   # "normal" | "recruit" | "group"

# ========== SIGNALS ==========
signal_lock = threading.Lock()
_restart_timestamp = 0
_stop_all_flag = False
_stop_all_lock = threading.Lock()

def trigger_restart_all():
    global _restart_timestamp
    with signal_lock: _restart_timestamp = time.time()

def get_restart_timestamp():
    with signal_lock: return _restart_timestamp

def set_stop_all(v):
    global _stop_all_flag
    with _stop_all_lock: _stop_all_flag = bool(v)

def is_stopped():
    with _stop_all_lock: return _stop_all_flag

# ========== CONFIG ==========
DEFAULT_WELCOME_MSG = (
    "[B][C][00FFFF]╔━━━──[FF0000] • [00FFFF]──━━━╗\n"
    "[FFFFFF]        ⚡ WELCOME  ⚡\n\n"
    "[FF0000]          MAHIR BOT\n\n"
    "[00FF00]  WELCOME TO MAHIR BOT\n\n"
    "[00FFFF]╚━━━──[FF0000] • [00FFFF]──━━━╝\n\n"
    "[FFFF00]★ Power OF MAHIR ★\n\n"
    "[FFFFFF]🎯 STATUS   : [00FF00]ONLINE 24/7\n"
    "[FFFFFF]🤖 SPEED    : [00FF00]ULTRA FAST\n"
    "[FFFFFF]🔒 SECURITY : [00FF00]PROTECTED\n\n"
    "[FF0000]👑 OWNER    : [00FFFF]MAHIR\n"
    "[FFFFFF]📱 TIKTOK   : [FFFF00]MAHIR__222\n"
    "[FFFFFF]📢 TELEGRAM : [00FFFF]THEMAHIRWORLD\n"
)

web_config = {
    "ghost_name": "[C][B][FF0000]TIKTOK : [C][B][FFFFFF]MAHIR__222",
    "welcome_msg": DEFAULT_WELCOME_MSG,
    "join_delay_sec": 0.1,
    "wait_before_exit_sec": 0.5,      # ⬅️ 0.5 → 20.0  (৫ সেকেন্ডে ৪ বার animation)
    "skip_level_max": 20,              # ⬅️ 2 → 20  (level 1-20 skip)
    "send_craftland": True,
}
web_config_lock = threading.Lock()

def load_web_config():
    try:
        saved = {}
        if os.path.exists(WEB_CONFIG_FILE):
            with open(WEB_CONFIG_FILE, "r", encoding="utf-8") as f: saved = json.load(f)
        with web_config_lock:
            if isinstance(saved.get("ghost_name"), str) and saved["ghost_name"]:
                web_config["ghost_name"] = saved["ghost_name"]
            if isinstance(saved.get("welcome_msg"), str) and saved["welcome_msg"]:
                web_config["welcome_msg"] = saved["welcome_msg"]
            for k, (lo, hi) in {"join_delay_sec":(0.1,30), "wait_before_exit_sec":(0.3,30)}.items():
                v = saved.get(k)
                if isinstance(v, (int, float)) and lo <= float(v) <= hi:
                    web_config[k] = float(v)
            sl = saved.get("skip_level_max")
            if isinstance(sl, int) and 0 <= sl <= 100: web_config["skip_level_max"] = sl
            if isinstance(saved.get("send_craftland"), bool):
                web_config["send_craftland"] = saved["send_craftland"]
        console.print("[bold green]✅ Config Loaded[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Config Load Error: {e}[/bold red]")

def save_web_config():
    try:
        with web_config_lock:
            data = {k: web_config[k] for k in [
                "ghost_name","welcome_msg","join_delay_sec",
                "wait_before_exit_sec","skip_level_max","send_craftland",
            ]}
        with open(WEB_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        console.print(f"[bold red]Save Error: {e}[/bold red]"); return False

# ========== ACCOUNTS ==========
def load_accounts(file_path=ACCOUNTS_FILE):
    try:
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f: f.write("")
            return {}
        with open(file_path, "r", encoding="utf-8") as f: lines = f.readlines()
        accounts = {}
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"): continue
            sep = ":" if ":" in line else ("|" if "|" in line else None)
            if sep is None: continue
            parts = line.split(sep, 1)
            if len(parts) != 2: continue
            uid, pwd = parts[0].strip(), parts[1].strip()
            if uid.isdigit() and pwd: accounts[uid] = pwd
        return accounts
    except Exception: return {}

def save_accounts_raw(text, file_path=ACCOUNTS_FILE):
    try:
        with open(file_path, "w", encoding="utf-8") as f: f.write(text)
        return True
    except Exception: return False

def save_accounts(accs, file_path=ACCOUNTS_FILE):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            for uid, pwd in accs.items(): f.write(f"{uid}:{pwd}\n")
        return True
    except Exception: return False

# ========== RECRUITS (UID-only + uid:code) ==========
def load_recruits(file_path=RECRUIT_FILE):
    """
    RECRUITS.txt ফরম্যাট:
      owner_uid:recruit_code   → Join_By_RecruitCode  (recruit mode)
      owner_uid                → Join_Group_Packet    (group join mode, UID only)
    """
    recruits = []
    try:
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"): continue

                if ":" in line or "|" in line:
                    sep = ":" if ":" in line else "|"
                    parts = line.split(sep, 1)
                    if len(parts) != 2: continue
                    owner_uid, rcode = parts[0].strip(), parts[1].strip()
                    if owner_uid.isdigit() and rcode:
                        recruits.append((owner_uid, rcode))
                elif line.isdigit():
                    recruits.append((line, ""))   # group join mode
    except Exception as e:
        console.print(f"[red]Recruit load error: {e}[/red]")
    return recruits

def save_recruits_raw(text, file_path=RECRUIT_FILE):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        return True
    except Exception as e:
        console.print(f"[red]Recruit save error: {e}[/red]")
        return False

# ========== HELPERS ==========
def safe_get_data(f):
    if f is None: return None
    if isinstance(f, dict): return f.get("data")
    return f

def safe_get_int(f, default=None):
    v = safe_get_data(f)
    if v is None: return default
    if isinstance(v, bool): return int(v)
    if isinstance(v, int): return v
    if isinstance(v, (str, bytes, bytearray)):
        try: return int(v)
        except: return default
    return default

def safe_get_str(f, default=""):
    v = safe_get_data(f)
    if v is None: return default
    if isinstance(v, str): return v
    if isinstance(v, (bytes, bytearray)):
        try: return v.decode('utf-8', errors='ignore')
        except: return default
    return str(v)

def read_varint(data, pos):
    result = shift = 0
    while pos < len(data):
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80): break
        shift += 7
    return result, pos

def parse_pb(data):
    fields = {}; pos = 0; n = len(data)
    while pos < n:
        try: key, pos = read_varint(data, pos)
        except: break
        fn = key >> 3; wt = key & 0x07
        try:
            if wt == 0: val, pos = read_varint(data, pos)
            elif wt == 2:
                ln, pos = read_varint(data, pos); val = data[pos:pos + ln]; pos += ln
            elif wt == 5: val = data[pos:pos + 4]; pos += 4
            elif wt == 1: val = data[pos:pos + 8]; pos += 8
            else: break
        except: break
        fields.setdefault(fn, []).append(val)
    return fields

def extract_player_name(login_data_bytes):
    try:
        fields = parse_pb(login_data_bytes)
        for fn in [4, 3, 5, 6]:
            if fn in fields:
                nv = fields[fn][0]
                if isinstance(nv, (bytes, bytearray)):
                    d = nv.decode('utf-8', errors='ignore')
                    if d and len(d) < 60 and not d.startswith("0OuCe") and not d.startswith("eyJ"):
                        return d
    except: pass
    return None

def Uaa():
    versions = ['5.0.1B2','5.1.0P1','5.2.0B1']
    models = ['SM-A125F','Redmi 9A','POCO M3']
    return f"GarenaMSDK/{random.choice(versions)}({random.choice(models)};Android {random.choice(['11','12','13'])};en-US;USA;)"

Hr = {
    'User-Agent': Uaa(), 'Connection': "Keep-Alive", 'Accept-Encoding': "gzip",
    'Content-Type': "application/x-www-form-urlencoded",
    'X-Unity-Version': "2018.4.11f1", 'X-GA': "v1 1", 'ReleaseVersion': ob
}

def update_bot_info(uid, **kwargs):
    with bot_lock:
        if uid not in bot_status:
            bot_status[uid] = {"guest_uid": uid, "account_uid": "Loading...", "status": "🔄 Initializing...",
                               "last_squad_id": "None", "last_active": "N/A", "squad_active": False}
        bot_status[uid].update(kwargs)

def update_active_account(uid, **kwargs):
    with active_lock:
        for acc in active_accounts:
            if acc['uid'] == uid:
                acc.update(kwargs); return
        active_accounts.append({
            'uid': uid, 'bot_uid': kwargs.get('bot_uid', uid),
            'name': kwargs.get('name', 'Unknown'), 'region': kwargs.get('region', 'BD'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'squad_id': kwargs.get('squad_id', 'Joining...'),
            'squad_members': kwargs.get('squad_members', '0/0')
        })

def remove_active_account(uid):
    global online_count
    with active_lock:
        active_accounts[:] = [a for a in active_accounts if a['uid'] != uid]
        if online_count > 0: online_count -= 1

# ================================================================
# AUTH HELPERS
# ================================================================
async def GeNeRaTeAccAccess(uid, password):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {"Host":"100067.connect.garena.com","User-Agent":Uaa(),
               "Content-Type":"application/x-www-form-urlencoded","Connection":"close"}
    data = {"uid":uid,"password":password,"response_type":"token","client_type":"2",
            "client_secret":"2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3","client_id":"100067"}
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(url, headers=headers, data=data) as resp:
                if resp.status != 200: return None, None
                d = await resp.json()
                return d.get("open_id"), d.get("access_token")
    except: return None, None

def encode_varint(value):
    result = []
    if value < 0: value &= (1 << 64) - 1
    while True:
        byte = value & 0x7F; value >>= 7
        if value: byte |= 0x80
        result.append(byte)
        if not value: break
    return bytes(result)

def create_proto(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, dict):
            nested = create_proto(value)
            packet.extend(encode_varint((field << 3) | 2))
            packet.extend(encode_varint(len(nested))); packet.extend(nested)
        elif isinstance(value, int):
            packet.extend(encode_varint((field << 3) | 0)); packet.extend(encode_varint(value))
        elif isinstance(value, str):
            encoded = value.encode('utf-8')
            packet.extend(encode_varint((field << 3) | 2))
            packet.extend(encode_varint(len(encoded))); packet.extend(encoded)
        elif isinstance(value, bytes):
            packet.extend(encode_varint((field << 3) | 2))
            packet.extend(encode_varint(len(value))); packet.extend(value)
    return bytes(packet)

def encrypt_aes(hex_data: str) -> str:
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv  = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(bytes.fromhex(hex_data), AES.block_size)).hex()

async def EncRypTMajoRLoGin(open_id, access_token, version_):
    fields = {
        3: str(datetime.now())[:-7], 4: "free fire", 5: 1, 7: str(version_),
        8: "Android OS 11 / API-30 (RP1A.200720.011/230921V810)", 9: "Handheld",
        10: "Grameenphone", 11: "WIFI", 12: 1708, 13: 750, 14: "480",
        15: "ARM64 FP ASIMD AES | 2000 | 8", 16: 5767, 17: "Mali-G52 MC2",
        18: "OpenGL ES 3.2 v1.r26p0-01eac0.f143e3f9482527bbad36b3ec27f93e59",
        19: "Google|3f10d414-be33-4ac3-b9fc-fcbf47c183b5", 20: "103.200.36.134",
        21: "en", 22: str(open_id), 23: "4", 24: "Handheld",
        25: "INFINIX MOBILITY LIMITED Infinix X6812", 26: "BD", 29: str(access_token), 30: 1,
        41: "Grameenphone", 42: "WIFI", 57: "7428b253defc164018c604a1ebbfebdf",
        60: 110962, 61: 80611, 62: 1051, 64: 80829, 65: 110962, 66: 80829, 67: 110962, 73: 2,
        74: "/data/app/~~MxBbX9YA6AkFscre_RExgw==/com.dts.freefireth-hLOkTeh1Q46L_oLV4UXQTg==/lib/arm64", 76: 1,
        77: "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~MxBbX9YA6AkFscre_RExgw==/com.dts.freefireth-hLOkTeh1Q46L_oLV4UXQTg==/base.apk",
        78: 3, 79: 2, 81: "64", 83: "2019121229", 85: 3, 86: "OpenGLES2", 87: 4095, 88: 4,
        91: {9: 65}, 92: 10508, 93: "android",
        94: "KqsHT76RdsVKvnpkirzc2FQs3eu0OZChfZxMTZn+Rjv06Ri2qeOQkyPcdk5JceWKmXhOFFUPuNy9S8esTr37yCT5piY32iUcehVw0bL4F4lzAmyD",
        95: 111207, 96: '{"cur_rate":[60,90],"support_etc2":false}', 97: 1, 98: 1, 99: "4", 100: "4",
        102: "B\\FFP[[\tf", 103: 1, 104: 28754, 105: 1,
        106: "https://dl.ak.freefiremobile.com/live/ABHotUpdates/|https://core-ak.freefiremobile.com/live/ABHotUpdates/|a4332cb1c1a84e51dd77441e4856ed5a",
        107: "1.477aa00e98bf924c"
    }
    return bytes.fromhex(encrypt_aes(create_proto(fields).hex()))

async def MajorLogin(payload):
    base = login_url.rstrip("/")
    if not base.startswith(("http://", "https://")): base = "https://" + base
    url = f"{base}/MajorLogin"
    Hr["X-GA-SV"] = str(int(time.time()))
    Hr["ReleaseVersion"] = ob
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False; ssl_context.verify_mode = ssl.CERT_NONE
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=Hr, ssl=ssl_context) as r:
            if r.status != 200: return None
            raw = await r.read()
            return raw[64:] if len(raw) > 64 else raw

async def GetLoginData(base_url, payload, token):
    url = f"{base_url}/GetLoginData"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False; ssl_context.verify_mode = ssl.CERT_NONE
    Hr['Authorization'] = f"Bearer {token}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=Hr, ssl=ssl_context) as r:
            if r.status == 200: return await r.read()
            return None

async def DecRypTMajoRLoGin(MajoRLoGinResPonsE):
    class P:
        def __init__(self, f):
            self.account_uid = int(f.get(1, 0)); self.region = str(f.get(2, ""))
            self.token = str(f.get(8, "")); self.url = str(f.get(10, ""))
            self.timestamp = int(f.get(21, 0))
            rk = f.get(22, b"")
            self.key = bytes.fromhex(rk.replace(" ", "")) if isinstance(rk, str) else bytes(rk)
            riv = f.get(23, b"")
            self.iv = bytes.fromhex(riv.replace(" ", "")) if isinstance(riv, str) else bytes(riv)
    def dv(buf, off):
        res, sh = 0, 0
        while True:
            if off >= len(buf): raise IndexError
            b = buf[off]; off += 1
            res += (b & 0x7F) << sh; sh += 7
            if b < 0x80: break
        return res, off
    def dp(buf):
        off, parts, blen = 0, [], len(buf)
        try:
            while off < blen:
                it, off = dv(buf, off)
                wt, fn = it & 7, it >> 3
                if wt == 0: val, off = dv(buf, off)
                elif wt == 2:
                    length, off = dv(buf, off)
                    if off + length > blen: return None
                    val = buf[off:off+length]; off += length
                elif wt == 5:
                    if off + 4 > blen: return None
                    val = struct.unpack_from("<I", buf, off)[0]; off += 4
                elif wt == 1:
                    if off + 8 > blen: return None
                    val = struct.unpack_from("<Q", buf, off)[0]; off += 8
                else: return None
                parts.append((fn, wt, val))
            return parts
        except: return None
    def td(parts):
        r = {}
        for fn, wt, v in parts:
            if wt == 2:
                try: val = v.decode("utf-8")
                except: val = v
            else: val = v
            r[fn] = val
        return r
    buf = MajoRLoGinResPonsE
    try:
        c = AES.new(b'Yg&tc%DEuh6%Zc^8', AES.MODE_CBC, b'6oyZDr22E3ychjM%')
        buf = unpad(c.decrypt(buf), AES.block_size)
    except: pass
    p = dp(buf)
    if p:
        d = td(p)
        if 1 in d or 8 in d or 10 in d: return P(d)
    for o in range(len(buf)):
        p = dp(buf[o:])
        if p:
            d = td(p)
            if 1 in d or 8 in d or 10 in d: return P(d)
    return P({})

# ================================================================
# SQUAD BOT — Join → Msg → Exit → Ghost
# ================================================================
class SquadBot:
    def __init__(self, uid, password, server='bd', index=0, recruit=None):
        self.uid, self.password, self.server, self.index = uid, password, server, index
        self.recruit = recruit
        self.is_running = True
        self.key = self.iv = self.region = None
        self.chat_writer = self.online_writer = None
        self.chat_reader = self.online_reader = None
        self.bot_uid = None
        self.Nm = "Unknown"
        self.jwt_token = None
        self.chat_auth = None
        self.online_auth = None
        self.chat_ip = self.chat_port = None
        self.online_ip = self.online_port = None
        self.seen_restart_ts = 0
        self.tasks = []
        self._ready_event = None
        update_bot_info(self.uid, status="🔄 Initializing...")

    async def _do_login(self):
        oi, at = await GeNeRaTeAccAccess(self.uid, self.password)
        if not oi: return False
        payload = await EncRypTMajoRLoGin(oi, at, FREEFIRE_VERSION_NAME)
        resp = await MajorLogin(payload)
        if not resp: return False
        try: auth = await DecRypTMajoRLoGin(resp)
        except: return False
        if not getattr(auth, 'token', None) or not getattr(auth, 'url', None): return False

        ld = await GetLoginData(auth.url, payload, auth.token)
        if not ld: return False

        self.key, self.iv = auth.key, auth.iv
        self.region, self.bot_uid = auth.region, auth.account_uid
        self.jwt_token = auth.token

        en = extract_player_name(ld)
        if en and len(en) < 60: self.Nm = en
        else:
            try:
                dj = jwt.decode(auth.token, options={"verify_signature": False})
                fb = dj.get('nickname')
                self.Nm = str(fb) if fb and len(str(fb)) < 30 else f"Player_{str(auth.account_uid)[-4:]}"
            except: self.Nm = f"Player_{str(auth.account_uid)[-4:]}"

        try:
            from Pb2 import PorTs_pb2
            pd = PorTs_pb2.GetLoginData(); pd.ParseFromString(ld)
            oip, opp = pd.Online_IP_Port.split(":")
            cip, cpp = pd.AccountIP_Port.split(":")
            self.online_ip, self.online_port = oip, int(opp)
            self.chat_ip, self.chat_port = cip, int(cpp)
        except Exception as e:
            console.print(f"[red]❌ [{self.uid}] Parse IP err: {e}[/red]")
            return False

        self.chat_auth = create_auth_token_chat(auth.account_uid, auth.token, auth.timestamp, auth.key, auth.iv)
        self.online_auth = create_auth_token_online(auth.account_uid, auth.token, auth.timestamp, auth.key, auth.iv)
        if not self.chat_auth or not self.online_auth: return False

        update_bot_info(self.uid, status="✅ Logged In", account_uid=str(auth.account_uid))
        console.print(f"[green]✔ [{self.uid}] Login OK: {self.Nm} | {self.region}[/green]")
        return True

    async def keep_online_forever(self):
        global online_count
        while self.is_running:
            if is_stopped():
                console.print(f"[red]🛑 [{self.uid}] Stopped[/red]"); break
            try:
                self.seen_restart_ts = get_restart_timestamp()

                if not await self._do_login():
                    update_bot_info(self.uid, status="❌ Login Failed")
                    await asyncio.sleep(10); continue

                with active_lock:
                    if not any(a['uid'] == self.uid for a in active_accounts):
                        online_count += 1
                        active_accounts.append({
                            'uid': self.uid, 'bot_uid': str(self.bot_uid),
                            'name': self.Nm, 'region': self.region or 'BD',
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'squad_id': 'Joining...', 'squad_members': '0/0'
                        })

                self._ready_event = asyncio.Event()
                t_chat   = asyncio.create_task(self.tcp_chat())
                t_online = asyncio.create_task(self.tcp_online())
                self.tasks = [t_chat, t_online]

                try:
                    await asyncio.gather(t_chat, t_online, return_exceptions=True)
                finally:
                    for t in self.tasks:
                        if not t.done(): t.cancel()

            except Exception as e:
                if not is_stopped():
                    console.print(f"[red]❌ [{self.uid}] Err: {e}[/red]")
                update_bot_info(self.uid, status="❌ Error")

            remove_active_account(self.uid)

            if is_stopped():
                break
            if get_restart_timestamp() > self.seen_restart_ts:
                console.print(f"[green]♻️ [{self.uid}] Reconnecting...[/green]"); continue
            await asyncio.sleep(8)

    async def tcp_chat(self):
        while self.is_running:
            if is_stopped(): break
            try:
                reader, writer = await asyncio.open_connection(self.chat_ip, self.chat_port)
                writer.write(bytes.fromhex(self.chat_auth)); await writer.drain()
                self.chat_reader, self.chat_writer = reader, writer
                if self._ready_event and not self._ready_event.is_set():
                    self._ready_event.set()
                console.print(f"[cyan]ℹ [{self.uid}] CHAT Connected ✅[/cyan]")
                while self.is_running and not is_stopped():
                    try:
                        data = await asyncio.wait_for(reader.read(4096), timeout=5.0)
                        if not data: break
                    except asyncio.TimeoutError: continue
                    except Exception: break
            except Exception as e:
                if not is_stopped():
                    console.print(f"[yellow]⚠ [{self.uid}] chat err: {e}[/yellow]")
            if is_stopped(): break
            await asyncio.sleep(5)

    async def tcp_online(self):
        if self._ready_event: await self._ready_event.wait()
        await asyncio.sleep(0.5)

        while self.is_running:
            if is_stopped(): break
            try:
                reader, writer = await asyncio.open_connection(self.online_ip, self.online_port)
                writer.write(bytes.fromhex(self.online_auth)); await writer.drain()
                self.online_reader, self.online_writer = reader, writer
                update_bot_info(self.uid, status="✅ Online")
                console.print(f"[cyan]ℹ [{self.uid}] ONLINE Connected ✅[/cyan]")

                await self._send_craftland()

                # ── JOIN: recruit-code / group-uid / random ──
                if self.recruit:
                    owner_uid, rcode = self.recruit
                    if rcode:
                        join_pkt = await Join_By_RecruitCode(
                            owner_uid, rcode, self.key, self.iv, self.region or 'bd'
                        )
                        console.print(
                            f"[bold magenta]🎯 [{self.uid}] RecruitCode → "
                            f"{owner_uid} (code: {str(rcode)[:22]}...)[/bold magenta]"
                        )
                    else:
                        join_pkt = await Join_Group_Packet(owner_uid, self.key, self.iv)
                        console.print(
                            f"[bold yellow]👥 [{self.uid}] Group-Join UID → {owner_uid}[/bold yellow]"
                        )
                else:
                    join_pkt = await Join_Sq(self.key, self.iv)
                    console.print(f"[bold cyan]📤 [{self.uid}] Join_Sq sent[/bold cyan]")

                writer.write(join_pkt); await writer.drain()

                detected = await self._wait_for_target()
                if detected:
                    try: writer.close()
                    except: pass
                    continue

            except Exception as e:
                if not is_stopped():
                    console.print(f"[yellow]⚠ [{self.uid}] online err: {e}[/yellow]")
            if is_stopped(): break
            await asyncio.sleep(3)

    async def _send_craftland(self):
        try:
            with web_config_lock: enabled = web_config.get("send_craftland", True)
            if not enabled: return
            maps = ["#FREEFIRE5047CD63A7E2810EF344C6F0A880B17AK200",
                    "#FREEFIREA79043F8AFF0F0D39468FA40C40E21A4K200",
                    "#FREEFIREF63E5AB9D1C9BECFEF06BBF1AD75D3E1K200"]
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, send_craftland_share_sync,
                                        None, self.bot_uid, 0, 1, random.choice(maps), self.key, self.iv)
        except Exception:
            pass

    async def _wait_for_target(self, timeout_sec=60):
        start = time.time()
        while self.is_running and not is_stopped():
            if time.time() - start > timeout_sec:
                return False
            try:
                data = await asyncio.wait_for(self.online_reader.read(8192), timeout=2.0)
                if not data: return False
                dh = data.hex()
                if dh.startswith("0500") and len(dh) > 100:
                    try:
                        js = DeCode_PackEt(dh[10:])
                        if not js: continue
                        pj = json.loads(js)

                        # 🔒 Safe dict helpers
                        def _sd(d, k):
                            if not isinstance(d, dict): return {}
                            v = d.get(k, {})
                            return v if isinstance(v, dict) else {}

                        squad_data = _sd(_sd(pj, '5'), 'data')
                        if not isinstance(squad_data, dict) or not squad_data:
                            continue
                        player_data = _sd(_sd(squad_data, '6'), 'data')

                        target_uid    = (safe_get_int(squad_data.get('1')) or
                                         safe_get_int(player_data.get('1')))
                        target_name   = (safe_get_str(player_data.get('2')) or "MAHIR")
                        target_region = (safe_get_str(player_data.get('3')) or self.region)
                        target_level  = safe_get_int(player_data.get('5'), 0)
                        squad_code    = safe_get_str(squad_data.get('31'))
                        chat_code     = safe_get_str(squad_data.get('17'))

                        if not (target_uid and squad_code and chat_code):
                            continue

                        with web_config_lock:
                            skip_level_max = web_config.get("skip_level_max", 2)
                        if target_level and target_level <= skip_level_max:
                            continue

                        with bot_lock:
                            console.print(f"[bold green]═══════════════════════════════════[/bold green]")
                            console.print(f"[bold yellow]🤖 BOT UID  :[/bold yellow] {self.bot_uid}")
                            console.print(f"[bold cyan]👤 NAME     :[/bold cyan] {target_name}")
                            console.print(f"[bold white]🆔 OWNER UID:[/bold white] {target_uid}")
                            console.print(f"[bold magenta]🌐 SERVER   :[/bold magenta] {target_region}")
                            console.print(f"[bold yellow]⭐ LEVEL    :[/bold yellow] {target_level}")
                            console.print(f"[bold green]═══════════════════════════════════[/bold green]")

                        update_active_account(self.uid, squad_id=str(target_uid), squad_members="detected")

                        ok = await self._handle_target(
                            target_uid, target_name, target_region,
                            squad_code, chat_code
                        )
                        if ok: return True
                    except Exception as e:
                        console.print(f"[dim][{self.uid}] parse err: {e}[/dim]")
            except asyncio.TimeoutError:
                continue
            except Exception:
                return False
        return False

    async def _handle_target(self, target_uid, target_name, target_region, squad_code, chat_code):
        """
        Flow:
          STEP 0   : 🎴 V-Badge InviteCard → target_uid (OWNER UID) — 2 বার
          STEP 1   : 💬 Welcome message
          STEP 1.5 : 🎬 Animation/Bundle — প্রতি 5s background loop
          STEP 2   : ⏳ wait_before_exit_sec
          STEP 3   : 🚪 Exit
          STEP 4   : 👻 Ghost
        """
        anim_stop_event = asyncio.Event()
        anim_task = None

        try:
            # ── Load config ──
            with web_config_lock:
                wmsg        = web_config.get("welcome_msg", DEFAULT_WELCOME_MSG)
                wait_exit   = float(web_config.get("wait_before_exit_sec", 0.5))
                ghost_name  = web_config.get("ghost_name",
                                             "[C][B][FF0000]TIKTOK : [C][B][FFFFFF]MAHIR__222")

            msg        = wmsg.replace("{user_name}", str(target_name))
            region_use = target_region or self.region or "bd"

            # ═══════════════════════════════════════════════════════════
            # STEP 0 : 🎴 V-Badge Invite Card → OWNER UID (target_uid)
            # ═══════════════════════════════════════════════════════════
            try:
                console.print(
                    f"[bold cyan]📨 [{self.uid}] Sending InviteCard → OWNER {target_uid}...[/bold cyan]"
                )

                ok = await auto_s2_invite_async(
                    target_uid, self.key, self.iv, region_use, self.online_writer
                )
                if ok:
                    console.print(
                        f"[bold green]🎴 [{self.uid}] InviteCard → {target_uid} ✔[/bold green]"
                    )
                else:
                    console.print(
                        f"[yellow]⚠ [{self.uid}] InviteCard returned False[/yellow]"
                    )

                # 🆕 Second send — target নিশ্চিত দেখবে
                await asyncio.sleep(0.3)
                ok2 = await auto_s2_invite_async(
                    target_uid, self.key, self.iv, region_use, self.online_writer
                )
                if ok2:
                    console.print(
                        f"[bold green]🎴 [{self.uid}] InviteCard (2nd) → {target_uid} ✔[/bold green]"
                    )
            except Exception as e:
                console.print(f"[yellow]⚠ [{self.uid}] InviteCard err: {e}[/yellow]")

            # ═══════════════════════════════════════════════════════════
            # STEP 1 : 💬 Welcome Message (chat server)
            # ═══════════════════════════════════════════════════════════
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                sock.connect((self.chat_ip, self.chat_port))
                sock.send(bytes.fromhex(self.chat_auth))
                await asyncio.sleep(0.05)

                sock.send(await yasser_Chat(target_uid, chat_code, self.key, self.iv))
                await asyncio.sleep(0.05)

                sock.send(await Msg_Packet(msg, target_uid, self.bot_uid, self.key, self.iv))
                await asyncio.sleep(0.05)

                sock.send(await yasser_quitcaht(target_uid, self.key, self.iv))
                await asyncio.sleep(0.05)

                sock.close()
                console.print(f"[green]✔ [{self.uid}] Msg ✔[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠ [{self.uid}] Msg err: {e}[/yellow]")

            # ═══════════════════════════════════════════════════════════
            # STEP 1.5 : 🎬 Animation / Bundle — every 5s (background)
            # ═══════════════════════════════════════════════════════════
            anim_counter = {"n": 0}

            async def _anim_worker():
                while not anim_stop_event.is_set():
                    try:
                        anim_counter["n"] += 1
                        n = anim_counter["n"]

                        if random.random() < 0.5:
                            aid = random.choice(ANIMATION_POOL)
                            ap = await mahir_animation_packet_async(aid, self.key, self.iv)
                            if ap and self.online_writer and not self.online_writer.is_closing():
                                self.online_writer.write(ap)
                                await self.online_writer.drain()
                                console.print(
                                    f"[cyan]🎬 [{self.uid}] #{n} Anim {aid} → {target_uid}[/cyan]"
                                )
                        else:
                            bid = random.choice(AUTO_BUNDLE_POOL)
                            bp = await Mahir_bundle_packet_async(
                                bid, self.key, self.iv, region_use
                            )
                            if bp and self.online_writer and not self.online_writer.is_closing():
                                self.online_writer.write(bp)
                                await self.online_writer.drain()
                                console.print(
                                    f"[cyan]🎬 [{self.uid}] #{n} Bundle {bid} → {target_uid}[/cyan]"
                                )
                    except Exception as e:
                        console.print(f"[dim]anim err: {e}[/dim]")

                    # wait 5s (or exit instantly if stop event set)
                    try:
                        await asyncio.wait_for(anim_stop_event.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        pass

            anim_task = asyncio.create_task(_anim_worker())
            console.print(
                f"[magenta]🎬 [{self.uid}] Animation loop started (5s interval)[/magenta]"
            )

            # ═══════════════════════════════════════════════════════════
            # STEP 2 : ⏳ Wait before exit
            # ═══════════════════════════════════════════════════════════
            await asyncio.sleep(wait_exit)

            # ═══════════════════════════════════════════════════════════
            # STEP 3 : 🚪 Exit (online server)
            # ═══════════════════════════════════════════════════════════
            try:
                self.online_writer.write(await ExiT(self.key, self.iv))
                await self.online_writer.drain()
                console.print(f"[yellow]🚪 [{self.uid}] Exit ✔[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠ [{self.uid}] Exit err: {e}[/yellow]")

            # ── Stop animation worker ──
            anim_stop_event.set()
            if anim_task is not None:
                try:
                    await asyncio.wait_for(anim_task, timeout=1.0)
                except Exception:
                    pass

            await asyncio.sleep(0.05)

            # ═══════════════════════════════════════════════════════════
            # STEP 4 : 👻 Ghost
            # ═══════════════════════════════════════════════════════════
            try:
                ghost_pkt = await Ghost_Final_Packet(
                    target_uid, ghost_name, squad_code, self.key, self.iv
                )
                self.online_writer.write(ghost_pkt)
                await self.online_writer.drain()
                console.print(f"[bold magenta]👻 [{self.uid}] Ghost ✔[/bold magenta]")
            except Exception as e:
                console.print(f"[yellow]⚠ [{self.uid}] Ghost err: {e}[/yellow]")

            update_bot_info(self.uid, status="✅ Cycle Done")
            console.print(
                f"[bold green]═══════════════════════════════════[/bold green]\n"
                f"[bold green]✅ [{self.uid}] Cycle Complete — {target_uid}[/bold green]\n"
                f"[bold green]═══════════════════════════════════[/bold green]"
            )
            return True

        except Exception as e:
            console.print(f"[red]❌ [{self.uid}] Target handler err: {e}[/red]")
            return False

        finally:
            # ✅ Safety: animation worker always stops
            if not anim_stop_event.is_set():
                anim_stop_event.set()
            if anim_task is not None and not anim_task.done():
                try:
                    anim_task.cancel()
                except Exception:
                    pass

# ================================================================
# BATCH LOADER
# ================================================================
async def batch_account_loader():
    global total_accounts, current_mode
    active_bots, bot_tasks, last_passwords = {}, {}, {}
    console.print("[bold cyan]🚀 Batch Loader started...[/bold cyan]")

    while True:
        try:
            accounts = load_accounts()
            recruits = load_recruits()
            total_accounts = len(accounts)
            stopped = is_stopped()

            if not recruits:
                desired_mode = "normal"
            else:
                has_code = any(rc for _, rc in recruits)
                has_uid  = any(not rc for _, rc in recruits)
                if has_code and has_uid: desired_mode = "mixed"
                elif has_code:           desired_mode = "recruit"
                else:                    desired_mode = "group"

            if desired_mode != current_mode:
                console.print(f"[yellow]🔄 Mode change: {current_mode} → {desired_mode}[/yellow]")
                for k in list(bot_tasks.keys()):
                    try:
                        if k in active_bots: active_bots[k].is_running = False
                        if not bot_tasks[k].done(): bot_tasks[k].cancel()
                    except: pass
                bot_tasks.clear(); active_bots.clear()
                with running_bots_lock: running_bots.clear()
                current_mode = desired_mode

            if desired_mode == "normal":
                for uid, pwd in accounts.items():
                    if uid in last_passwords and last_passwords[uid] != pwd:
                        if uid in active_bots:
                            try: active_bots[uid].is_running = False
                            except: pass
                            del active_bots[uid]
                        if uid in bot_tasks:
                            if not bot_tasks[uid].done(): bot_tasks[uid].cancel()
                            del bot_tasks[uid]
                    last_passwords[uid] = pwd

            if stopped:
                for k in list(bot_tasks.keys()):
                    try:
                        if k in active_bots: active_bots[k].is_running = False
                        if not bot_tasks[k].done(): bot_tasks[k].cancel()
                    except: pass
                    uid_part = k.split(":")[0] if ":" in k else k
                    remove_active_account(uid_part)
                    with running_bots_lock: running_bots.discard(k)
                bot_tasks.clear(); active_bots.clear()

            elif desired_mode in ("recruit", "group", "mixed"):
                for i, (uid, pwd) in enumerate(accounts.items()):
                    owner_uid, rcode = recruits[i % len(recruits)]
                    task_key = f"{uid}:{owner_uid}"
                    with running_bots_lock: running_bots.add(task_key)
                    if task_key in bot_tasks and not bot_tasks[task_key].done(): continue
                    if task_key in bot_tasks: del bot_tasks[task_key]
                    bot = SquadBot(uid=uid, password=pwd, server='bd',
                                   index=i + 1, recruit=(owner_uid, rcode))
                    active_bots[task_key] = bot
                    bot_tasks[task_key] = asyncio.create_task(bot.keep_online_forever())
                    await asyncio.sleep(0.05)

            else:
                for uid, pwd in accounts.items():
                    with running_bots_lock: running_bots.add(uid)
                    if uid in bot_tasks and not bot_tasks[uid].done(): continue
                    if uid in bot_tasks: del bot_tasks[uid]
                    bot = SquadBot(uid=uid, password=pwd, server='bd', index=len(bot_tasks) + 1)
                    active_bots[uid] = bot
                    bot_tasks[uid] = asyncio.create_task(bot.keep_online_forever())
                    await asyncio.sleep(0.05)

        except Exception as e:
            console.print(f"[red]Loader: {e}[/red]")
        await asyncio.sleep(2)

# ================================================================
# WEB SERVER
# ================================================================
class BotHandler(BaseHTTPRequestHandler):
    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _text_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(data if isinstance(data, bytes) else data.encode('utf-8'))

    def _read_body(self):
        try:
            cl = int(self.headers.get('Content-Length', 0))
            return self.rfile.read(cl).decode('utf-8')
        except: return ""

    def _esc(self, s):
        return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with active_lock:
                cur_online, cur_total, cur_threads = online_count, total_accounts, len(active_accounts)
            with web_config_lock:
                ghost_name = web_config.get("ghost_name", "")
                welcome_msg = web_config.get("welcome_msg", DEFAULT_WELCOME_MSG)
                join_delay = web_config.get("join_delay_sec", 0.5)
                wait_exit = web_config.get("wait_before_exit_sec", 0.5)
                skip_level = web_config.get("skip_level_max", 2)
                craftland = web_config.get("send_craftland", True)
            ghost_esc = self._esc(ghost_name)
            welcome_esc = self._esc(welcome_msg)
            stopped_now = is_stopped()

            try:
                with open(RECRUIT_FILE, "r", encoding="utf-8") as f:
                    recruit_content = f.read()
            except: recruit_content = ""
            recruit_esc = self._esc(recruit_content)
            recruit_count = len(load_recruits())

            html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAHIR · Control Center</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#05070F;--panel:#0F1628;--line:#1E2A44;--cyan:#22D3EE;--violet:#A855F7;--magenta:#EC4899;--green:#10B981;--amber:#F59E0B;--red:#EF4444;--txt:#F8FAFC;--txt2:#94A3B8;--txt3:#64748B;--r:16px}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Rajdhani',sans-serif;background:var(--bg);color:var(--txt);min-height:100vh}}
body::before{{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background:radial-gradient(1000px 700px at -5% -10%,rgba(34,211,238,.10),transparent 55%),radial-gradient(1000px 700px at 105% 110%,rgba(168,85,247,.10),transparent 55%)}}
.layout{{display:flex;min-height:100vh;position:relative;z-index:1}}
.sidebar{{width:240px;background:linear-gradient(180deg,rgba(10,15,30,.98),rgba(5,7,15,.98));border-right:1px solid var(--line);padding:22px 14px;position:sticky;top:0;height:100vh;overflow-y:auto}}
.sb-logo{{display:flex;gap:12px;align-items:center;padding:8px 8px 20px;border-bottom:1px solid var(--line);margin-bottom:18px}}
.sb-mark{{width:44px;height:44px;border-radius:12px;display:grid;place-items:center;font-size:1.4em;background:linear-gradient(135deg,var(--cyan),var(--violet) 55%,var(--magenta));box-shadow:0 0 24px rgba(34,211,238,.5)}}
.sb-logo h2{{font-family:'Orbitron',sans-serif;font-size:1em;font-weight:900;letter-spacing:1.6px;background:linear-gradient(135deg,#fff,var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sb-logo p{{font-size:.6em;color:var(--txt3);letter-spacing:2px;text-transform:uppercase}}
.sb-link{{display:flex;align-items:center;gap:12px;padding:11px 14px;border-radius:10px;color:var(--txt2);text-decoration:none;font-weight:600;font-size:.9em;cursor:pointer;transition:all .2s;margin-bottom:4px}}
.sb-link:hover{{background:rgba(34,211,238,.07);color:var(--txt)}}
.sb-link.active{{background:linear-gradient(90deg,rgba(34,211,238,.18),rgba(168,85,247,.12));color:var(--cyan);box-shadow:inset 3px 0 0 var(--cyan)}}
.sb-link .ico{{font-size:1.1em;width:22px;text-align:center}}
.main{{flex:1;padding:20px 24px 40px;min-width:0}}
.topbar{{position:relative;display:flex;align-items:center;justify-content:space-between;gap:14px;padding:18px 22px;background:linear-gradient(135deg,rgba(15,22,40,.92),rgba(19,27,51,.75));backdrop-filter:blur(20px);border:1px solid var(--line);border-radius:var(--r);margin-bottom:18px;flex-wrap:wrap;overflow:hidden}}
.topbar::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--cyan),var(--violet),var(--magenta),transparent);background-size:200% 100%;animation:slide 5s linear infinite}}
@keyframes slide{{to{{background-position:200% 0}}}}
.tb-title{{font-family:'Orbitron',sans-serif;font-size:1.05em;font-weight:900;letter-spacing:2px;background:linear-gradient(135deg,#fff,var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.pill{{display:inline-flex;align-items:center;gap:6px;padding:6px 13px;border-radius:999px;font-size:.68em;font-weight:700;letter-spacing:1.3px;text-transform:uppercase;border:1px solid rgba(34,211,238,.35);background:rgba(34,211,238,.06);color:var(--cyan)}}
.pill.green{{background:rgba(16,185,129,.08);color:var(--green);border-color:rgba(16,185,129,.35)}}
.pill.red{{background:rgba(239,68,68,.08);color:var(--red);border-color:rgba(239,68,68,.35)}}
.pill.violet{{background:rgba(168,85,247,.08);color:var(--violet);border-color:rgba(168,85,247,.35)}}
.dot{{width:7px;height:7px;border-radius:50%;background:currentColor;box-shadow:0 0 8px currentColor;animation:blink 1.4s infinite}}
@keyframes blink{{50%{{opacity:.4;transform:scale(.85)}}}}
.status-banner{{position:relative;overflow:hidden;display:flex;align-items:center;justify-content:center;gap:14px;padding:16px 22px;border-radius:var(--r);margin-bottom:20px;font-family:'Orbitron',sans-serif;font-weight:900;letter-spacing:3px;font-size:.95em;color:#fff;border:1px solid rgba(255,255,255,.15);text-transform:uppercase;transition:background .4s}}
.status-banner::after{{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.2),transparent);animation:swipe 3.5s linear infinite;pointer-events:none}}
@keyframes swipe{{0%{{transform:translateX(-100%)}}100%{{transform:translateX(100%)}}}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin-bottom:20px}}
.stat-card{{position:relative;overflow:hidden;background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:20px;display:flex;align-items:center;gap:14px;transition:all .3s}}
.stat-card:hover{{transform:translateY(-3px);border-color:rgba(56,189,248,.35);box-shadow:0 14px 42px rgba(0,0,0,.4)}}
.stat-ico{{width:50px;height:50px;flex-shrink:0;border-radius:13px;display:grid;place-items:center;font-size:1.4em;background:rgba(255,255,255,.04);border:1px solid rgba(56,189,248,.35)}}
.stat-body{{display:flex;flex-direction:column;gap:3px;min-width:0}}
.stat-value{{font-family:'Orbitron',sans-serif;font-size:1.75em;font-weight:900;line-height:1;color:var(--vc,var(--cyan));text-shadow:0 0 22px var(--vc,var(--cyan));word-break:break-all}}
.stat-label{{font-size:.66em;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--txt2)}}
.stat-card.s-green{{--vc:#34D399}}
.stat-card.s-blue{{--vc:#60A5FA}}
.stat-card.s-violet{{--vc:#C084FC}}
.stat-card.s-cyan{{--vc:#22D3EE}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:22px;margin-bottom:18px}}
.panel-head{{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;padding-bottom:14px;margin-bottom:18px;border-bottom:1px solid var(--line)}}
.panel-title{{display:flex;align-items:center;gap:12px;font-family:'Orbitron',sans-serif;font-size:.95em;font-weight:700;letter-spacing:2px;text-transform:uppercase}}
.panel-ico{{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;font-size:1em;background:linear-gradient(135deg,rgba(34,211,238,.18),rgba(168,85,247,.14));border:1px solid rgba(56,189,248,.35)}}
.btn{{position:relative;overflow:hidden;display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 22px;border:1px solid rgba(255,255,255,.12);border-radius:11px;font-family:'Rajdhani',sans-serif;font-size:.88em;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:#fff;cursor:pointer;transition:all .2s;background:linear-gradient(135deg,var(--red),#B91C1C)}}
.btn:hover:not(:disabled){{transform:translateY(-2px);box-shadow:0 12px 30px rgba(0,0,0,.45)}}
.btn:disabled{{opacity:.55;cursor:not-allowed}}
.btn.green{{background:linear-gradient(135deg,var(--green),#047857)}}
.btn.amber{{background:linear-gradient(135deg,var(--amber),#D97706)}}
.btn.pink{{background:linear-gradient(135deg,var(--magenta),#BE185D)}}
.btn.blue{{background:linear-gradient(135deg,#3B82F6,#1D4ED8)}}
.btn.ghost{{background:rgba(255,255,255,.04);border:1px solid rgba(56,189,248,.35);color:var(--txt)}}
.action-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}
.action-tile{{display:flex!important;align-items:center;justify-content:flex-start!important;gap:14px;padding:16px 20px!important;text-transform:none!important;letter-spacing:0!important;min-height:75px;border-radius:13px!important}}
.action-tile .t-ico{{font-size:1.6em;flex-shrink:0}}
.action-tile .t-txt{{display:flex;flex-direction:column;gap:2px;text-align:left;min-width:0}}
.action-tile .t-main{{font-family:'Orbitron',sans-serif;font-size:.9em;font-weight:900;letter-spacing:1.2px;text-transform:uppercase;line-height:1.15}}
.action-tile .t-sub{{font-size:.7em;font-weight:600;opacity:.8}}
.action-tile.stop{{background:linear-gradient(135deg,var(--red),#7F1D1D)!important;animation:pulseRed 2.4s ease-in-out infinite}}
.action-tile.start{{background:linear-gradient(135deg,var(--green),#065F46)!important;animation:pulseGreen 2.4s ease-in-out infinite}}
@keyframes pulseRed{{0%,100%{{box-shadow:0 0 24px rgba(239,68,68,.32)}}50%{{box-shadow:0 0 46px rgba(239,68,68,.7)}}}}
@keyframes pulseGreen{{0%,100%{{box-shadow:0 0 24px rgba(16,185,129,.32)}}50%{{box-shadow:0 0 46px rgba(16,185,129,.7)}}}}
.field{{display:flex;flex-direction:column;gap:8px}}
.field-label{{font-size:.7em;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--txt2)}}
input,textarea{{width:100%;padding:12px 14px;background:rgba(5,7,15,.8);border:1px solid var(--line);border-radius:11px;font-family:'JetBrains Mono',monospace;font-size:.85em;color:var(--cyan);outline:none;transition:all .2s}}
input:focus,textarea:focus{{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(34,211,238,.12)}}
textarea{{line-height:1.7;resize:vertical;font-size:.8em}}
.chips{{display:flex;flex-wrap:wrap;gap:10px}}
.chip{{display:inline-flex;align-items:center;gap:8px;padding:10px 14px;border-radius:11px;border:1px solid var(--line);background:rgba(5,7,15,.6);color:var(--txt2);font-weight:600;font-size:.82em;cursor:pointer;transition:all .22s}}
.chip:hover{{border-color:var(--cyan);color:var(--txt)}}
.chip:has(input:checked){{border-color:var(--cyan);background:linear-gradient(135deg,rgba(34,211,238,.18),rgba(168,85,247,.14));color:var(--txt);box-shadow:0 0 24px rgba(34,211,238,.28)}}
.chip input{{width:14px;height:14px;accent-color:var(--cyan);cursor:pointer}}
.stack{{display:flex;flex-direction:column;gap:16px}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.acc-box{{padding:18px;border-radius:13px;border:1px solid var(--line);background:linear-gradient(135deg,rgba(5,7,15,.5),rgba(15,22,40,.4))}}
.acc-box.cyan{{border-color:rgba(34,211,238,.3)}}
.acc-box.pink{{border-color:rgba(236,72,153,.3)}}
.acc-box.violet{{border-color:rgba(168,85,247,.3)}}
.box-title{{display:flex;align-items:center;gap:10px;font-family:'Orbitron',sans-serif;font-size:.82em;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;color:var(--cyan)}}
.box-title.pink{{color:var(--magenta)}}
.box-title.violet{{color:var(--violet)}}
.row{{display:grid;grid-template-columns:1fr 1fr auto;gap:12px;align-items:end}}
.btn-row{{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}}
.hint{{color:var(--txt3);font-size:.75em;line-height:1.6;font-style:italic;margin-top:6px}}
.hint b{{color:var(--amber);font-style:normal}}
.table-shell{{overflow-x:auto;max-height:460px;overflow-y:auto;border-radius:11px;border:1px solid var(--line);background:rgba(5,7,15,.55)}}
table{{width:100%;border-collapse:collapse;text-align:left}}
th,td{{padding:12px 14px;border-bottom:1px solid var(--line);font-size:.84em;white-space:nowrap}}
th{{position:sticky;top:0;background:linear-gradient(180deg,rgba(19,27,51,.98),rgba(15,22,40,.98));color:var(--cyan);font-family:'Orbitron',sans-serif;font-size:.66em;font-weight:700;letter-spacing:1.6px;text-transform:uppercase}}
tbody tr:hover{{background:rgba(34,211,238,.06)}}
.badge-live{{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:rgba(16,185,129,.16);color:var(--green);font-size:.7em;font-weight:700;letter-spacing:1px;border:1px solid rgba(16,185,129,.35)}}
.badge-live::before{{content:'';width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);animation:blink 1.4s infinite}}
.log-shell{{height:400px;overflow-y:auto;padding:16px;border-radius:11px;border:1px solid var(--line);background:#02040A;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.8;color:#4ADE80}}
.log-shell > div{{padding:3px 10px;border-left:2px solid transparent;transition:all .18s;word-break:break-word}}
.log-shell > div:hover{{background:rgba(34,211,238,.06);border-left-color:var(--cyan)}}
.foot{{text-align:center;padding:22px;color:var(--txt3);font-size:.78em;letter-spacing:1.6px;border-top:1px solid var(--line);margin-top:12px}}
.foot b{{color:var(--cyan)}}
.toast{{visibility:hidden;position:fixed;right:20px;bottom:20px;z-index:9999;min-width:270px;padding:15px 20px;border-radius:11px;color:#fff;font-weight:700;font-size:.92em;background:linear-gradient(135deg,var(--green),#059669);box-shadow:0 14px 42px rgba(0,0,0,.6);border:1px solid rgba(255,255,255,.18);opacity:0;transform:translateY(20px);transition:all .35s}}
.toast.show{{visibility:visible;opacity:1;transform:translateY(0)}}
@media(max-width:900px){{.sidebar{{position:fixed;left:0;top:0;transform:translateX(-100%);z-index:100}}.sidebar.open{{transform:translateX(0)}}.main{{padding:14px}}.row{{grid-template-columns:1fr}}.grid-2{{grid-template-columns:1fr}}.tb-menu{{display:grid!important}}}}
.tb-menu{{display:none;width:38px;height:38px;border-radius:10px;background:rgba(34,211,238,.08);border:1px solid rgba(56,189,248,.35);color:var(--cyan);cursor:pointer;font-size:1.1em}}
.overlay{{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:99;display:none;backdrop-filter:blur(3px)}}
.overlay.show{{display:block}}
</style></head><body>
<div class="overlay" id="overlay" onclick="toggleSidebar()"></div>
<div class="layout">
<aside class="sidebar" id="sidebar">
<div class="sb-logo"><div class="sb-mark">🔥</div><div><h2>MAHIR</h2><p>Join Bot</p></div></div>
<nav class="sb-nav">
<a class="sb-link active" href="#section-dashboard"><span class="ico">⚡</span> Dashboard</a>
<a class="sb-link" href="#section-accounts"><span class="ico">👥</span> Accounts</a>
<a class="sb-link" href="#section-recruits"><span class="ico">🎯</span> Recruits</a>
<a class="sb-link" href="#section-config"><span class="ico">⚙️</span> Config</a>
<a class="sb-link" href="#section-bots"><span class="ico">📋</span> Active Bots</a>
<a class="sb-link" href="#section-logs"><span class="ico">📜</span> Live Logs</a>
</nav>
</aside>
<main class="main">
<header class="topbar">
<button class="tb-menu" onclick="toggleSidebar()">☰</button>
<div class="tb-title">CONTROL CENTER</div>
<div style="display:flex;gap:8px;flex-wrap:wrap">
<span class="pill green"><span class="dot"></span> System Online</span>
<span class="pill violet">📦 {FREEFIRE_VERSION_NAME}</span>
<span class="pill">{CURRENT_OB}</span>
<span class="pill violet" id="mode-pill">Mode: {current_mode}</span>
</div>
</header>
<div class="status-banner" id="status-banner" style="background:{'linear-gradient(135deg,#EF4444,#7F1D1D)' if stopped_now else 'linear-gradient(135deg,#10B981,#065F46)'}">
<span id="banner-text">{'🛑 BOTS STOPPED' if stopped_now else '🟢 BOTS RUNNING'}</span>
</div>
<section id="section-dashboard" class="stats-grid">
<div class="stat-card s-green"><div class="stat-ico">🟢</div><div class="stat-body"><div class="stat-value" id="stat-online">{cur_online}</div><div class="stat-label">Online Bots</div></div></div>
<div class="stat-card s-blue"><div class="stat-ico">📊</div><div class="stat-body"><div class="stat-value" id="stat-total">{cur_total}</div><div class="stat-label">Total Accounts</div></div></div>
<div class="stat-card s-violet"><div class="stat-ico">⚙️</div><div class="stat-body"><div class="stat-value" id="stat-threads">{cur_threads}</div><div class="stat-label">Active Threads</div></div></div>
<div class="stat-card s-cyan"><div class="stat-ico">📦</div><div class="stat-body"><div class="stat-value" id="stat-version" style="font-size:1.1em">{FREEFIRE_VERSION_NAME}</div><div class="stat-label">{CURRENT_OB} · Build</div></div></div>
</section>
<section class="panel">
<div class="panel-head"><div class="panel-title"><div class="panel-ico">⚡</div> Quick Actions</div></div>
<div class="action-grid">
<button class="btn action-tile stop" id="btn-stop-all" onclick="doStopAll()" style="display:{'none' if stopped_now else 'inline-flex'}"><span class="t-ico">🛑</span><span class="t-txt"><span class="t-main">Stop All</span><span class="t-sub">Disconnect every bot</span></span></button>
<button class="btn action-tile start" id="btn-start-all" onclick="doStartAll()" style="display:{'inline-flex' if stopped_now else 'none'}"><span class="t-ico">🚀</span><span class="t-txt"><span class="t-main">Start All</span><span class="t-sub">Resume every account</span></span></button>
<button class="btn action-tile amber" onclick="doAccountRestart()"><span class="t-ico">♻️</span><span class="t-txt"><span class="t-main">Account Restart</span><span class="t-sub">Reconnect all bots</span></span></button>
</div>
</section>
<section class="panel" id="section-accounts">
<div class="panel-head"><div class="panel-title"><div class="panel-ico">👥</div> Account Manager</div><span class="pill" id="acc-count">0 Accounts</span></div>
<div class="stack">
<div class="acc-box cyan"><div class="box-title">➕ Add Single Account</div>
<div class="row"><div class="field"><label class="field-label">UID</label><input type="text" id="new-uid" placeholder="e.g. 1234567890"></div><div class="field"><label class="field-label">Password</label><input type="text" id="new-pwd"></div><button class="btn green" onclick="addSingleAccount()">➕ Add</button></div></div>
<div class="acc-box pink"><div class="box-title pink">📂 Upload TXT</div>
<div class="hint">Format: uid:password প্রতি লাইনে</div>
<div class="row" style="grid-template-columns:1fr auto;margin-top:10px"><input type="file" id="acc-file" accept=".txt"><button class="btn pink" onclick="uploadAccFile()">📤 Upload & Replace</button></div></div>
<div class="acc-box violet"><div class="box-title violet">✏️ Edit / View All</div>
<textarea id="acc-content" style="height:220px;color:#4ADE80;background:#02040A" spellcheck="false"></textarea>
<div class="hint">Format: <b>uid:password</b> প্রতি লাইনে</div>
<div class="btn-row"><button class="btn green" id="acc-save-btn" onclick="saveAllAccounts()">💾 Save</button><button class="btn amber" onclick="reloadAccounts()">🔄 Reload</button><button class="btn blue" onclick="downloadAccounts()">📥 Download</button></div></div>
</div></section>
<section class="panel" id="section-recruits">
<div class="panel-head">
  <div class="panel-title"><div class="panel-ico">🎯</div> Recruit / Group Targets</div>
  <span class="pill violet" id="recruit-count">{recruit_count} Targets</span>
</div>
<div class="acc-box violet">
  <div class="box-title violet">✏️ Edit RECRUITS.txt</div>
  <textarea id="recruit-content" style="height:180px;color:#C084FC;background:#02040A" spellcheck="false" placeholder="owner_uid:recruit_code  বা  owner_uid">{recruit_esc}</textarea>
  <div class="hint">
    প্রতি লাইনে একটি target:<br>
    • <b>owner_uid:recruit_code</b> → <b>Join_By_RecruitCode</b><br>
    • <b>owner_uid</b> (শুধু UID) → <b>Join_Group_Packet</b> (direct group join)<br>
    • ফাইল খালি → <b>Join_Sq</b> (random match)
  </div>
  <div class="btn-row">
    <button class="btn green" id="recruit-save-btn" onclick="saveRecruits()">💾 Save Recruits</button>
    <button class="btn amber" onclick="reloadRecruits()">🔄 Reload</button>
  </div>
</div>
</section>
<section class="panel" id="section-config">
<div class="panel-head"><div class="panel-title"><div class="panel-ico">⚙️</div> Workflow Config</div></div>
<form onsubmit="saveConfig(event)"><div class="stack">
<div class="field"><label class="field-label">👻 Ghost Name</label><input type="text" id="ghost_name" value="{ghost_esc}"></div>
<div class="grid-2">
<div class="field"><label class="field-label">⏱️ Join Delay (sec)</label><input type="number" min="0.1" max="30" step="0.1" id="join_delay_sec" value="{join_delay}"></div>
<div class="field"><label class="field-label">⏱️ Wait Before Exit (sec)</label><input type="number" min="0.3" max="30" step="0.05" id="wait_before_exit_sec" value="{wait_exit}"></div>
</div>
<div class="grid-2">
<div class="field"><label class="field-label">⭐ Skip Level ≤</label><input type="number" min="0" max="100" id="skip_level_max" value="{skip_level}"></div>
<div class="field"><label class="field-label">🎨 Craftland Share</label>
<div class="chips"><label class="chip"><input type="checkbox" id="send_craftland" {'checked' if craftland else ''}><span>Enable</span></label></div></div>
</div>
<div class="field"><label class="field-label">💬 Welcome Message</label><textarea id="welcome_msg" style="height:180px;color:#F59E0B" spellcheck="false">{welcome_esc}</textarea>
<div class="hint">Placeholder: <b>{{user_name}}</b></div></div>
<button type="submit" class="btn green" id="cfg-save-btn" style="padding:14px;width:100%">💾 Save Config</button>
</div></form></section>
<section class="panel" id="section-bots">
<div class="panel-head"><div class="panel-title"><div class="panel-ico">📋</div> Active Bots</div><span class="pill green"><span class="dot"></span> Live</span></div>
<div class="table-shell"><table><thead><tr><th>Bot UID</th><th>UID</th><th>Name</th><th>Region</th><th>Target UID</th><th>Time</th><th>Status</th></tr></thead>
<tbody id="accounts-tbody"><tr><td colspan="7" style="text-align:center;padding:36px;color:var(--txt3)">🔄 Loading...</td></tr></tbody></table></div>
</section>
<section class="panel" id="section-logs">
<div class="panel-head"><div class="panel-title"><div class="panel-ico">📜</div> Live Log</div><button class="btn ghost" onclick="clearLogView()" style="padding:8px 16px;font-size:.8em">🗑️ Clear</button></div>
<div id="live-log" class="log-shell">📡 Waiting...</div>
</section>
<footer class="foot">© 2026 <b>MAHIR · JOIN BOT</b> · Cyberpunk Edition</footer>
</main></div>
<div class="toast" id="toast"></div>
<script>
let CURRENT_STOPPED = {str(stopped_now).lower()};
function toggleSidebar(){{document.getElementById('sidebar').classList.toggle('open');document.getElementById('overlay').classList.toggle('show')}}
function showToast(m,c){{const t=document.getElementById('toast');t.innerText=m;t.style.background=`linear-gradient(135deg,${{c||'#10B981'}},${{c||'#10B981'}}cc)`;t.classList.add('show');clearTimeout(window._tt);window._tt=setTimeout(()=>t.classList.remove('show'),3500)}}
async function doStopAll(){{if(!confirm('Stop ALL?'))return;await fetch('/stop_all_bots',{{method:'POST'}});showToast('🛑 Stopped','#EF4444');await refreshStatus()}}
async function doStartAll(){{if(!confirm('Start ALL?'))return;await fetch('/start_all_bots',{{method:'POST'}});showToast('🚀 Started','#10B981');await refreshStatus()}}
async function doAccountRestart(){{if(!confirm('Restart ALL?'))return;await fetch('/restart_accounts',{{method:'POST'}});showToast('♻️ Restart triggered','#F59E0B')}}
async function refreshStatus(){{try{{const r=await fetch('/api/status');if(!r.ok)return;const d=await r.json();CURRENT_STOPPED=d.stopped;if(d.mode)document.getElementById('mode-pill').innerText='Mode: '+d.mode;updateStatusUI()}}catch(e){{}}}}
function updateStatusUI(){{const b=document.getElementById('status-banner'),bt=document.getElementById('banner-text'),sb=document.getElementById('btn-stop-all'),stb=document.getElementById('btn-start-all');if(CURRENT_STOPPED){{b.style.background='linear-gradient(135deg,#EF4444,#7F1D1D)';bt.innerText='🛑 BOTS STOPPED';sb.style.display='none';stb.style.display='inline-flex'}}else{{b.style.background='linear-gradient(135deg,#10B981,#065F46)';bt.innerText='🟢 BOTS RUNNING';sb.style.display='inline-flex';stb.style.display='none'}}}}
async function saveConfig(e){{e.preventDefault();const btn=document.getElementById('cfg-save-btn');btn.disabled=true;btn.innerText='⏳';const body=new URLSearchParams();body.append('ghost_name',document.getElementById('ghost_name').value);body.append('welcome_msg',document.getElementById('welcome_msg').value);body.append('join_delay_sec',document.getElementById('join_delay_sec').value);body.append('wait_before_exit_sec',document.getElementById('wait_before_exit_sec').value);body.append('skip_level_max',document.getElementById('skip_level_max').value);body.append('send_craftland',document.getElementById('send_craftland').checked?'1':'0');try{{const r=await fetch('/save_config',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:body.toString()}});if(r.ok)showToast('⚙️ Config saved','#10B981');else showToast('❌ Failed','#EF4444')}}catch(e){{showToast('❌ Err','#EF4444')}}btn.disabled=false;btn.innerText='💾 Save Config'}}
async function loadAccountsList(){{try{{const r=await fetch('/api/accounts');if(!r.ok)return;const d=await r.json();document.getElementById('acc-content').value=d.content||'';document.getElementById('acc-count').innerText=(d.count||0)+' Accounts'}}catch(e){{}}}}
async function addSingleAccount(){{const uid=document.getElementById('new-uid').value.trim(),pwd=document.getElementById('new-pwd').value.trim();if(!uid||!pwd){{showToast('❌ Empty','#EF4444');return}}if(!/^[0-9]+$/.test(uid)){{showToast('❌ Digits only','#EF4444');return}}try{{const body=new URLSearchParams();body.append('uid',uid);body.append('password',pwd);const r=await fetch('/add_account',{{method:'POST',body:body.toString()}});if(r.ok){{showToast('✅ Added','#10B981');document.getElementById('new-uid').value='';document.getElementById('new-pwd').value='';await loadAccountsList()}}else showToast('❌ Failed','#EF4444')}}catch(e){{showToast('❌','#EF4444')}}}}
async function saveAllAccounts(){{const c=document.getElementById('acc-content').value;const btn=document.getElementById('acc-save-btn');btn.disabled=true;btn.innerText='⏳';try{{const body=new URLSearchParams();body.append('content',c);const r=await fetch('/save_accounts',{{method:'POST',body:body.toString()}});if(r.ok){{showToast('💾 Saved','#10B981');await loadAccountsList()}}else showToast('❌','#EF4444')}}catch(e){{showToast('❌','#EF4444')}}btn.disabled=false;btn.innerText='💾 Save'}}
async function reloadAccounts(){{await loadAccountsList();showToast('🔄 Reloaded','#3B82F6')}}
function downloadAccounts(){{const c=document.getElementById('acc-content').value;const b=new Blob([c],{{type:'text/plain'}});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='accounts.txt';a.click();showToast('📥 Downloaded','#22D3EE')}}
async function uploadAccFile(){{const fi=document.getElementById('acc-file');if(!fi.files||!fi.files[0]){{showToast('❌ No file','#EF4444');return}}const r=new FileReader();r.onload=async(e)=>{{const c=e.target.result;document.getElementById('acc-content').value=c;try{{const body=new URLSearchParams();body.append('content',c);const resp=await fetch('/save_accounts',{{method:'POST',body:body.toString()}});if(resp.ok){{showToast('📤 Uploaded','#EC4899');await loadAccountsList();fi.value=''}}else showToast('❌','#EF4444')}}catch(err){{showToast('❌','#EF4444')}}}};r.readAsText(fi.files[0])}}
async function loadRecruitsList(){{try{{const r=await fetch('/api/recruits');if(!r.ok)return;const d=await r.json();document.getElementById('recruit-content').value=d.content||'';document.getElementById('recruit-count').innerText=(d.count||0)+' Targets'}}catch(e){{}}}}
async function saveRecruits(){{const c=document.getElementById('recruit-content').value;const btn=document.getElementById('recruit-save-btn');btn.disabled=true;btn.innerText='⏳';try{{const body=new URLSearchParams();body.append('content',c);const r=await fetch('/save_recruits',{{method:'POST',body:body.toString()}});if(r.ok){{showToast('🎯 Recruits saved','#A855F7');await loadRecruitsList()}}else showToast('❌ Failed','#EF4444')}}catch(e){{showToast('❌','#EF4444')}}btn.disabled=false;btn.innerText='💾 Save Recruits'}}
async function reloadRecruits(){{await loadRecruitsList();showToast('🔄 Reloaded','#3B82F6')}}
async function fetchStats(){{try{{const r=await fetch('/api/stats');if(!r.ok)return;const d=await r.json();document.getElementById('stat-online').innerText=d.online;document.getElementById('stat-total').innerText=d.total;document.getElementById('stat-threads').innerText=d.threads;const tb=document.getElementById('accounts-tbody');if(d.accounts&&d.accounts.length){{tb.innerHTML=d.accounts.map(a=>`<tr><td style="font-family:monospace;color:var(--txt2)">${{a.bot_uid}}</td><td style="font-family:monospace;color:var(--txt2)">${{a.uid}}</td><td style="color:var(--cyan);font-weight:700">${{a.name}}</td><td><span style="color:var(--amber);font-weight:700">${{a.region}}</span></td><td style="color:#FACC15;font-family:monospace">${{a.squad_id||'—'}}</td><td style="color:var(--txt3);font-family:monospace">${{a.time}}</td><td><span class="badge-live">ONLINE</span></td></tr>`).join('')}}else tb.innerHTML='<tr><td colspan="7" style="text-align:center;padding:36px;color:var(--txt3)">⚠️ No active bots</td></tr>'}}catch(e){{}}}}
async function fetchLogs(){{try{{const r=await fetch('/api/logs');if(!r.ok)return;const d=await r.json();const el=document.getElementById('live-log');const logs=d.logs||[];if(!logs.length){{el.innerHTML='📡 Waiting...';return}}const atBottom=el.scrollTop+el.clientHeight>=el.scrollHeight-30;el.innerHTML=logs.map(l=>`<div>${{l.replace(/&/g,'&amp;').replace(/</g,'&lt;')}}</div>`).join('');if(atBottom)el.scrollTop=el.scrollHeight}}catch(e){{}}}}
function clearLogView(){{document.getElementById('live-log').innerHTML='📡 Cleared';showToast('🗑️','#F59E0B')}}
loadAccountsList();setInterval(loadAccountsList,15000);loadRecruitsList();setInterval(loadRecruitsList,15000);fetchStats();setInterval(fetchStats,2000);fetchLogs();setInterval(fetchLogs,2500);refreshStatus();setInterval(refreshStatus,3000);
</script></body></html>"""
            self.wfile.write(html.encode('utf-8')); return

        if self.path == '/api/stats':
            with active_lock:
                accs = list(active_accounts); oc = online_count
            try: total = len(load_accounts())
            except: total = 0
            self._json_response({'online':oc,'total':total,'threads':len(accs),
                                 'version':FREEFIRE_VERSION_NAME or "loading...",
                                 'release':CURRENT_OB or "loading...",
                                 'mode':current_mode,
                                 'accounts':accs}); return

        if self.path == '/api/logs':
            with log_lock: logs = list(log_buffer)
            self._json_response({'logs':logs}); return

        if self.path == '/api/accounts':
            try:
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f: content = f.read()
            except: content = ""
            accs = load_accounts()
            self._json_response({'content':content,'count':len(accs),
                                 'accounts':[{'uid':u,'password':p} for u,p in accs.items()]}); return

        if self.path == '/api/recruits':
            try:
                with open(RECRUIT_FILE, "r", encoding="utf-8") as f: content = f.read()
            except: content = ""
            recruits = load_recruits()
            self._json_response({
                'content': content,
                'count': len(recruits),
                'recruits': [{'owner_uid': o, 'code': c} for o, c in recruits]
            }); return

        if self.path == '/api/status':
            self._json_response({'stopped':is_stopped(),'online':online_count,
                                 'total':total_accounts,'mode':current_mode}); return

        self.send_response(404); self.end_headers()

    def do_POST(self):
        raw = self._read_body()

        if self.path == '/restart_accounts':
            trigger_restart_all(); self._text_response('OK'); return
        if self.path == '/stop_all_bots':
            set_stop_all(True); self._text_response('OK'); return
        if self.path == '/start_all_bots':
            set_stop_all(False); self._text_response('OK'); return

        if self.path == '/save_accounts':
            params = parse_qs(raw)
            new_content = params.get('content', [''])[0]
            try:
                save_accounts_raw(new_content)
                cnt = len(load_accounts())
                self._text_response(f'OK:{cnt}')
            except Exception as e:
                self._text_response(f'Error: {e}', 500)
            return

        if self.path == '/add_account':
            params = parse_qs(raw)
            uid = params.get('uid', [''])[0].strip()
            pwd = params.get('password', [''])[0].strip()
            if not uid.isdigit() or not pwd:
                self._text_response('Invalid', 400); return
            try:
                accs = load_accounts(); accs[uid] = pwd; save_accounts(accs)
                self._text_response('OK')
            except Exception as e:
                self._text_response(f'Error: {e}', 500)
            return

        if self.path == '/save_recruits':
            params = parse_qs(raw)
            new_content = params.get('content', [''])[0]
            try:
                save_recruits_raw(new_content)
                cnt = len(load_recruits())
                self._text_response(f'OK:{cnt}')
            except Exception as e:
                self._text_response(f'Error: {e}', 500)
            return

        if self.path == '/save_config':
            params = parse_qs(raw)
            try:
                with web_config_lock:
                    gn = params.get('ghost_name', [''])[0]
                    if gn: web_config['ghost_name'] = gn
                    wm = params.get('welcome_msg', [''])[0]
                    if wm: web_config['welcome_msg'] = wm
                    jd = float(params.get('join_delay_sec', ['0.5'])[0] or 0.5)
                    if 0.1 <= jd <= 30: web_config['join_delay_sec'] = jd
                    we = float(params.get('wait_before_exit_sec', ['0.5'])[0] or 0.5)
                    if 0.3 <= we <= 30: web_config['wait_before_exit_sec'] = we
                    sl = int(params.get('skip_level_max', ['2'])[0] or 2)
                    if 0 <= sl <= 100: web_config['skip_level_max'] = sl
                    web_config['send_craftland'] = params.get('send_craftland', ['1'])[0] == '1'
                save_web_config()
                self._text_response('OK')
            except Exception as e:
                self._text_response(f'Error: {e}', 400)
            return

        self.send_response(404); self.end_headers()

    def log_message(self, format, *args): pass

# ================================================================
# MAIN
# ================================================================
def start_web_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(('0.0.0.0', port), BotHandler)
        console.print(f"[bold green]🌐 Dashboard: http://0.0.0.0:{port}[/bold green]")
        server.serve_forever()
    except OSError:
        console.print(f"[bold red]❌ Port {port} in use.[/bold red]")

async def main_async():
    print(render('MAHIR', colors=['white', 'red'], align='center'))
    load_web_config()
    threading.Thread(target=start_web_server, daemon=True).start()
    await asyncio.sleep(1)
    asyncio.create_task(batch_account_loader())
    console.print(Panel(
        "[bold green]✅ Join→Msg→Exit→Ghost Workflow Active[/bold green]\n"
        "[cyan]🌐 http://localhost:8080[/cyan]\n"
        f"[white]📦 {CURRENT_OB} | {FREEFIRE_VERSION_NAME}[/white]\n"
        "[magenta]📤 Modes: normal (Join_Sq) / recruit (uid:code) / group (uid only)[/magenta]\n"
        "[blue]💬 RECRUITS.txt: uid:code → recruit | uid → group | empty → random[/blue]\n"
        "[bold yellow]⚡ Fast Exit (1s) + Fast Ghost (0.05s delay)[/bold yellow]\n"
        "[bold yellow]⚠️ NO FALLBACK — Pure API Data[/bold yellow]",
        title="[bold red]🔥 MAHIR JOIN BOT 🔥[/bold red]",
        border_style="bright_red", expand=False))
    while True: await asyncio.sleep(3600)

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: loop.run_until_complete(main_async())
    except KeyboardInterrupt: console.print("\n[bold red]Shutdown.[/bold red]")

if __name__ == "__main__":
    main()