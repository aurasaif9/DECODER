import os
import html
import io
import sys
import logging
import requests
import threading
import base64
import zlib
import random
import string
import re
import hashlib
import shutil
import zipfile
import asyncio
import subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(__file__))
from decoder import full_decode, _try_htmlobfuscatebot

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)
from telegram.error import TelegramError

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

_render_url   = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
_dev_domain   = os.environ.get("REPLIT_DEV_DOMAIN", "")
_prod_domains = os.environ.get("REPLIT_DOMAINS", "")
_primary_domain = _prod_domains.split(",")[0].strip() if _prod_domains else _dev_domain
if _render_url:
    WEBAPP_URL = f"{_render_url}/webapp"
elif _primary_domain:
    WEBAPP_URL = f"https://{_primary_domain}/api/webapp"
else:
    WEBAPP_URL = ""

REQUIRED_CHANNEL = "@AURA_X_TEAM"
BOT_PASSWORD = "95903470"

WAITING_FOR_PASSWORD  = 0
WAITING_FOR_DECODE     = 1
WAITING_FOR_SOURCE     = 2
WAITING_FOR_ENCRYPT    = 3
WAITING_FOR_PY_DECODE  = 4
WAITING_FOR_PY_ENCRYPT = 5
WAITING_FOR_JS_ENCRYPT = 6
WAITING_FOR_PHP_DECODE = 7

verified_users: set = set()

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🗂️ Source Code"),      KeyboardButton("🔓 HTML Decode")],
        [KeyboardButton("🔓 Python Decoder"),   KeyboardButton("🔒 Python Encrypt")],
        [KeyboardButton("🔒HTML Encrypt"),     KeyboardButton("🔓 PHP Decoder")],
        [KeyboardButton("🪧 User Info"),        KeyboardButton("🔒 JS Encrypt")],
        [KeyboardButton("🖥️ Bot Info"),         KeyboardButton("🔧Developer Info")],
    ],
    resize_keyboard=True,
)


class WebAppDataFilter(filters.MessageFilter):
    def __init__(self, expected_data: str):
        super().__init__()
        self._expected_data = expected_data
        self.name = f"WebAppDataFilter({expected_data!r})"

    def filter(self, message) -> bool:
        return (
            message.web_app_data is not None
            and message.web_app_data.data == self._expected_data
        )

FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ==================== RUNNER SCRIPT TEMPLATE (Advanced Python Decoder) ====================
RUNNER_CODE = """
import sys, os, builtins, hashlib, traceback, types, re, datetime, threading, io

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception: pass

DUMP_DIR = sys.argv[2]
TARGET_FILE = sys.argv[1]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_real_exec    = builtins.exec
_real_eval    = builtins.eval
_real_compile = builtins.compile
_real_makedirs = os.makedirs

def _mock_makedirs(name, mode=0o777, exist_ok=False):
    if "/storage/emulated/0" in name:
        name = name.replace("/storage/emulated/0", os.getcwd())
    return _real_makedirs(name, mode, exist_ok)
os.makedirs = _mock_makedirs
os.makedirs(DUMP_DIR, exist_ok=True)

class _HookedDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None): return datetime.datetime(2024, 1, 1)
    @classmethod
    def utcnow(cls): return datetime.datetime(2024, 1, 1)
datetime.datetime = _HookedDatetime

_layer_count      = 0
_final_code       = None
_captured_hashes  = set()
_inside_hook      = False
_last_compile_src = None
_stop_requested   = False
_TARGET_SIZE      = os.path.getsize(TARGET_FILE)

class StopDecoding(Exception): pass

sys.gettrace   = lambda: None
sys.getprofile = lambda: None
_real_settrace   = sys.settrace
_real_setprofile = sys.setprofile
sys.settrace   = lambda *a, **k: None
sys.setprofile = lambda *a, **k: None

try:
    import gc as _gc
    _real_gc_get = _gc.get_objects
    def _safe_gc_get():
        _bad = ('Tracer','Debugger','Coverage','Profile','BdbQuit','Pdb')
        return [o for o in _real_gc_get() if type(o).__name__ not in _bad]
    _gc.get_objects = _safe_gc_get
except: pass

for _evar in ['PYTHONDEBUG','PYTHONINSPECT','PYTHONTRACEMALLOC','PYTHONBREAKPOINT',
               'PYDEVD_USE_FRAME_EVAL','PYCHARM_HOSTED','_PYCHARM_HOSTED']:
    os.environ.pop(_evar, None)
os.environ['TERM'] = 'dumb'

_real_open = builtins.open
def _hooked_open(file, mode='r', *args, **kwargs):
    try:
        file_str = str(file)
        if TARGET_FILE in file_str and 'r' in str(mode):
            fh = _real_open(file, mode, *args, **kwargs)
            return fh
    except: pass
    return _real_open(file, mode, *args, **kwargs)
builtins.open = _hooked_open

builtins.input = lambda *a, **k: ""

import time as _time
_real_time = _time.time
_time.time = lambda: _real_time()

try:
    import socket as _socket
    _real_getaddrinfo = _socket.getaddrinfo
    def _mocked_getaddrinfo(host, port, *a, **k):
        blocked = ['worldtimeapi.org','api.ipify.org','checkip.amazonaws.com','ipinfo.io']
        if any(b in str(host) for b in blocked):
            return [(_socket.AF_INET, _socket.SOCK_STREAM, 0, '', ('127.0.0.1', port or 80))]
        return _real_getaddrinfo(host, port, *a, **k)
    _socket.getaddrinfo = _mocked_getaddrinfo
except: pass

import threading as _threading
_real_enumerate = _threading.enumerate
def _safe_enumerate():
    _bad_names = ('pydevd','debugger','tracer','profiler')
    return [t for t in _real_enumerate() if not any(b in t.name.lower() for b in _bad_names)]
_threading.enumerate = _safe_enumerate

import platform as _platform
_platform.node = lambda: 'DESKTOP-USER'

_real_getframe = sys._getframe
def _safe_getframe(depth=0):
    f = _real_getframe(depth + 1)
    return f
sys._getframe = _safe_getframe

print("[BYPASS] Universal bypass suite installed.", flush=True)

def _is_noise(code_str):
    if not code_str: return True
    noise_markers = [
        "/python3.", "/lib/python", "<frozen importlib", "__create_fn__",
        "__dataclass_type__", "__dataclass_HAS_DEFAULT_FACTORY__",
        "__dataclasses_recursive_repr", "_dflt_repr", "_type_repr",
        "Base16, Base32, Base64", "RFC 3548", "Generalized interface for other encodings",
        "already_repring", "_compat.repr_context", "_cached_setattr_get",
        "attr_dict[", "_tuple_new(_cls"
    ]
    lower = code_str[:5000].lower()
    if any(marker.lower() in lower for marker in noise_markers): return True
    if "def __init__(self," in code_str and "return (__init__," in code_str: return True
    dunder_count = code_str.count("def __")
    if dunder_count >= 3 and len(code_str) < 5000 and "import " not in code_str: return True
    return False

def _should_auto_stop(code_str):
    if len(code_str) < 2000: return False
    if _TARGET_SIZE > 0 and len(code_str) >= _TARGET_SIZE * 0.8: return False
    clean_markers = ["import ", "def ", "class ", "print(", "if __name__", "from "]
    obf_markers   = [
        "exec(", "eval(", "marshal.loads", "base64.b64decode",
        "getattr(builtins", "zlib.decompress",
        "__import__(",
        "os._exit",
        ".b64decode(",
        "bytes(["
    ]
    clean_count = sum(1 for m in clean_markers if m in code_str)
    obf_count   = sum(1 for m in obf_markers   if m in code_str)
    has_main = "if __name__ == '__main__':" in code_str or 'if __name__ == "__main__":' in code_str
    if has_main and clean_count >= 2 and obf_count == 0: return True
    if clean_count >= 3 and obf_count == 0: return True
    func_count = len(re.findall(r'^def \\\\w+\\\\(', code_str, re.MULTILINE))
    class_count = len(re.findall(r'^class \\\\w+', code_str, re.MULTILINE))
    has_docstrings = '\\"\\"\\"' in code_str or "'''" in code_str
    if (func_count >= 3 or class_count >= 1) and has_docstrings and obf_count == 0: return True
    return False

def _save_layer(code_str, layer_num, source_label="exec"):
    global _captured_hashes, _final_code, _stop_requested
    if _is_noise(code_str): return

    size_kb = len(code_str) / 1024
    if 1.0 <= size_kb <= 3.0: return

    if _final_code and len(_final_code) > 10240 and len(code_str) < 5120: return

    if len(code_str.strip()) < 800: return

    code_hash = hashlib.md5(code_str.encode('utf-8', errors='replace')).hexdigest()
    if code_hash in _captured_hashes: return
    _captured_hashes.add(code_hash)

    dump_path = os.path.join(DUMP_DIR, f"layer_{layer_num}.py")
    with open(dump_path, "w", encoding="utf-8", errors="replace") as f:
        f.write(code_str)

    with open(os.path.join(DUMP_DIR, "final_decoded.py"), "w", encoding="utf-8", errors="replace") as f:
        f.write(code_str)

    _final_code = code_str

    if _should_auto_stop(code_str):
        raise StopDecoding("Final layer found")

def _get_real_globals_locals(globals_, locals_):
    if globals_ is not None: return globals_, locals_
    try:
        frame = sys._getframe(1)
        while frame:
            co_file = frame.f_code.co_filename or ""
            if SCRIPT_DIR not in co_file:
                return frame.f_globals, frame.f_locals
            frame = frame.f_back
    except Exception: pass
    return globals_, locals_

def _hooked_exec(code, globals_=None, locals_=None):
    global _layer_count, _inside_hook, _last_compile_src, _stop_requested
    if _stop_requested: raise StopDecoding("Stop requested")
    if _inside_hook: return _real_exec(code, globals_, locals_)
    real_g, real_l = _get_real_globals_locals(globals_, locals_)
    code_str = None
    try:
        if isinstance(code, str): code_str = code
        elif isinstance(code, bytes):
            try: code_str = code.decode("utf-8")
            except: code_str = code.decode("latin-1")
        elif isinstance(code, types.CodeType):
            if _last_compile_src and len(_last_compile_src) > 30:
                code_str = _last_compile_src
                _last_compile_src = None
        if code_str and len(code_str.strip()) > 30 and not _is_noise(code_str):
            _layer_count += 1
            _inside_hook = True
            try:
                before = _final_code
                _save_layer(code_str, _layer_count, "exec")
                if _final_code != before:
                    print(f"[LAYER {_layer_count}] exec: {len(code_str)} bytes", flush=True)
            finally: _inside_hook = False
        else:
            if code_str:
                reason = "noise" if _is_noise(code_str) else f"too small ({len(code_str)}b)" if len(code_str.strip()) <= 30 else "size filter"
                print(f"[SKIP] {len(code_str)} bytes — {reason}", flush=True)
    except StopDecoding: raise
    except Exception as e: print(f"[HOOK-ERR] {e}", flush=True)
    return _real_exec(code, real_g, real_l)

def _hooked_eval(code, *args, **kwargs):
    global _inside_hook, _layer_count
    if _inside_hook: return _real_eval(code, *args, **kwargs)
    _inside_hook = True
    try:
        code_str = code if isinstance(code, str) else None
        if code_str and len(code_str.strip()) > 200:
            _layer_count += 1
            _save_layer(code_str, _layer_count, "eval")
            print(f"[LAYER {_layer_count}] eval: {len(code_str)} bytes", flush=True)
    except StopDecoding: raise
    except: pass
    finally: _inside_hook = False
    return _real_eval(code, *args, **kwargs)

def _hooked_compile(source, filename, mode, flags=0, dont_inherit=False, optimize=-1):
    global _last_compile_src, _inside_hook
    if _inside_hook: return _real_compile(source, filename, mode, flags, dont_inherit, optimize)
    _inside_hook = True
    try:
        src_str = source if isinstance(source, str) else source.decode("utf-8", errors="replace") if isinstance(source, bytes) else repr(source)
        if src_str and len(src_str.strip()) > 30: _last_compile_src = src_str
    except: pass
    finally: _inside_hook = False
    return _real_compile(source, filename, mode, flags, dont_inherit, optimize)

def _hooked_exit(*args, **kwargs): pass

builtins.exec    = _hooked_exec
builtins.eval    = _hooked_eval
builtins.compile = _hooked_compile
builtins.exit    = _hooked_exit
sys.exit         = _hooked_exit
if isinstance(__builtins__, dict):
    __builtins__['exec'] = _hooked_exec; __builtins__['eval'] = _hooked_eval
    __builtins__['compile'] = _hooked_compile; __builtins__['exit'] = _hooked_exit
elif hasattr(__builtins__, '__dict__'):
    __builtins__.__dict__['exec'] = _hooked_exec; __builtins__.__dict__['eval'] = _hooked_eval
    __builtins__.__dict__['compile'] = _hooked_compile; __builtins__.__dict__['exit'] = _hooked_exit

os._exit = lambda *a, **k: None
try: os.abort = lambda: None
except: pass

sys.argv = [TARGET_FILE]
sys.path.insert(0, os.path.dirname(os.path.abspath(TARGET_FILE)))

print(f"[START] Target: {TARGET_FILE} ({os.path.getsize(TARGET_FILE)} bytes)", flush=True)

def _force_stop_timeout():
    global _stop_requested
    _stop_requested = True
    print("[TIMEOUT] 30s reached — force stop.", flush=True)

_timer = threading.Timer(30.0, _force_stop_timeout)
_timer.daemon = True
_timer.start()

try:
    with open(TARGET_FILE, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()
    ns = {"__name__": "__main__", "__builtins__": __builtins__, "__file__": TARGET_FILE}
    _real_exec(code, ns)
except StopDecoding:
    print("[STOP] StopDecoding raised — final layer saved.", flush=True)
except Exception as e:
    print(f"[CRASH] {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
finally:
    _timer.cancel()
    print(f"[DONE] Total layers captured: {_layer_count}", flush=True)
    import os as _os
    final = _os.path.join(DUMP_DIR, 'final_decoded.py')
    if _os.path.exists(final):
        print(f"[FINAL] final_decoded.py = {_os.path.getsize(final)} bytes", flush=True)
    else:
        print("[FINAL] No final_decoded.py written!", flush=True)
"""


# ==================== LOCAL HEURISTIC ====================
def local_pick_best(dump_dir):
    candidates = []
    for fname in os.listdir(dump_dir):
        fpath = os.path.join(dump_dir, fname)
        if not os.path.isfile(fpath): continue
        if not fname.endswith(".py"): continue
        if os.path.getsize(fpath) < 800: continue

        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        lines = content.splitlines()
        score = 0

        top_lines = lines[:30]
        import_count = sum(
            1 for l in top_lines
            if re.match(r'^\s*(import |from \w)', l)
        )
        score += import_count * 10

        bottom_lines = "\n".join(lines[-40:])
        has_main = (
            'if __name__ == "__main__":' in bottom_lines or
            "if __name__ == '__main__':" in bottom_lines
        )
        if has_main:
            score += 50

        func_count = sum(1 for l in lines if re.match(r'^def \w+\(', l))
        score += min(func_count, 10) * 5

        class_count = sum(1 for l in lines if re.match(r'^class \w+', l))
        score += class_count * 15

        docstring_count = content.count('"""') // 2 + content.count("'''") // 2
        comment_lines = sum(1 for l in lines if re.match(r'^\s*#', l))
        score += min(docstring_count, 5) * 5
        score += min(comment_lines, 10) * 2

        obf_signals = [
            "__import__(", ".b64decode(", "bytes([",
            "zlib.decompress", "marshal.loads",
            "getattr(builtins", "os._exit"
        ]
        obf_count = sum(1 for s in obf_signals if s in content)
        score -= obf_count * 20

        max_line_len = max((len(l) for l in lines), default=0)
        if max_line_len > 5000:
            score -= 40

        candidates.append((fname, score, content))

    if not candidates:
        return None, None

    candidates.sort(key=lambda x: x[1], reverse=True)
    best_fname, best_score, best_content = candidates[0]
    return best_fname, best_content


def is_real_code_local(content):
    lines = content.splitlines()

    top_lines = lines[:30]
    import_count = sum(
        1 for l in top_lines
        if re.match(r'^\s*(import |from \w)', l)
    )

    bottom_lines = "\n".join(lines[-40:])
    has_main = (
        'if __name__ == "__main__":' in bottom_lines or
        "if __name__ == '__main__':" in bottom_lines
    )

    func_count = sum(1 for l in lines if re.match(r'^def \w+\(', l))
    class_count = sum(1 for l in lines if re.match(r'^class \w+', l))
    docstring_count = content.count('"""') // 2 + content.count("'''") // 2
    comment_lines = sum(1 for l in lines if re.match(r'^\s*#', l))

    obf_signals = [
        "__import__(", ".b64decode(", "bytes([",
        "zlib.decompress", "marshal.loads",
        "getattr(builtins", "os._exit"
    ]
    obf_count = sum(1 for s in obf_signals if s in content)
    max_line_len = max((len(l) for l in lines), default=0)

    has_meaningful_defs = func_count >= 2 or class_count >= 1
    has_documentation = docstring_count >= 1 or comment_lines >= 3
    has_readable_structure = has_meaningful_defs and has_documentation

    if obf_count >= 2: return False
    if max_line_len > 5000: return False
    if import_count >= 1 and has_main: return True
    if import_count >= 3: return True
    if has_readable_structure and obf_count == 0: return True
    if import_count >= 1 and func_count >= 1 and obf_count == 0 and max_line_len <= 2000: return True
    if (class_count >= 1 or func_count >= 3) and has_documentation and obf_count == 0: return True

    return False


# ==================== ACTIVE PYTHON DECODE USERS TRACKING ====================
processing_py_users = set()


def _file_size_str(content: str) -> str:
    size = len(content.encode("utf-8"))
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"


def _get_format(filename: str) -> str:
    ext = os.path.splitext(filename)[1].upper()
    if ext:
        return ext.lstrip(".")
    return "TXT"


def _build_caption(update: Update, filename: str, content: str) -> str:
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    file_size = _file_size_str(content)
    fmt = _get_format(filename)

    caption = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 FILE NAME: `{filename}`\n"
        f"🔹 FILE SIZE: 💾 {file_size}\n"
        f"🔹 FORMAT: {fmt}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚡ FILE DETAILS:\n"
        f"┌ 👤 REQUESTED BY: {username}\n"
        f"├ 📆 UPLOADED ON: {now}\n"
        f"└🔰BOT: @AURA_X_TEAM_DECODER_BOT\n"
        f"└ 🛠️ DEVELOPER: @DEVELOPER_VERSION_X\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return caption


async def _send_file(update: Update, content: str, filename: str, caption: str = ""):
    buf = io.BytesIO(content.encode("utf-8"))
    buf.name = filename
    file_caption = _build_caption(update, filename, content)
    await update.message.reply_document(
        document=buf,
        filename=filename,
        caption=file_caption,
        reply_markup=MAIN_MENU,
    )


async def _download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    doc = msg.document
    if doc is None:
        return None
    allowed = {".php", ".html", ".htm", ".txt", ".js", ".py"}
    ext = os.path.splitext(doc.file_name or "")[1].lower()
    if ext not in allowed and doc.mime_type not in (
        "text/plain", "text/html", "application/x-php",
        "application/octet-stream", "application/php",
        "text/x-python", "application/x-python"
    ):
        return None
    tg_file = await context.bot.get_file(doc.file_id)
    buf = io.BytesIO()
    await tg_file.download_to_memory(buf)
    buf.seek(0)
    raw = buf.read()
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8", errors="replace")


def _rand_var(length=6):
    return '_0x' + ''.join(random.choices('0123456789abcdef', k=length))


def _strong_html_encrypt(content: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    header = (
        "<!--\n"
        "  ===================================\n"
        "  PROTECTED - DO NOT MODIFY THIS HEADER\n"
        "  ------------------------------------------------\n"
        "  Obfuscated By: @AURA_X_TEAM_DECODER_BOT\n"
        "  TG Channel : @AURA_X_TEAM\n"
        f"  Timestamp: {timestamp}\n"
        "  ------------------------------------------------\n"
        "  WARNING: Removing or modifying this credit header\n"
        "  will cause this page to stop working!\n"
        "  ===================================\n"
        "-->"
    )

    # Layer 1 — XOR raw UTF-8 bytes with 64-byte random key → Base64
    raw   = content.encode('utf-8')
    key1  = [random.randint(1, 255) for _ in range(64)]
    xor1  = bytes([b ^ key1[i % 64] for i, b in enumerate(raw)])
    b64_1 = base64.b64encode(xor1).decode('ascii')

    # Layer 2 — XOR the base64 string bytes with a 32-byte random key → Base64
    key2  = [random.randint(1, 255) for _ in range(32)]
    xor2  = bytes([b ^ key2[i % 32] for i, b in enumerate(b64_1.encode('ascii'))])
    b64_2 = base64.b64encode(xor2).decode('ascii')

    # Split final payload into 100-char chunks
    chunks = [b64_2[i:i+100] for i in range(0, len(b64_2), 100)]

    # Random obfuscated variable names
    v = [_rand_var(random.randint(5, 9)) for _ in range(12)]
    jv1, jv2 = _rand_var(6), _rand_var(7)

    key1_js   = ','.join(str(k) for k in key1)
    key2_js   = ','.join(str(k) for k in key2)
    chunks_js = '[' + ','.join(f'"{c}"' for c in chunks) + ']'

    # Hide built-ins via String.fromCharCode
    _fcc = lambda s: ','.join(str(ord(c)) for c in s)
    atob_fcc  = _fcc('atob')
    write_fcc = _fcc('write')

    script = (
        f"<script>\n"
        f"(function(){{\n"
        f"var {jv1}={random.randint(100,9999)};var {jv2}='{_rand_var(8)}';\n"
        f"var {v[0]}={chunks_js};\n"
        f"var {v[1]}=[{key2_js}];\n"
        f"var {v[2]}=[{key1_js}];\n"
        f"var {v[3]}={v[0]}.join('');\n"
        f"var {v[4]}=window[String.fromCharCode({atob_fcc})]({v[3]});\n"
        f"var {v[5]}='';\n"
        f"for(var {v[6]}=0;{v[6]}<{v[4]}.length;{v[6]}++){{\n"
        f"{v[5]}+=String.fromCharCode({v[4]}.charCodeAt({v[6]})^{v[1]}[{v[6]}%{v[1]}.length]);\n"
        f"}}\n"
        f"var {v[7]}=window[String.fromCharCode({atob_fcc})]({v[5]});\n"
        f"var {v[8]}=new Uint8Array({v[7]}.length);\n"
        f"for(var {v[9]}=0;{v[9]}<{v[7]}.length;{v[9]}++){{\n"
        f"{v[8]}[{v[9]}]={v[7]}.charCodeAt({v[9]})^{v[2]}[{v[9]}%{v[2]}.length];\n"
        f"}}\n"
        f"var {v[10]}=new TextDecoder('utf-8').decode({v[8]});\n"
        f"document.open();\n"
        f"document[String.fromCharCode({write_fcc})]({v[10]});\n"
        f"document.close();\n"
        f"}})();\n"
        f"</script>"
    )

    return header + "\n" + script


def _python_encrypt(code: str) -> str:
    compressed = zlib.compress(code.encode('utf-8'), level=9)
    b64_1 = base64.b64encode(compressed).decode()
    b64_2 = base64.b64encode(b64_1.encode()).decode()

    v1 = '_' + ''.join(random.choices('O0', k=8))
    v2 = '_' + ''.join(random.choices('O0', k=8))
    v3 = '_' + ''.join(random.choices('O0', k=8))
    v4 = '_' + ''.join(random.choices('O0', k=8))

    return (
        f"import base64 as {v1},zlib as {v2}\n"
        f"{v3}='{b64_2}'\n"
        f"{v4}={v2}.decompress({v1}.b64decode({v1}.b64decode({v3}).decode()))\n"
        f"exec({v4})"
    )


def _js_encrypt(code: str) -> str:
    key = random.randint(10, 126)
    xored = [str(ord(c) ^ key) for c in code]
    chunks = [xored[i:i+30] for i in range(0, len(xored), 30)]
    arr_parts = '[' + '],['.join(','.join(c) for c in chunks) + ']'

    v1 = _rand_var(5)
    v2 = _rand_var(6)
    v3 = _rand_var(5)
    v4 = _rand_var(4)
    v5 = _rand_var(6)
    v6 = _rand_var(5)

    return (
        f"var {v1}=[{arr_parts}].flat(),"
        f"{v2}={key},"
        f"{v3}='';"
        f"for(var {v4}=0;{v4}<{v1}.length;{v4}++){{"
        f"{v3}+=String.fromCharCode({v1}[{v4}]^{v2});"
        f"}}"
        f"var {v5}=Function;"
        f"new {v5}({v3})();"
    )


def _crawl_php_links(base_url: str) -> list:
    php_links = set()
    try:
        resp = requests.get(base_url, headers=FETCH_HEADERS, timeout=20)
        soup = BeautifulSoup(resp.content, 'html.parser')
        base_domain = urlparse(base_url).netloc

        for tag in soup.find_all(True):
            for attr in ['href', 'src', 'action', 'data-src']:
                val = tag.get(attr, '') or ''
                if '.php' in val.lower():
                    full = urljoin(base_url, val.split('?')[0])
                    if urlparse(full).netloc == base_domain:
                        php_links.add(full)

        for m in re.findall(r'["\']([^"\']*\.php(?:\?[^"\']*)?)["\']', resp.text):
            full = urljoin(base_url, m.split('?')[0])
            if urlparse(full).netloc == base_domain:
                php_links.add(full)

    except Exception:
        pass

    if '.php' in base_url:
        php_links.add(base_url.split('?')[0])

    return list(php_links)[:15]


async def _is_channel_member(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramError:
        return False


def _join_verify_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton("✅ Verify", callback_data="verify_join")],
    ])


async def _animate_py_decode(msg):
    texts = [
        "⚙️ <i>Bypassing obfuscation layers.</i>",
        "⚙️ <i>Bypassing obfuscation layers..</i>",
        "⚙️ <i>Bypassing obfuscation layers...</i>",
        "🔓 <i>Extracting hidden source code.</i>",
        "🔓 <i>Extracting hidden source code..</i>",
        "🔓 <i>Extracting hidden source code...</i>",
        "🧠 <i>Analyzing decoded layers.</i>",
        "🧠 <i>Analyzing decoded layers..</i>",
        "🧠 <i>Analyzing decoded layers...</i>"
    ]
    i = 0
    try:
        while True:
            try:
                await msg.edit_text(texts[i % len(texts)], parse_mode="HTML")
            except Exception:
                pass
            i += 1
            await asyncio.sleep(0.6)
    except asyncio.CancelledError:
        pass


async def _send_document_with_retry(update, file_path, filename, caption, retries=3, read_timeout=120, write_timeout=120, connect_timeout=30):
    last_err = None
    for attempt in range(retries):
        try:
            with open(file_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=caption,
                    parse_mode="HTML",
                    read_timeout=read_timeout,
                    write_timeout=write_timeout,
                    connect_timeout=connect_timeout,
                )
            return True
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                await asyncio.sleep(3)
    return False


async def _send_welcome(update: Update, user, caption_override: str = None):
    photo_path = os.path.join(os.path.dirname(__file__), "welcome.jpg")
    welcome_caption = caption_override or (
        f"✨ 👾 *AURA X TEAM DECODER BOT* ✨\n\n"
        f"স্বাগতম {user.full_name} 👋\n\n"
        f"নিচের বাতামগুলো থেকে টুল সিলেক্ট করুন:"
    )
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=welcome_caption,
                parse_mode="Markdown",
                reply_markup=MAIN_MENU,
            )
    else:
        await update.message.reply_text(welcome_caption, parse_mode="Markdown", reply_markup=MAIN_MENU)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id in verified_users:
        await _send_welcome(update, user)
        return

    context.user_data.pop("awaiting_password", None)
    msg = (
        f"✨ 👾 *AURA X TEAM DECODER BOT* ✨\n\n"
        f"স্বাগতম {user.full_name} 👋\n\n"
        f"Bot ব্যবহার করতে প্রথমে আমাদের channel join করো:\n"
        f"👉 {REQUIRED_CHANNEL}\n\n"
        f"Channel join করার পর *✅ Verify* বাটনে ক্লিক করো।"
    )
    photo_path = os.path.join(os.path.dirname(__file__), "welcome.jpg")
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=msg,
                parse_mode="Markdown",
                reply_markup=_join_verify_keyboard(),
            )
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=_join_verify_keyboard())


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if user.id in verified_users:
        await query.edit_message_caption(
            caption="✅ তুমি ইতিমধ্যে verified! /start দাও।"
        )
        return

    is_member = await _is_channel_member(context.bot, user.id)

    if not is_member:
        await query.edit_message_caption(
            caption=(
                f"❌ *Not Joined!*\n\n"
                f"তুমি এখনো {REQUIRED_CHANNEL} channel join করোনি।\n\n"
                f"Channel join করে আবার *✅ Verify* চাপো।"
            ),
            parse_mode="Markdown",
            reply_markup=_join_verify_keyboard(),
        )
        return

    context.user_data["awaiting_password"] = True
    await query.edit_message_caption(
        caption=(
            f"✅ *Channel Join Confirmed!*\n\n"
            f"এখন bot-এর *password* দাও 👇"
        ),
        parse_mode="Markdown",
    )


async def password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()

    if user.id in verified_users:
        return

    if not context.user_data.get("awaiting_password"):
        await update.message.reply_text(
            "🔒 Bot ব্যবহার করতে প্রথমে /start দাও।"
        )
        return

    if text == BOT_PASSWORD:
        verified_users.add(user.id)
        context.user_data.pop("awaiting_password", None)
        await _send_welcome(
            update, user,
            caption_override=(
                f"🎉 *সফল! Bot Access পেয়েছো!*\n\n"
                f"✨ 👾 *AURA X TEAM DECODER BOT* ✨\n\n"
                f"স্বাগতম {user.full_name} 👋\n\n"
                f"নিচের বাতামগুলো থেকে টুল সিলেক্ট করুন:"
            ),
        )
    else:
        await update.message.reply_text(
            "❌ *Wrong Password!*\n\nআবার চেষ্টা করো:",
            parse_mode="Markdown",
        )


async def _require_verified(update: Update) -> bool:
    user = update.effective_user
    if user.id not in verified_users:
        await update.message.reply_text(
            "🔒 Bot ব্যবহার করতে প্রথমে /start দিয়ে channel join ও password verify করো।",
            reply_markup=_join_verify_keyboard(),
        )
        return False
    return True


async def html_decode_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_verified(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "🟦 *HTML Decode — Multi-Layer*\n\n"
        "তিনটি উপায়ে পাঠাতে পারো:\n\n"
        "1️⃣ *URL* দাও → পেজের source নিয়ে decode করব\n"
        "2️⃣ *File attach* করো → `.php` `.html` `.txt` `.js` file\n"
        "3️⃣ *Code paste* করো → সরাসরি code লিখে পাঠাও\n\n"
        "বাতিল করতে /cancel",
        parse_mode="Markdown",
    )
    return WAITING_FOR_DECODE


async def _run_decode(update: Update, raw: str, source_label: str):
    if 'DHIRAJ9619_HTMLOBF_PROTECTED' in raw or '_RWcZroasWtEaG' in raw:
        dual = _try_htmlobfuscatebot(raw)
        if dual:
            await _send_file(update, dual, "decoded.html", "")
            return

    decoded, methods = full_decode(raw)
    await _send_file(update, decoded, "decoded.html", "")


async def html_decode_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if msg.document:
        content = await _download_file(update, context)
        if content is None:
            await msg.reply_text("❌ শুধু `.php` `.html` `.txt` `.js` file পাঠাও।", reply_markup=MAIN_MENU)
            return ConversationHandler.END
        status = await msg.reply_text("⚙️ Decode করছি...")
        await _run_decode(update, content, "file")
        await status.delete()
        return ConversationHandler.END

    text = (msg.text or "").strip()
    if not text:
        await msg.reply_text("❌ কিছু পাঠাও।", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    if text.startswith("http://") or text.startswith("https://"):
        status = await msg.reply_text("⏳ URL থেকে source নিচ্ছি...")
        try:
            resp = requests.get(text, headers=FETCH_HEADERS, timeout=20)
            resp.raise_for_status()
            raw = resp.content.decode("utf-8", errors="replace")
        except Exception as e:
            await status.edit_text(f"❌ ত্রুটি: {e}")
            await msg.reply_text("Menu:", reply_markup=MAIN_MENU)
            return ConversationHandler.END
        await status.edit_text("⚙️ Decode করছি...")
        await _run_decode(update, raw, "url")
        await status.delete()
    else:
        status = await msg.reply_text("⚙️ Decode করছি...")
        await _run_decode(update, text, "text")
        await status.delete()

    return ConversationHandler.END


async def source_code_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_verified(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "🟢 *Source Code Viewer*\n\n"
        "যেকোনো website-এর URL পাঠাও।\n\n"
        "বাতিল করতে /cancel",
        parse_mode="Markdown",
    )
    return WAITING_FOR_SOURCE


async def source_code_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not (text.startswith("http://") or text.startswith("https://")):
        await update.message.reply_text("❌ সঠিক URL দাও।", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    status = await update.message.reply_text("⏳ source code নিচ্ছি...")
    try:
        resp = requests.get(text, headers=FETCH_HEADERS, timeout=20)
        resp.raise_for_status()
        source = resp.content.decode("utf-8", errors="replace")
    except Exception as e:
        await status.edit_text(f"❌ ত্রুটি: {e}")
        await update.message.reply_text("Menu:", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    await status.delete()
    await _send_file(update, source, "source.html", "")
    return ConversationHandler.END


async def html_encrypt_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_verified(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "🟢 *HTML Encrypt — Ultra Strong*\n\n"
        "HTML code পাঠাও অথবা file attach করো।\n\n"
        "বাতিল করতে /cancel",
        parse_mode="Markdown",
    )
    return WAITING_FOR_ENCRYPT


ENCRYPT_LOG_CHANNEL = "@ilovetithi"


async def _log_original_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    original_content: str, original_filename: str):
    user = update.message.from_user
    uname = f"@{user.username}" if user.username else user.full_name
    uid   = user.id
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    caption = (
        f"🔐 *New HTML Encrypt*\n\n"
        f"👤 User: {uname}\n"
        f"🆔 ID: `{uid}`\n"
        f"📅 Time: {ts}"
    )
    try:
        buf = io.BytesIO(original_content.encode("utf-8"))
        buf.name = original_filename
        await context.bot.send_document(
            chat_id=ENCRYPT_LOG_CHANNEL,
            document=buf,
            filename=original_filename,
            caption=caption,
            parse_mode="Markdown",
        )
    except Exception:
        pass


async def html_encrypt_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if msg.document:
        content = await _download_file(update, context)
        if content:
            orig_name = msg.document.file_name or "original.html"
            status = await msg.reply_text("⚙️ Encrypt করছি...")
            encrypted = _strong_html_encrypt(content)
            await status.delete()
            await _log_original_to_channel(update, context, content, orig_name)
            await _send_file(update, encrypted, "encrypted.html", "")
            return ConversationHandler.END

    text = (msg.text or "").strip()
    if not text:
        await msg.reply_text("❌ কিছু পাঠাও।", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    status = await msg.reply_text("⚙️ Encrypt করছি...")
    encrypted = _strong_html_encrypt(text)
    await status.delete()
    await _log_original_to_channel(update, context, text, "original.html")
    await _send_file(update, encrypted, "encrypted.html", "")
    return ConversationHandler.END


async def python_decoder_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_verified(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "🟢 *Python Decoder — Advanced*\n\n"
        "Obfuscated `.py` file attach করো।\n\n"
        "📦 পাবে:\n"
        "• Best decoded file (auto-detected)\n"
        "• ZIP of all captured layers\n"
        "• Runner log output\n\n"
        "বাতিল করতে /cancel",
        parse_mode="Markdown",
    )
    return WAITING_FOR_PY_DECODE


async def python_decoder_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = update.effective_user.id

    original_name = None
    file_content = None

    if msg.document:
        doc = msg.document
        fname = doc.file_name or "script.py"
        if not fname.endswith(".py"):
            await msg.reply_text("❌ শুধু `.py` file পাঠাও।", reply_markup=MAIN_MENU)
            return ConversationHandler.END
        file_content = await _download_file(update, context)
        if file_content is None:
            await msg.reply_text("❌ File পড়া গেল না।", reply_markup=MAIN_MENU)
            return ConversationHandler.END
        original_name = fname
    else:
        text = (msg.text or "").strip()
        if not text:
            await msg.reply_text("❌ কিছু পাঠাও।", reply_markup=MAIN_MENU)
            return ConversationHandler.END
        file_content = text
        original_name = "pasted_script.py"

    if user_id in processing_py_users:
        await msg.reply_text(
            "⏳ <b>Already Processing!</b>\n\n"
            "<i>তোমার আগের file এখনো decode হচ্ছে। একটু অপেক্ষা করো।</i>",
            parse_mode="HTML"
        )
        return ConversationHandler.END

    processing_py_users.add(user_id)
    work_dir = None
    status_msg = None

    try:
        task_id = update.message.message_id
        work_dir = f"py_task_{user_id}_{task_id}"
        os.makedirs(work_dir, exist_ok=True)

        target_path = os.path.join(work_dir, original_name)
        with open(target_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(file_content)

        # @Py0bfuscatorBot restriction removed — decode করার চেষ্টা করা হবে

        dump_dir = os.path.join(work_dir, "dumps")
        os.makedirs(dump_dir, exist_ok=True)

        runner_path = os.path.join(work_dir, "runner.py")
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(RUNNER_CODE)

        status_msg = await msg.reply_text("⏳ <i>Initializing secure environment...</i>", parse_mode="HTML")
        anim_task = asyncio.create_task(_animate_py_decode(status_msg))

        stdout_raw = ""
        stderr_raw = ""

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "runner.py", original_name, "dumps",
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=35)
            stdout_raw = stdout_data.decode("utf-8", errors="replace")
            stderr_raw = stderr_data.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            stdout_raw += "\n[BOT] Subprocess force-killed after 35s timeout."

        anim_task.cancel()
        try:
            await anim_task
        except asyncio.CancelledError:
            pass

        await status_msg.edit_text("📦 <i>Packaging all layers...</i>", parse_mode="HTML")

        dump_files_list = []
        for fname in sorted(os.listdir(dump_dir)):
            fpath = os.path.join(dump_dir, fname)
            if os.path.isfile(fpath) and fname.endswith(".py"):
                dump_files_list.append(fname)

        best_fname, best_content = local_pick_best(dump_dir)

        zip_path = os.path.join(work_dir, f"AllLayers_{original_name.replace('.py','')}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in dump_files_list:
                fpath = os.path.join(dump_dir, fname)
                zf.write(fpath, arcname=fname)

        log_combined = ""
        if stdout_raw:
            log_combined += "=== STDOUT ===\n" + stdout_raw
        if stderr_raw:
            log_combined += "\n=== STDERR ===\n" + stderr_raw

        if log_combined:
            if len(log_combined) > 3500:
                log_path = os.path.join(work_dir, "runner_log.txt")
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(log_combined)
                await _send_document_with_retry(
                    update, log_path, "runner_log.txt",
                    "📋 <b>Raw Runner Log</b>"
                )
            else:
                await msg.reply_text(
                    f"📋 <b>Raw Runner Log:</b>\n<pre>{log_combined[:3500]}</pre>",
                    parse_mode="HTML"
                )

        if os.path.exists(zip_path) and os.path.getsize(zip_path) > 0:
            await _send_document_with_retry(
                update, zip_path, os.path.basename(zip_path),
                f"📦 <b>All Captured Layers</b>\n<i>Total files: {len(dump_files_list)}</i>"
            )
        else:
            await msg.reply_text("⚠️ <i>কোনো dump layer capture হয়নি।</i>", parse_mode="HTML")

        if best_fname and best_content:
            is_real = is_real_code_local(best_content)
            final_path = os.path.join(dump_dir, best_fname)
            decoded_name = f"Decoded_{original_name}"

            if is_real:
                caption = (
                    "✅ <b>Best Decoded File</b>\n\n"
                    f"📄 <i>Selected: <b>{best_fname}</b></i>\n"
                    "<i>Detected as: Real human-readable code</i>"
                )
            else:
                caption = (
                    "⚠️ <b>Best Layer (May Still Be Obfuscated)</b>\n\n"
                    f"📄 <i>Selected: <b>{best_fname}</b></i>\n"
                    "<i>পুরোপুরি decode নিশ্চিত হওয়া যায়নি।\n"
                    "ZIP-এ অন্য layers চেক করো।</i>"
                )

            await _send_document_with_retry(update, final_path, decoded_name, caption)
        else:
            await msg.reply_text(
                "❌ <i>কোনো valid decoded file পাওয়া যায়নি।\n"
                "ZIP-এ raw layers চেক করো।</i>",
                parse_mode="HTML",
                reply_markup=MAIN_MENU
            )

        if status_msg:
            try:
                await status_msg.delete()
            except Exception:
                pass

    except Exception as e:
        logger.error("python_decoder_process error user %s: %s", user_id, e)
        try:
            await msg.reply_text(
                f"❌ <b>Unexpected Error</b>\n\n<pre>{str(e)[:500]}</pre>",
                parse_mode="HTML",
                reply_markup=MAIN_MENU
            )
        except Exception:
            pass

    finally:
        processing_py_users.discard(user_id)
        if work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)

    return ConversationHandler.END


async def python_encrypt_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_verified(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "🟦 *Python Encrypt*\n\n"
        "Python code পাঠাও অথবা `.py` file attach করো।\n\n"
        "বাতিল করতে /cancel",
        parse_mode="Markdown",
    )
    return WAITING_FOR_PY_ENCRYPT


async def python_encrypt_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.document:
        content = await _download_file(update, context)
        if content is None:
            await msg.reply_text("❌ `.py` file পাঠাও।", reply_markup=MAIN_MENU)
            return ConversationHandler.END
    else:
        content = (msg.text or "").strip()
        if not content:
            await msg.reply_text("❌ কিছু পাঠাও।", reply_markup=MAIN_MENU)
            return ConversationHandler.END

    status = await msg.reply_text("⚙️ Python encrypt করছি...")
    encrypted = _python_encrypt(content)
    await status.delete()
    await _send_file(update, encrypted, "encrypted.py", "")
    return ConversationHandler.END


async def js_encrypt_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_verified(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "🟦 *JS Encrypt*\n\n"
        "JavaScript code পাঠাও অথবা `.js` file attach করো।\n\n"
        "বাতিল করতে /cancel",
        parse_mode="Markdown",
    )
    return WAITING_FOR_JS_ENCRYPT


async def js_encrypt_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.document:
        content = await _download_file(update, context)
        if content is None:
            await msg.reply_text("❌ `.js` file পাঠাও।", reply_markup=MAIN_MENU)
            return ConversationHandler.END
    else:
        content = (msg.text or "").strip()
        if not content:
            await msg.reply_text("❌ কিছু পাঠাও।", reply_markup=MAIN_MENU)
            return ConversationHandler.END

    status = await msg.reply_text("⚙️ JS encrypt করছি...")
    encrypted = _js_encrypt(content)
    await status.delete()
    await _send_file(update, encrypted, "encrypted.js", "")
    return ConversationHandler.END


async def php_decoder_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_verified(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "🟦 *PHP Decoder*\n\n"
        "Website-এর URL দাও — সব PHP file খুঁজে decode করব।\n\n"
        "বাতিল করতে /cancel",
        parse_mode="Markdown",
    )
    return WAITING_FOR_PHP_DECODE


async def php_decoder_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not (text.startswith("http://") or text.startswith("https://")):
        await update.message.reply_text("❌ সঠিক URL দাও।", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    status = await update.message.reply_text("⏳ Website স্ক্যান করছি...")
    php_links = _crawl_php_links(text)

    if not php_links:
        await status.edit_text("❌ কোনো PHP file পাওয়া যায়নি।")
        await update.message.reply_text("Menu:", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    await status.edit_text(f"⚙️ {len(php_links)}টা PHP file পাওয়া গেছে, decode করছি...")

    results = []
    for php_url in php_links:
        try:
            r = requests.get(php_url, headers=FETCH_HEADERS, timeout=15)
            content = r.content.decode("utf-8", errors="replace")
            decoded, methods = full_decode(content)
            fname = urlparse(php_url).path.split('/')[-1] or 'index.php'
            if not fname.endswith('.php'):
                fname += '.php'
            results.append((fname, decoded, methods, php_url))
        except Exception:
            continue

    await status.delete()

    if not results:
        await update.message.reply_text("❌ PHP file download করা গেল না।", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    for fname, content, methods, url in results:
        await _send_file(update, content, fname)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ বাতিল করা হয়েছে।", reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_verified(update):
        return
    user = update.effective_user
    info = (
        f"🟢 *User Info*\n\n"
        f"🆔 ID: `{user.id}`\n"
        f"👤 নাম: {user.full_name}\n"
        f"📛 Username: @{user.username or 'নেই'}\n"
        f"🌐 ভাষা: {user.language_code or 'অজানা'}\n"
        f"🤖 Bot: {'হ্যাঁ' if user.is_bot else 'না'}\n"
        f"👑 Premium: {'হ্যাঁ' if getattr(user, 'is_premium', False) else 'না'}"
    )
    await update.message.reply_text(info, parse_mode="Markdown", reply_markup=MAIN_MENU)


async def bot_info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_verified(update):
        return
    await update.message.reply_text(
        "🟢 *Bot Info*\n\n"
        "🤖 নাম: AURA X TEAM DECODER BOT\n"
        "⚙️ *Features:*\n"
        "  • 🟦 HTML Decode (URL / File / Text)\n"
        "  • 🟦 @HTMLObfuscateBot decoder (DHIRAJ9619) — FULL decode\n"
        "  • 🟢 Source Code Viewer\n"
        "  • 🟢 HTML Encrypt (XOR+Base64)\n"
        "  • 🟢 Python Decoder (Advanced RUNNER_CODE — exec/eval hook)\n"
        "  • 🟦 Python Encrypt\n"
        "  • 🟦 JS Encrypt\n"
        "  • 🟦 PHP Decoder\n"
        "  • 🟢 User Info\n\n"
        "💬 *Decode করতে পারে:*\n"
        "@HTMLObfuscateBot (FULL — password+logic সহ) • PHPKodo\n"
        "PHPCabbo • PHPKobo • Base64 • gzinflate • str\\_rot13\n"
        "HTML entities • Hex • URL encoding\n"
        "JS eval/atob • Python exec/eval/zlib multi-layer chains",
        parse_mode="Markdown", reply_markup=MAIN_MENU,
    )


async def developer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_verified(update):
        return
    await update.message.reply_text(
        "🟦 *Developer Info*\n\n"
        "👤 Name: MD.SHAHRIAR SAIF\n"
        "📱 Telegram: @DEVELOPER\\_VERSION\\_X\n\n"
        "🤖 This bot was created and developed\n"
        "by MD.SHAHRIAR SAIF.\n\n"
        "📩 যেকোনো সমস্যা বা feature request-এর জন্য\n"
        "Telegram-এ contact করো।",
        parse_mode="Markdown", reply_markup=MAIN_MENU
    )


_WEBAPP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no"/>
  <title>AURA X TEAM Bot</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--tg-theme-bg-color,#1c1c1e);color:var(--tg-theme-text-color,#fff);padding:14px 12px 20px;min-height:100vh}
    .header{text-align:center;margin-bottom:16px}
    .header h2{font-size:16px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;opacity:.85}
    .header p{font-size:12px;opacity:.45;margin-top:3px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .btn{display:flex;align-items:center;justify-content:center;gap:8px;padding:20px 10px;border:none;border-radius:16px;font-size:14px;font-weight:700;cursor:pointer;color:#fff;transition:transform .12s ease,opacity .12s ease;-webkit-tap-highlight-color:transparent;outline:none;width:100%}
    .btn:active{transform:scale(.94);opacity:.82}
    .btn-blue{background:linear-gradient(135deg,#2d88f5 0%,#1a6fd4 100%);box-shadow:0 4px 14px rgba(45,136,245,.35)}
    .btn-green{background:linear-gradient(135deg,#2dcc5c 0%,#1daa48 100%);box-shadow:0 4px 14px rgba(45,204,92,.35)}
    .icon{font-size:18px;line-height:1}
  </style>
</head>
<body>
  <div class="header"><h2>⚡ AURA X TEAM</h2><p>Select a tool below</p></div>
  <div class="grid">
    <button class="btn btn-blue"  onclick="send('🔵 Source Code')"><span class="icon">🌐</span> Source Code</button>
    <button class="btn btn-blue"  onclick="send('🔵 HTML Decode')"><span class="icon">🔒</span> HTML Decode</button>
    <button class="btn btn-green" onclick="send('🟢 Python Decoder')"><span class="icon">🐍</span> Python Decoder</button>
    <button class="btn btn-green" onclick="send('🟢 Python Encrypt')"><span class="icon">🔐</span> Python Encrypt</button>
    <button class="btn btn-blue"  onclick="send('🔵 HTML Encrypt')"><span class="icon">🔒</span> HTML Encrypt</button>
    <button class="btn btn-blue"  onclick="send('🔵 PHP Decoder')"><span class="icon">🕷️</span> PHP Decoder</button>
    <button class="btn btn-green" onclick="send('🟢 User Info')"><span class="icon">👤</span> User Info</button>
    <button class="btn btn-green" onclick="send('🟢 JS Encrypt')"><span class="icon">🔏</span> JS Encrypt</button>
    <button class="btn btn-blue"  onclick="send('🔵 Bot Info')"><span class="icon">ℹ️</span> Bot Info</button>
    <button class="btn btn-blue"  onclick="send('🔵 Developer Info')"><span class="icon">👨‍💻</span> Dev Info</button>
  </div>
  <script>
    const tg=window.Telegram.WebApp;tg.ready();tg.expand();
    function send(a){tg.sendData(a);}
  </script>
</body>
</html>"""


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.rstrip("/") == "/webapp":
            body = _WEBAPP_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    def log_message(self, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info("Web server running on port %d", port)
    server.serve_forever()


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set!")
        sys.exit(1)

    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    decode_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🔵 HTML Decode$"), html_decode_ask),
            MessageHandler(WebAppDataFilter("🔵 HTML Decode"), html_decode_ask),
        ],
        states={
            WAITING_FOR_DECODE: [
                MessageHandler(filters.Document.ALL, html_decode_process),
                MessageHandler(filters.TEXT & ~filters.COMMAND, html_decode_process),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    source_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🔵 Source Code$"), source_code_ask),
            MessageHandler(WebAppDataFilter("🔵 Source Code"), source_code_ask),
        ],
        states={
            WAITING_FOR_SOURCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, source_code_process),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    encrypt_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🔵 HTML Encrypt$"), html_encrypt_ask),
            MessageHandler(WebAppDataFilter("🔵 HTML Encrypt"), html_encrypt_ask),
        ],
        states={
            WAITING_FOR_ENCRYPT: [
                MessageHandler(filters.Document.ALL, html_encrypt_process),
                MessageHandler(filters.TEXT & ~filters.COMMAND, html_encrypt_process),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    py_decode_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🟢 Python Decoder$"), python_decoder_ask),
            MessageHandler(WebAppDataFilter("🟢 Python Decoder"), python_decoder_ask),
        ],
        states={
            WAITING_FOR_PY_DECODE: [
                MessageHandler(filters.Document.ALL, python_decoder_process),
                MessageHandler(filters.TEXT & ~filters.COMMAND, python_decoder_process),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    py_encrypt_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🟢 Python Encrypt$"), python_encrypt_ask),
            MessageHandler(WebAppDataFilter("🟢 Python Encrypt"), python_encrypt_ask),
        ],
        states={
            WAITING_FOR_PY_ENCRYPT: [
                MessageHandler(filters.Document.ALL, python_encrypt_process),
                MessageHandler(filters.TEXT & ~filters.COMMAND, python_encrypt_process),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    js_encrypt_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🟢 JS Encrypt$"), js_encrypt_ask),
            MessageHandler(WebAppDataFilter("🟢 JS Encrypt"), js_encrypt_ask),
        ],
        states={
            WAITING_FOR_JS_ENCRYPT: [
                MessageHandler(filters.Document.ALL, js_encrypt_process),
                MessageHandler(filters.TEXT & ~filters.COMMAND, js_encrypt_process),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    php_decode_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🔵 PHP Decoder$"), php_decoder_ask),
            MessageHandler(WebAppDataFilter("🔵 PHP Decoder"), php_decoder_ask),
        ],
        states={
            WAITING_FOR_PHP_DECODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, php_decoder_process),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_join$"))

    app.add_handler(decode_conv)
    app.add_handler(source_conv)
    app.add_handler(encrypt_conv)
    app.add_handler(py_decode_conv)
    app.add_handler(py_encrypt_conv)
    app.add_handler(js_encrypt_conv)
    app.add_handler(php_decode_conv)

    app.add_handler(MessageHandler(filters.Regex("^🟢 User Info$"),      user_info))
    app.add_handler(MessageHandler(filters.Regex("^🔵 Bot Info$"),       bot_info_cmd))
    app.add_handler(MessageHandler(filters.Regex("^🔵 Developer Info$"), developer_info))

    async def web_app_simple_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message is None or update.message.web_app_data is None:
            return
        if not await _require_verified(update):
            return
        data = update.message.web_app_data.data
        if data == "🟢 User Info":
            await user_info(update, context)
        elif data == "🔵 Bot Info":
            await bot_info_cmd(update, context)
        elif data == "🔵 Developer Info":
            await developer_info(update, context)

    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_simple_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, password_input), group=99)

    logger.info("✅ Bot চালু হয়েছে...")
    print("✅ Bot চালু হয়েছে...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
