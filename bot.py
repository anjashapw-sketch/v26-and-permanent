"""
================================================================
  Num Info Bot — v28.2 FINAL (FJ Real-Check Fix)
  ✅ FJ: Real get_chat_member check — no blind verify
  ✅ Join nahi kiya → verify fail
  ✅ Join kiya → verify pass
================================================================
"""

import os, sys, re, json, time, random, string, threading, queue
import asyncio
import html as html_module, csv, io
from datetime import datetime, timedelta

import requests
import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, BotCommand
)
from pymongo import MongoClient, ReturnDocument
from bson.objectid import ObjectId

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception: pass

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import logging
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("num_info_bot")

def now(): return datetime.now()
def env(k, d):
    v = os.getenv(k); return v if v else d

# =================================================================
#  AESTHETIC
# =================================================================
_SMALLCAPS = {
    'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ғ','g':'ɢ','h':'ʜ','i':'ɪ',
    'j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ',
    's':'ꜱ','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ',
    '0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹',
}
_DIV = "━━━━━━━━━━━━━━━━━━━━"
_DIV_SOFT = "— — — — — — — — — — — —"
def fancy(t): return "".join(_SMALLCAPS.get(c.lower(), c) for c in str(t))
def div(): return _DIV
def div_soft(): return _DIV_SOFT
def fancy_dt(): return now().strftime("%d-%b-%Y %I:%M %p")

# =================================================================
#  CONFIG
# =================================================================
BOT_TOKEN = env("BOT_TOKEN", "")
ADMIN_ID = int(env("ADMIN_ID", "0"))
BOT_USERNAME = env("BOT_USERNAME", "@EthicalDetails_bot")
ADMIN_USERNAME = env("ADMIN_USERNAME", "@itzanjasha")
TG2NUM_URL = env("TG2NUM_URL", "")
TG2NUM_KEY = env("TG2NUM_KEY", "")
TG2NUM_COST = int(env("TG2NUM_COST", "5"))
API_URL = env("API_URL", "")
API_KEY = env("API_KEY", "")
SEARCH_COST = int(env("SEARCH_COST", "5"))
AADHAAR_URL = env("AADHAAR_URL", "")
AADHAAR_KEY = env("AADHAAR_KEY", "")
AADHAAR_COST = int(env("AADHAAR_COST", "10"))
VEHICLE_URL = env("VEHICLE_URL", "")
VEHICLE_KEY = env("VEHICLE_KEY", "")
VEHICLE_COST = int(env("VEHICLE_COST", "10"))
WELCOME_BONUS = int(env("WELCOME_BONUS", "15"))
REFERRAL_BONUS = int(env("REFERRAL_BONUS", "10"))
DAILY_TRIES = int(env("DAILY_TRIES", "0"))
MONGO_URI = env("MONGO_URI", "")
DB_NAME = env("DB_NAME", "num2info_bot")
FORCE_CHANNELS_ENV = env("FORCE_CHANNELS", "")
CHANNEL_LINKS_ENV = env("CHANNEL_LINKS", "")
CREDITS_PER_RUPEE = int(env("CREDITS_PER_RUPEE", "1"))
MIN_PAYMENT = int(env("MIN_PAYMENT_AMOUNT", "1"))
MAX_PAYMENT = int(env("MAX_PAYMENT_AMOUNT", "50000"))
UPI_MANUAL_ID = env("UPI_MANUAL_ID", "")
UPI_MANUAL_QR = env("UPI_MANUAL_QR", "")
FAM_CREATE_URL = env("FAM_CREATE_URL", "")
FAM_VERIFY_URL = env("FAM_VERIFY_URL", "")
FAM_CHECKOUT_URL = env("FAM_CHECKOUT_STATUS_URL", "")
FAM_API_KEY = env("FAM_API_KEY", "")
FAM_REDIRECT_URL = env("FAM_REDIRECT_URL", "")
PYRO_API_ID = int(env("PYRO_API_ID", "0"))
PYRO_API_HASH = env("PYRO_API_HASH", "")
PYRO_SESSION = env("PYRO_SESSION", "")

WELCOME_EMOJIS = ["🌟","🚀","💫","🌈","🔥","⚡","🎯","💎","🌸","✨","🎉","💪","⭐","🦋","🍀"]
ORDER_LIFETIME = 300
CACHE_MAX_AGE_DAYS = 30
MSG_SAFE_LIMIT = 3800
GROUP_AUTO_DELETE_SECONDS = 3600

if not BOT_TOKEN: logger.critical("❌ BOT_TOKEN missing"); sys.exit(1)
if not MONGO_URI: logger.critical("❌ MONGO_URI missing"); sys.exit(1)

DEFAULT_QUICK_AMOUNTS = [10, 25, 50, 100, 200, 500]

SERVICE_KEYS = ["number", "username", "aadhaar", "vehicle"]
SERVICE_LABELS = {
    "number": "📞 Number To Info",
    "username": "🔒 Username To Info",
    "aadhaar": "🆔 Aadhaar To Info",
    "vehicle": "🚗 Vehicle Info",
}
SERVICE_EMOJI = {"number": "📞", "username": "🔒", "aadhaar": "🆔", "vehicle": "🚗"}

def is_url(s):
    if not s: return False
    s = str(s).strip()
    return s.startswith("http://") or s.startswith("https://")
def is_group(m): return m.chat.type in ('group', 'supergroup')
def is_private(m): return m.chat.type == 'private'

# =================================================================
#  MONGODB
# =================================================================
def connect_mongo():
    last = None
    for i in range(3):
        try:
            c = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
            c.admin.command("ping")
            logger.info(f"✅ MongoDB connected (attempt {i+1})")
            return c
        except Exception as e:
            last = e; logger.warning(f"⚠️ Mongo {i+1}: {e}"); time.sleep(3)
    logger.critical(f"❌ MongoDB failed: {last}"); sys.exit(1)

mongo_client = connect_mongo()
db = mongo_client[DB_NAME]
users_col    = db.users
payments_col = db.payments
promo_col    = db.promo_codes
settings_col = db.settings
channels_col = db.force_channels
tg_users_col = db.tg_users
groups_col   = db.groups
logs_col     = db.logs
audit_col    = db.audit_log
admins_col   = db.admins
feedback_col = db.feedback
notes_col    = db.user_notes
history_col  = db.search_history
api_stats_col= db.api_stats

# =================================================================
#  ADMIN CHECKS
# =================================================================
def is_main_admin(uid): return uid == ADMIN_ID
def is_sub_admin(uid):
    if uid == ADMIN_ID: return True
    try: return admins_col.find_one({"user_id": uid}) is not None
    except: return False
def is_admin_user(uid): return uid == ADMIN_ID or is_sub_admin(uid)

# =================================================================
#  DB INIT
# =================================================================
def init_db():
    try:
        users_col.create_index("user_id", unique=True)
        channels_col.create_index("channel_id", unique=True)
        payments_col.create_index("status")
        payments_col.create_index("user_id")
        payments_col.create_index("order_id", sparse=True)
        payments_col.create_index("utr", sparse=True)
        tg_users_col.create_index("user_id", unique=True)
        tg_users_col.create_index("username_lower", sparse=True)
        groups_col.create_index("chat_id", unique=True)
        admins_col.create_index("user_id", unique=True)
        notes_col.create_index("user_id")
        history_col.create_index([("user_id", 1), ("at", -1)])
        audit_col.create_index([("at", -1)])
    except Exception as e: logger.warning(f"⚠️ Index: {e}")
    try: payments_col.drop_index("utr_1")
    except: pass
    try:
        payments_col.create_index("utr", unique=True,
            partialFilterExpression={"utr": {"$type": "string"}},
            name="utr_unique_partial")
    except: pass

    defaults = {
        "credits_per_rupee": CREDITS_PER_RUPEE,
        "search_cost": SEARCH_COST, "aadhaar_cost": AADHAAR_COST,
        "tg2num_cost": TG2NUM_COST, "vehicle_cost": VEHICLE_COST,
        "welcome_bonus": WELCOME_BONUS, "referral_bonus": REFERRAL_BONUS,
        "referral_enabled": 1, "daily_tries": DAILY_TRIES,
        "gateway_enabled": 0,
        "gateway_create_url": FAM_CREATE_URL,
        "gateway_checkout_status_url": FAM_CHECKOUT_URL,
        "gateway_api_key": FAM_API_KEY,
        "gateway_redirect_url": FAM_REDIRECT_URL,
        "upi_manual_id": UPI_MANUAL_ID, "upi_manual_qr": UPI_MANUAL_QR,
        "upi_manual_enabled": 1, "force_enabled": "1", "maintenance_mode": 0,
        "min_payment": MIN_PAYMENT, "max_payment": MAX_PAYMENT,
        "group_enabled": 1, "group_auto_delete": 1, "group_welcome": "",
        "group_auto_delete_seconds": GROUP_AUTO_DELETE_SECONDS,
        "broadcast_pin": 0, "broadcast_forward": 0,
        "welcome_emoji": "", "powered_by": "", "about_text": "",
        "api_url_env": API_URL, "api_key_env": API_KEY,
        "tg2num_url_env": TG2NUM_URL, "tg2num_key_env": TG2NUM_KEY,
        "aadhaar_url_env": AADHAAR_URL, "aadhaar_key_env": AADHAAR_KEY,
        "vehicle_url_env": VEHICLE_URL, "vehicle_key_env": VEHICLE_KEY,
        "support_link": "", "fj_custom_msg": "",
        "service_number_enabled": 1, "service_username_enabled": 1,
        "service_aadhaar_enabled": 1, "service_vehicle_enabled": 1,
        "service_number_msg": "", "service_username_msg": "",
        "service_aadhaar_msg": "", "service_vehicle_msg": "",
        "output_mode": "formatted",
        "watermark_text": "", "rate_limit_seconds": 0, "auto_refund_on_fail": 1,
        "banned_words": "", "maintenance_custom_msg": "",
        "cooldown_number": 0, "cooldown_username": 0,
        "cooldown_aadhaar": 0, "cooldown_vehicle": 0,
        "quick_amounts": ",".join(str(x) for x in DEFAULT_QUICK_AMOUNTS),
        "buy_note": "",
        "auto_backup_enabled": 0, "auto_backup_hour": 3,
        "auto_backup_last_run": "",
        "admin_rate_limit_sec": 0,
        "large_payment_alert": 500,
    }
    for k, v in defaults.items():
        try:
            if not settings_col.find_one({"key": k}):
                settings_col.insert_one({"key": k, "value": v})
        except: pass

    if channels_col.count_documents({}) == 0 and FORCE_CHANNELS_ENV:
        ids = [int(c.strip()) for c in FORCE_CHANNELS_ENV.split(",") if c.strip()]
        links = [l.strip() for l in CHANNEL_LINKS_ENV.split(",") if l.strip()] if CHANNEL_LINKS_ENV else []
        for i, cid in enumerate(ids):
            link = links[i] if i < len(links) else f"https://t.me/joinchat/{cid}"
            try: channels_col.insert_one({"channel_id": cid, "channel_link": link, "enabled": 1})
            except: pass
    logger.info("✅ DB initialized")

def get_setting(k, d=None):
    try:
        doc = settings_col.find_one({"key": k})
        return doc["value"] if doc else d
    except: return d

def set_setting(k, v):
    try: settings_col.update_one({"key": k}, {"$set": {"value": v}}, upsert=True)
    except: pass

def log_action(aid, action, details=None):
    try: logs_col.insert_one({"admin_id": aid, "action": action,
        "details": details or "", "at": now()})
    except: pass

def audit(aid, action, target=None, details=None):
    try:
        audit_col.insert_one({"admin_id": aid, "action": action,
            "target": target, "details": details or "", "at": now()})
    except: pass

def audit_count():
    try: return audit_col.count_documents({})
    except: return 0

def get_recent_audit(limit=20):
    try: return list(audit_col.find().sort("at", -1).limit(limit))
    except: return []

# =================================================================
#  ADMIN ACTION RATE LIMIT
# =================================================================
_admin_action_log = {}
def admin_rate_ok(aid, action="default"):
    if is_main_admin(aid): return True
    limit = int(get_setting("admin_rate_limit_sec", 0))
    if limit <= 0: return True
    ts = time.time()
    arr = _admin_action_log.get(aid, [])
    arr = [x for x in arr if ts - x < limit]
    if arr: return False
    arr.append(ts); _admin_action_log[aid] = arr
    return True

# =================================================================
#  SERVICE TOGGLE
# =================================================================
def is_service_enabled(svc):
    return int(get_setting(f"service_{svc}_enabled", 1)) == 1

def toggle_service(svc):
    cur = int(get_setting(f"service_{svc}_enabled", 1))
    new = 0 if cur else 1
    set_setting(f"service_{svc}_enabled", new)
    return new == 1

def get_service_disabled_msg(svc):
    custom = (get_setting(f"service_{svc}_msg", "") or "").strip()
    if custom: return custom
    label = SERVICE_LABELS.get(svc, svc)
    emoji = SERVICE_EMOJI.get(svc, "🚧")
    return (f"{emoji} <b>{fancy('temporarily unavailable')}</b>\n{div()}\n\n"
            f"📛 ꜱᴇʀᴠɪᴄᴇ: <b>{label}</b>\n"
            f"⚙️ ꜱᴛᴀᴛᴜꜱ: <b>ᴄᴏᴍɪɴɢ ꜱᴏᴏɴ / ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ</b>\n\n"
            f"ᴋʀɪᴘʏᴀ ᴛʜᴏᴅɪ ᴅᴇʀ ʙᴀᴀᴅ ᴛʀʏ ᴋᴀʀᴇɪɴ.\n\n"
            f"{div_soft()}\n📞 ᴄᴏɴᴛᴀᴄᴛ: {ADMIN_USERNAME}")

def ensure_service(svc, uid, cid, reply_to=None, force_admin=False):
    if is_service_enabled(svc): return True
    if is_admin_user(uid):
        if force_admin: return True
        st = states.get(uid, {})
        if st.get('force_svc') == svc:
            st.pop('force_svc', None)
            states[uid] = st
            return True
        kb = InlineKeyboardMarkup(row_width=1)
        kb.row(InlineKeyboardButton("⚠️ Continue Anyway", callback_data=f"svc_force_{svc}"),
               InlineKeyboardButton("🔙 Cancel", callback_data="close"))
        try:
            bot.send_message(cid,
                f"⚠️ <b>Service is DISABLED</b>\n{div()}\n\n"
                f"📛 ꜱᴇʀᴠɪᴄᴇ: <b>{SERVICE_LABELS.get(svc, svc)}</b>\n"
                f"⚙️ ꜱᴛᴀᴛᴜꜱ: <b>🔴 OFF</b>\n\n"
                f"👤 ᴀᴅᴍɪɴ, <b>Continue Anyway</b> ᴋᴀʀ ꜱᴀᴋᴛᴇ ʜᴀɪɴ.",
                parse_mode='HTML', reply_markup=kb, reply_to_message_id=reply_to)
        except: pass
        return False
    try:
        bot.send_message(cid, get_service_disabled_msg(svc),
            parse_mode='HTML', reply_to_message_id=reply_to)
    except: pass
    return False

# =================================================================
#  RATE LIMIT
# =================================================================
_last_search_time = {}
def check_rate_limit(uid, svc):
    if is_admin_user(uid): return True, 0
    gl = int(get_setting("rate_limit_seconds", 0))
    if gl > 0:
        now_ts = time.time()
        last = _last_search_time.get(uid, {}).get("_global", 0)
        wait = gl - (now_ts - last)
        if wait > 0: return False, int(wait)
    cd = int(get_setting(f"cooldown_{svc}", 0))
    if cd > 0:
        now_ts = time.time()
        last = _last_search_time.get(uid, {}).get(svc, 0)
        wait = cd - (now_ts - last)
        if wait > 0: return False, int(wait)
    return True, 0

def mark_search_time(uid, svc):
    try:
        if uid not in _last_search_time: _last_search_time[uid] = {}
        _last_search_time[uid][svc] = time.time()
        _last_search_time[uid]["_global"] = time.time()
    except: pass

def apply_banned_words(text):
    words = get_setting("banned_words", "") or ""
    if not words.strip(): return text
    parts = re.split(r'(<[^>]+>)', text)
    out = []
    for part in parts:
        if part.startswith('<') and part.endswith('>'):
            out.append(part); continue
        for w in words.split(","):
            w = w.strip()
            if not w: continue
            try: part = re.sub(re.escape(w), "***", part, flags=re.IGNORECASE)
            except: pass
        out.append(part)
    return "".join(out)

# =================================================================
#  USER
# =================================================================
def today_str(): return now().strftime("%Y-%m-%d")

def get_or_create_user(uid):
    try:
        u = users_col.find_one({"user_id": uid})
        if u: return u
        wb = max(0, int(get_setting("welcome_bonus", WELCOME_BONUS)))
        doc = {"user_id": uid, "credits": wb, "total_referrals": 0,
            "bonus_earned": 0, "banned": 0, "shadow_banned": 0, "searches": 0,
            "tries_used": 0, "tries_date": today_str(),
            "joined_at": now(), "last_seen": now(),
            "total_spent": 0, "total_purchased": 0}
        users_col.update_one({"user_id": uid}, {"$setOnInsert": doc}, upsert=True)
        return users_col.find_one({"user_id": uid}) or doc
    except: return {"user_id": uid, "credits": 0, "banned": 0}

def get_credits(uid): return get_or_create_user(uid).get("credits", 0)

def add_credits(uid, amt):
    try:
        get_or_create_user(uid)
        users_col.update_one({"user_id": uid}, {"$inc": {"credits": amt}})
    except: pass

def deduct_credits(uid, amt):
    try:
        r = users_col.find_one_and_update({"user_id": uid, "credits": {"$gte": amt}},
            {"$inc": {"credits": -amt}}, return_document=ReturnDocument.AFTER)
        return r is not None
    except: return False

def incr_searches(uid):
    try: users_col.update_one({"user_id": uid}, {"$inc": {"searches": 1}})
    except: pass

def log_search_history(uid, svc, query, success=True):
    try:
        history_col.insert_one({"user_id": uid, "service": svc, "query": str(query)[:100],
            "success": success, "at": now()})
        cnt = history_col.count_documents({"user_id": uid})
        if cnt > 50:
            old = list(history_col.find({"user_id": uid}).sort("at", 1).limit(cnt - 50))
            for o in old: history_col.delete_one({"_id": o["_id"]})
    except: pass

def get_tries_remaining(uid):
    if is_admin_user(uid): return "unlimited"
    limit = int(get_setting("daily_tries", DAILY_TRIES))
    if limit <= 0: return "unlimited"
    try:
        u = get_or_create_user(uid)
        used = int(u.get("tries_used", 0))
        if u.get("tries_date") != today_str():
            users_col.update_one({"user_id": uid},
                {"$set": {"tries_used": 0, "tries_date": today_str()}})
            used = 0
        return max(0, limit - used)
    except: return limit

def consume_try(uid):
    if is_admin_user(uid): return True, False
    limit = int(get_setting("daily_tries", DAILY_TRIES))
    if limit <= 0: return True, False
    try:
        today = today_str()
        users_col.update_one({"user_id": uid, "tries_date": {"$ne": today}},
            {"$set": {"tries_used": 0, "tries_date": today}})
        r = users_col.find_one_and_update({"user_id": uid, "tries_used": {"$lt": limit}},
            {"$inc": {"tries_used": 1}}, return_document=ReturnDocument.AFTER)
        return (r is not None), (r is not None)
    except: return True, False

def refund_try(uid, consumed):
    if not consumed: return
    if is_admin_user(uid): return
    try:
        u = users_col.find_one({"user_id": uid})
        cur = int(u.get("tries_used", 0)) if u else 0
        if cur <= 0: return
        users_col.update_one({"user_id": uid, "tries_used": {"$gt": 0}},
            {"$inc": {"tries_used": -1}})
    except: pass

def tries_display(uid):
    r = get_tries_remaining(uid)
    if r == "unlimited": return f"{fancy('unlimited')} ♾️"
    return str(r)

def add_referral_bonus(rid):
    try:
        if is_banned(rid): return
        b = max(0, int(get_setting("referral_bonus", REFERRAL_BONUS)))
        users_col.update_one({"user_id": rid},
            {"$inc": {"credits": b, "total_referrals": 1, "bonus_earned": b}})
    except: pass

def is_banned(uid):
    try:
        u = users_col.find_one({"user_id": uid})
        return u and u.get("banned", 0) == 1
    except: return False

def ban_user(uid):
    try: users_col.update_one({"user_id": uid}, {"$set": {"banned": 1}}, upsert=True)
    except: pass
def unban_user(uid):
    try: users_col.update_one({"user_id": uid}, {"$set": {"banned": 0}}, upsert=True)
    except: pass
def shadow_ban_user(uid):
    try: users_col.update_one({"user_id": uid}, {"$set": {"shadow_banned": 1}}, upsert=True)
    except: pass

def all_users():
    try: return [u["user_id"] for u in users_col.find({"banned": 0}, {"user_id": 1})]
    except: return []

def active_users_24h():
    try:
        c = now() - timedelta(hours=24)
        return [u["user_id"] for u in users_col.find(
            {"banned": 0, "last_seen": {"$gte": c}}, {"user_id": 1})]
    except: return []

def paying_users():
    try: return payments_col.distinct("user_id", {"status": "approved"})
    except: return []

def non_paying_users():
    try:
        paid = set(paying_users())
        return [u for u in all_users() if u not in paid]
    except: return []

def user_stats(uid):
    u = get_or_create_user(uid)
    return u.get("total_referrals",0), u.get("bonus_earned",0), u.get("searches",0)

def user_purchase_stats(uid):
    try:
        pays = list(payments_col.find({"user_id": uid, "status": "approved"}))
        total_amt = sum(p.get("amount", 0) for p in pays)
        total_cr = sum(p.get("credits", 0) for p in pays)
        return total_amt, total_cr, len(pays)
    except: return 0, 0, 0

def total_users():
    try: return users_col.count_documents({"banned": 0})
    except: return 0

def total_searches():
    try:
        a = list(users_col.aggregate([{"$group": {"_id": None, "t": {"$sum": "$searches"}}}]))
        return a[0]["t"] if a else 0
    except: return 0

def new_users_24h():
    try:
        c = now() - timedelta(hours=24)
        return users_col.count_documents({"joined_at": {"$gte": c}})
    except: return 0

def searches_1h():
    try:
        c = now() - timedelta(hours=1)
        return history_col.count_documents({"at": {"$gte": c}})
    except: return 0

def failed_searches_24h():
    try:
        c = now() - timedelta(hours=24)
        return history_col.count_documents({"at": {"$gte": c}, "success": False})
    except: return 0

def total_searches_24h():
    try:
        c = now() - timedelta(hours=24)
        return history_col.count_documents({"at": {"$gte": c}})
    except: return 0

def revenue_today():
    try:
        start = now().replace(hour=0, minute=0, second=0, microsecond=0)
        agg = list(payments_col.aggregate([
            {"$match": {"status": "approved", "approved_at": {"$gte": start}}},
            {"$group": {"_id": None, "t": {"$sum": "$amount"}}}]))
        return agg[0]["t"] if agg else 0
    except: return 0

def revenue_yesterday():
    try:
        today_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
        y_start = today_start - timedelta(days=1)
        agg = list(payments_col.aggregate([
            {"$match": {"status": "approved",
                        "approved_at": {"$gte": y_start, "$lt": today_start}}},
            {"$group": {"_id": None, "t": {"$sum": "$amount"}}}]))
        return agg[0]["t"] if agg else 0
    except: return 0

def conversion_rate():
    try:
        total = users_col.count_documents({"banned": 0})
        paid = len(paying_users())
        if total <= 0: return 0.0
        return round((paid / total) * 100, 1)
    except: return 0.0

def top_services_24h(limit=5):
    try:
        c = now() - timedelta(hours=24)
        agg = list(history_col.aggregate([
            {"$match": {"at": {"$gte": c}}},
            {"$group": {"_id": "$service", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}]))
        return [(a["_id"], a["count"]) for a in agg]
    except: return []

def upd_last_seen(uid):
    try: users_col.update_one({"user_id": uid}, {"$set": {"last_seen": now()}})
    except: pass

def export_csv():
    try:
        us = list(users_col.find({}, {"user_id":1,"credits":1,"searches":1,
                                       "total_referrals":1,"banned":1,"joined_at":1}))
        o = io.StringIO(); w = csv.writer(o)
        w.writerow(["User ID","Credits","Searches","Referrals","Banned","Joined"])
        for u in us:
            w.writerow([u.get("user_id"),u.get("credits",0),u.get("searches",0),
                u.get("total_referrals",0),u.get("banned",0),
                u.get("joined_at","").strftime("%Y-%m-%d") if u.get("joined_at") else ""])
        return o.getvalue()
    except: return None

# =================================================================
#  GROUPS / CACHE
# =================================================================
def register_group(chat_id, title, username=None):
    try:
        groups_col.update_one({"chat_id": chat_id},
            {"$set": {"title": title, "username": username, "last_seen": now()},
             "$setOnInsert": {"added_at": now(), "enabled": 1}}, upsert=True)
    except: pass

def remove_group(chat_id):
    try: groups_col.delete_one({"chat_id": chat_id})
    except: pass

def all_groups():
    try: return list(groups_col.find().sort("added_at", -1))
    except: return []

def group_count():
    try: return groups_col.count_documents({})
    except: return 0

def cache_tg_user(user):
    try:
        if not user or getattr(user, 'is_bot', False): return
        doc = {"user_id": user.id, "username": getattr(user, 'username', None),
            "first_name": getattr(user, 'first_name', '') or "",
            "last_name": getattr(user, 'last_name', '') or "",
            "full_name": f"{getattr(user,'first_name','') or ''} {getattr(user,'last_name','') or ''}".strip(),
            "cached_at": now(), "last_seen": now()}
        upd = {"$set": doc}
        if doc.get("username"): upd["$set"]["username_lower"] = doc["username"].lower()
        tg_users_col.update_one({"user_id": user.id}, upd, upsert=True)
    except: pass

def cache_dict(d):
    try:
        if not d or not d.get("user_id"): return
        doc = {"user_id": d["user_id"]}
        for k in ("username","first_name","last_name","full_name","bio",
                  "is_bot","is_premium","is_verified"):
            if d.get(k) is not None: doc[k] = d[k]
        doc["cached_at"] = now(); doc["last_seen"] = now()
        upd = {"$set": doc}
        if d.get("username"): upd["$set"]["username_lower"] = d["username"].lower()
        else: upd["$unset"] = {"username_lower": ""}
        tg_users_col.update_one({"user_id": d["user_id"]}, upd, upsert=True)
    except: pass

def get_cached_user(uid=None, username=None):
    try:
        q = {}
        if uid is not None: q["user_id"] = uid
        elif username: q["username_lower"] = username.lower()
        else: return None
        u = tg_users_col.find_one(q)
        if not u: return None
        ca = u.get("cached_at")
        if ca and (now() - ca).days > CACHE_MAX_AGE_DAYS: return None
        return u
    except: return None

def clean_old_cache():
    try:
        cutoff = now() - timedelta(days=CACHE_MAX_AGE_DAYS)
        r = tg_users_col.delete_many({"cached_at": {"$lt": cutoff}})
        return r.deleted_count
    except: return 0

# =================================================================
#  PYROGRAM
# =================================================================
pyro = None; _pyro_loop = None; _pyro_ready = False; _pyro_me = None; _pyro_error = None

def init_pyrogram():
    global _pyro_loop, _pyro_ready, _pyro_error
    try: asyncio.set_event_loop(asyncio.new_event_loop())
    except: pass
    if not PYRO_SESSION or not PYRO_API_ID or not PYRO_API_HASH:
        _pyro_error = "no_session"; return
    try: from pyrogram import Client
    except ImportError: _pyro_error = "no_lib"; return
    _pyro_loop = asyncio.new_event_loop()
    def _runner():
        asyncio.set_event_loop(_pyro_loop)
        try: _pyro_loop.run_until_complete(_boot())
        except Exception as e:
            logger.error(f"❌ Pyro: {e}"); _pyro_error = f"{type(e).__name__}: {e}"
    threading.Thread(target=_runner, daemon=True, name="PyroRunner").start()
    for _ in range(60):
        if _pyro_ready: break
        time.sleep(0.5)
    if not _pyro_ready: logger.warning(f"⚠️ Pyro not ready ({_pyro_error})")

async def _boot():
    global pyro, _pyro_ready, _pyro_me, _pyro_error
    try:
        from pyrogram import Client
        from pyrogram.errors import AuthKeyUnregistered, AuthKeyDuplicated
    except ImportError as e: _pyro_error = f"import: {e}"; return
    try:
        pyro = Client("pyro_session", api_id=PYRO_API_ID, api_hash=PYRO_API_HASH,
            session_string=PYRO_SESSION, in_memory=True, no_updates=True)
        await pyro.start(); await asyncio.sleep(0.3)
        _pyro_me = await pyro.get_me()
        _pyro_ready = True
        logger.info(f"✅ Pyrogram: @{_pyro_me.username or _pyro_me.id}")
    except AuthKeyUnregistered: _pyro_error = "auth_key_unregistered"; return
    except AuthKeyDuplicated: _pyro_error = "auth_key_duplicated"; return
    except Exception as e: _pyro_error = f"{type(e).__name__}: {e}"; return
    while True:
        try: await asyncio.sleep(3600)
        except asyncio.CancelledError: break

def pyro_resolve_username(username, timeout=20):
    if not _pyro_ready or not pyro or not _pyro_loop: return None
    try:
        u = username.strip().lstrip("@")
        if not u: return None
        fut = asyncio.run_coroutine_threadsafe(_resolve_u_async(u), _pyro_loop)
        return fut.result(timeout=timeout)
    except Exception as e: logger.error(f"resolve_u: {e}"); return None

def pyro_resolve_id(uid, timeout=15):
    if not _pyro_ready or not pyro or not _pyro_loop: return None
    try:
        fut = asyncio.run_coroutine_threadsafe(_resolve_id_async(int(uid)), _pyro_loop)
        return fut.result(timeout=timeout)
    except Exception as e: logger.error(f"resolve_id: {e}"); return None

async def _resolve_u_async(username):
    try:
        from pyrogram.errors import UsernameNotOccupied, UsernameInvalid, FloodWait
        user = await pyro.get_users(username); return await _u_to_info(user)
    except UsernameNotOccupied: return {"error": "not_found"}
    except UsernameInvalid: return {"error": "invalid"}
    except FloodWait as e: return {"error": f"flood_{e.value}s"}
    except Exception as e: logger.error(f"_resolve_u: {e}"); return None

async def _resolve_id_async(uid):
    try:
        from pyrogram.errors import PeerIdInvalid, FloodWait
        user = await pyro.get_users(uid); return await _u_to_info(user)
    except PeerIdInvalid: return {"error": "peer_id_invalid"}
    except FloodWait as e: return {"error": f"flood_{e.value}s"}
    except Exception as e: logger.error(f"_resolve_id: {e}"); return None

async def _u_to_info(user):
    info = {"user_id": user.id, "username": user.username,
        "first_name": getattr(user, 'first_name', '') or "",
        "last_name": getattr(user, 'last_name', '') or "",
        "is_bot": getattr(user, 'is_bot', False),
        "is_premium": getattr(user, 'is_premium', False),
        "is_verified": getattr(user, 'is_verified', False), "source": "mtproto"}
    info["full_name"] = f"{info['first_name']} {info['last_name']}".strip()
    return info

# =================================================================
#  API QUERIES
# =================================================================
def record_api_call(svc, success):
    try:
        api_stats_col.insert_one({"service": svc, "success": success, "at": now()})
        cnt = api_stats_col.count_documents({"service": svc})
        if cnt > 500:
            old = list(api_stats_col.find({"service": svc}).sort("at", 1).limit(cnt - 500))
            for o in old: api_stats_col.delete_one({"_id": o["_id"]})
    except: pass

def api_success_rate(svc, last_n=100):
    try:
        arr = list(api_stats_col.find({"service": svc}).sort("at", -1).limit(last_n))
        if not arr: return None
        ok = sum(1 for a in arr if a.get("success"))
        return round((ok / len(arr)) * 100, 1)
    except: return None

def query_number(phone):
    api_url = get_setting("api_url_env", API_URL)
    api_key = get_setting("api_key_env", API_KEY)
    if not api_url: return False, None, "API URL not configured"
    try:
        base_url = api_url.rstrip('/')
        params = {"number": phone}
        if api_key: params["key"] = api_key
        r = requests.get(base_url + "/", params=params, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            record_api_call("number", False); return False, None, f"HTTP {r.status_code}"
        try: data = r.json()
        except:
            record_api_call("number", False); return False, None, "Invalid JSON"
        if not data.get("success"):
            record_api_call("number", False)
            return False, None, data.get("message", "API error")
        if not data.get("result") and not data.get("data"):
            record_api_call("number", False); return False, None, "No data"
        record_api_call("number", True)
        return True, data, None
    except requests.exceptions.Timeout:
        record_api_call("number", False); return False, None, "Timeout"
    except Exception as e:
        record_api_call("number", False); return False, None, str(e)

def query_aadhaar(aadhaar):
    a_url = get_setting("aadhaar_url_env", AADHAAR_URL)
    a_key = get_setting("aadhaar_key_env", AADHAAR_KEY)
    if not a_url: return False, None, "Aadhaar URL not configured"
    try:
        base = str(a_url).strip()
        a = re.sub(r'\D', '', str(aadhaar))
        if base.endswith('=') or base.endswith('?q=') or base.endswith('?aadhaar='):
            url = f"{base}{a}"; params = {}
        else: url = base; params = {"q": a}
        if a_key: params["key"] = a_key
        r = requests.get(url, params=params or None, timeout=45,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            record_api_call("aadhaar", False); return False, None, f"HTTP {r.status_code}"
        try: data = r.json()
        except:
            record_api_call("aadhaar", False); return False, None, "Invalid JSON"
        if isinstance(data, dict):
            if data.get("success") is False:
                record_api_call("aadhaar", False)
                return False, None, data.get("message", "Not found")
            if data.get("status") in ("error","fail","failed"):
                record_api_call("aadhaar", False)
                return False, None, data.get("message", "Not found")
            if data.get("error"):
                record_api_call("aadhaar", False)
                return False, None, str(data.get("error"))
        record_api_call("aadhaar", True)
        return True, data, None
    except requests.exceptions.Timeout:
        record_api_call("aadhaar", False); return False, None, "Timeout"
    except Exception as e:
        record_api_call("aadhaar", False); return False, None, str(e)

def query_vehicle(vehicle):
    v_url = get_setting("vehicle_url_env", VEHICLE_URL)
    v_key = get_setting("vehicle_key_env", VEHICLE_KEY)
    if not v_url: return False, None, "Vehicle URL not configured"
    try:
        base = str(v_url).strip()
        v = re.sub(r'[\s\-]', '', str(vehicle)).upper()
        if base.endswith('=') or base.endswith('?vehicle='):
            url = f"{base}{requests.utils.quote(v)}"; params = {}
        else: url = base; params = {"vehicle": v}
        if v_key: params["key"] = v_key
        r = requests.get(url, params=params or None, timeout=45,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            record_api_call("vehicle", False); return False, None, f"HTTP {r.status_code}"
        try: data = r.json()
        except:
            record_api_call("vehicle", False); return False, None, "Invalid JSON"
        if isinstance(data, dict):
            if data.get("success") is False:
                record_api_call("vehicle", False)
                return False, None, data.get("message", "Not found")
            if data.get("status") in ("error","fail","failed"):
                record_api_call("vehicle", False)
                return False, None, data.get("message", "Not found")
            if data.get("error"):
                record_api_call("vehicle", False)
                return False, None, str(data.get("error"))
        record_api_call("vehicle", True)
        return True, data, None
    except requests.exceptions.Timeout:
        record_api_call("vehicle", False); return False, None, "Timeout"
    except Exception as e:
        record_api_call("vehicle", False); return False, None, str(e)

def query_tg2num_id(tg_id):
    tg_url = get_setting("tg2num_url_env", TG2NUM_URL)
    tg_key = get_setting("tg2num_key_env", TG2NUM_KEY)
    if not tg_url: return False, None, "TG2NUM_URL not configured"
    try:
        base = tg_url.rstrip("/")
        params = {"id": str(tg_id).strip()}
        if tg_key: params["key"] = tg_key
        r = requests.get(base + "/", params=params, timeout=30)
        if r.status_code != 200:
            record_api_call("username", False); return False, None, f"HTTP {r.status_code}"
        try: data = r.json()
        except:
            record_api_call("username", False); return False, None, "Invalid JSON"
        if not data.get("success"):
            record_api_call("username", False)
            return False, None, data.get("message", "API error")
        result = data.get("result")
        if isinstance(result, list) and result: result = result[0]
        if not isinstance(result, dict) or not result.get("number"):
            record_api_call("username", False); return False, None, "No number"
        record_api_call("username", True)
        return True, result, None
    except requests.exceptions.Timeout:
        record_api_call("username", False); return False, None, "Timeout"
    except Exception as e:
        record_api_call("username", False); return False, None, str(e)

# =================================================================
#  RESOLVER
# =================================================================
def resolve_any(query):
    q = str(query).strip()
    if "t.me/" in q or "telegram.me/" in q:
        part = q.split("t.me/")[-1] if "t.me/" in q else q.split("telegram.me/")[-1]
        part = part.split("?")[0].strip("/")
        if "/" in part: part = part.split("/")[0]
        q = part
    q = q.lstrip("@")
    if not q: return None, None
    if q.isdigit():
        uid = int(q)
        u = get_cached_user(uid=uid)
        if u: u["source"] = "cache"; return u, "cache"
        if _pyro_ready:
            r = pyro_resolve_id(uid, timeout=15)
            if r and r.get("user_id"): cache_dict(r); return r, "mtproto"
        try:
            chat = bot.get_chat(uid)
            info = {"user_id": chat.id, "username": getattr(chat, 'username', None),
                "first_name": getattr(chat, 'first_name', None),
                "last_name": getattr(chat, 'last_name', None),
                "full_name": f"{getattr(chat,'first_name','') or ''} {getattr(chat,'last_name','') or ''}".strip(),
                "source": "telegram_api"}
            cache_dict(info); return info, "telegram_api"
        except: pass
        return None, None
    u = get_cached_user(username=q)
    if u: u["source"] = "cache"; return u, "cache"
    if _pyro_ready:
        r = pyro_resolve_username(q, timeout=20)
        if r and r.get("user_id"): cache_dict(r); return r, "mtproto"
    try:
        chat = bot.get_chat(f"@{q}")
        info = {"user_id": chat.id, "username": getattr(chat, 'username', None),
            "first_name": getattr(chat, 'first_name', None),
            "last_name": getattr(chat, 'last_name', None),
            "full_name": f"{getattr(chat,'first_name','') or ''} {getattr(chat,'last_name','') or ''}".strip(),
            "source": "telegram_api"}
        cache_dict(info); return info, "telegram_api"
    except: pass
    return None, None

# =================================================================
#  PAYMENTS
# =================================================================
def create_payment(uid, cid, amount, credits, pay_mode, screenshot_id=None,
                    order_id=None, payment_link=None, gateway_raw=None):
    doc = {"user_id": uid, "chat_id": cid, "amount": amount, "credits": credits,
        "pay_mode": pay_mode, "screenshot_id": screenshot_id,
        "order_id": order_id, "payment_link": payment_link,
        "status": "pending", "created_at": now(),
        "approved_at": None, "approved_by": None,
        "reject_reason": None, "gateway_response": gateway_raw, "refunded": 0}
    try: return str(payments_col.insert_one(doc).inserted_id)
    except: return None

def get_payment(pid):
    try: return payments_col.find_one({"_id": ObjectId(pid)})
    except: return None

def get_pending():
    try: return list(payments_col.find({"status": "pending"}).sort("created_at", 1))
    except: return []

def get_user_payments(uid, limit=10):
    try: return list(payments_col.find({"user_id": uid}).sort("created_at", -1).limit(limit))
    except: return []

def approve_atomic(pid, aid):
    try: oid = ObjectId(pid)
    except: return False, None
    try:
        r = payments_col.find_one_and_update({"_id": oid, "status": "pending"},
            {"$set": {"status": "approved", "approved_at": now(), "approved_by": aid}},
            return_document=ReturnDocument.AFTER)
        if not r: return False, payments_col.find_one({"_id": oid})
        return True, r
    except: return False, None

def reject_atomic(pid, aid, reason="Rejected"):
    try: oid = ObjectId(pid)
    except: return False, None
    try:
        r = payments_col.find_one_and_update({"_id": oid, "status": "pending"},
            {"$set": {"status": "rejected", "rejected_at": now(),
                      "approved_by": aid, "reject_reason": reason}},
            return_document=ReturnDocument.AFTER)
        if not r: return False, payments_col.find_one({"_id": oid})
        return True, r
    except: return False, None

def refund_payment(pid, aid):
    try: oid = ObjectId(pid)
    except: return False, None, "Invalid ID"
    try:
        p = payments_col.find_one({"_id": oid})
        if not p: return False, None, "Not found"
        if p.get("status") != "approved":
            return False, p, "Only approved can be refunded"
        if p.get("refunded", 0) == 1:
            return False, p, "Already refunded"
        uid = p["user_id"]; cr = p.get("credits", 0)
        u = users_col.find_one({"user_id": uid}) or {}
        have = int(u.get("credits", 0))
        deduct = min(have, cr)
        users_col.update_one({"user_id": uid}, {"$inc": {"credits": -deduct}})
        users_col.update_one({"user_id": uid},
            {"$inc": {"total_spent": -p.get("amount", 0), "total_purchased": -cr}})
        payments_col.update_one({"_id": oid},
            {"$set": {"status": "refunded", "refunded": 1,
                      "refunded_at": now(), "refunded_by": aid,
                      "refunded_credits": deduct}})
        return True, p, f"Refunded {deduct}cr (had {have})"
    except Exception as e:
        return False, None, str(e)

def search_payments(query, limit=20):
    try:
        q = str(query).strip()
        conds = []
        if q.isdigit(): conds.append({"user_id": int(q)})
        try: conds.append({"_id": ObjectId(q)})
        except: pass
        conds.append({"utr": q})
        conds.append({"order_id": q})
        conds.append({"utr": {"$regex": re.escape(q), "$options": "i"}})
        conds.append({"order_id": {"$regex": re.escape(q), "$options": "i"}})
        return list(payments_col.find({"$or": conds}).sort("created_at", -1).limit(limit))
    except: return []

def pay_stats():
    try:
        p = payments_col.count_documents({"status": "pending"})
        a = payments_col.count_documents({"status": "approved"})
        r = payments_col.count_documents({"status": "rejected"})
        rf = payments_col.count_documents({"status": "refunded"})
        agg = list(payments_col.aggregate([{"$match": {"status": "approved"}},
            {"$group": {"_id": None, "t": {"$sum": "$amount"}}}]))
        rev = agg[0]["t"] if agg else 0
        return p, a, r, rev, rf
    except: return 0, 0, 0, 0, 0

def total_credits_sold():
    try:
        agg = list(payments_col.aggregate([{"$match": {"status": "approved"}},
            {"$group": {"_id": None, "t": {"$sum": "$credits"}}}]))
        return agg[0]["t"] if agg else 0
    except: return 0

def revenue_24h():
    try:
        c = now() - timedelta(hours=24)
        agg = list(payments_col.aggregate([
            {"$match": {"status": "approved", "approved_at": {"$gte": c}}},
            {"$group": {"_id": None, "t": {"$sum": "$amount"}}}]))
        return agg[0]["t"] if agg else 0
    except: return 0

def revenue_7d():
    try:
        c = now() - timedelta(days=7)
        agg = list(payments_col.aggregate([
            {"$match": {"status": "approved", "approved_at": {"$gte": c}}},
            {"$group": {"_id": None, "t": {"$sum": "$amount"}}}]))
        return agg[0]["t"] if agg else 0
    except: return 0

def revenue_daily_chart(days=7):
    try:
        result = []
        for i in range(days - 1, -1, -1):
            day = now() - timedelta(days=i)
            start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            agg = list(payments_col.aggregate([
                {"$match": {"status": "approved",
                            "approved_at": {"$gte": start, "$lt": end}}},
                {"$group": {"_id": None, "t": {"$sum": "$amount"}}}]))
            amt = agg[0]["t"] if agg else 0
            result.append((start.strftime("%d-%b"), amt))
        return result
    except: return []

def all_promos():
    try: return list(promo_col.find().sort("_id", -1))
    except: return []

def gen_promo():
    c = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = ''.join(random.choices(c, k=12))
        if not promo_col.find_one({"code": code}): return code
    return ''.join(random.choices(c, k=12))

def save_promo(code, rc, mu, aid):
    try:
        promo_col.insert_one({"code": code, "reward_credits": rc, "max_users": mu,
            "used_count": 0, "used_by": [], "generated_by": aid,
            "created_at": datetime.now().strftime('%Y-%m-%d'), "active": 1})
    except: pass

def redeem_promo(code, uid):
    try:
        d = promo_col.find_one({"code": code})
        if not d: return None
        if d.get("active", 1) == 0: return None
        if uid in d.get("used_by", []): return -1
        res = promo_col.find_one_and_update(
            {"code": code, "active": 1, "used_count": {"$lt": d.get("max_users", 0)},
             "used_by": {"$ne": uid}},
            {"$inc": {"used_count": 1}, "$push": {"used_by": uid}},
            return_document=ReturnDocument.AFTER)
        if not res: return -1 if uid in d.get("used_by", []) else None
        r = res.get("reward_credits", 0)
        add_credits(uid, r)
        return r
    except: return None

def all_channels():
    try: return list(channels_col.find({"enabled": 1}))
    except: return []
def channel_list():
    try: return list(channels_col.find().sort("_id", 1))
    except: return []
def add_channel_db(cid, link):
    try:
        if channels_col.find_one({"channel_id": cid}): return False
        channels_col.insert_one({"channel_id": cid, "channel_link": link, "enabled": 1})
        return True
    except: return False
def remove_channel_db(cid):
    try: return channels_col.delete_one({"channel_id": cid}).deleted_count > 0
    except: return False

def is_auto_upi_available():
    if int(get_setting("gateway_enabled", 0)) != 1: return False
    if not get_setting("gateway_create_url", ""): return False
    if not get_setting("gateway_api_key", ""): return False
    return True

def create_gateway_order(amount, uid):
    url = get_setting("gateway_create_url", "") or FAM_CREATE_URL
    key = get_setting("gateway_api_key", "") or FAM_API_KEY
    redirect = get_setting("gateway_redirect_url", "") or FAM_REDIRECT_URL
    if not url or not key: return False, None, None, None, None, "Not configured"
    try:
        headers = {"X-Api-Key": key, "Content-Type": "application/json"}
        payload = {"amount": float(amount), "redirect_url": redirect,
                   "customer_name": f"user_{uid}", "api_key": key}
        r = requests.post(url, headers=headers, json=payload, timeout=25)
        if r.status_code not in (200, 201): return False, None, None, None, None, f"HTTP {r.status_code}"
        try: raw = r.json()
        except: return False, None, None, None, None, "Bad JSON"
        if raw.get("status") != "success":
            return False, None, None, None, None, f"Status: {raw.get('status')}"
        data = raw.get("data") or {}
        oid = data.get("order_id")
        if not oid: return False, None, None, None, None, "No order_id"
        return True, str(oid), data.get("checkout_url"), data.get("qr_url"), data.get("upi_id"), raw
    except requests.exceptions.Timeout: return False, None, None, None, None, "Timeout"
    except Exception as e: return False, None, None, None, None, f"Error: {e}"

def verify_gateway_order(order_id):
    cs = get_setting("gateway_checkout_status_url", "") or FAM_CHECKOUT_URL
    try:
        r = requests.get(cs, params={"order_id": order_id}, timeout=15)
        if r.status_code == 200:
            try:
                raw = r.json()
                status = str(raw.get("status", "")).lower()
                if status == "success":
                    return True, "success", {"utr": raw.get("utr"),
                        "sender_name": raw.get("sender_name"),
                        "paid_at": raw.get("paid_at"),
                        "amount": raw.get("amount"), "raw": raw}
                elif status in ("pending", "expired"): return False, status, raw
            except: pass
    except: pass
    return False, "error", None

def download_qr_bytes(qr_url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(qr_url, timeout=15, allow_redirects=True)
            if r.status_code == 200 and len(r.content) > 100: return r.content
        except: pass
        time.sleep(1)
    return None

def send_qr_image(cid, qr_url, caption, kb, reply_to=None):
    content = download_qr_bytes(qr_url)
    if not content: return None
    try:
        kw = {"caption": caption, "parse_mode": "HTML", "reply_markup": kb}
        if reply_to: kw["reply_to_message_id"] = reply_to
        return bot.send_photo(cid, content, **kw)
    except Exception as e: logger.error(f"[QR] {e}"); return None

# =================================================================
#  BOT INIT
# =================================================================
bot = telebot.TeleBot(BOT_TOKEN)
try: bot.remove_webhook()
except: pass

def send_typing(cid):
    try: bot.send_chat_action(cid, 'typing')
    except: pass

def safe_ans(call, text=None, alert=False):
    try:
        if text is None: bot.answer_callback_query(call.id)
        else: bot.answer_callback_query(call.id, text, show_alert=alert)
    except: pass

def safe_edit(call, text, **kw):
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, **kw)
        return True
    except: return False

# =================================================================
#  FOOTER
# =================================================================
def build_footer(uid):
    powered = get_setting("powered_by", "") or f"{BOT_USERNAME} | {ADMIN_USERNAME}"
    wm = get_setting("watermark_text", "") or ""
    wm_line = f"\n💧 {wm}" if wm.strip() else ""
    return (f"{div_soft()}\n"
            f"📅 {fancy('generated')}: {fancy_dt()}\n"
            f"🛡️ {fancy('powered by')} {powered}{wm_line}\n"
            f"{div_soft()}\n"
            f"🎯 {fancy('tries remaining')}: <b>{tries_display(uid)}</b>")

# =================================================================
#  ANIMATION
# =================================================================
class AnimMsg:
    EDIT_INTERVAL = 1.1; BAR_LEN = 18
    SPINNERS = ["◐", "◓", "◑", "◒"]
    def __init__(self, cid, stages=None, title="PROCESSING", reply_to=None):
        self.cid = cid; self.reply_to = reply_to
        self.title = fancy(title)
        self.mid = None; self._stop = threading.Event(); self._t = None
        self._start_time = time.time(); self._dead = False
        self.frames = self._build(stages or [])
    def _build(self, stages):
        frames = []; total = len(stages) or 1; BAR = self.BAR_LEN
        for idx, stage in enumerate(stages):
            label = fancy(stage.get("label", "Working"))
            emojis = stage.get("emojis", ["⏳"]); duration = stage.get("duration", 1.5)
            n_frames = max(2, int(duration / self.EDIT_INTERVAL))
            for i in range(n_frames):
                sf = (i + 1) / n_frames; ov = (idx + sf) / total
                pct = min(99, int(ov * 100))
                filled = int(BAR * ov)
                bar = "█" * filled + "░" * (BAR - filled)
                spin = self.SPINNERS[i % len(self.SPINNERS)]
                emoji = emojis[i % len(emojis)]
                step_txt = fancy(f"step {idx+1} of {total}")
                frames.append(f"<b>🎯 {self.title}</b>\n{div()}\n"
                    f"<code>{bar}</code> <b>{pct}%</b>\n\n"
                    f"{spin} {emoji} <b>{label}</b>\n<i>{step_txt}</i>")
        return frames
    def start(self):
        try:
            kw = {"parse_mode": "HTML"}
            if self.reply_to: kw["reply_to_message_id"] = self.reply_to
            m = bot.send_message(self.cid, self.frames[0], **kw)
            self.mid = m.message_id
            self._t = threading.Thread(target=self._run, daemon=True); self._t.start()
            return True
        except: return False
    def _run(self):
        i = 1
        while not self._stop.is_set() and i < len(self.frames):
            if self._dead: return
            try: bot.edit_message_text(self.frames[i], self.cid, self.mid, parse_mode="HTML")
            except Exception as e:
                err = str(e).lower()
                if "message to edit not found" in err or "message can't be edited" in err:
                    self._dead = True; return
                if "too many requests" in err: time.sleep(3); continue
            i += 1
            end = time.time() + self.EDIT_INTERVAL
            while time.time() < end:
                if self._stop.is_set(): return
                time.sleep(0.1)
        while not self._stop.is_set() and not self._dead:
            try: bot.edit_message_text(self.frames[-1], self.cid, self.mid, parse_mode="HTML")
            except Exception as e:
                if "message to edit not found" in str(e).lower():
                    self._dead = True; return
            time.sleep(2)
    def stop(self):
        self._stop.set()
        if self._t:
            try: self._t.join(timeout=3)
            except: pass
    def flash_complete(self, delay=0.4):
        if self._dead: return
        elapsed = time.time() - self._start_time
        bar = "█" * self.BAR_LEN
        text = (f"<b>🎯 {self.title}</b>\n{div()}\n"
                f"<code>{bar}</code> <b>100%</b>\n\n"
                f"✅ <b>{fancy('complete')}</b>\n<i>⏱ {fancy(f'took {elapsed:.1f}s')}</i>")
        try: bot.edit_message_text(text, self.cid, self.mid, parse_mode="HTML")
        except: pass
        time.sleep(delay)
    def edit(self, text, mark=None):
        if self._dead:
            try: bot.send_message(self.cid, text, parse_mode="HTML", reply_markup=mark)
            except: pass
            return
        try: bot.edit_message_text(text, self.cid, self.mid, parse_mode="HTML", reply_markup=mark)
        except:
            try: bot.send_message(self.cid, text, parse_mode="HTML", reply_markup=mark)
            except: pass
    def delete(self):
        try: bot.delete_message(self.cid, self.mid)
        except: pass

def err_frame(title, message):
    return (f"<b>❌ {fancy(title)}</b>\n{div()}\n"
            f"<code>{'░'*18}</code> <b>0%</b>\n\n{message}")

def stg_number(): return [
    {"label": "Connecting to server", "emojis": ["📡","🌐","🔌"], "duration": 1.0},
    {"label": "Authenticating API", "emojis": ["🔐","🔑","✔️"], "duration": 0.8},
    {"label": "Searching database", "emojis": ["🔎","🔍","🧠"], "duration": 1.6},
    {"label": "Fetching records", "emojis": ["📥","📦","📂"], "duration": 1.2},
    {"label": "Parsing data", "emojis": ["🧩","🔧","⚙️"], "duration": 0.9}]
def stg_aadhaar(): return [
    {"label": "Connecting Aadhaar API", "emojis": ["🛰️","📡","🌐"], "duration": 1.0},
    {"label": "Verifying identity", "emojis": ["🔐","🔒","🛡️"], "duration": 1.2},
    {"label": "Fetching records", "emojis": ["📥","📦","📊"], "duration": 1.6},
    {"label": "Assembling dossier", "emojis": ["🧩","📋","✅"], "duration": 1.0}]
def stg_vehicle(): return [
    {"label": "Connecting RTO server", "emojis": ["🛰️","📡","🌐"], "duration": 1.0},
    {"label": "Searching RC database", "emojis": ["🔎","🔍","📂"], "duration": 1.4},
    {"label": "Fetching vehicle info", "emojis": ["📥","📦","📊"], "duration": 1.2},
    {"label": "Assembling records", "emojis": ["🧩","📋","✅"], "duration": 0.9}]
def stg_tg(): return [
    {"label": "Resolving username", "emojis": ["🔍","🔎","🧭"], "duration": 1.2},
    {"label": "Querying MTProto", "emojis": ["🛰️","📡","🌐"], "duration": 1.2},
    {"label": "Fetching profile", "emojis": ["👤","📋","📊"], "duration": 1.2},
    {"label": "Calling TG2Num API", "emojis": ["🔌","⚡","✅"], "duration": 1.2}]
def stg_create(): return [
    {"label": "Contacting gateway", "emojis": ["⚡","🌐","📡"], "duration": 1.0},
    {"label": "Generating order", "emojis": ["🔐","🎫","💳"], "duration": 1.2},
    {"label": "Rendering QR", "emojis": ["🎨","🖼️","📸"], "duration": 0.9}]
def stg_verify(): return [
    {"label": "Pinging gateway", "emojis": ["📡","🔌","🌐"], "duration": 0.9},
    {"label": "Reading bank records", "emojis": ["📧","📬","💌"], "duration": 1.5},
    {"label": "Confirming UTR", "emojis": ["🏦","🔐","✔️"], "duration": 1.2}]

def no_data_msg(uid, svc="number"):
    if svc == "number": line = "ᴛʜɪꜱ ɴᴜᴍʙᴇʀ ɪꜱ ɴᴏᴛ ɪɴ ᴏᴜʀ ᴅᴀᴛᴀꜱᴇᴛꜱ."
    elif svc == "aadhaar": line = "ᴛʜɪꜱ ᴀᴀᴅʜᴀᴀʀ ɪꜱ ɴᴏᴛ ɪɴ ᴏᴜʀ ᴅᴀᴛᴀꜱᴇᴛꜱ."
    elif svc == "vehicle": line = "ᴛʜɪꜱ ᴠᴇʜɪᴄʟᴇ ɪꜱ ɴᴏᴛ ɪɴ ᴏᴜʀ ᴅᴀᴛᴀꜱᴇᴛꜱ."
    else: line = "ᴛʜɪꜱ ᴜꜱᴇʀ ɪꜱ ɴᴏᴛ ɪɴ ᴏᴜʀ ᴅᴀᴛᴀꜱᴇᴛꜱ."
    return (f"😔 <b>{fancy('no data found')}</b>\n\n"
            f"{line}\nᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɴᴏᴛʜᴇʀ {svc}.\n\n"
            f"{div_soft()}\n💎 ᴄʀᴇᴅɪᴛꜱ <b>{fancy('not deducted')}</b>\n"
            f"🎯 {fancy('tries remaining')}: <b>{tries_display(uid)}</b>")

def no_tries_msg(uid):
    return (f"⏳ <b>{fancy('daily limit reached')}</b>\n\n"
            f"ᴀᴀᴊ ᴋᴀ ʟɪᴍɪᴛ ᴋʜᴀᴛᴀᴍ.\nᴋᴀʟ ᴅᴏʙᴀʀᴀ ᴛʀʏ ᴋᴀʀᴇɪɴ.\n\n"
            f"{div_soft()}\n🎯 ᴛʀɪᴇꜱ: <b>0</b>")

def low_credit_text(uid, need, have):
    return (f"⚠️ <b>{fancy('not enough credits')}</b>\n\n"
            f"ɴᴇᴇᴅᴇᴅ: <b>{need} ᴄʀ</b>\nʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ: <b>{have} ᴄʀ</b>\n\n"
            f"{div_soft()}\n🎯 ᴛʀɪᴇꜱ: <b>{tries_display(uid)}</b>\n\n"
            f"📌 ʀᴇꜰᴇʀ ꜰʀɪᴇɴᴅ ᴏʀ ʙᴜʏ ᴄʀᴇᴅɪᴛꜱ:")

def low_credit_kb(uid):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(InlineKeyboardButton("🎁 ʀᴇꜰᴇʀ & ᴇᴀʀɴ", callback_data=f"copyref_{uid}"),
           InlineKeyboardButton("💳 ʙᴜʏ ᴄʀᴇᴅɪᴛꜱ", callback_data="buy_menu"))
    return kb

def rate_limit_msg(wait):
    return (f"⏳ <b>{fancy('please wait')}</b>\n\nᴀᴀᴘ ᴛᴏᴏ ꜰᴀꜱᴛ ʜᴀɪɴ!\nᴡᴀɪᴛ: <b>{wait}s</b>")

# =================================================================
#  INPUT HELPERS
# =================================================================
def extract_phone_digits(text):
    if not text: return None
    d = re.sub(r'\D', '', str(text))
    if not d: return None
    if d.startswith("00"): d = d[2:]
    if len(d) == 10 and d[0] in "6789": return d
    if len(d) == 11 and d.startswith("0") and d[1] in "6789": return d[1:]
    if len(d) == 12 and d.startswith("91") and d[2] in "6789": return d[2:]
    if len(d) == 13 and d.startswith("091") and d[3] in "6789": return d[3:]
    if len(d) > 12 and d[-10] in "6789": return d[-10:]
    return None

def is_vehicle_number(text):
    if not text: return False
    v = re.sub(r'[\s\-]', '', str(text)).upper()
    if re.match(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$', v): return True
    if re.match(r'^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$', v): return True
    return False

def classify_input(text):
    if not text: return None, None
    t = text.strip()
    if not t: return None, None
    if "t.me/" in t or "telegram.me/" in t:
        part = t.split("t.me/")[-1] if "t.me/" in t else t.split("telegram.me/")[-1]
        part = part.split("?")[0].strip("/")
        if "/" in part: part = part.split("/")[0]
        if not part: return None, None
        if part.startswith("+") or part.startswith("joinchat"): return None, None
        if part.isdigit(): return "tgid", part
        return "username", part
    if t.startswith("@"):
        u = t[1:].strip()
        if 5 <= len(u) <= 32 and re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', u):
            return "username", u
        return None, None
    if t.isdigit():
        if len(t) == 12: return "aadhaar", t
        phone = extract_phone_digits(t)
        if phone: return "number", phone
        if 5 <= len(t) <= 15: return "tgid", t
        return None, None
    if t.startswith("+"):
        phone = extract_phone_digits(t)
        if phone: return "number", phone
        d = re.sub(r'\D', '', t)
        if 5 <= len(d) <= 15: return "tgid", d
        return None, None
    if is_vehicle_number(t):
        return "vehicle", re.sub(r'[\s\-]', '', t).upper()
    if re.match(r'^[\+\d\s\-\(\)]+$', t):
        phone = extract_phone_digits(t)
        if phone: return "number", phone
        d = re.sub(r'\D', '', t)
        if 5 <= len(d) <= 15: return "tgid", d
        return None, None
    if re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', t): return "username", t
    return None, None

def is_maintenance(): return int(get_setting("maintenance_mode", 0)) == 1
def referral_enabled(): return int(get_setting("referral_enabled", 1)) == 1
def group_enabled(): return int(get_setting("group_enabled", 1)) == 1
def group_auto_delete(): return int(get_setting("group_auto_delete", 1)) == 1
def group_auto_delete_seconds():
    try: return int(get_setting("group_auto_delete_seconds", GROUP_AUTO_DELETE_SECONDS))
    except: return GROUP_AUTO_DELETE_SECONDS

def normalize_phone(num, cc=None):
    if not num: return None
    n = re.sub(r'\D', '', str(num))
    cc_d = re.sub(r'\D', '', str(cc or ""))
    if n.startswith("00"): n = n[2:]
    if cc_d:
        if n.startswith(cc_d) and len(n) > len(cc_d): return n
        return f"{cc_d}{n}"
    if len(n) == 10 and n[0] in "6789": return f"91{n}"
    return n

# =================================================================
#  JSON / FORMATTED OUTPUT
# =================================================================
def _clean_val(v):
    if v is None: return ""
    if isinstance(v, (list, dict)):
        try: return json.dumps(v, ensure_ascii=False)
        except: return str(v)
    s = str(v).strip()
    if s in ("", "null", "None", "nan", "N/A", "n/a", "-"): return ""
    return s

def _extract_number_records(data):
    if not isinstance(data, dict):
        if isinstance(data, list): return [x for x in data if isinstance(x, dict)]
        return []
    for key in ("result", "data", "results", "records", "info", "list", "response"):
        if key in data:
            res = data[key]
            if isinstance(res, list):
                recs = [x for x in res if isinstance(x, dict)]
                if recs: return recs
            elif isinstance(res, dict):
                for k2 in ("result", "data", "results", "records", "info", "list"):
                    if k2 in res:
                        r2 = res[k2]
                        if isinstance(r2, list):
                            recs = [x for x in r2 if isinstance(x, dict)]
                            if recs: return recs
                        elif isinstance(r2, dict): return [r2]
                return [res]
    return [data]

def build_json_text(records, query_info=None):
    if not records: return None
    results = []
    for rec in records:
        if not isinstance(rec, dict): continue
        out = {}
        for k, v in rec.items():
            if not isinstance(k, str): continue
            cv = _clean_val(v)
            if cv: out[k] = cv
        if out: results.append(out)
    if not results: return None
    payload = {"summary": f"{len(results)} record(s) found"}
    if query_info: payload["query"] = query_info
    payload["results"] = results
    return json.dumps(payload, indent=2, ensure_ascii=False)

def _format_record_html(rec, idx=None):
    if not isinstance(rec, dict): return ""
    lines = []
    if idx is not None:
        lines.append(f"<b>#{idx} ─────────────────</b>")
    priority = [
        ("name", "👤", "ɴᴀᴍᴇ"), ("owner_name", "👤", "ᴏᴡɴᴇʀ"),
        ("father_name", "👨", "ꜰᴀᴛʜᴇʀ"), ("father", "👨", "ꜰᴀᴛʜᴇʀ"),
        ("mobile", "📱", "ᴍᴏʙɪʟᴇ"), ("number", "📞", "ɴᴜᴍʙᴇʀ"),
        ("alt_mobile", "📱", "ᴀʟᴛ ᴍᴏʙɪʟᴇ"), ("alternate_number", "📱", "ᴀʟᴛ ɴᴜᴍʙᴇʀ"),
        ("aadhaar", "🆔", "ᴀᴀᴅʜᴀᴀʀ"), ("circle", "📡", "ᴄɪʀᴄʟᴇ"),
        ("address", "🏠", "ᴀᴅᴅʀᴇꜱꜱ"), ("email", "📧", "ᴇᴍᴀɪʟ"),
        ("dob", "🎂", "ᴅᴏʙ"), ("gender", "⚧️", "ɢᴇɴᴅᴇʀ"),
        ("village", "🏘️", "ᴠɪʟʟᴀɢᴇ"), ("district", "🏙️", "ᴅɪꜱᴛʀɪᴄᴛ"),
        ("state", "🌆", "ꜱᴛᴀᴛᴇ"), ("pincode", "📮", "ᴘɪɴᴄᴏᴅᴇ"),
        ("vehicle_number", "🚗", "ᴠᴇʜɪᴄʟᴇ ɴᴏ"), ("reg_no", "🚗", "ʀᴇɢ ɴᴏ"),
        ("chassis", "🔩", "ᴄʜᴀꜱꜱɪꜱ"), ("chassis_number", "🔩", "ᴄʜᴀꜱꜱɪꜱ"),
        ("engine", "⚙️", "ᴇɴɢɪɴᴇ"), ("engine_number", "⚙️", "ᴇɴɢɪɴᴇ"),
        ("fuel", "⛽", "ꜰᴜᴇʟ"), ("fuel_type", "⛽", "ꜰᴜᴇʟ"),
        ("vehicle_class", "🏷️", "ᴄʟᴀꜱꜱ"), ("maker", "🏭", "ᴍᴀᴋᴇʀ"),
        ("model", "🚙", "ᴍᴏᴅᴇʟ"), ("reg_date", "📅", "ʀᴇɢ ᴅᴀᴛᴇ"),
        ("registration_date", "📅", "ʀᴇɢ ᴅᴀᴛᴇ"), ("insurance", "🛡️", "ɪɴꜱᴜʀᴀɴᴄᴇ"),
        ("fitness", "✅", "ꜰɪᴛɴᴇꜱꜱ"), ("puc", "🌫️", "ᴘᴜᴄ"),
        ("rto", "🏢", "ʀᴛᴏ"), ("financer", "🏦", "ꜰɪɴᴀɴᴄᴇʀ"),
        ("tg_id", "🆔", "ᴛɢ ɪᴅ"), ("country", "🌍", "ᴄᴏᴜɴᴛʀʏ"),
        ("country_code", "📞", "ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ"),
    ]
    used_keys = set()
    low_rec = {k.lower(): v for k, v in rec.items() if isinstance(k, str)}
    for key, emoji, label in priority:
        if key.lower() in low_rec:
            v = _clean_val(low_rec[key.lower()])
            if v:
                if key in ("address",) and len(v) > 120: v = v[:117] + "..."
                lines.append(f"{emoji} <b>{label}:</b> <code>{html_module.escape(v)}</code>")
                used_keys.add(key.lower())
    extras = []
    for k, v in low_rec.items():
        if k in used_keys: continue
        cv = _clean_val(v)
        if cv and len(cv) < 200:
            extras.append(f"▫️ <b>{html_module.escape(k.upper())}:</b> <code>{html_module.escape(cv)}</code>")
    if extras:
        lines.append("")
        lines.append(f"<i>➕ {len(extras)} extra field(s):</i>")
        lines.extend(extras[:15])
    return "\n".join(lines)

def build_formatted_text(records, query_info=None, service="number"):
    if not records: return None
    parts = []
    total = len(records)
    parts.append(f"✅ <b>{total} ʀᴇᴄᴏʀᴅ(ꜱ) ꜰᴏᴜɴᴅ</b>\n")
    for i, rec in enumerate(records[:10], 1):
        if total > 1: parts.append(f"\n{div_soft()}")
        parts.append(_format_record_html(rec, i if total > 1 else None))
        parts.append("")
    if total > 10:
        parts.append(f"\n{div_soft()}")
        parts.append(f"<i>⚠️ Showing 10 of {total}. Switch to JSON mode for all.</i>")
    return "\n".join(parts)

def send_service_result(uid, cid, records, query_info, service,
                        header_line, remaining, is_priv, reply_to=None,
                        reply_markup=None):
    mode = str(get_setting("output_mode", "formatted")).lower()
    footer = "\n\n"
    if not is_priv:
        footer += f"{div_soft()}\n💎 ᴄʀᴇᴅɪᴛꜱ ʟᴇꜰᴛ: <b>{remaining}</b>\n"
    footer += build_footer(uid)

    if mode == "json":
        json_text = build_json_text(records, query_info)
        if not json_text:
            send_result(uid, cid, no_data_msg(uid, service), reply_to=reply_to); return
        if len(json_text) > 3000:
            txt = header_line + f"<i>📎 JSON too long — sent as file below...</i>" + footer
            send_result(uid, cid, txt, reply_to=reply_to, reply_markup=reply_markup)
            try:
                bio = io.BytesIO(json_text.encode('utf-8'))
                bio.name = f"{service}_result.json"
                bot.send_document(cid, bio, caption=f"📄 {len(records)} record(s)", parse_mode='HTML')
            except: pass
            return
        safe_json = html_module.escape(json_text)
        txt = header_line + f"<pre>{safe_json}</pre>" + footer
        send_result(uid, cid, txt, reply_to=reply_to, reply_markup=reply_markup)
    elif mode == "both":
        fmt = build_formatted_text(records, query_info, service)
        if not fmt:
            send_result(uid, cid, no_data_msg(uid, service), reply_to=reply_to); return
        txt = header_line + "\n" + fmt + footer
        send_result(uid, cid, txt, reply_to=reply_to, reply_markup=reply_markup)
        json_text = build_json_text(records, query_info)
        if json_text:
            if len(json_text) > 3000:
                try:
                    bio = io.BytesIO(json_text.encode('utf-8'))
                    bio.name = f"{service}_json.json"
                    bot.send_document(cid, bio, caption="📄 Full JSON", parse_mode='HTML')
                except: pass
            else:
                safe_json = html_module.escape(json_text)
                send_result(uid, cid, f"📄 <b>{fancy('json data')}</b>\n\n<pre>{safe_json}</pre>")
    else:
        fmt = build_formatted_text(records, query_info, service)
        if not fmt:
            send_result(uid, cid, no_data_msg(uid, service), reply_to=reply_to); return
        txt = header_line + "\n" + fmt + footer
        send_result(uid, cid, txt, reply_to=reply_to, reply_markup=reply_markup)

# =================================================================
#  KEYBOARDS
# =================================================================
def main_kb(uid):
    ia = is_admin_user(uid)
    kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.row(KeyboardButton("📞 Number To Info"), KeyboardButton("🔒 Username To Info"))
    kb.row(KeyboardButton("🆔 Aadhaar To Info"), KeyboardButton("🚗 Vehicle Info"))
    kb.row(KeyboardButton("🛒 Buy Credits"), KeyboardButton("💰 Refer & Earn"))
    kb.row(KeyboardButton("🎟 Redeem Code"), KeyboardButton("👤 My Profile"))
    kb.row(KeyboardButton("➕ Add Me To Group"), KeyboardButton("❓ Help"))
    kb.row(KeyboardButton("ℹ️ About"))
    if ia: kb.row(KeyboardButton("👑 ADMIN PANEL"))
    return kb

def admin_kb():
    kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.row(KeyboardButton("📊 Dashboard"), KeyboardButton("👥 Users"))
    kb.row(KeyboardButton("💳 Payments"), KeyboardButton("🔧 Services"))
    kb.row(KeyboardButton("🎟 Promos"), KeyboardButton("📢 Broadcast"))
    kb.row(KeyboardButton("📢 Force Join"), KeyboardButton("👥 Groups"))
    kb.row(KeyboardButton("⚙️ Settings"), KeyboardButton("🛡️ Security"))
    kb.row(KeyboardButton("📈 Analytics"), KeyboardButton("💾 Backup"))
    kb.row(KeyboardButton("🚀 Bot Info"), KeyboardButton("📝 Logs"))
    kb.row(KeyboardButton("🔒 Audit Log"), KeyboardButton("📮 Feedback"))
    kb.row(KeyboardButton("🔙 Back to Menu"))
    return kb

def dashboard_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(InlineKeyboardButton("🔄 Refresh", callback_data="adm_dash_refresh"),
           InlineKeyboardButton("📥 Export", callback_data="adm_dash_export"))
    kb.row(InlineKeyboardButton("📊 Detailed", callback_data="adm_dash_detailed"))
    kb.row(InlineKeyboardButton("📈 Revenue Graph", callback_data="adm_dash_revgraph"))
    kb.row(InlineKeyboardButton("🎛 Service Status", callback_data="adm_dash_svcstatus"))
    kb.row(InlineKeyboardButton("🚨 Alerts", callback_data="adm_dash_alerts"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def users_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(InlineKeyboardButton("🔍 Search", callback_data="adm_user_search"),
           InlineKeyboardButton("🚫 Ban", callback_data="adm_user_ban"))
    kb.row(InlineKeyboardButton("✅ Unban", callback_data="adm_user_unban"),
           InlineKeyboardButton("👻 Shadow Ban", callback_data="adm_user_shadowban"))
    kb.row(InlineKeyboardButton("💎 Add CR", callback_data="adm_user_addcr"),
           InlineKeyboardButton("➖ Remove CR", callback_data="adm_user_remcr"))
    kb.row(InlineKeyboardButton("💰 Set Balance", callback_data="adm_user_setcr"),
           InlineKeyboardButton("📊 Full Info", callback_data="adm_user_fullinfo"))
    kb.row(InlineKeyboardButton("📝 Notes", callback_data="adm_user_notes"),
           InlineKeyboardButton("📜 History", callback_data="adm_user_history"))
    kb.row(InlineKeyboardButton("📥 Export CSV", callback_data="adm_user_export"),
           InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def payments_kb():
    p, a, r, rev, rf = pay_stats()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton(f"⏳ Pending ({p})", callback_data="adm_pay_pending"))
    kb.row(InlineKeyboardButton(f"✅ Approved ({a})", callback_data="adm_pay_approved"))
    kb.row(InlineKeyboardButton(f"❌ Rejected ({r})", callback_data="adm_pay_rejected"))
    kb.row(InlineKeyboardButton(f"💸 Refunded ({rf})", callback_data="adm_pay_refunded"))
    kb.row(InlineKeyboardButton(f"💰 Revenue: ₹{rev} (24h: ₹{revenue_24h()})", callback_data="adm_pay_revenue"))
    kb.row(InlineKeyboardButton("🔍 Search Payment", callback_data="adm_pay_search"))
    kb.row(InlineKeyboardButton("💎 Manual Credit", callback_data="adm_pay_manual"))
    kb.row(InlineKeyboardButton("🧾 Recent", callback_data="adm_pay_recent"))
    kb.row(InlineKeyboardButton("📊 Revenue Graph", callback_data="adm_pay_revgraph"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def services_kb():
    sc = get_setting("search_cost", 5); ac = get_setting("aadhaar_cost", 10)
    tc = get_setting("tg2num_cost", 5); vc = get_setting("vehicle_cost", 10)
    out_mode = str(get_setting("output_mode", "formatted")).upper()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("🎛 Service ON/OFF", callback_data="adm_svc_toggle_panel"))
    kb.row(InlineKeyboardButton(f"🎨 Output: {out_mode}", callback_data="adm_svc_output_mode"))
    kb.row(InlineKeyboardButton(f"📞 Number: {sc}cr", callback_data="adm_svc_numcost"))
    kb.row(InlineKeyboardButton(f"🔒 Username: {tc}cr", callback_data="adm_svc_tgcost"))
    kb.row(InlineKeyboardButton(f"🆔 Aadhaar: {ac}cr", callback_data="adm_svc_aadhaarcost"))
    kb.row(InlineKeyboardButton(f"🚗 Vehicle: {vc}cr", callback_data="adm_svc_vehiclecost"))
    kb.row(InlineKeyboardButton("🔗 API Endpoints", callback_data="adm_svc_endpoints"))
    kb.row(InlineKeyboardButton("🧪 Test APIs", callback_data="adm_svc_test"))
    kb.row(InlineKeyboardButton("⏱ Cooldowns", callback_data="adm_svc_cooldown"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def services_toggle_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    for svc in SERVICE_KEYS:
        enabled = is_service_enabled(svc)
        status = "🟢 ON" if enabled else "🔴 OFF"
        emoji = SERVICE_EMOJI.get(svc, "🔹")
        label = SERVICE_LABELS.get(svc, svc).replace(emoji + " ", "")
        kb.add(InlineKeyboardButton(f"{emoji} {label}: {status}", callback_data=f"adm_svc_tog_{svc}"))
    kb.add(InlineKeyboardButton("✏️ Custom Messages", callback_data="adm_svc_custom_msgs"))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="adm_svc_back"))
    return kb

def services_custom_msgs_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    for svc in SERVICE_KEYS:
        emoji = SERVICE_EMOJI.get(svc, "🔹")
        label = SERVICE_LABELS.get(svc, svc).replace(emoji + " ", "")
        has_custom = bool((get_setting(f"service_{svc}_msg", "") or "").strip())
        tag = "✏️" if has_custom else "📝"
        kb.add(InlineKeyboardButton(f"{tag} {emoji} {label}", callback_data=f"adm_svc_editmsg_{svc}"))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="adm_svc_toggle_panel"))
    return kb

def ep_edit_kb(field):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(InlineKeyboardButton("✏️ Edit", callback_data=f"ep_edit_{field}"),
           InlineKeyboardButton("🗑 Clear", callback_data=f"ep_clear_{field}"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_svc_endpoints"))
    return kb

def services_endpoints_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("📞 Number URL", callback_data="adm_ep_numurl"))
    kb.row(InlineKeyboardButton("📞 Number Key", callback_data="adm_ep_numkey"))
    kb.row(InlineKeyboardButton("🔒 TG2Num URL", callback_data="adm_ep_tgurl"))
    kb.row(InlineKeyboardButton("🔒 TG2Num Key", callback_data="adm_ep_tgkey"))
    kb.row(InlineKeyboardButton("🆔 Aadhaar URL", callback_data="adm_ep_aadhaarurl"))
    kb.row(InlineKeyboardButton("🆔 Aadhaar Key", callback_data="adm_ep_aadhaarkey"))
    kb.row(InlineKeyboardButton("🚗 Vehicle URL", callback_data="adm_ep_vehicleurl"))
    kb.row(InlineKeyboardButton("🚗 Vehicle Key", callback_data="adm_ep_vehiclekey"))
    kb.row(InlineKeyboardButton("🔄 View All", callback_data="adm_ep_viewall"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_svc_back"))
    return kb

def services_cooldown_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    gl = get_setting("rate_limit_seconds", 0)
    kb.row(InlineKeyboardButton(f"🌐 Global: {gl}s", callback_data="adm_cd_setglobal"))
    for svc in SERVICE_KEYS:
        emoji = SERVICE_EMOJI.get(svc, "🔹")
        cd = get_setting(f"cooldown_{svc}", 0)
        kb.row(InlineKeyboardButton(f"{emoji} {svc.title()}: {cd}s", callback_data=f"adm_cd_set_{svc}"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_svc_back"))
    return kb

def promos_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("📦 Generate", callback_data="adm_promo_gen"))
    kb.row(InlineKeyboardButton("📋 List", callback_data="adm_promo_list"))
    kb.row(InlineKeyboardButton("📊 Stats", callback_data="adm_promo_stats"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def broadcast_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("📝 Text", callback_data="adm_bc_text"))
    kb.row(InlineKeyboardButton("📸 Photo", callback_data="adm_bc_photo"))
    kb.row(InlineKeyboardButton("🎬 Video", callback_data="adm_bc_video"))
    kb.row(InlineKeyboardButton("🎯 Filtered", callback_data="adm_bc_filtered"))
    kb.row(InlineKeyboardButton("📢 To Groups", callback_data="adm_bc_groups"))
    kb.row(InlineKeyboardButton("⚙️ Settings", callback_data="adm_bc_settings"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def broadcast_filtered_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton(f"👥 All ({len(all_users())})", callback_data="adm_bcf_all"))
    kb.row(InlineKeyboardButton(f"🔥 Active ({len(active_users_24h())})", callback_data="adm_bcf_active"))
    kb.row(InlineKeyboardButton(f"💰 Paying ({len(paying_users())})", callback_data="adm_bcf_paid"))
    kb.row(InlineKeyboardButton(f"🆓 Free ({len(non_paying_users())})", callback_data="adm_bcf_nonpaid"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_bc_back"))
    return kb

def broadcast_settings_kb():
    pin = "🟢 ON" if int(get_setting("broadcast_pin", 0)) else "🔴 OFF"
    fwd = "🟢 ON" if int(get_setting("broadcast_forward", 0)) else "🔴 OFF"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton(f"📌 Pin: {pin}", callback_data="adm_bc_tog_pin"))
    kb.row(InlineKeyboardButton(f"↗️ Forward: {fwd}", callback_data="adm_bc_tog_fwd"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_bc_back"))
    return kb

def force_kb():
    en = manager.global_enabled if manager else False
    st = "✅ ON" if en else "❌ OFF"
    ch_count = len(manager.channels) if manager else 0
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(InlineKeyboardButton(f"🔄 Toggle ({st})", callback_data="fj_toggle"))
    kb.row(InlineKeyboardButton("➕ Add", callback_data="fj_add"),
           InlineKeyboardButton("➖ Remove", callback_data="fj_remove"))
    kb.row(InlineKeyboardButton(f"📋 List ({ch_count})", callback_data="fj_list"),
           InlineKeyboardButton("📊 Stats", callback_data="fj_stats"))
    kb.row(InlineKeyboardButton("✏️ Custom Msg", callback_data="fj_set_msg"))
    kb.row(InlineKeyboardButton("🧪 Preview", callback_data="fj_test"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def groups_kb():
    enabled = "🟢 ON" if group_enabled() else "🔴 OFF"
    auto_del = "🟢 ON" if group_auto_delete() else "🔴 OFF"
    secs = group_auto_delete_seconds()
    mins = secs // 60
    time_str = f"{mins}m" if mins < 60 else f"{mins//60}h"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton(f"🔀 Group Mode: {enabled}", callback_data="adm_grp_toggle"))
    kb.row(InlineKeyboardButton(f"🗑 Auto Delete ({time_str}): {auto_del}", callback_data="adm_grp_tog_autodel"))
    kb.row(InlineKeyboardButton("⏱ Set Time", callback_data="adm_grp_set_deltime"))
    kb.row(InlineKeyboardButton("📋 List Groups", callback_data="adm_grp_list"))
    kb.row(InlineKeyboardButton("📢 Broadcast", callback_data="adm_grp_bc"))
    kb.row(InlineKeyboardButton("📝 Welcome Msg", callback_data="adm_grp_welcome"))
    kb.row(InlineKeyboardButton("🗑 Leave All", callback_data="adm_grp_leave_all"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def settings_main_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("💎 Economics", callback_data="ads_eco"))
    kb.row(InlineKeyboardButton("🔍 Service Costs", callback_data="ads_costs"))
    kb.row(InlineKeyboardButton("🎯 Tries & Limits", callback_data="ads_tries"))
    kb.row(InlineKeyboardButton("💳 Payment", callback_data="ads_pay"))
    kb.row(InlineKeyboardButton("⚙️ System", callback_data="ads_sys"))
    kb.row(InlineKeyboardButton("🎨 Customization", callback_data="ads_custom"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def admin_economics_kb():
    wb = get_setting("welcome_bonus", WELCOME_BONUS)
    rb = get_setting("referral_bonus", REFERRAL_BONUS)
    rate = get_rate()
    ref = "🟢 ON" if referral_enabled() else "🔴 OFF"
    qa = get_quick_amounts()
    qa_str = ",".join(str(x) for x in qa)
    if len(qa_str) > 25: qa_str = qa_str[:22] + "..."
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(f"💎 Welcome Bonus: {wb}cr", callback_data="ads_set_welcome"))
    kb.add(InlineKeyboardButton(f"🎁 Referral Bonus: {rb}cr", callback_data="ads_set_refbonus"))
    kb.add(InlineKeyboardButton(f"💱 Rate: ₹1 = {rate}cr", callback_data="ads_set_rate"))
    kb.add(InlineKeyboardButton(f"⚡ Quick Amounts: {qa_str}", callback_data="ads_set_quick"))
    kb.add(InlineKeyboardButton(f"🔀 Referral: {ref}", callback_data="ads_tog_ref"))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="ads_back"))
    return kb

def admin_costs_kb():
    sc = get_setting("search_cost", 5); ac = get_setting("aadhaar_cost", 10)
    tc = get_setting("tg2num_cost", 5); vc = get_setting("vehicle_cost", 10)
    mn = get_setting("min_payment", MIN_PAYMENT); mx = get_setting("max_payment", MAX_PAYMENT)
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(f"📞 Number: {sc}cr", callback_data="ads_set_scost"))
    kb.add(InlineKeyboardButton(f"🆔 Aadhaar: {ac}cr", callback_data="ads_set_acost"))
    kb.add(InlineKeyboardButton(f"🔒 Username: {tc}cr", callback_data="ads_set_tcost"))
    kb.add(InlineKeyboardButton(f"🚗 Vehicle: {vc}cr", callback_data="ads_set_vcost"))
    kb.add(InlineKeyboardButton(f"💵 Min ₹{mn}", callback_data="ads_set_minpay"))
    kb.add(InlineKeyboardButton(f"💵 Max ₹{mx}", callback_data="ads_set_maxpay"))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="ads_back"))
    return kb

def admin_tries_kb():
    dt = get_setting("daily_tries", DAILY_TRIES)
    dt_str = f"{dt}" if dt > 0 else "∞ Unlimited"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(f"🎯 Daily Tries: {dt_str}", callback_data="ads_set_tries"))
    kb.add(InlineKeyboardButton("♾️ Set Unlimited", callback_data="ads_tries_unlimited"))
    kb.add(InlineKeyboardButton("🔄 Reset All Users", callback_data="ads_tries_reset_all"))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="ads_back"))
    return kb

def admin_pay_kb():
    mon = int(get_setting("upi_manual_enabled", 1))
    upi = get_setting("upi_manual_id", "not set") or "not set"
    avail = is_auto_upi_available()
    gws = "🟢 ON" if avail else "🔴 OFF"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(f"🔌 Gateway: {gws}", callback_data="ads_tog_gw"))
    kb.add(InlineKeyboardButton("🔑 Gateway Key", callback_data="ads_set_gwkey"))
    kb.add(InlineKeyboardButton("🔗 Create URL", callback_data="ads_set_gwcreate"))
    kb.add(InlineKeyboardButton("🔗 Status URL", callback_data="ads_set_gwstatus"))
    kb.add(InlineKeyboardButton("🌐 Redirect URL", callback_data="ads_set_gwredirect"))
    kb.add(InlineKeyboardButton(f"{'🟢' if mon else '🔴'} UPI: {str(upi)[:20]}", callback_data="ads_set_upiid"))
    kb.add(InlineKeyboardButton("🖼 QR URL", callback_data="ads_set_upiqr"))
    kb.add(InlineKeyboardButton(f"{'🔴 OFF' if mon else '🟢 ON'} Manual", callback_data="ads_tog_manual"))
    kb.add(InlineKeyboardButton(f"🚨 Alert ≥ ₹{get_setting('large_payment_alert',500)}", callback_data="ads_set_alert"))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="ads_back"))
    return kb

def admin_sys_kb():
    mm = "🟢 ON" if is_maintenance() else "🔴 OFF"
    bk = "🟢 ON" if int(get_setting("auto_backup_enabled", 0)) else "🔴 OFF"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(f"🔧 Maintenance: {mm}", callback_data="ads_tog_mm"))
    kb.add(InlineKeyboardButton(f"💾 Auto-Backup: {bk}", callback_data="ads_tog_backup"))
    kb.add(InlineKeyboardButton("⏰ Backup Hour", callback_data="ads_set_backup_hour"))
    kb.add(InlineKeyboardButton("📤 Manual Backup Now", callback_data="ads_backup_now"))
    kb.add(InlineKeyboardButton("📤 Export Users", callback_data="ads_export"))
    kb.add(InlineKeyboardButton("🧹 Clean Cache", callback_data="ads_cleancache"))
    kb.add(InlineKeyboardButton("🛰️ Pyrogram", callback_data="ads_pyro"))
    kb.add(InlineKeyboardButton("💾 Mongo", callback_data="ads_mongo"))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="ads_back"))
    return kb

def admin_custom_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🛡️ Powered By", callback_data="ads_set_powered"))
    kb.add(InlineKeyboardButton("💧 Watermark", callback_data="ads_set_watermark"))
    kb.add(InlineKeyboardButton("💬 Welcome Emoji", callback_data="ads_set_welcome_emoji"))
    kb.add(InlineKeyboardButton("📢 About", callback_data="ads_set_about"))
    kb.add(InlineKeyboardButton("📞 Support", callback_data="ads_set_support"))
    kb.add(InlineKeyboardButton("🚫 Banned Words", callback_data="ads_set_bannedwords"))
    kb.add(InlineKeyboardButton("⚙️ Maint. Msg", callback_data="ads_set_maintmsg"))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="ads_back"))
    return kb

def security_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("🚫 Banned Users", callback_data="adm_sec_banned"))
    kb.row(InlineKeyboardButton("👻 Shadow Banned", callback_data="adm_sec_shadow_banned"))
    kb.row(InlineKeyboardButton("⚠️ Maintenance", callback_data="adm_sec_maint"))
    kb.row(InlineKeyboardButton("👑 Sub-Admins", callback_data="adm_sec_subadmins"))
    kb.row(InlineKeyboardButton("⏱ Admin Rate Limit", callback_data="adm_sec_adminlimit"))
    kb.row(InlineKeyboardButton("🔒 Audit Log", callback_data="adm_sec_audit"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def subadmins_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("➕ Add", callback_data="adm_sub_add"))
    kb.row(InlineKeyboardButton("➖ Remove", callback_data="adm_sub_remove"))
    kb.row(InlineKeyboardButton("📋 List", callback_data="adm_sub_list"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_sec_back"))
    return kb

def analytics_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("📊 User Growth", callback_data="adm_an_growth"))
    kb.row(InlineKeyboardButton("🔍 Search Trends", callback_data="adm_an_searches"))
    kb.row(InlineKeyboardButton("💰 Revenue", callback_data="adm_an_revenue"))
    kb.row(InlineKeyboardButton("🏆 Top Users", callback_data="adm_an_top"))
    kb.row(InlineKeyboardButton("🎁 Referral Board", callback_data="adm_an_refboard"))
    kb.row(InlineKeyboardButton("📡 API Health", callback_data="adm_an_api_health"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def backup_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("📤 Users CSV", callback_data="adm_bk_users"))
    kb.row(InlineKeyboardButton("📤 Payments CSV", callback_data="adm_bk_payments"))
    kb.row(InlineKeyboardButton("💾 Full JSON", callback_data="adm_bk_full"))
    kb.row(InlineKeyboardButton("📮 Feedback", callback_data="adm_bk_feedback"))
    kb.row(InlineKeyboardButton("📝 Notes", callback_data="adm_bk_notes"))
    kb.row(InlineKeyboardButton("📜 Audit Log JSON", callback_data="adm_bk_audit"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def botinfo_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("🔄 Refresh", callback_data="adm_info_refresh"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def feedback_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("📖 View", callback_data="adm_fb_view"))
    kb.row(InlineKeyboardButton("💬 Reply", callback_data="adm_fb_reply"))
    kb.row(InlineKeyboardButton("🗑 Clear", callback_data="adm_fb_clear"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def audit_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("🔄 Refresh", callback_data="adm_audit_refresh"))
    kb.row(InlineKeyboardButton("📤 Export JSON", callback_data="adm_audit_export"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back"))
    return kb

def refund_confirm_kb(pid):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(InlineKeyboardButton("✅ Yes, Refund", callback_data=f"refund_yes_{pid}"),
           InlineKeyboardButton("❌ Cancel", callback_data=f"pv_{pid}"))
    return kb

# =================================================================
#  BUY SYSTEM
# =================================================================
def get_quick_amounts():
    raw = get_setting("quick_amounts", ",".join(str(x) for x in DEFAULT_QUICK_AMOUNTS)) or ""
    out = []
    for x in raw.split(","):
        x = x.strip()
        if x.isdigit() and int(x) > 0: out.append(int(x))
    if not out: out = list(DEFAULT_QUICK_AMOUNTS)
    return out[:12]

def get_rate():
    try:
        r = int(get_setting("credits_per_rupee", 1))
        return r if r > 0 else 1
    except: return 1

def buy_main_kb():
    amounts = get_quick_amounts()
    kb = InlineKeyboardMarkup(row_width=3)
    btns = []
    for amt in amounts:
        btns.append(InlineKeyboardButton(f"₹{amt}", callback_data=f"buy_amt_{amt}"))
    for i in range(0, len(btns), 3):
        kb.row(*btns[i:i+3])
    kb.row(InlineKeyboardButton("✏️ Custom Amount", callback_data="buy_custom"))
    kb.row(InlineKeyboardButton("📜 My Orders", callback_data="buy_history"),
           InlineKeyboardButton("🏠 Home", callback_data="home"))
    kb.row(InlineKeyboardButton("❌ Close", callback_data="close"))
    return kb

def buy_confirm_kb(amount, credits):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("💳 Proceed to Pay", callback_data=f"buy_next_{amount}_{credits}"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="buy_menu"))
    return kb

def payment_method_kb(amount, credits):
    mon = int(get_setting("upi_manual_enabled", 1))
    auto_ok = is_auto_upi_available()
    kb = InlineKeyboardMarkup(row_width=1)
    if auto_ok:
        kb.add(InlineKeyboardButton("⚡ Auto UPI (Instant)", callback_data=f"pay_auto_{amount}_{credits}"))
    if mon:
        kb.add(InlineKeyboardButton("📋 Manual UPI", callback_data=f"pay_manual_{amount}_{credits}"))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data=f"buy_amt_{amount}"))
    return kb

def show_buy_menu(uid, cid, reply_to=None):
    rate = get_rate()
    cur_cr = get_credits(uid)
    sc = get_setting("search_cost", 5); tc = get_setting("tg2num_cost", 5)
    ac = get_setting("aadhaar_cost", 10); vc = get_setting("vehicle_cost", 10)
    note = (get_setting("buy_note", "") or "").strip()

    txt = (f"🛒 <b>{fancy('buy credits')}</b>\n{div()}\n\n"
           f"💰 ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ: <b>{cur_cr} ᴄʀ</b>\n"
           f"💱 ʀᴀᴛᴇ: <b>₹1 = {rate} ᴄʀ</b>\n\n"
           f"<b>{fancy('service costs')}:</b>\n"
           f"📞 ɴᴜᴍʙᴇʀ: {sc}ᴄʀ\n🔒 ᴜꜱᴇʀɴᴀᴍᴇ: {tc}ᴄʀ\n"
           f"🆔 ᴀᴀᴅʜᴀᴀʀ: {ac}ᴄʀ\n🚗 ᴠᴇʜɪᴄʟᴇ: {vc}ᴄʀ\n\n")
    if note:
        txt += f"📢 <i>{html_module.escape(note)}</i>\n\n"
    txt += f"📌 ꜱᴇʟᴇᴄᴛ ᴀᴍᴏᴜɴᴛ:"
    bot.send_message(cid, txt, parse_mode='HTML',
                     reply_markup=buy_main_kb(), reply_to_message_id=reply_to)

def show_confirm(uid, cid, amount, edit_mid=None):
    rate = get_rate()
    credits = amount * rate
    txt = (f"💳 <b>{fancy('confirm purchase')}</b>\n{div()}\n\n"
           f"💰 ᴀᴍᴏᴜɴᴛ: <b>₹{amount}</b>\n"
           f"💎 ʏᴏᴜ'ʟʟ ɢᴇᴛ: <b>{credits} ᴄʀ</b>\n"
           f"💱 ʀᴀᴛᴇ: ₹1 = {rate}ᴄʀ\n\n"
           f"📌 ᴘʀᴏᴄᴇᴇᴅ ᴛᴏ ᴘᴀʏᴍᴇɴᴛ:")
    kb = buy_confirm_kb(amount, credits)
    if edit_mid:
        try: bot.edit_message_text(txt, cid, edit_mid, parse_mode='HTML', reply_markup=kb); return
        except: pass
    bot.send_message(cid, txt, parse_mode='HTML', reply_markup=kb)

def show_payment_method(uid, cid, amount, credits, edit_mid=None):
    txt = (f"💳 <b>{fancy('choose payment method')}</b>\n{div()}\n\n"
           f"💰 ₹{amount} → 💎 {credits}ᴄʀ\n\n📌 ꜱᴇʟᴇᴄᴛ ᴍᴇᴛʜᴏᴅ:")
    kb = payment_method_kb(amount, credits)
    if edit_mid:
        try: bot.edit_message_text(txt, cid, edit_mid, parse_mode='HTML', reply_markup=kb); return
        except: pass
    bot.send_message(cid, txt, parse_mode='HTML', reply_markup=kb)

def show_order_history(uid, cid, reply_to=None):
    pays = get_user_payments(uid, 10)
    total_amt, total_cr, count = user_purchase_stats(uid)
    if not pays:
        bot.send_message(cid,
            f"📜 <b>{fancy('order history')}</b>\n{div()}\n\nɴᴏ ᴏʀᴅᴇʀꜱ ʏᴇᴛ.",
            parse_mode='HTML', reply_to_message_id=reply_to,
            reply_markup=InlineKeyboardMarkup().row(
                InlineKeyboardButton("🛒 Buy Credits", callback_data="buy_menu")))
        return
    lines = [f"📜 <b>{fancy('order history')}</b>\n{div()}\n",
             f"📊 ᴛᴏᴛᴀʟ ꜱᴘᴇɴᴛ: <b>₹{total_amt}</b>\n",
             f"💎 ᴄʀᴇᴅɪᴛꜱ ʙᴏᴜɢʜᴛ: <b>{total_cr}</b>\n",
             f"🧾 ᴏʀᴅᴇʀꜱ: <b>{count}</b>\n"]
    for p in pays:
        status = p.get("status", "pending")
        emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌",
                 "expired": "⌛", "refunded": "💸"}.get(status, "❓")
        amt = p.get("amount", 0); cr = p.get("credits", 0)
        t = p.get("created_at")
        t_str = t.strftime("%d-%b %H:%M") if hasattr(t, 'strftime') else "?"
        lines.append(f"\n{emoji} <b>₹{amt}</b> → {cr}ᴄʀ\n   <code>{t_str}</code> | <i>{status.title()}</i>")
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(InlineKeyboardButton("🛒 Buy More", callback_data="buy_menu"),
           InlineKeyboardButton("🏠 Home", callback_data="home"))
    bot.send_message(cid, "\n".join(lines), parse_mode='HTML',
                     reply_markup=kb, reply_to_message_id=reply_to)

def handle_auto_payment(uid, cid, amount, credits, edit_mid=None):
    if not is_auto_upi_available():
        bot.send_message(cid, "⚡ Auto UPI unavailable."); return
    if edit_mid:
        try: bot.delete_message(cid, edit_mid)
        except: pass
    am = AnimMsg(cid, stages=stg_create(), title="CREATING ORDER")
    am.start()
    try: ok, oid, link, qr, upi, raw = create_gateway_order(amount, uid)
    except Exception as e: ok, oid, link, qr, upi, raw = False, None, None, None, None, str(e)
    am.stop()
    if not ok:
        am.edit(err_frame("ORDER FAILED", f"<i>{str(raw)[:200]}</i>")); return
    am.flash_complete(); am.delete()
    pid = create_payment(uid, cid, amount, credits, "auto", order_id=oid, payment_link=link)
    states[uid] = {'state': 'waiting_payment', 'order_id': oid, 'payment_id': pid,
                    'amount': amount, 'credits': credits, 'pay_mode': 'auto'}
    lines = [f"✅ <b>{fancy('order created')}</b>\n{div()}\n",
             f"💰 ₹{amount} → 💎 {credits}ᴄʀ",
             f"🆔 <code>{oid}</code>"]
    if upi: lines.append(f"📱 ᴜᴘɪ: <code>{upi}</code>")
    lines.append(f"\n⏱ ᴠᴀʟɪᴅ ꜰᴏʀ 5 ᴍɪɴᴜᴛᴇꜱ")
    caption = "\n".join(lines)
    kb = InlineKeyboardMarkup(row_width=1)
    if link: kb.add(InlineKeyboardButton("💳 Pay Now", url=link))
    kb.add(InlineKeyboardButton("🔄 Check Status", callback_data=f"chk_{oid}"))
    kb.add(InlineKeyboardButton("📸 Send Screenshot", callback_data=f"scr_{oid}"))
    kb.add(InlineKeyboardButton("🔙 Cancel", callback_data="buy_menu"))
    qr_msg = None
    if qr and qr.startswith("http"):
        qr_msg = send_qr_image(cid, qr, caption, kb)
    if qr_msg:
        threading.Thread(target=poll_order_async,
            args=(uid, cid, oid, amount, credits, qr_msg.message_id), daemon=True).start()
    else:
        if qr: caption += f"\n\n🖼 <a href='{qr}'>QR</a>"
        bot.send_message(cid, caption, parse_mode='HTML', reply_markup=kb)
        threading.Thread(target=poll_order_async,
            args=(uid, cid, oid, amount, credits, None), daemon=True).start()

def handle_manual_payment(uid, cid, amount, credits, edit_mid=None):
    upi = get_setting("upi_manual_id", "not set")
    qr = get_setting("upi_manual_qr", "")
    caption = (f"📋 <b>{fancy('manual upi')}</b>\n{div()}\n\n"
               f"💰 ᴀᴍᴏᴜɴᴛ: <b>₹{amount}</b>\n"
               f"💎 ᴄʀᴇᴅɪᴛꜱ: <b>{credits}ᴄʀ</b>\n\n"
               f"📱 <b>ᴜᴘɪ ɪᴅ:</b>\n<code>{upi}</code>\n\n"
               f"<b>ꜱᴛᴇᴘꜱ:</b>\n"
               f"1️⃣ ₹{amount} ᴘᴀʏ ᴋᴀʀᴏ\n"
               f"2️⃣ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ ʟᴏ\n"
               f"3️⃣ ɴᴇᴇᴄʜᴇ ✅ ᴛᴀᴘ ᴋᴀʀᴏ")
    kb = InlineKeyboardMarkup(row_width=1)
    kb.row(InlineKeyboardButton("✅ I've Paid", callback_data=f"paid_manual_{amount}_{credits}"))
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="buy_menu"))
    if edit_mid:
        try: bot.delete_message(cid, edit_mid)
        except: pass
    sent = None
    if qr and qr.startswith("http"):
        sent = send_qr_image(cid, qr, caption, kb)
    if not sent:
        bot.send_message(cid, caption, parse_mode='HTML', reply_markup=kb)

def process_manual_paid(uid, cid, amount, credits, edit_mid=None):
    pid = create_payment(uid, cid, amount, credits, "manual")
    states[uid] = {'state': 'waiting_ss', 'payment_id': pid, 'amount': amount,
                    'credits': credits, 'pay_mode': 'manual'}
    txt = (f"📸 <b>{fancy('send screenshot')}</b>\n{div()}\n\n"
           f"💰 ₹{amount} → 💎 {credits}ᴄʀ\n\n"
           f"📌 ᴘᴀʏᴍᴇɴᴛ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ ʙʜᴇᴊᴏ.\n"
           f"ᴀᴅᴍɪɴ ᴠᴇʀɪꜰʏ ᴋᴀʀᴋᴇ ᴄʀᴇᴅɪᴛ ᴅᴇɢᴀ.")
    if edit_mid:
        try: bot.delete_message(cid, edit_mid)
        except: pass
    bot.send_message(cid, txt, parse_mode='HTML')

def process_check_status(uid, cid, order_id):
    p = payments_col.find_one({"order_id": order_id, "user_id": uid, "status": "pending"})
    if not p:
        bot.send_message(cid, "✅ Already processed or expired."); return
    amt = p["amount"]; cr = p["credits"]
    am = AnimMsg(cid, stages=stg_verify(), title="VERIFYING")
    am.start()
    ok, status, info = verify_gateway_order(order_id)
    am.stop()
    if ok:
        sent = _credit_on_success(uid, cid, order_id, amt, cr, info, None)
        am.flash_complete()
        if not sent:
            am.edit(f"✅ <b>Verified</b>\n💎 +{cr}ᴄʀ\n💰 {get_credits(uid)}")
        else:
            try: am.delete()
            except: pass
        states[uid] = {}
    else:
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("🔄 Check Again", callback_data=f"chk_{order_id}"),
               InlineKeyboardButton("📸 Screenshot", callback_data=f"scr_{order_id}"))
        am.edit(f"⏳ <b>Pending</b>\n\nᴘᴀʏᴍᴇɴᴛ ɴᴀʜɪ ᴍɪʟɪ ᴀʙʜɪ.", mark=kb)

def process_screenshot_prompt(uid, cid, order_id):
    p = payments_col.find_one({"order_id": order_id, "user_id": uid, "status": "pending"})
    if not p:
        bot.send_message(cid, "⚠️ Order not found or expired."); return
    states[uid] = {'state': 'waiting_ss', 'payment_id': str(p["_id"]),
                    'amount': p["amount"], 'credits': p["credits"], 'order_id': order_id}
    bot.send_message(cid, "📸 Send payment screenshot:")

# =================================================================
#  POLLER
# =================================================================
def poll_order_async(uid, cid, order_id, amount, credits, msg_id=None):
    start = time.time(); checks = 0
    while (time.time() - start) < ORDER_LIFETIME:
        time.sleep(3 if checks < 10 else 6); checks += 1
        try:
            ok, status, info = verify_gateway_order(order_id)
            if ok:
                _credit_on_success(uid, cid, order_id, amount, credits, info, msg_id); return
            if status == "expired":
                _mark_expired(order_id); return
        except Exception as e: logger.warning(f"[POLL] {checks}: {e}")
    _mark_expired(order_id)

def _mark_expired(order_id):
    try: payments_col.update_one({"order_id": order_id, "status": "pending"},
        {"$set": {"status": "expired", "expired_at": now()}})
    except: pass

def _credit_on_success(uid, cid, order_id, amount, credits, info, msg_id):
    p = payments_col.find_one({"order_id": order_id, "user_id": uid})
    if not p: return False
    utr = (info.get("utr") if info else None) or f"FG_{order_id}"
    try:
        u = payments_col.find_one_and_update({"_id": p["_id"], "status": "pending"},
            {"$set": {"status": "approved", "approved_at": now(), "utr": utr,
                      "gateway_response": (info.get("raw") if info else None),
                      "auto_verified": True}}, return_document=ReturnDocument.AFTER)
    except:
        u = payments_col.find_one_and_update({"_id": p["_id"], "status": "pending"},
            {"$set": {"status": "approved", "approved_at": now(),
                      "auto_verified": True}}, return_document=ReturnDocument.AFTER)
    if not u: return False
    add_credits(uid, credits)
    try:
        users_col.update_one({"user_id": uid},
            {"$inc": {"total_spent": amount, "total_purchased": credits}})
    except: pass
    txt = (f"✅ <b>{fancy('payment verified')}</b>\n{div()}\n\n"
           f"💰 ₹{amount}\n💎 +{credits}ᴄʀ\n"
           f"📊 ʙᴀʟᴀɴᴄᴇ: <b>{get_credits(uid)}ᴄʀ</b>\n"
           f"🆔 <code>{order_id}</code>")
    if info and info.get("utr"): txt += f"\n🧾 {info['utr']}"
    if msg_id:
        try:
            bot.edit_message_caption(chat_id=cid, message_id=msg_id, caption=txt, parse_mode='HTML')
            return True
        except: pass
    try: bot.send_message(cid, txt, parse_mode='HTML'); return True
    except: return False

def resume_pending_orders():
    try:
        pending = list(payments_col.find({"status":"pending","pay_mode":"auto",
                                          "order_id":{"$exists":True,"$ne":None}}))
    except: return
    for p in pending:
        c = p.get("created_at")
        if c and (now() - c).total_seconds() > ORDER_LIFETIME:
            _mark_expired(p["order_id"]); continue
        cid = p.get("chat_id") or p.get("user_id")
        if cid:
            threading.Thread(target=poll_order_async,
                args=(p["user_id"], cid, p["order_id"], p["amount"], p["credits"], None),
                daemon=True).start()

# =================================================================
#  AUTO BACKUP
# =================================================================
def do_auto_backup():
    try:
        data = {"users": list(users_col.find({}, {"_id": 0})),
            "payments": list(payments_col.find({}, {"_id": 0})),
            "promos": list(promo_col.find({}, {"_id": 0})),
            "groups": list(groups_col.find({}, {"_id": 0})),
            "settings": list(settings_col.find({}, {"_id": 0})),
            "feedback": list(feedback_col.find({}, {"_id": 0})),
            "notes": list(notes_col.find({}, {"_id": 0})),
            "exported_at": now().isoformat(), "exported_by": "auto_backup"}
        js = json.dumps(data, default=str, indent=2)
        bio = io.BytesIO(js.encode('utf-8'))
        bio.name = f"backup_{now().strftime('%Y%m%d_%H%M')}.json"
        bot.send_document(ADMIN_ID, bio,
            caption=f"💾 Auto-Backup\n📅 {fancy_dt()}\n📦 {len(data['users'])} users")
        return True
    except Exception as e:
        logger.error(f"Auto-backup failed: {e}"); return False

def auto_backup_worker():
    while True:
        try:
            enabled = int(get_setting("auto_backup_enabled", 0)) == 1
            if enabled:
                target_hour = int(get_setting("auto_backup_hour", 3))
                cur = now()
                last = get_setting("auto_backup_last_run", "")
                today_run_key = cur.strftime("%Y-%m-%d")
                if cur.hour == target_hour and last != today_run_key:
                    if do_auto_backup():
                        set_setting("auto_backup_last_run", today_run_key)
                        logger.info(f"✅ Auto-backup done for {today_run_key}")
            time.sleep(600)
        except Exception as e:
            logger.error(f"auto_backup_worker: {e}"); time.sleep(300)

threading.Thread(target=auto_backup_worker, daemon=True, name="AutoBackup").start()

# =================================================================
#  BROADCAST
# =================================================================
bcast_q = queue.Queue()
def bcast_worker():
    while True:
        task = bcast_q.get()
        if task is None: break
        us, msg, kw = task
        pin = int(get_setting("broadcast_pin", 0))
        for u in us:
            try:
                sent = bot.send_message(u, msg, **kw)
                if pin:
                    try: bot.pin_chat_message(u, sent.message_id)
                    except: pass
                time.sleep(0.05)
            except: pass
        bcast_q.task_done()

threading.Thread(target=bcast_worker, daemon=True).start()

def bcast_photo_worker(us, file_id, caption):
    pin = int(get_setting("broadcast_pin", 0))
    for u in us:
        try:
            sent = bot.send_photo(u, file_id, caption=caption)
            if pin:
                try: bot.pin_chat_message(u, sent.message_id)
                except: pass
            time.sleep(0.05)
        except: pass

_start_time = time.time()

# =================================================================
#  SEND RESULT
# =================================================================
def _split_safe_html(text, limit=MSG_SAFE_LIMIT):
    if len(text) <= limit: return [text]
    parts = []
    rem = text
    while rem:
        if len(rem) <= limit:
            parts.append(rem); break
        chunk = rem[:limit]
        idx = chunk.rfind('\n')
        if idx < limit // 2: idx = limit
        open_last = chunk.rfind('<')
        close_last = chunk.rfind('>')
        if open_last > close_last:
            idx = open_last if open_last < idx else idx
        piece = rem[:idx]
        open_tags = re.findall(r'<(b|i|code|pre|u|s)>', piece)
        close_tags = re.findall(r'</(b|i|code|pre|u|s)>', piece)
        opened = []
        for t in open_tags:
            if t in close_tags:
                close_tags.remove(t)
            else:
                opened.append(t)
        for t in reversed(opened):
            piece += f"</{t}>"
        parts.append(piece)
        rem = "".join(f"<{t}>" for t in opened) + rem[idx:]
    return parts

def send_result(uid, cid, txt, reply_to=None, reply_markup=None):
    is_private_chat = (cid == uid or cid > 0)
    txt = apply_banned_words(txt)
    parts = _split_safe_html(txt, MSG_SAFE_LIMIT)
    sent_msgs = []
    for i, part in enumerate(parts):
        kw = {'parse_mode': 'HTML', 'disable_web_page_preview': True}
        if i == 0 and reply_to: kw['reply_to_message_id'] = reply_to
        if i == len(parts) - 1 and reply_markup: kw['reply_markup'] = reply_markup
        try:
            m = bot.send_message(cid, part, **kw)
            sent_msgs.append(m.message_id)
        except:
            try:
                plain = re.sub(r'<[^>]+>', '', part)
                plain = html_module.unescape(plain)
                m = bot.send_message(cid, plain[:4000])
                sent_msgs.append(m.message_id)
            except: pass
    if sent_msgs and not is_private_chat and group_auto_delete():
        delay = group_auto_delete_seconds()
        delete_ids = list(sent_msgs)
        if reply_to: delete_ids.append(reply_to)
        def _del():
            time.sleep(delay)
            for mid in delete_ids:
                try: bot.delete_message(cid, mid)
                except: pass
        threading.Thread(target=_del, daemon=True).start()

# =================================================================
#  PRE-CHECK
# =================================================================
def pre_check(svc, uid, cid, reply_to, force_admin=False):
    if is_maintenance() and not is_admin_user(uid):
        msg = get_setting("maintenance_custom_msg", "") or f"🔧 {fancy('maintenance')}"
        bot.send_message(cid, msg, parse_mode='HTML', reply_to_message_id=reply_to)
        return False
    if is_banned(uid) and not is_admin_user(uid):
        bot.send_message(cid, f"🚫 {fancy('banned')}", reply_to_message_id=reply_to)
        return False
    if not ensure_service(svc, uid, cid, reply_to, force_admin=force_admin):
        return False
    return True

# =================================================================
#  PROCESSORS
# =================================================================
def process_number(uid, cid, phone, reply_to=None, force_admin=False):
    if not pre_check("number", uid, cid, reply_to, force_admin): return
    clean = extract_phone_digits(phone)
    if not clean:
        bot.send_message(cid,
            f"❌ <b>{fancy('invalid number')}</b>\n\nꜱᴇɴᴅ 10-ᴅɪɢɪᴛ.\nᴇx: <code>9876543210</code>",
            parse_mode='HTML', reply_to_message_id=reply_to); return
    phone = clean
    allowed, wait = check_rate_limit(uid, "number")
    if not allowed:
        bot.send_message(cid, rate_limit_msg(wait), parse_mode='HTML', reply_to_message_id=reply_to); return
    cost = int(get_setting("search_cost", 5))
    is_priv = is_admin_user(uid)
    if not is_priv and get_credits(uid) < cost:
        bot.send_message(cid, low_credit_text(uid, cost, get_credits(uid)),
            parse_mode='HTML', reply_to_message_id=reply_to, reply_markup=low_credit_kb(uid)); return
    ok_try, consumed = consume_try(uid)
    if not ok_try:
        bot.send_message(cid, no_tries_msg(uid), parse_mode='HTML', reply_to_message_id=reply_to); return
    mark_search_time(uid, "number")
    send_typing(cid)
    am = AnimMsg(cid, stages=stg_number(), title="NUMBER SEARCH", reply_to=reply_to)
    am.start()
    ok, data, msg = query_number(phone)
    am.stop()
    if not ok:
        log_search_history(uid, "number", phone, False)
        if int(get_setting("auto_refund_on_fail", 1)) == 1:
            refund_try(uid, consumed)
        am.edit(err_frame("NO DATA", no_data_msg(uid, "number"))); return
    records = _extract_number_records(data)
    if not records:
        log_search_history(uid, "number", phone, False)
        if int(get_setting("auto_refund_on_fail", 1)) == 1:
            refund_try(uid, consumed)
        am.edit(err_frame("NO DATA", no_data_msg(uid, "number"))); return
    if not is_priv:
        if not deduct_credits(uid, cost):
            am.edit(err_frame("ERROR", low_credit_text(uid, cost, get_credits(uid)))); return
        remaining = get_credits(uid)
    else: remaining = "♾️"
    incr_searches(uid); log_search_history(uid, "number", phone, True)
    am.flash_complete(); am.delete()
    query_info = {"number": phone, "type": "phone"}
    header = f"📞 <b>{fancy('number info')}</b> — <code>{phone}</code>\n\n"
    send_service_result(uid, cid, records, query_info, "number",
                        header, remaining, is_priv, reply_to=reply_to)

def process_aadhaar(uid, cid, aadhaar, reply_to=None, force_admin=False):
    if not pre_check("aadhaar", uid, cid, reply_to, force_admin): return
    aadhaar = re.sub(r'\D', '', str(aadhaar))
    if len(aadhaar) != 12:
        bot.send_message(cid, f"❌ <b>{fancy('invalid aadhaar')}</b>\n\nꜱᴇɴᴅ 12-ᴅɪɢɪᴛ.",
            parse_mode='HTML', reply_to_message_id=reply_to); return
    allowed, wait = check_rate_limit(uid, "aadhaar")
    if not allowed:
        bot.send_message(cid, rate_limit_msg(wait), parse_mode='HTML', reply_to_message_id=reply_to); return
    cost = int(get_setting("aadhaar_cost", 10))
    is_priv = is_admin_user(uid)
    if not is_priv and get_credits(uid) < cost:
        bot.send_message(cid, low_credit_text(uid, cost, get_credits(uid)),
            parse_mode='HTML', reply_to_message_id=reply_to, reply_markup=low_credit_kb(uid)); return
    ok_try, consumed = consume_try(uid)
    if not ok_try:
        bot.send_message(cid, no_tries_msg(uid), parse_mode='HTML', reply_to_message_id=reply_to); return
    mark_search_time(uid, "aadhaar")
    send_typing(cid)
    am = AnimMsg(cid, stages=stg_aadhaar(), title="AADHAAR SEARCH", reply_to=reply_to)
    am.start()
    ok, data, msg = query_aadhaar(aadhaar)
    am.stop()
    if not ok:
        log_search_history(uid, "aadhaar", aadhaar, False)
        if int(get_setting("auto_refund_on_fail", 1)) == 1:
            refund_try(uid, consumed)
        am.edit(err_frame("NO DATA", no_data_msg(uid, "aadhaar"))); return
    records = _extract_number_records(data)
    if not records:
        log_search_history(uid, "aadhaar", aadhaar, False)
        if int(get_setting("auto_refund_on_fail", 1)) == 1:
            refund_try(uid, consumed)
        am.edit(err_frame("NO DATA", no_data_msg(uid, "aadhaar"))); return
    if not is_priv:
        if not deduct_credits(uid, cost):
            am.edit(err_frame("ERROR", low_credit_text(uid, cost, get_credits(uid)))); return
        remaining = get_credits(uid)
    else: remaining = "♾️"
    incr_searches(uid); log_search_history(uid, "aadhaar", f"****{aadhaar[-4:]}", True)
    am.flash_complete(); am.delete()
    query_info = {"aadhaar": f"****{aadhaar[-4:]}", "type": "aadhaar"}
    header = f"🆔 <b>{fancy('aadhaar info')}</b> — <code>****{aadhaar[-4:]}</code>\n\n"
    send_service_result(uid, cid, records, query_info, "aadhaar",
                        header, remaining, is_priv, reply_to=reply_to)

def process_vehicle(uid, cid, vehicle, reply_to=None, force_admin=False):
    if not pre_check("vehicle", uid, cid, reply_to, force_admin): return
    v = re.sub(r'[\s\-]', '', str(vehicle)).upper()
    if not is_vehicle_number(v):
        bot.send_message(cid, f"❌ <b>{fancy('invalid vehicle')}</b>\n\nᴇx: <code>JH15U4500</code>",
            parse_mode='HTML', reply_to_message_id=reply_to); return
    vehicle = v
    allowed, wait = check_rate_limit(uid, "vehicle")
    if not allowed:
        bot.send_message(cid, rate_limit_msg(wait), parse_mode='HTML', reply_to_message_id=reply_to); return
    cost = int(get_setting("vehicle_cost", 10))
    is_priv = is_admin_user(uid)
    if not is_priv and get_credits(uid) < cost:
        bot.send_message(cid, low_credit_text(uid, cost, get_credits(uid)),
            parse_mode='HTML', reply_to_message_id=reply_to, reply_markup=low_credit_kb(uid)); return
    ok_try, consumed = consume_try(uid)
    if not ok_try:
        bot.send_message(cid, no_tries_msg(uid), parse_mode='HTML', reply_to_message_id=reply_to); return
    mark_search_time(uid, "vehicle")
    send_typing(cid)
    am = AnimMsg(cid, stages=stg_vehicle(), title="VEHICLE SEARCH", reply_to=reply_to)
    am.start()
    ok, data, msg = query_vehicle(vehicle)
    am.stop()
    if not ok:
        log_search_history(uid, "vehicle", vehicle, False)
        if int(get_setting("auto_refund_on_fail", 1)) == 1:
            refund_try(uid, consumed)
        am.edit(err_frame("NO DATA", no_data_msg(uid, "vehicle"))); return
    records = _extract_number_records(data)
    if not records:
        log_search_history(uid, "vehicle", vehicle, False)
        if int(get_setting("auto_refund_on_fail", 1)) == 1:
            refund_try(uid, consumed)
        am.edit(err_frame("NO DATA", no_data_msg(uid, "vehicle"))); return
    if not is_priv:
        if not deduct_credits(uid, cost):
            am.edit(err_frame("ERROR", low_credit_text(uid, cost, get_credits(uid)))); return
        remaining = get_credits(uid)
    else: remaining = "♾️"
    incr_searches(uid); log_search_history(uid, "vehicle", vehicle, True)
    am.flash_complete(); am.delete()
    query_info = {"vehicle": vehicle, "type": "vehicle"}
    header = f"🚗 <b>{fancy('vehicle info')}</b> — <code>{vehicle}</code>\n\n"
    send_service_result(uid, cid, records, query_info, "vehicle",
                        header, remaining, is_priv, reply_to=reply_to)

def process_tg2num(uid, cid, query, reply_to=None, force_admin=False):
    if not pre_check("username", uid, cid, reply_to, force_admin): return
    allowed, wait = check_rate_limit(uid, "username")
    if not allowed:
        bot.send_message(cid, rate_limit_msg(wait), parse_mode='HTML', reply_to_message_id=reply_to); return
    cost = int(get_setting("tg2num_cost", 5))
    is_priv = is_admin_user(uid)
    if not is_priv and get_credits(uid) < cost:
        bot.send_message(cid, low_credit_text(uid, cost, get_credits(uid)),
            parse_mode='HTML', reply_to_message_id=reply_to, reply_markup=low_credit_kb(uid)); return
    ok_try, consumed = consume_try(uid)
    if not ok_try:
        bot.send_message(cid, no_tries_msg(uid), parse_mode='HTML', reply_to_message_id=reply_to); return
    mark_search_time(uid, "username")
    send_typing(cid)
    am = AnimMsg(cid, stages=stg_tg(), title="USERNAME SEARCH", reply_to=reply_to)
    am.start()
    resolved, src = resolve_any(query)
    tg_id = None
    if resolved and resolved.get("user_id"): tg_id = resolved.get("user_id")
    if not tg_id and str(query).strip().isdigit(): tg_id = int(str(query).strip())
    result = None
    if tg_id:
        ok_c, res_c, msg_c = query_tg2num_id(tg_id)
        if ok_c: result = res_c
    am.stop()
    if not result or not result.get("number"):
        log_search_history(uid, "username", str(query), False)
        if int(get_setting("auto_refund_on_fail", 1)) == 1:
            refund_try(uid, consumed)
        am.edit(err_frame("NO DATA", no_data_msg(uid, "username"))); return
    if not is_priv:
        if not deduct_credits(uid, cost):
            am.edit(err_frame("ERROR", low_credit_text(uid, cost, get_credits(uid)))); return
        remaining = get_credits(uid)
    else: remaining = "♾️"
    incr_searches(uid); log_search_history(uid, "username", str(query), True)
    am.flash_complete(); am.delete()
    api_tg_id = result.get("tg_id") or tg_id
    country = result.get("country"); cc = result.get("country_code"); number = result.get("number")
    records = [{"tg_id": str(api_tg_id) if api_tg_id else "", "country": country or "",
                "country_code": cc or "", "number": number or ""}]
    query_info = {"query": str(query), "type": "username"}
    header = f"🔒 <b>{fancy('username to info')}</b> — <code>{html_module.escape(str(query))}</code>\n\n"
    if src:
        src_map = {"mtproto": "🛰️ ᴍᴛᴘʀᴏᴛᴏ", "cache": "💾 ᴄᴀᴄʜᴇ", "telegram_api": "🌐 ᴛɢ ᴀᴘɪ"}
        header += f"📡 ꜱᴏᴜʀᴄᴇ: {src_map.get(src, src)}\n\n"
    reply_markup = None
    full_number = normalize_phone(number, cc) if number else None
    if full_number:
        wa_msg = random.choice(["Hi", "Hello", "Hey", "Hi!", "Hello 👋", "Hey there"])
        wa_url = f"https://wa.me/{full_number}?text={requests.utils.quote(wa_msg)}"
        reply_markup = InlineKeyboardMarkup(row_width=1)
        reply_markup.row(InlineKeyboardButton("💬 ᴡʜᴀᴛꜱᴀᴘᴘ", url=wa_url))
    send_service_result(uid, cid, records, query_info, "username",
                        header, remaining, is_priv, reply_to=reply_to, reply_markup=reply_markup)

# =================================================================
#  ★★★ FJ MANAGER — REAL CHECK FIX ★★★
# =================================================================
class FJManager:
    def __init__(self, bot):
        self.bot = bot
        self.pending = {}
        self.msg = {}
        # ✅ verify_clicked REMOVED — ab sirf real API check
        self.channels = []
        self.global_enabled = False
        self._load()

    def _load(self):
        try:
            bi = self.bot.get_me()
        except:
            self.channels = []
            self.global_enabled = False
            return
        valid = []
        failed = []
        for c in all_channels():
            try:
                m = self.bot.get_chat_member(c["channel_id"], bi.id)
                if m.status in ('administrator', 'creator'):
                    valid.append((c["channel_id"], c["channel_link"]))
                else:
                    failed.append((c["channel_id"], m.status))
            except Exception as e:
                failed.append((c["channel_id"], str(e)[:60]))
        self.channels = valid
        self.global_enabled = str(get_setting("force_enabled", "1")) == "1"
        if failed:
            logger.warning(f"⚠️ FJ: {len(failed)} channel(s) failed admin check")

    def reload(self):
        self._load()

    def is_on(self):
        return self.global_enabled and bool(self.channels)

    def _is_private(self, link):
        s = str(link or "")
        return '+' in s or 'joinchat' in s

    def check(self, uid):
        """
        ✅ REAL CHECK — always uses get_chat_member API.
        No blind trust. Join nahi kiya to missing return karega.
        """
        if not self.is_on():
            return None
        if is_admin_user(uid):
            return None

        missing = []
        for cid, link in self.channels:
            joined = False
            try:
                m = self.bot.get_chat_member(cid, uid)
                status = str(getattr(m, 'status', '')).lower()
                # Ye statuses joined maane jayenge
                if status in ('member', 'administrator', 'creator', 'restricted'):
                    joined = True
            except Exception as e:
                err = str(e).lower()
                # Ye errors = user NOT joined
                if ('user_not_participant' in err
                    or 'user not participant' in err
                    or 'user not found' in err
                    or 'peer_id_invalid' in err
                    or 'participant' in err):
                    joined = False
                elif 'chat_admin_required' in err or 'bot is not a member' in err:
                    # Bot admin nahi hai to check skip karo (admin ko warning already mila)
                    logger.warning(f"FJ skip {cid}: bot not admin")
                    joined = True  # assume joined to avoid blocking users
                else:
                    # Unknown error → conservative: check fail → mark missing
                    logger.warning(f"FJ err {cid}: {e}")
                    joined = False
            if not joined:
                missing.append((cid, link))
        return missing if missing else None

    def ensure(self, uid, cid, pending=None):
        try:
            chat = self.bot.get_chat(cid)
            if chat.type != 'private':
                return True
        except:
            return True
        if is_admin_user(uid):
            return True
        if self.check(uid) is None:
            return True
        if pending:
            self.pending[uid] = pending
        old = self.msg.pop(uid, None)
        if old:
            try:
                self.bot.delete_message(cid, old)
            except:
                pass
        missing = self.check(uid)
        if not missing:
            return True
        kb = InlineKeyboardMarkup(row_width=1)
        for i, (ch, lk) in enumerate(missing[:100]):
            kb.add(InlineKeyboardButton(f"📢 Channel {i+1}", url=lk))
        kb.add(InlineKeyboardButton("✅ Verify", callback_data="force_verify"))
        cm = get_setting("fj_custom_msg", "")
        if cm:
            text = cm
        else:
            text = (f"⚠️ <b>{fancy('please join channels')}</b>\n\n"
                    f"ᴊᴏɪɴ ᴋᴀʀᴋᴇ ᴠᴇʀɪꜰʏ ᴅᴀʙᴀᴏ.\n\n"
                    f"<i>ᴘᴠᴛ ᴄʜᴀɴɴᴇʟ ᴍᴇ ʀᴇQᴜᴇꜱᴛ ʙʜᴇᴊᴏ, ᴀᴜᴛᴏ ᴀᴘᴘʀᴏᴠᴇ ʜᴏ ᴊᴀʏᴇɢᴀ.</i>")
        try:
            s = self.bot.send_message(cid, text, parse_mode='HTML', reply_markup=kb)
            self.msg[uid] = s.message_id
            try:
                settings_col.update_one({"key": "fj_stats_blocks"}, {"$inc": {"value": 1}}, upsert=True)
            except:
                pass
        except:
            pass
        return False

    def verify_cb(self, call):
        uid = call.from_user.id
        cid = call.message.chat.id

        # ✅ FIX: Real check only. 1 sec delay for Telegram sync.
        time.sleep(1)

        missing = self.check(uid)

        if missing is None:
            # ✅ User joined — verified!
            mid = self.msg.pop(uid, None)
            if mid:
                try:
                    self.bot.delete_message(cid, mid)
                except:
                    pass
            p = self.pending.pop(uid, None)
            if p:
                self._exec(uid, cid, p, call)
            else:
                uname = call.from_user.username or "user"
                self.bot.send_message(cid, welcome_txt(uid, uname),
                    parse_mode='HTML', reply_markup=main_kb(uid))
            try:
                settings_col.update_one({"key": "fj_stats_verifies"},
                    {"$inc": {"value": 1}}, upsert=True)
            except:
                pass
            try:
                self.bot.answer_callback_query(call.id, "✅ Verified!")
            except:
                pass
        else:
            # ❌ User NOT joined — fail!
            om = self.msg.pop(uid, None)
            if om:
                try:
                    self.bot.delete_message(cid, om)
                except:
                    pass
            try:
                self.bot.answer_callback_query(call.id,
                    "❌ Pehle channel join karo!", show_alert=True)
            except:
                pass
            # Re-show prompt
            self.ensure(uid, cid)

    def _exec(self, uid, cid, p, call):
        t, d = p.get('type'), p.get('data')
        if t == 'number_search':
            process_number(uid, cid, d)
        elif t == 'aadhaar_search':
            process_aadhaar(uid, cid, d)
        elif t == 'vehicle_search':
            process_vehicle(uid, cid, d)
        elif t == 'tg2num_search':
            process_tg2num(uid, cid, d)
        elif t == 'menu_button':
            process_menu(uid, cid, d)
        elif t == 'promo_redeem':
            process_promo(uid, cid, d)
        else:
            uname = call.from_user.username or "user"
            self.bot.send_message(cid, welcome_txt(uid, uname),
                parse_mode='HTML', reply_markup=main_kb(uid))

    def toggle(self):
        cur = str(get_setting("force_enabled", "1")) == "1"
        set_setting("force_enabled", "0" if cur else "1")
        self.reload()
        return not cur

    def add(self, cid, link=None):
        if not link:
            return False, "Link required"
        if not link.startswith("http"):
            return False, "Invalid"
        try:
            bi = self.bot.get_me()
            m = self.bot.get_chat_member(cid, bi.id)
            if m.status not in ('administrator', 'creator'):
                return False, f"Bot is {m.status}"
        except Exception as e:
            return False, str(e)
        if not add_channel_db(cid, link):
            return False, "Already exists"
        self.reload()
        return True, "Added"

    def rm(self, cid):
        if remove_channel_db(cid):
            self.reload()
            return True, "Removed"
        return False, "Not found"

    def stats(self):
        try:
            b = settings_col.find_one({"key": "fj_stats_blocks"})
            v = settings_col.find_one({"key": "fj_stats_verifies"})
            return {
                "blocks": b.get("value", 0) if b else 0,
                "verifies": v.get("value", 0) if v else 0,
            }
        except:
            return {"blocks": 0, "verifies": 0}

manager = None
states = {}

# =================================================================
#  WELCOME / HELP
# =================================================================
def welcome_txt(uid, uname):
    e = get_setting("welcome_emoji", "") or random.choice(WELCOME_EMOJIS)
    u = get_or_create_user(uid)
    cr = u.get("credits", 0); banned = u.get("banned")
    if is_admin_user(uid): cd = "♾️ ᴜɴʟɪᴍɪᴛᴇᴅ"
    elif banned: cd = "🚫 ʙᴀɴɴᴇᴅ"
    else: cd = f"{cr} ᴄʀ"
    wb = get_setting("welcome_bonus", WELCOME_BONUS)
    bonus_line = ""
    if not banned:
        bonus_line = f"🎁 <b>{fancy('welcome bonus')}: {wb} ꜰʀᴇᴇ ᴄʀᴇᴅɪᴛꜱ!</b>\n\n"
    return (f"👋 <b>{fancy('hello')}</b> @{uname}\n🆔 <code>{uid}</code>\n"
            f"💎 ᴄʀᴇᴅɪᴛꜱ: {cd}\n🎯 ᴛʀɪᴇꜱ: {tries_display(uid)}\n\n{bonus_line}"
            f"<b>{fancy('services')}:</b>\n"
            f"📞 ɴᴜᴍʙᴇʀ — {get_setting('search_cost',5)}ᴄʀ\n"
            f"🔒 ᴜꜱᴇʀɴᴀᴍᴇ — {get_setting('tg2num_cost',5)}ᴄʀ\n"
            f"🆔 ᴀᴀᴅʜᴀᴀʀ — {get_setting('aadhaar_cost',10)}ᴄʀ\n"
            f"🚗 ᴠᴇʜɪᴄʟᴇ — {get_setting('vehicle_cost',10)}ᴄʀ\n\n{e}")

def group_help_txt():
    lines = [f"👥 <b>{fancy('group commands')}</b>", div(), ""]
    for svc in SERVICE_KEYS:
        emoji = SERVICE_EMOJI.get(svc, "🔹")
        st = "🟢" if is_service_enabled(svc) else "🔴"
        if svc == "number": usage = "/num 9876543210"
        elif svc == "aadhaar": usage = "/aadhar 123456789012"
        elif svc == "username": usage = "/tg @username"
        elif svc == "vehicle": usage = "/vehicle DL01AB1234"
        else: usage = "/"
        lines.append(f"{st} {emoji} <code>{usage}</code>")
    lines.append("")
    lines.append(div_soft())
    lines.append(f"💡 <i>ɢʀᴏᴜᴘ ᴍᴇ ꜱɪʀꜰ ᴄᴏᴍᴍᴀɴᴅꜱ ᴡᴏʀᴋ ᴋᴀʀᴛᴇ ʜᴀɪɴ</i>")
    return "\n".join(lines)

def extract_cmd_args(text):
    if not text: return ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2: return ""
    return parts[1].strip()

# =================================================================
#  MENU
# =================================================================
def process_menu(uid, cid, text, reply_to=None):
    upd_last_seen(uid)
    is_admin = is_admin_user(uid)

    if text == "👑 ADMIN PANEL":
        if not is_admin:
            bot.send_message(cid, "❌ Admin only", reply_to_message_id=reply_to); return
        txt = (f"👑 <b>{fancy('admin panel v28.2')}</b>\n{div()}\n"
               f"ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴜʟᴛʀᴀ ᴄᴏɴᴛʀᴏʟ ᴄᴇɴᴛᴇʀ")
        bot.send_message(cid, txt, parse_mode='HTML',
            reply_markup=admin_kb(), reply_to_message_id=reply_to); return

    if text == "🔙 Back to Menu":
        bot.send_message(cid, f"🔙 {fancy('menu')}", reply_markup=main_kb(uid),
            reply_to_message_id=reply_to); return

    if is_admin:
        if text == "📊 Dashboard":
            p, a, r, rev, rf = pay_stats()
            txt = (f"📊 <b>{fancy('dashboard')}</b>\n{div()}\n\n"
                   f"👥 ᴜꜱᴇʀꜱ: <b>{total_users()}</b>\n"
                   f"🆕 ɴᴇᴡ (24ʜ): <b>{new_users_24h()}</b>\n"
                   f"👥 ɢʀᴏᴜᴘꜱ: <b>{group_count()}</b>\n"
                   f"🔍 ꜱᴇᴀʀᴄʜᴇꜱ: <b>{total_searches()}</b>\n"
                   f"🔥 ʟᴀꜱᴛ 1ʜ: <b>{searches_1h()}</b>\n\n"
                   f"💰 ᴘᴇɴᴅɪɴɢ: <b>{p}</b> | ✅ <b>{a}</b> | ❌ <b>{r}</b> | 💸 <b>{rf}</b>\n"
                   f"💵 ᴛᴏᴛᴀʟ ʀᴇᴠᴇɴᴜᴇ: <b>₹{rev}</b>\n"
                   f"📈 ʀᴇᴠ (24ʜ): <b>₹{revenue_24h()}</b>\n"
                   f"📅 ᴛᴏᴅᴀʏ: <b>₹{revenue_today()}</b> | ᴋᴀʟ: <b>₹{revenue_yesterday()}</b>\n"
                   f"🎯 ᴄᴏɴᴠᴇʀꜱɪᴏɴ: <b>{conversion_rate()}%</b>")
            bot.send_message(cid, txt, parse_mode='HTML',
                reply_markup=dashboard_kb(), reply_to_message_id=reply_to); return
        if text == "👥 Users":
            bot.send_message(cid, f"👥 <b>{fancy('user management')}</b>", parse_mode='HTML',
                reply_markup=users_kb(), reply_to_message_id=reply_to); return
        if text == "💳 Payments":
            bot.send_message(cid, f"💳 <b>{fancy('payment management')}</b>", parse_mode='HTML',
                reply_markup=payments_kb(), reply_to_message_id=reply_to); return
        if text == "🔧 Services":
            bot.send_message(cid, f"🔧 <b>{fancy('service configuration')}</b>", parse_mode='HTML',
                reply_markup=services_kb(), reply_to_message_id=reply_to); return
        if text == "🎟 Promos":
            bot.send_message(cid, f"🎟 <b>{fancy('promo management')}</b>", parse_mode='HTML',
                reply_markup=promos_kb(), reply_to_message_id=reply_to); return
        if text == "📢 Broadcast":
            bot.send_message(cid, f"📢 <b>{fancy('broadcast center')}</b>", parse_mode='HTML',
                reply_markup=broadcast_kb(), reply_to_message_id=reply_to); return
        if text == "📢 Force Join":
            bot.send_message(cid, f"📢 <b>{fancy('force join')}</b>", parse_mode='HTML',
                reply_markup=force_kb(), reply_to_message_id=reply_to); return
        if text == "👥 Groups":
            txt = f"👥 <b>{fancy('group management')}</b>\n{div()}\n\nᴛᴏᴛᴀʟ: <b>{group_count()}</b>"
            bot.send_message(cid, txt, parse_mode='HTML',
                reply_markup=groups_kb(), reply_to_message_id=reply_to); return
        if text == "⚙️ Settings":
            bot.send_message(cid, f"⚙️ <b>{fancy('admin settings')}</b>",
                parse_mode='HTML', reply_markup=settings_main_kb(), reply_to_message_id=reply_to); return
        if text == "🛡️ Security":
            bot.send_message(cid, f"🛡️ <b>{fancy('security')}</b>", parse_mode='HTML',
                reply_markup=security_kb(), reply_to_message_id=reply_to); return
        if text == "📈 Analytics":
            bot.send_message(cid, f"📈 <b>{fancy('analytics')}</b>",
                parse_mode='HTML', reply_markup=analytics_kb(), reply_to_message_id=reply_to); return
        if text == "💾 Backup":
            bot.send_message(cid, f"💾 <b>{fancy('backup & export')}</b>",
                parse_mode='HTML', reply_markup=backup_kb(), reply_to_message_id=reply_to); return
        if text == "📮 Feedback":
            cnt = feedback_col.count_documents({})
            bot.send_message(cid, f"📮 <b>Feedback ({cnt})</b>",
                parse_mode='HTML', reply_markup=feedback_kb(), reply_to_message_id=reply_to); return
        if text == "🔒 Audit Log":
            send_audit_panel(uid, cid, reply_to); return
        if text == "🚀 Bot Info":
            uptime = time.time() - _start_time
            hh = int(uptime // 3600); mm = int((uptime % 3600) // 60)
            txt = (f"🚀 <b>{fancy('bot info')}</b>\n{div()}\n\n"
                   f"📛 ɴᴀᴍᴇ: <b>{BOT_USERNAME}</b>\n"
                   f"⏱ ᴜᴘᴛɪᴍᴇ: <b>{hh}h {mm}m</b>\n"
                   f"🛰️ ᴘʏʀᴏɢʀᴀᴍ: <b>{'✅ READY' if _pyro_ready else '🔴 DISABLED'}</b>\n"
                   f"🔒 ᴀᴜᴅɪᴛ: <b>{audit_count()}</b>\n"
                   f"🐍 ᴠᴇʀꜱɪᴏɴ: <b>v28.2 FINAL</b>")
            bot.send_message(cid, txt, parse_mode='HTML',
                reply_markup=botinfo_kb(), reply_to_message_id=reply_to); return
        if text == "📝 Logs":
            try:
                logs = list(logs_col.find().sort("at", -1).limit(20))
                if not logs:
                    bot.send_message(cid, "No logs yet.", reply_to_message_id=reply_to); return
                r = f"📝 <b>{fancy('recent logs')}</b>\n{div()}\n\n"
                for lg in logs:
                    t = lg.get("at", "").strftime("%d-%b %H:%M") if lg.get("at") else "?"
                    r += f"<code>{t}</code> | {lg.get('action','?')}\n"
                bot.send_message(cid, r[:4000], parse_mode='HTML', reply_to_message_id=reply_to)
            except Exception as e:
                bot.send_message(cid, f"❌ {e}", reply_to_message_id=reply_to)
            return

    if is_maintenance() and not is_admin:
        msg = get_setting("maintenance_custom_msg", "") or f"🔧 {fancy('maintenance')}"
        bot.send_message(cid, msg, parse_mode='HTML', reply_to_message_id=reply_to); return
    if is_banned(uid) and not is_admin:
        bot.send_message(cid, f"🚫 {fancy('banned')}", reply_to_message_id=reply_to); return

    if text == "📞 Number To Info":
        if not ensure_service("number", uid, cid, reply_to): return
        states[uid] = {'state': 'awaiting_number'}
        bot.send_message(cid, f"📱 <b>{fancy('send number')}</b>\n\n"
            f"• <code>9876543210</code>\n• <code>+919876543210</code>\n\n"
            f"ᴄᴏꜱᴛ: {get_setting('search_cost',5)}ᴄʀ",
            parse_mode='HTML', reply_to_message_id=reply_to)
    elif text == "🔒 Username To Info":
        if not ensure_service("username", uid, cid, reply_to): return
        states[uid] = {'state': 'awaiting_username'}
        bot.send_message(cid, f"🔒 <b>{fancy('username to info')}</b>\n\nꜱᴇɴᴅ:\n"
            f"• <code>@username</code>\n• <code>t.me/username</code>\n\n"
            f"ᴄᴏꜱᴛ: {get_setting('tg2num_cost',5)}ᴄʀ",
            parse_mode='HTML', reply_to_message_id=reply_to)
    elif text == "🆔 Aadhaar To Info":
        if not ensure_service("aadhaar", uid, cid, reply_to): return
        states[uid] = {'state': 'awaiting_aadhaar'}
        bot.send_message(cid, f"🆔 <b>{fancy('send 12-digit aadhaar')}</b>\n\nᴄᴏꜱᴛ: {get_setting('aadhaar_cost',10)}ᴄʀ",
            parse_mode='HTML', reply_to_message_id=reply_to)
    elif text == "🚗 Vehicle Info":
        if not ensure_service("vehicle", uid, cid, reply_to): return
        states[uid] = {'state': 'awaiting_vehicle'}
        bot.send_message(cid,
            f"🚗 <b>{fancy('send vehicle number')}</b>\n\n"
            f"• <code>JH15U4500</code>\n• <code>DL01AB1234</code>\n\n"
            f"ᴄᴏꜱᴛ: {get_setting('vehicle_cost',10)}ᴄʀ",
            parse_mode='HTML', reply_to_message_id=reply_to)
    elif text == "💰 Refer & Earn":
        link = f"https://t.me/{BOT_USERNAME.replace('@','')}?start=ref_{uid}"
        refs, bonus, searches = user_stats(uid)
        rb = get_setting("referral_bonus", 10)
        r = (f"🎁 <b>{fancy('refer and earn')}</b>\n\n"
             f"🔗 ʏᴏᴜʀ ʟɪɴᴋ:\n<code>{link}</code>\n\n"
             f"📌 +{rb} ᴄʀ ᴘᴇʀ ʀᴇꜰᴇʀʀᴀʟ\n\n📊 ʀᴇꜰꜱ: {refs} | ʙᴏɴᴜꜱ: {bonus}")
        kb = InlineKeyboardMarkup(row_width=2)
        kb.row(InlineKeyboardButton("📋 Copy", callback_data=f"copyref_{uid}"),
               InlineKeyboardButton("🔙", callback_data="home"))
        bot.send_message(cid, r, parse_mode='HTML', reply_markup=kb, reply_to_message_id=reply_to)
    elif text == "🛒 Buy Credits":
        show_buy_menu(uid, cid, reply_to)
    elif text == "🎟 Redeem Code":
        states[uid] = {'state': 'awaiting_promo'}
        bot.send_message(cid, "🎟 Send code:", reply_to_message_id=reply_to)
    elif text == "👤 My Profile":
        u = get_or_create_user(uid)
        st = "👑 ᴀᴅᴍɪɴ" if is_admin else ("🚫 ʙᴀɴɴᴇᴅ" if u.get("banned") else f"{u.get('credits',0)} ᴄʀ")
        refs, bonus, searches = user_stats(uid)
        total_amt, total_cr, order_count = user_purchase_stats(uid)
        r = (f"👤 <b>{fancy('profile')}</b>\n{div()}\n\n🆔 <code>{uid}</code>\n"
             f"💎 ᴄʀᴇᴅɪᴛꜱ: <b>{st}</b>\n🎯 ᴛʀɪᴇꜱ: {tries_display(uid)}\n\n"
             f"📌 ʀᴇꜰꜱ: {refs}\n🎁 ʙᴏɴᴜꜱ: {bonus}\n🔍 ꜱᴇᴀʀᴄʜᴇꜱ: {searches}\n\n"
             f"💳 ᴛᴏᴛᴀʟ ꜱᴘᴇɴᴛ: ₹{total_amt}\n"
             f"💎 ᴘᴜʀᴄʜᴀꜱᴇᴅ: {total_cr}ᴄʀ\n"
             f"🧾 ᴏʀᴅᴇʀꜱ: {order_count}")
        bot.send_message(cid, r, parse_mode='HTML', reply_to_message_id=reply_to)
    elif text == "➕ Add Me To Group":
        bot_username = BOT_USERNAME.replace('@','')
        group_url = f"https://t.me/{bot_username}?startgroup=true"
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("➕ ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴘ", url=group_url))
        bot.send_message(cid,
            f"👥 <b>{fancy('add me to your group')}</b>\n\nᴀᴅᴅ ᴛʜɪꜱ ʙᴏᴛ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ!",
            parse_mode='HTML', reply_markup=kb, reply_to_message_id=reply_to)
    elif text == "❓ Help":
        bot.send_message(cid, f"📞 ᴄᴏɴᴛᴀᴄᴛ: {ADMIN_USERNAME}\n\nᴜꜱᴇ /start ꜰᴏʀ ᴍᴇɴᴜ",
            reply_to_message_id=reply_to)
    elif text == "ℹ️ About":
        about = get_setting("about_text", "") or f"ℹ️ ᴏꜱɪɴᴛ ʙᴏᴛ ᴠ28.2\n{BOT_USERNAME}"
        bot.send_message(cid, about, reply_to_message_id=reply_to)

def send_audit_panel(uid, cid, reply_to=None):
    rows = get_recent_audit(15)
    if not rows:
        bot.send_message(cid,
            f"🔒 <b>{fancy('audit log')}</b>\n{div()}\n\nɴᴏ ᴇɴᴛʀɪᴇꜱ ʏᴇᴛ.",
            parse_mode='HTML', reply_to_message_id=reply_to, reply_markup=audit_kb())
        return
    txt = f"🔒 <b>{fancy('audit log')}</b>\n{div()}\n\n"
    for r in rows:
        t = r.get("at", "").strftime("%d-%b %H:%M") if r.get("at") else "?"
        txt += (f"<code>{t}</code> | <b>{r.get('action','?')}</b>\n"
                f"   👑 <code>{r.get('admin_id')}</code>")
        if r.get("target"): txt += f" → <code>{r.get('target')}</code>"
        txt += "\n\n"
    bot.send_message(cid, txt[:4000], parse_mode='HTML',
                     reply_to_message_id=reply_to, reply_markup=audit_kb())

def process_promo(uid, cid, code, reply_to=None):
    r = redeem_promo(code, uid)
    if r is None:
        bot.send_message(cid, "❌ Invalid/expired", parse_mode='HTML', reply_to_message_id=reply_to)
    elif r == -1:
        bot.send_message(cid, "⚠️ Already used", parse_mode='HTML', reply_to_message_id=reply_to)
    else:
        bot.send_message(cid, f"✅ +{r} ᴄʀ!\nʙᴀʟᴀɴᴄᴇ: {get_credits(uid)}",
            parse_mode='HTML', reply_to_message_id=reply_to)

# =================================================================
#  COMMANDS
# =================================================================
@bot.message_handler(commands=['start'])
def cmd_start(m):
    uid = m.from_user.id
    uname = m.from_user.username or "user"
    cid = m.chat.id
    cache_tg_user(m.from_user); upd_last_seen(uid)
    if is_banned(uid) and not is_admin_user(uid):
        bot.reply_to(m, f"🚫 {fancy('banned')}"); return
    get_or_create_user(uid)
    if ' ' in m.text:
        parts = m.text.split()
        if len(parts) > 1 and parts[1].startswith('ref_'):
            try: rid = int(parts[1].replace('ref_', ''))
            except: rid = None
            if rid and rid != uid and referral_enabled():
                ex = users_col.find_one({"user_id": uid})
                if ex and not ex.get("referred_by"):
                    users_col.update_one({"user_id": uid}, {"$set": {"referred_by": rid}})
                    add_referral_bonus(rid)
                    try:
                        rb = get_setting("referral_bonus", 10)
                        bot.send_message(rid, f"🎉 ɴᴇᴡ ʀᴇꜰᴇʀʀᴀʟ!\n+{rb}ᴄʀ")
                    except: pass
    if is_group(m):
        if group_enabled():
            register_group(m.chat.id, m.chat.title, getattr(m.chat, 'username', None))
        bot.reply_to(m, group_help_txt(), parse_mode='HTML'); return
    if not manager.ensure(uid, cid, {"type": "start"}): return
    bot.reply_to(m, welcome_txt(uid, uname), parse_mode='HTML', reply_markup=main_kb(uid))

@bot.message_handler(commands=['num', 'number', 'phone'])
def cmd_group_num(m):
    uid = m.from_user.id
    cid = m.chat.id
    cache_tg_user(m.from_user); upd_last_seen(uid)
    if is_banned(uid) and not is_admin_user(uid):
        bot.reply_to(m, f"🚫 {fancy('banned')}"); return
    if is_group(m):
        if not group_enabled(): return
        register_group(m.chat.id, m.chat.title, getattr(m.chat, 'username', None))
        args = extract_cmd_args(m.text)
        if not args:
            bot.reply_to(m,
                f"📞 <b>{fancy('number search')}</b>\n\nᴜꜱᴀɢᴇ: <code>/num 9876543210</code>\n"
                f"ᴄᴏꜱᴛ: {get_setting('search_cost',5)}ᴄʀ",
                parse_mode='HTML'); return
        process_number(uid, cid, args, m.message_id)
    else:
        if not manager.ensure(uid, cid, {"type": "menu_button", "data": "📞 Number To Info"}): return
        if not ensure_service("number", uid, cid, m.message_id): return
        states[uid] = {'state': 'awaiting_number'}
        bot.reply_to(m, f"📱 <b>{fancy('send number')}</b>\n\nᴄᴏꜱᴛ: {get_setting('search_cost',5)}ᴄʀ",
                     parse_mode='HTML')

@bot.message_handler(commands=['aadhar', 'aadhaar', 'adhar'])
def cmd_group_aadhar(m):
    uid = m.from_user.id
    cid = m.chat.id
    cache_tg_user(m.from_user); upd_last_seen(uid)
    if is_banned(uid) and not is_admin_user(uid):
        bot.reply_to(m, f"🚫 {fancy('banned')}"); return
    if is_group(m):
        if not group_enabled(): return
        register_group(m.chat.id, m.chat.title, getattr(m.chat, 'username', None))
        args = extract_cmd_args(m.text)
        if not args:
            bot.reply_to(m,
                f"🆔 <b>{fancy('aadhaar search')}</b>\n\nᴜꜱᴀɢᴇ: <code>/aadhar 123456789012</code>\n"
                f"ᴄᴏꜱᴛ: {get_setting('aadhaar_cost',10)}ᴄʀ", parse_mode='HTML'); return
        process_aadhaar(uid, cid, args, m.message_id)
    else:
        if not manager.ensure(uid, cid, {"type": "menu_button", "data": "🆔 Aadhaar To Info"}): return
        if not ensure_service("aadhaar", uid, cid, m.message_id): return
        states[uid] = {'state': 'awaiting_aadhaar'}
        bot.reply_to(m, f"🆔 <b>{fancy('send 12-digit aadhaar')}</b>\n\nᴄᴏꜱᴛ: {get_setting('aadhaar_cost',10)}ᴄʀ",
                     parse_mode='HTML')

@bot.message_handler(commands=['tg', 'username', 'uname', 'info'])
def cmd_group_tg(m):
    uid = m.from_user.id
    cid = m.chat.id
    cache_tg_user(m.from_user); upd_last_seen(uid)
    if is_banned(uid) and not is_admin_user(uid):
        bot.reply_to(m, f"🚫 {fancy('banned')}"); return
    if is_group(m):
        if not group_enabled(): return
        register_group(m.chat.id, m.chat.title, getattr(m.chat, 'username', None))
        args = extract_cmd_args(m.text)
        if not args:
            bot.reply_to(m,
                f"🔒 <b>{fancy('username to info')}</b>\n\nᴜꜱᴀɢᴇ: <code>/tg @username</code>\n"
                f"ᴄᴏꜱᴛ: {get_setting('tg2num_cost',5)}ᴄʀ", parse_mode='HTML'); return
        process_tg2num(uid, cid, args, m.message_id)
    else:
        if not manager.ensure(uid, cid, {"type": "menu_button", "data": "🔒 Username To Info"}): return
        if not ensure_service("username", uid, cid, m.message_id): return
        states[uid] = {'state': 'awaiting_username'}
        bot.reply_to(m, f"🔒 <b>{fancy('username to info')}</b>\n\nᴄᴏꜱᴛ: {get_setting('tg2num_cost',5)}ᴄʀ",
                     parse_mode='HTML')

@bot.message_handler(commands=['vehicle', 'rc', 'vnum', 'car'])
def cmd_group_vehicle(m):
    uid = m.from_user.id
    cid = m.chat.id
    cache_tg_user(m.from_user); upd_last_seen(uid)
    if is_banned(uid) and not is_admin_user(uid):
        bot.reply_to(m, f"🚫 {fancy('banned')}"); return
    if is_group(m):
        if not group_enabled(): return
        register_group(m.chat.id, m.chat.title, getattr(m.chat, 'username', None))
        args = extract_cmd_args(m.text)
        if not args:
            bot.reply_to(m,
                f"🚗 <b>{fancy('vehicle search')}</b>\n\nᴜꜱᴀɢᴇ: <code>/vehicle DL01AB1234</code>\n"
                f"ᴄᴏꜱᴛ: {get_setting('vehicle_cost',10)}ᴄʀ", parse_mode='HTML'); return
        process_vehicle(uid, cid, args, m.message_id)
    else:
        if not manager.ensure(uid, cid, {"type": "menu_button", "data": "🚗 Vehicle Info"}): return
        if not ensure_service("vehicle", uid, cid, m.message_id): return
        states[uid] = {'state': 'awaiting_vehicle'}
        bot.reply_to(m, f"🚗 <b>{fancy('send vehicle number')}</b>\n\nᴄᴏꜱᴛ: {get_setting('vehicle_cost',10)}ᴄʀ",
                     parse_mode='HTML')

@bot.message_handler(commands=['grouphelp', 'ghelp'])
def cmd_group_help(m):
    bot.reply_to(m, group_help_txt(), parse_mode='HTML')

@bot.message_handler(commands=['buy'])
def cmd_buy(m):
    uid = m.from_user.id
    cache_tg_user(m.from_user)
    if is_group(m):
        bot.reply_to(m, "💡 ᴜꜱᴇ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ: " + f"https://t.me/{BOT_USERNAME.replace('@','')}")
        return
    if not manager.ensure(uid, m.chat.id): return
    show_buy_menu(uid, m.chat.id)

@bot.message_handler(commands=['admin'])
def cmd_admin(m):
    uid = m.from_user.id
    if not is_admin_user(uid): bot.reply_to(m, "❌ Admin only"); return
    if is_group(m): bot.reply_to(m, "💡 ᴜꜱᴇ ᴘʀɪᴠᴀᴛᴇ"); return
    bot.reply_to(m, f"👑 <b>{fancy('admin panel v28.2')}</b>", parse_mode='HTML', reply_markup=admin_kb())

@bot.message_handler(commands=['cancel'])
def cmd_cancel(m):
    uid = m.from_user.id
    if uid in states:
        states.pop(uid, None); bot.reply_to(m, "✅ Cancelled.")
    else: bot.reply_to(m, "Nothing to cancel.")

@bot.message_handler(commands=['addgroup'])
def cmd_addgroup(m):
    bot_username = BOT_USERNAME.replace('@','')
    group_url = f"https://t.me/{bot_username}?startgroup=true"
    kb = InlineKeyboardMarkup().row(InlineKeyboardButton("➕ ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴘ", url=group_url))
    bot.reply_to(m, f"👥 <b>{fancy('add me to group')}</b>", parse_mode='HTML', reply_markup=kb)

@bot.message_handler(commands=['my_tries'])
def cmd_my_tries(m):
    bot.reply_to(m, f"🎯 ᴛʀɪᴇꜱ: <b>{tries_display(m.from_user.id)}</b>", parse_mode='HTML')

@bot.message_handler(commands=['help'])
def cmd_help(m):
    if is_group(m): bot.reply_to(m, group_help_txt(), parse_mode='HTML'); return
    txt = (f"❓ <b>{fancy('help')}</b>\n{div()}\n\n"
           f"<b>ᴄᴏᴍᴍᴀɴᴅꜱ:</b>\n"
           f"/start — ᴍᴇɴᴜ\n/buy — ʙᴜʏ ᴄʀᴇᴅɪᴛꜱ\n/my_tries — ᴛʀɪᴇꜱ\n"
           f"/help — ᴛʜɪꜱ\n/addgroup — ᴀᴅᴅ ʙᴏᴛ\n/feedback — ꜰᴇᴇᴅʙᴀᴄᴋ\n/cancel — ᴀʙᴏʀᴛ\n\n"
           f"<b>ɢʀᴏᴜᴘ:</b>\n<code>/num 9876543210</code>\n"
           f"<code>/aadhar 123456789012</code>\n<code>/tg @username</code>\n"
           f"<code>/vehicle DL01AB1234</code>\n\n"
           f"{div_soft()}\n📞 ᴄᴏɴᴛᴀᴄᴛ: {ADMIN_USERNAME}")
    bot.reply_to(m, txt, parse_mode='HTML')

@bot.message_handler(commands=['feedback'])
def cmd_feedback(m):
    if is_group(m): bot.reply_to(m, "💡 ᴜꜱᴇ ᴘʀɪᴠᴀᴛᴇ"); return
    uid = m.from_user.id; cid = m.chat.id
    if not manager.ensure(uid, cid, {"type": "menu_button", "data": "❓ Help"}): return
    states[uid] = {'state': 'feedback'}
    bot.reply_to(m, "📮 Send feedback:")

@bot.message_handler(commands=['pyro_health'])
def cmd_pyro_health(m):
    if m.from_user.id != ADMIN_ID: return
    info = [f"🛰️ <b>Pyrogram</b>",
            f"Session: {'✅' if PYRO_SESSION else '❌'}",
            f"Ready: {'✅' if _pyro_ready else '❌'}",
            f"Error: <code>{_pyro_error or 'none'}</code>"]
    if _pyro_ready and _pyro_me:
        info.append(f"Account: @{_pyro_me.username or _pyro_me.id}")
    bot.reply_to(m, "\n".join(info), parse_mode='HTML')

@bot.message_handler(commands=['stats'])
def cmd_stats(m):
    if not is_admin_user(m.from_user.id): return
    p, a, r, rev, rf = pay_stats()
    txt = (f"📊 <b>Quick Stats</b>\n\n👥 Users: {total_users()}\n"
           f"👥 Groups: {group_count()}\n🔍 Searches: {total_searches()}\n"
           f"💰 Revenue: ₹{rev}\n⏳ Pending: {p}\n💸 Refunded: {rf}")
    bot.reply_to(m, txt, parse_mode='HTML')

# =================================================================
#  JOIN REQUEST — AUTO APPROVE
# =================================================================
@bot.message_handler(content_types=['chat_join_request'])
def on_join_request(m):
    try:
        cid = m.chat.id
        uid = m.from_user.id
        uname = m.from_user.username or "user"
        fname = m.from_user.first_name or ""
        logger.info(f"📥 JOIN REQ: uid={uid} chat={cid}")
        auto_ok = False
        try:
            bot.approve_chat_join_request(chat_id=cid, user_id=uid)
            auto_ok = True
            logger.info(f"✅ APPROVED: {uid} → {cid}")
        except Exception as e:
            logger.error(f"❌ APPROVE FAIL: {e}")
            try:
                bot.approve_chat_join_request(cid, uid)
                auto_ok = True
                logger.info(f"✅ APPROVED (retry): {uid}")
            except Exception as e2:
                logger.error(f"❌ RETRY FAIL: {e2}")
        try:
            bot.send_message(ADMIN_ID,
                f"📥 <b>Join Request</b>\n\n"
                f"👤 <b>{fname}</b> (@{uname})\n"
                f"🆔 <code>{uid}</code>\n📢 <code>{cid}</code>\n\n"
                f"{'✅ Auto-Approved' if auto_ok else '⚠️ Manual needed'}",
                parse_mode='HTML')
        except: pass
    except Exception as e:
        logger.error(f"join_request: {e}")

# =================================================================
#  MENU BUTTONS
# =================================================================
ALL_MENU_BUTTONS = [
    "📞 Number To Info","🔒 Username To Info","🆔 Aadhaar To Info","🚗 Vehicle Info",
    "🛒 Buy Credits","💰 Refer & Earn","🎟 Redeem Code","👤 My Profile",
    "➕ Add Me To Group","❓ Help","ℹ️ About","👑 ADMIN PANEL",
    "📊 Dashboard","👥 Users","💳 Payments","🔧 Services","🎟 Promos",
    "📢 Broadcast","📢 Force Join","👥 Groups","⚙️ Settings","🛡️ Security",
    "📈 Analytics","💾 Backup","🚀 Bot Info","📝 Logs","📮 Feedback",
    "🔒 Audit Log","🔙 Back to Menu"
]

@bot.message_handler(func=lambda m: m.text in ALL_MENU_BUTTONS)
def menu_btn(m):
    if is_group(m): return
    uid = m.from_user.id; cid = m.chat.id
    cache_tg_user(m.from_user)
    if not manager.ensure(uid, cid, {"type": "menu_button", "data": m.text}): return
    process_menu(uid, cid, m.text, m.message_id)

# =================================================================
#  TEXT HANDLER
# =================================================================
@bot.message_handler(content_types=['text'])
def text_handler(m):
    uid = m.from_user.id
    cid = m.chat.id
    text = m.text.strip()
    mid = m.message_id
    cache_tg_user(m.from_user); upd_last_seen(uid)
    if is_group(m):
        if group_enabled(): register_group(m.chat.id, m.chat.title, getattr(m.chat, 'username', None))
        return
    if is_banned(uid) and not is_admin_user(uid):
        bot.reply_to(m, f"🚫 {fancy('banned')}"); return
    if text in ALL_MENU_BUTTONS: return
    if text.startswith('/'): return

    st = states.get(uid, {}); s = st.get('state')
    bypass = s in ('promo1','promo2','broadcast','ban','unban','manual_ss','waiting_payment',
        'waiting_ss','custom_amt','ads_input','fj_add','fj_add_link','user_search',
        'user_addcr','user_remcr','user_setcr','sub_add','grp_welcome','bc_custom','manual_credit',
        'awaiting_number','awaiting_username','awaiting_aadhaar','awaiting_promo',
        'awaiting_vehicle','feedback','user_fullinfo','fj_custom_msg',
        'ep_edit','svc_msg_edit','user_notes','cd_input','bc_filtered_custom',
        'fb_reply','wm_input','banned_words','maint_msg','quick_amounts_edit','buy_custom',
        'pay_search','refund_reason','shadow_ban','alert_set','backup_hour')
    is_admin = is_admin_user(uid)
    if not is_admin and is_maintenance() and not bypass:
        msg = get_setting("maintenance_custom_msg", "") or f"🔧 {fancy('maintenance')}"
        bot.send_message(cid, msg, parse_mode='HTML', reply_to_message_id=mid); return

    if not bypass and is_private(m):
        _k, _v = classify_input(text)
        if _k == "number": _pending = {"type": "number_search", "data": _v}
        elif _k == "aadhaar": _pending = {"type": "aadhaar_search", "data": _v}
        elif _k == "vehicle": _pending = {"type": "vehicle_search", "data": _v}
        elif len(text) == 12 and text.isalnum() and text.isupper():
            _pending = {"type": "promo_redeem", "data": text}
        else: _pending = {"type": "start"}
        if not manager.ensure(uid, cid, _pending): return

    if s == 'awaiting_number': states[uid] = {}; process_number(uid, cid, text, mid); return
    if s == 'awaiting_username': states[uid] = {}; process_tg2num(uid, cid, text, mid); return
    if s == 'awaiting_aadhaar': states[uid] = {}; process_aadhaar(uid, cid, text, mid); return
    if s == 'awaiting_vehicle': states[uid] = {}; process_vehicle(uid, cid, text, mid); return
    if s == 'awaiting_promo': states[uid] = {}; process_promo(uid, cid, text, mid); return

    if s == 'feedback':
        try:
            feedback_col.insert_one({"user_id": uid, "text": text[:1000],
                "at": now(), "username": m.from_user.username or ""})
            bot.reply_to(m, "✅ Thanks!")
            try:
                bot.send_message(ADMIN_ID, f"📮 <b>Feedback</b>\n👤 <code>{uid}</code>\n@{m.from_user.username or 'user'}\n\n{text[:800]}",
                    parse_mode='HTML')
            except: pass
        except: bot.reply_to(m, "❌ Failed")
        states[uid] = {}; return

    if len(text) == 12 and text.isalnum() and text.isupper():
        try:
            if promo_col.find_one({"code": text}): process_promo(uid, cid, text, mid); return
        except: pass

    if s == 'buy_custom':
        try:
            amt = int(text.strip())
            mn = int(get_setting("min_payment", MIN_PAYMENT))
            mx = int(get_setting("max_payment", MAX_PAYMENT))
            if amt < mn or amt > mx:
                bot.reply_to(m, f"❌ ₹{mn}–₹{mx}"); return
            states[uid] = {}
            show_confirm(uid, cid, amt)
        except: bot.reply_to(m, "❌ Valid amount")
        return

    if is_admin:
        if not admin_rate_ok(uid, "admin"):
            bot.reply_to(m, "⏳ Too fast! Wait."); states[uid] = {}; return

        if s == 'pay_search':
            arr = search_payments(text.strip(), 20)
            if not arr:
                bot.reply_to(m, "❌ No payments found."); states[uid] = {}; return
            txt = f"🔍 <b>Results ({len(arr)})</b>\n{div()}\n\n"
            kb = InlineKeyboardMarkup(row_width=1)
            for p in arr[:10]:
                emoji = {"pending":"⏳","approved":"✅","rejected":"❌",
                         "expired":"⌛","refunded":"💸"}.get(p.get("status"),"❓")
                txt += (f"{emoji} <b>₹{p.get('amount')}</b> → {p.get('credits')}cr\n"
                        f"   👤 <code>{p.get('user_id')}</code>\n"
                        f"   🆔 <code>{p.get('_id')}</code>\n\n")
                kb.add(InlineKeyboardButton(
                    f"{emoji} ₹{p.get('amount')} → {p.get('credits')}cr | U{p.get('user_id')}",
                    callback_data=f"pv_{str(p['_id'])}"))
            kb.add(InlineKeyboardButton("🔙 Back", callback_data="adm_back_pay"))
            bot.send_message(cid, txt[:4000], parse_mode='HTML', reply_markup=kb)
            audit(uid, "payment_search", target=text.strip())
            states[uid] = {}; return

        if s == 'refund_reason':
            pid = st.get('pid')
            reason = text.strip()[:100]
            ok, p, msg = refund_payment(pid, uid)
            if ok:
                audit(uid, "refund", target=p.get("user_id"), details=f"pid={pid} cr={p.get('credits')}")
                bot.reply_to(m, f"✅ Refunded: {msg}")
                try:
                    bot.send_message(p["user_id"],
                        f"💸 <b>Refund Processed</b>\n\n₹{p.get('amount')} refunded.\n"
                        f"Credits: {p.get('credits',0)}", parse_mode='HTML')
                except: pass
            else:
                bot.reply_to(m, f"❌ {msg}")
            states[uid] = {}; return

        if s == 'shadow_ban':
            t = text.replace('@','').strip()
            try: tid = int(t)
            except:
                try: tid = bot.get_chat(f"@{t}").id
                except: bot.reply_to(m, "❌ Not found"); states[uid] = {}; return
            shadow_ban_user(tid); audit(uid, "shadow_ban", target=tid)
            bot.reply_to(m, f"👻 Shadow-banned {tid}")
            states[uid] = {}; return

        if s == 'alert_set':
            try:
                v = int(text.strip())
                if v < 0: bot.reply_to(m, "❌ >= 0"); return
                set_setting("large_payment_alert", v)
                bot.reply_to(m, f"✅ Alert threshold = ₹{v}")
                audit(uid, "set_large_payment_alert", details=str(v))
            except: bot.reply_to(m, "❌ Number")
            states[uid] = {}
            bot.send_message(cid, "💳 Payment", reply_markup=admin_pay_kb())
            return

        if s == 'backup_hour':
            try:
                v = int(text.strip())
                if v < 0 or v > 23: bot.reply_to(m, "❌ 0–23"); return
                set_setting("auto_backup_hour", v)
                bot.reply_to(m, f"✅ Backup hour {v}:00")
                audit(uid, "set_backup_hour", details=str(v))
            except: bot.reply_to(m, "❌ Invalid")
            states[uid] = {}
            bot.send_message(cid, "⚙️ System", reply_markup=admin_sys_kb())
            return

        if s == 'ep_edit':
            field = st.get('field'); label = st.get('label', field)
            is_secret = st.get('is_secret', False)
            value = text.strip()
            if field.endswith("_url_env") and not is_url(value):
                bot.reply_to(m, f"❌ Invalid URL\n/cancel", parse_mode='HTML'); return
            set_setting(field, value)
            show_val = value
            if is_secret and len(show_val) > 4: show_val = "***" + show_val[-4:]
            bot.reply_to(m, f"✅ <b>{label}</b> updated!", parse_mode='HTML')
            audit(uid, f"ep_edit_{field}", details="***" if is_secret else value[:100])
            states[uid] = {}
            bot.send_message(cid, "🔗 Endpoints:", reply_markup=services_endpoints_kb())
            return

        if s == 'svc_msg_edit':
            svc = st.get('svc'); txt = text.strip()
            if txt.lower() == 'reset' or txt == '/reset':
                set_setting(f"service_{svc}_msg", ""); bot.reply_to(m, f"✅ Reset for {svc}")
            else:
                set_setting(f"service_{svc}_msg", txt)
                bot.reply_to(m, f"✅ Set for {svc}", parse_mode='HTML')
            audit(uid, f"svc_msg_{svc}")
            states[uid] = {}
            bot.send_message(cid, "✏️ Custom Messages:", reply_markup=services_custom_msgs_kb())
            return

        if s == 'cd_input':
            field = st.get('field')
            try:
                val = int(text)
                if val < 0: bot.reply_to(m, "❌ >= 0"); return
                set_setting(field, val); bot.reply_to(m, f"✅ {field} = {val}s")
                audit(uid, f"set_{field}", details=str(val))
            except: bot.reply_to(m, "❌ Invalid")
            states[uid] = {}
            bot.send_message(cid, "⏱ Cooldowns:", reply_markup=services_cooldown_kb())
            return

        if s == 'user_notes':
            tid = st.get('tid')
            if not tid:
                try:
                    tid = int(text.strip())
                    states[uid] = {'state': 'user_notes', 'tid': tid}
                    bot.reply_to(m, f"📝 Send note for {tid}:")
                except: bot.reply_to(m, "❌ Invalid"); states[uid] = {}
                return
            try:
                notes_col.insert_one({"user_id": tid, "note": text[:500], "admin_id": uid, "at": now()})
                audit(uid, "user_note_add", target=tid)
                bot.reply_to(m, f"✅ Note added for {tid}")
            except Exception as e: bot.reply_to(m, f"❌ {e}")
            states[uid] = {}; return

        if s == 'fb_reply':
            if '|' not in text: bot.reply_to(m, "❌ Format: USER_ID|MESSAGE"); return
            try:
                parts = text.split('|', 1); tid = int(parts[0].strip()); msg_txt = parts[1].strip()
                bot.send_message(tid, f"📮 <b>Reply from Admin</b>\n\n{msg_txt[:3000]}", parse_mode='HTML')
                audit(uid, "feedback_reply", target=tid)
                bot.reply_to(m, "✅ Reply sent!")
            except Exception as e: bot.reply_to(m, f"❌ {e}")
            states[uid] = {}; return

        if s == 'wm_input':
            set_setting("watermark_text", text.strip())
            bot.reply_to(m, "✅ Watermark set")
            audit(uid, "set_watermark")
            states[uid] = {}
            bot.send_message(cid, "🎨 Customization:", reply_markup=admin_custom_kb())
            return

        if s == 'banned_words':
            set_setting("banned_words", text.strip())
            bot.reply_to(m, "✅ Banned words updated")
            audit(uid, "set_banned_words")
            states[uid] = {}
            bot.send_message(cid, "🎨 Customization:", reply_markup=admin_custom_kb())
            return

        if s == 'maint_msg':
            if text.strip().lower() == 'reset':
                set_setting("maintenance_custom_msg", ""); bot.reply_to(m, "✅ Reset")
            else:
                set_setting("maintenance_custom_msg", text.strip()); bot.reply_to(m, "✅ Set")
            audit(uid, "set_maintenance_msg")
            states[uid] = {}
            bot.send_message(cid, "🎨 Customization:", reply_markup=admin_custom_kb())
            return

        if s == 'quick_amounts_edit':
            raw = text.strip()
            vals = []
            for x in raw.replace(" ", "").split(","):
                if x.isdigit() and int(x) > 0: vals.append(int(x))
            if not vals: bot.reply_to(m, "❌ Send comma-separated numbers"); return
            set_setting("quick_amounts", ",".join(str(x) for x in vals))
            bot.reply_to(m, f"✅ Quick amounts: {', '.join('₹'+str(x) for x in vals)}")
            audit(uid, "set_quick_amounts")
            states[uid] = {}
            bot.send_message(cid, "⚙️ Economics:", reply_markup=admin_economics_kb())
            return

        if s == 'ads_input':
            field = st.get('field')
            try:
                int_fields = ('welcome_bonus','referral_bonus','search_cost','aadhaar_cost',
                              'tg2num_cost','vehicle_cost','credits_per_rupee','daily_tries',
                              'min_payment','max_payment','group_auto_delete_seconds')
                if field in int_fields:
                    val = int(text)
                    if field in ('welcome_bonus','referral_bonus','search_cost','aadhaar_cost',
                                 'tg2num_cost','vehicle_cost','credits_per_rupee',
                                 'min_payment','max_payment') and val < 0:
                        bot.reply_to(m, "❌ >= 0"); return
                    if field == 'daily_tries' and val < 0: bot.reply_to(m, "❌ >= 0"); return
                    if field == 'group_auto_delete_seconds' and val < 10:
                        bot.reply_to(m, "❌ Min 10s"); return
                    if field == 'credits_per_rupee' and val <= 0:
                        bot.reply_to(m, "❌ > 0"); return
                    set_setting(field, val)
                    bot.reply_to(m, f"✅ <b>{field}</b> = {val}", parse_mode='HTML')
                else:
                    set_setting(field, text.strip())
                    bot.reply_to(m, f"✅ <b>{field}</b> updated", parse_mode='HTML')
            except Exception as e: bot.reply_to(m, f"❌ {e}")
            audit(uid, f"set_{field}", details=text[:100])
            states[uid] = {}
            panel = st.get('panel', 'main')
            if panel == 'eco': bot.send_message(cid, "⚙️ Economics:", reply_markup=admin_economics_kb())
            elif panel == 'costs': bot.send_message(cid, "⚙️ Costs:", reply_markup=admin_costs_kb())
            elif panel == 'tries': bot.send_message(cid, "⚙️ Tries:", reply_markup=admin_tries_kb())
            elif panel == 'pay': bot.send_message(cid, "⚙️ Payment:", reply_markup=admin_pay_kb())
            elif panel == 'custom': bot.send_message(cid, "🎨 Custom:", reply_markup=admin_custom_kb())
            elif panel == 'endpoints': bot.send_message(cid, "🔗 Endpoints:", reply_markup=services_endpoints_kb())
            elif panel == 'groups': bot.send_message(cid, "👥 Groups:", reply_markup=groups_kb())
            else: bot.send_message(cid, "⚙️ Settings:", reply_markup=settings_main_kb())
            return

        if s == 'user_search':
            try:
                t = text.replace('@','').strip()
                if t.isdigit(): u = users_col.find_one({"user_id": int(t)})
                else: u = tg_users_col.find_one({"username_lower": t.lower()})
                if not u: bot.reply_to(m, "❌ Not found"); states[uid] = {}; return
                target_id = u.get("user_id")
                ud = users_col.find_one({"user_id": target_id}) or {}
                hist = list(history_col.find({"user_id": target_id}).sort("at", -1).limit(10))
                hist_txt = "\n".join(f"• {h.get('service')} — {h.get('query','')[:30]}"
                                     for h in hist) if hist else "None"
                txt = (f"👤 <b>User Details</b>\n{div()}\n\n"
                       f"🆔 <code>{target_id}</code>\n📛 @{u.get('username','N/A')}\n"
                       f"👋 {u.get('full_name','N/A')}\n💎 Credits: {ud.get('credits',0)}\n"
                       f"🔍 Searches: {ud.get('searches',0)}\n📌 Refs: {ud.get('total_referrals',0)}\n"
                       f"🚫 Banned: {'Yes' if ud.get('banned') else 'No'}\n"
                       f"👻 Shadow: {'Yes' if ud.get('shadow_banned') else 'No'}\n\n"
                       f"📜 <b>Recent:</b>\n{hist_txt}")
                bot.reply_to(m, txt, parse_mode='HTML')
            except Exception as e: bot.reply_to(m, f"❌ {e}")
            states[uid] = {}; return

        if s == 'user_fullinfo':
            try:
                tid = int(text.strip())
                ud = users_col.find_one({"user_id": tid}) or {}
                tu = tg_users_col.find_one({"user_id": tid}) or {}
                pays = list(payments_col.find({"user_id": tid, "status": "approved"}))
                total_paid = sum(p.get("amount", 0) for p in pays)
                total_cr = sum(p.get("credits", 0) for p in pays)
                notes = list(notes_col.find({"user_id": tid}).sort("at", -1).limit(5))
                notes_txt = "\n".join(f"• {n.get('note','')[:80]}" for n in notes) if notes else "None"
                txt = (f"👤 <b>Full Info</b>\n{div()}\n\n"
                       f"🆔 <code>{tid}</code>\n📛 @{tu.get('username','N/A')}\n"
                       f"👋 {tu.get('full_name','N/A')}\n\n"
                       f"💎 Credits: <b>{ud.get('credits',0)}</b>\n"
                       f"🔍 Searches: {ud.get('searches',0)}\n📌 Refs: {ud.get('total_referrals',0)}\n"
                       f"💰 <b>Payments</b>\nTotal: ₹{total_paid}\nCredits: {total_cr}\nCount: {len(pays)}\n\n"
                       f"📝 <b>Notes</b>\n{notes_txt}")
                bot.reply_to(m, txt, parse_mode='HTML')
            except Exception as e: bot.reply_to(m, f"❌ {e}")
            states[uid] = {}; return

        if s == 'user_addcr':
            try:
                parts = text.split(); tid = int(parts[0]); amt = int(parts[1])
                if amt <= 0: bot.reply_to(m, "❌ > 0"); states[uid] = {}; return
                add_credits(tid, amt); bot.reply_to(m, f"✅ +{amt}cr → {tid}\nNew: {get_credits(tid)}")
                audit(uid, "add_credits", target=tid, details=str(amt))
            except: bot.reply_to(m, "❌ <id> <amt>")
            states[uid] = {}; return

        if s == 'user_remcr':
            try:
                parts = text.split(); tid = int(parts[0]); amt = int(parts[1])
                if amt <= 0: bot.reply_to(m, "❌ > 0"); states[uid] = {}; return
                deduct_credits(tid, amt); bot.reply_to(m, f"✅ -{amt}cr\nNew: {get_credits(tid)}")
                audit(uid, "remove_credits", target=tid, details=str(amt))
            except: bot.reply_to(m, "❌ <id> <amt>")
            states[uid] = {}; return

        if s == 'user_setcr':
            try:
                parts = text.split(); tid = int(parts[0]); amt = int(parts[1])
                if amt < 0: bot.reply_to(m, "❌ >= 0"); states[uid] = {}; return
                users_col.update_one({"user_id": tid}, {"$set": {"credits": amt}}, upsert=True)
                bot.reply_to(m, f"✅ Balance → {amt}cr")
                audit(uid, "set_credits", target=tid, details=str(amt))
            except: bot.reply_to(m, "❌ <id> <bal>")
            states[uid] = {}; return

        if s == 'ban':
            t = text.replace('@','').strip()
            try: tid = int(t)
            except:
                try: tid = bot.get_chat(f"@{t}").id
                except: bot.reply_to(m, "❌ Not found"); states[uid] = {}; return
            if tid == uid: bot.reply_to(m, "❌ Self!"); states[uid] = {}; return
            if tid == ADMIN_ID: bot.reply_to(m, "❌ Can't ban main!"); states[uid] = {}; return
            ban_user(tid); bot.reply_to(m, f"✅ Banned {tid}")
            audit(uid, "ban", target=tid)
            states[uid] = {}; return

        if s == 'unban':
            t = text.replace('@','').strip()
            try: tid = int(t)
            except:
                try: tid = bot.get_chat(f"@{t}").id
                except: bot.reply_to(m, "❌ Not found"); states[uid] = {}; return
            unban_user(tid); bot.reply_to(m, f"✅ Unbanned {tid}")
            audit(uid, "unban", target=tid)
            states[uid] = {}; return

        if s == 'sub_add':
            if not is_main_admin(uid): bot.reply_to(m, "❌ Main only"); states[uid] = {}; return
            t = text.replace('@','').strip()
            try: tid = int(t)
            except:
                try: tid = bot.get_chat(f"@{t}").id
                except: bot.reply_to(m, "❌ Not found"); states[uid] = {}; return
            try:
                admins_col.insert_one({"user_id": tid, "added_by": uid, "added_at": now()})
                bot.reply_to(m, f"✅ Sub-admin {tid}")
                audit(uid, "subadmin_add", target=tid)
            except: bot.reply_to(m, "❌ Exists")
            states[uid] = {}; return

        if s == 'sub_remove':
            if not is_main_admin(uid): bot.reply_to(m, "❌ Main only"); states[uid] = {}; return
            try:
                tid = int(text.strip()); admins_col.delete_one({"user_id": tid})
                bot.reply_to(m, f"✅ Removed {tid}")
                audit(uid, "subadmin_rm", target=tid)
            except: bot.reply_to(m, "❌ Invalid")
            states[uid] = {}; return

        if s == 'grp_welcome':
            set_setting("group_welcome", text.strip())
            bot.reply_to(m, "✅ Group welcome set")
            audit(uid, "set_group_welcome")
            states[uid] = {}; return

        if s == 'promo1':
            if text.isdigit():
                v = int(text)
                if v <= 0: bot.reply_to(m, "❌ > 0"); return
                states[uid]['credits'] = v; states[uid]['state'] = 'promo2'
                bot.reply_to(m, "Kitne users?")
            else: bot.reply_to(m, "❌ Number")
            return

        if s == 'promo2':
            if text.isdigit():
                lim = int(text)
                if lim <= 0: bot.reply_to(m, "❌ > 0"); return
                cr = states[uid].get('credits')
                code = gen_promo(); save_promo(code, cr, lim, uid)
                bot.reply_to(m, f"🎁 <code>{code}</code>\n{cr}cr × {lim}", parse_mode='HTML')
                audit(uid, "promo_gen", details=f"{code}:{cr}:{lim}")
                states[uid] = {}
            else: bot.reply_to(m, "❌ Number")
            return

        if s == 'broadcast':
            bcast_q.put((all_users(), text, {'parse_mode':'HTML'}))
            bot.reply_to(m, "✅ Queued.")
            audit(uid, "broadcast_text")
            states[uid] = {}; return

        if s in ('bc_custom', 'bc_filtered_custom'):
            targets = st.get('targets', [])
            bcast_q.put((targets, text, {'parse_mode':'HTML'}))
            bot.reply_to(m, f"✅ Queued to {len(targets)}")
            audit(uid, "broadcast_filtered", details=f"{len(targets)} targets")
            states[uid] = {}; return

        if s == 'manual_credit':
            try:
                parts = text.split(); tid = int(parts[0]); amt = int(parts[1])
                if amt <= 0: bot.reply_to(m, "❌ > 0"); states[uid] = {}; return
                add_credits(tid, amt); bot.reply_to(m, f"✅ +{amt}cr → {tid}")
                audit(uid, "manual_credit", target=tid, details=str(amt))
            except: bot.reply_to(m, "❌ <id> <amt>")
            states[uid] = {}; return

        if s == 'fj_add':
            if text.startswith('@'):
                try: cid_ = bot.get_chat(text).id
                except Exception as e: bot.reply_to(m, f"❌ {e}"); states[uid]={}; return
            else:
                try: cid_ = int(text)
                except: bot.reply_to(m, "❌ Invalid"); states[uid]={}; return
            states[uid] = {'state': 'fj_add_link', 'cid': cid_}
            bot.reply_to(m, "Send invite link:")
            return

        if s == 'fj_add_link':
            cid_ = st.get('cid'); link = text.strip()
            if not link or link.lower() == 'skip': bot.reply_to(m, "❌ Link req"); states[uid] = {}; return
            ok, msg = manager.add(cid_, link)
            bot.reply_to(m, ("✅ " if ok else "❌ ") + msg)
            audit(uid, "fj_add", target=cid_)
            states[uid] = {}; return

        if s == 'fj_custom_msg':
            txt = text.strip()
            if txt.lower() == 'reset':
                set_setting("fj_custom_msg", ""); bot.reply_to(m, "✅ Reset")
            else:
                set_setting("fj_custom_msg", txt)
                bot.reply_to(m, f"✅ Set", parse_mode='HTML')
            audit(uid, "fj_custom_msg")
            states[uid] = {}
            bot.send_message(cid, "📢 Force Join:", reply_markup=force_kb())
            return

    kind, value = classify_input(text)
    if kind == "number":
        if is_private(m) and not manager.ensure(uid, cid, {"type":"number_search","data":value}): return
        process_number(uid, cid, value, mid); return
    elif kind == "aadhaar":
        if is_private(m) and not manager.ensure(uid, cid, {"type":"aadhaar_search","data":value}): return
        process_aadhaar(uid, cid, value, mid); return
    elif kind == "vehicle":
        if is_private(m) and not manager.ensure(uid, cid, {"type":"vehicle_search","data":value}): return
        process_vehicle(uid, cid, value, mid); return

# =================================================================
#  GROUP HANDLERS
# =================================================================
@bot.message_handler(content_types=['new_chat_members'])
def on_new_members(m):
    try:
        for member in m.new_chat_members:
            if member.id == bot.get_me().id:
                if group_enabled():
                    register_group(m.chat.id, m.chat.title, getattr(m.chat, 'username', None))
                    wl = get_setting("group_welcome", "") or group_help_txt()
                    bot.send_message(m.chat.id, wl, parse_mode='HTML')
                    logger.info(f"✅ Bot added to: {m.chat.title}")
    except Exception as e: logger.error(f"new_members: {e}")

@bot.message_handler(content_types=['left_chat_member'])
def on_left_member(m):
    try:
        if m.left_chat_member.id == bot.get_me().id:
            remove_group(m.chat.id)
    except: pass

# =================================================================
#  PHOTO HANDLER
# =================================================================
@bot.message_handler(content_types=['photo'])
def photo_h(m):
    uid = m.from_user.id; cid = m.chat.id
    cache_tg_user(m.from_user); upd_last_seen(uid)
    if is_group(m): return
    if not manager.ensure(uid, cid, {"type":"media"}): return
    if is_banned(uid) and not is_admin_user(uid): bot.reply_to(m, "🚫 Banned"); return
    st = states.get(uid, {}); s = st.get('state')

    if s in ('waiting_ss', 'manual_ss'):
        file_id = m.photo[-1].file_id
        pid = st.get('payment_id')
        if pid:
            existing = get_payment(pid)
            already_notified = existing.get("admin_notified", False) if existing else False
            payments_col.update_one({"_id": ObjectId(pid)}, {"$set": {"screenshot_id": file_id}})
            p = get_payment(pid)
        else:
            existing = payments_col.find_one({"user_id": uid, "status": "pending", "pay_mode": "manual"})
            if existing:
                payments_col.update_one({"_id": existing["_id"]}, {"$set": {"screenshot_id": file_id}})
                p = get_payment(str(existing["_id"]))
                already_notified = existing.get("admin_notified", False)
            else:
                amt = st.get('amount', 0); cr = st.get('credits', 0)
                pm = "manual" if s == 'manual_ss' else "auto"
                pid = create_payment(uid, cid, amt, cr, pm, screenshot_id=file_id, order_id=st.get('order_id'))
                p = get_payment(pid); already_notified = False
        if p:
            if already_notified:
                bot.reply_to(m, "✅ Already notified.")
                states[uid] = {}; return
            try:
                uname = bot.get_chat(uid).username or "user"
                threshold = int(get_setting("large_payment_alert", 500))
                alert_line = ""
                if threshold > 0 and p.get("amount", 0) >= threshold:
                    alert_line = f"\n\n🚨 <b>LARGE PAYMENT ALERT!</b>"
                txt = (f"📋 <b>PAYMENT</b>{alert_line}\n\n👤 @{uname} (<code>{uid}</code>)\n"
                       f"💵 ₹{p['amount']}\n💎 {p['credits']}\n🆔 <code>{p['_id']}</code>")
                kb = InlineKeyboardMarkup()
                kb.row(InlineKeyboardButton("✅ Approve", callback_data=f"ap_{p['_id']}"),
                       InlineKeyboardButton("❌ Reject", callback_data=f"rj_{p['_id']}"))
                admin_ids = [ADMIN_ID] + [a['user_id'] for a in admins_col.find()]
                sent_ok = False
                for aid in set(admin_ids):
                    try:
                        bot.send_photo(aid, file_id, caption=txt, parse_mode='HTML', reply_markup=kb)
                        sent_ok = True
                    except: pass
                if sent_ok:
                    payments_col.update_one({"_id": p["_id"]}, {"$set": {"admin_notified": True}})
                    bot.reply_to(m, "✅ Sent to admin.")
                else: bot.reply_to(m, "⚠️ Notification failed.")
            except Exception as e: logger.error(f"Forward: {e}")
        states[uid] = {}; return

    if is_admin_user(uid) and s == 'broadcast':
        file_id = m.photo[-1].file_id
        caption = m.caption or "📢 Broadcast"
        users = all_users()
        threading.Thread(target=bcast_photo_worker,
            args=(users, file_id, caption), daemon=True).start()
        bot.reply_to(m, f"📢 Queued to {len(users)}.")
        states[uid] = {}

@bot.message_handler(content_types=['video','document','audio','sticker','animation','voice'])
def bcast_media(m):
    uid = m.from_user.id
    if is_group(m): return
    if not is_admin_user(uid): return
    if states.get(uid, {}).get('state') != 'broadcast': return
    us = all_users(); ct = m.content_type
    def go():
        pin = int(get_setting("broadcast_pin", 0))
        for u in us:
            try:
                sent = None
                if ct=='video': sent = bot.send_video(u, m.video.file_id, caption="📢")
                elif ct=='document': sent = bot.send_document(u, m.document.file_id, caption="📢")
                elif ct=='audio': sent = bot.send_audio(u, m.audio.file_id, caption="📢")
                elif ct=='sticker': sent = bot.send_sticker(u, m.sticker.file_id)
                elif ct=='animation': sent = bot.send_animation(u, m.animation.file_id, caption="📢")
                elif ct=='voice': sent = bot.send_voice(u, m.voice.file_id, caption="📢")
                if pin and sent:
                    try: bot.pin_chat_message(u, sent.message_id)
                    except: pass
                time.sleep(0.05)
            except: pass
    threading.Thread(target=go, daemon=True).start()
    bot.reply_to(m, "📢 Queued."); states[uid] = {}

# =================================================================
#  CALLBACK HANDLER
# =================================================================
@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    uid = call.from_user.id
    cid = call.message.chat.id
    d = call.data
    cache_tg_user(call.from_user)
    is_admin = is_admin_user(uid)

    ADMIN_PREFIXES = ('adm_', 'fj_', 'ads_', 'ep_', 'ap_', 'rj_', 'pv_', 'refund_', 'audit_')
    if d.startswith(ADMIN_PREFIXES) and not is_admin:
        safe_ans(call, "❌ Admin only", True); return

    if is_group(call.message):
        GROUP_ALLOWED = ('force_verify',)
        if d not in GROUP_ALLOWED:
            safe_ans(call, "💡 Private me use karein", True); return

    if d.startswith(ADMIN_PREFIXES) and not admin_rate_ok(uid, "cb"):
        safe_ans(call, "⏳ Too fast", True); return

    if d == "buy_menu":
        show_buy_menu(uid, cid); safe_ans(call); return
    if d.startswith("buy_amt_"):
        try: amt = int(d.replace("buy_amt_", ""))
        except: safe_ans(call); return
        show_confirm(uid, cid, amt); safe_ans(call); return
    if d == "buy_custom":
        states[uid] = {'state': 'buy_custom'}
        mn = int(get_setting("min_payment", MIN_PAYMENT))
        mx = int(get_setting("max_payment", MAX_PAYMENT))
        bot.send_message(cid, f"✏️ Send amount (₹{mn}–₹{mx}):"); safe_ans(call); return
    if d.startswith("buy_next_"):
        try:
            parts = d.replace("buy_next_", "").split("_")
            amt = int(parts[0]); cr = int(parts[1])
        except: safe_ans(call); return
        show_payment_method(uid, cid, amt, cr, call.message.message_id)
        safe_ans(call); return
    if d == "buy_history":
        show_order_history(uid, cid); safe_ans(call); return
    if d.startswith("pay_auto_"):
        parts = d.replace("pay_auto_", "").split("_")
        try: amt = int(parts[0]); cr = int(parts[1])
        except: safe_ans(call); return
        handle_auto_payment(uid, cid, amt, cr, call.message.message_id)
        safe_ans(call); return
    if d.startswith("pay_manual_"):
        parts = d.replace("pay_manual_", "").split("_")
        try: amt = int(parts[0]); cr = int(parts[1])
        except: safe_ans(call); return
        handle_manual_payment(uid, cid, amt, cr, call.message.message_id)
        safe_ans(call); return
    if d.startswith("paid_manual_"):
        parts = d.replace("paid_manual_", "").split("_")
        try: amt = int(parts[0]); cr = int(parts[1])
        except: safe_ans(call); return
        process_manual_paid(uid, cid, amt, cr, call.message.message_id)
        safe_ans(call); return
    if d.startswith("chk_"):
        oid = d.replace("chk_", ""); process_check_status(uid, cid, oid); safe_ans(call); return
    if d.startswith("scr_"):
        oid = d.replace("scr_", ""); process_screenshot_prompt(uid, cid, oid); safe_ans(call); return

    if d.startswith("svc_force_"):
        svc = d.replace("svc_force_", "")
        if svc not in SERVICE_KEYS: safe_ans(call, "❌"); return
        st = states.get(uid, {})
        st['force_svc'] = svc
        states[uid] = st
        try: bot.delete_message(cid, call.message.message_id)
        except: pass
        hint = {"number":"📱 Send number now:","username":"🔒 Send username now:",
                "aadhaar":"🆔 Send aadhaar now:","vehicle":"🚗 Send vehicle now:"}.get(svc,"Send query:")
        bot.send_message(cid, f"✅ <b>Force mode ON for {svc}</b>\n\n{hint}", parse_mode='HTML')
        audit(uid, f"force_svc_{svc}")
        safe_ans(call, "⚠️ Continue"); return

    if d == "adm_svc_toggle_panel":
        txt = "🎛 <b>Service ON/OFF</b>\n\n📌 ᴛᴀᴘ ᴛᴏ ᴛᴏɢɢʟᴇ:"
        if not safe_edit(call, txt, parse_mode='HTML', reply_markup=services_toggle_kb()):
            bot.send_message(cid, txt, parse_mode='HTML', reply_markup=services_toggle_kb())
        safe_ans(call); return

    if d.startswith("adm_svc_tog_"):
        svc = d.replace("adm_svc_tog_", "")
        if svc not in SERVICE_KEYS: safe_ans(call, "❌", True); return
        new_state = toggle_service(svc)
        audit(uid, f"svc_toggle_{svc}", details="ON" if new_state else "OFF")
        label = SERVICE_LABELS.get(svc, svc)
        status = "🟢 <b>ENABLED</b>" if new_state else "🔴 <b>DISABLED</b>"
        try:
            bot.edit_message_text(f"🎛 <b>Toggle</b>\n\n📛 {label}\n⚙️ {status}",
                cid, call.message.message_id, parse_mode='HTML')
            time.sleep(0.6)
            bot.edit_message_text("🎛 <b>Service ON/OFF</b>\n\n📌 ᴛᴀᴘ:",
                cid, call.message.message_id, parse_mode='HTML',
                reply_markup=services_toggle_kb())
        except: pass
        safe_ans(call, f"{'✅ ON' if new_state else '🔴 OFF'}: {label}")
        return

    if d == "adm_svc_custom_msgs":
        if not safe_edit(call, "✏️ <b>Custom Messages</b>", parse_mode='HTML',
            reply_markup=services_custom_msgs_kb()):
            bot.send_message(cid, "✏️ Custom:", reply_markup=services_custom_msgs_kb())
        safe_ans(call); return

    if d.startswith("adm_svc_editmsg_"):
        svc = d.replace("adm_svc_editmsg_", "")
        if svc not in SERVICE_KEYS: safe_ans(call, "❌", True); return
        label = SERVICE_LABELS.get(svc, svc)
        current = get_setting(f"service_{svc}_msg", "") or "(default)"
        states[uid] = {'state': 'svc_msg_edit', 'svc': svc}
        try:
            bot.edit_message_text(
                f"✏️ <b>Editing: {label}</b>\n\n<b>Current:</b>\n<code>{html_module.escape(str(current)[:400])}</code>\n\nSend new or 'reset'",
                cid, call.message.message_id, parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🔙 Cancel", callback_data="adm_svc_custom_msgs")))
        except: pass
        safe_ans(call); return

    ep_labels = {
        'api_url_env': ('📞 Number URL', False), 'api_key_env': ('📞 Number Key', True),
        'tg2num_url_env': ('🔒 TG2Num URL', False), 'tg2num_key_env': ('🔒 TG2Num Key', True),
        'aadhaar_url_env': ('🆔 Aadhaar URL', False), 'aadhaar_key_env': ('🆔 Aadhaar Key', True),
        'vehicle_url_env': ('🚗 Vehicle URL', False), 'vehicle_key_env': ('🚗 Vehicle Key', True),
    }

    if d.startswith("ep_edit_"):
        field = d.replace("ep_edit_", "")
        if field not in ep_labels: safe_ans(call, "❌", True); return
        label, is_secret = ep_labels[field]
        current = get_setting(field, "") or "not set"
        if is_secret and len(str(current)) > 4: current = "***" + str(current)[-4:]
        states[uid] = {'state': 'ep_edit', 'field': field, 'label': label, 'is_secret': is_secret}
        try:
            bot.edit_message_text(
                f"✏️ <b>{label}</b>\n\n<b>Current:</b>\n<code>{html_module.escape(str(current)[:200])}</code>\n\nSend new or /cancel",
                cid, call.message.message_id, parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🔙 Cancel", callback_data="adm_svc_endpoints")))
        except: pass
        safe_ans(call); return

    if d.startswith("ep_clear_"):
        field = d.replace("ep_clear_", "")
        if field not in ep_labels: safe_ans(call, "❌", True); return
        label, _ = ep_labels[field]
        set_setting(field, "")
        audit(uid, f"ep_clear_{field}")
        try:
            bot.edit_message_text(f"🗑 Cleared: {label}", cid, call.message.message_id, parse_mode='HTML')
            time.sleep(0.6)
            bot.edit_message_text("🔗 Endpoints", cid, call.message.message_id, reply_markup=services_endpoints_kb())
        except: pass
        safe_ans(call); return

    if d == "adm_svc_endpoints":
        try: bot.edit_message_text("🔗 Endpoints", cid, call.message.message_id, reply_markup=services_endpoints_kb())
        except: pass
        safe_ans(call); return
    if d == "adm_svc_cooldown":
        try: bot.edit_message_text("⏱ Cooldowns", cid, call.message.message_id, reply_markup=services_cooldown_kb())
        except: pass
        safe_ans(call); return
    if d == "adm_cd_setglobal":
        states[uid] = {'state': 'cd_input', 'field': 'rate_limit_seconds'}
        bot.send_message(cid, "🌐 Global rate limit (sec, 0=off):"); safe_ans(call); return
    if d.startswith("adm_cd_set_"):
        svc = d.replace("adm_cd_set_", "")
        states[uid] = {'state': 'cd_input', 'field': f'cooldown_{svc}'}
        bot.send_message(cid, f"⏱ {svc.title()} cooldown (0=off):"); safe_ans(call); return

    if d == "adm_svc_output_mode":
        cur = str(get_setting("output_mode", "formatted")).lower()
        if cur == "json": new = "formatted"
        elif cur == "formatted": new = "both"
        else: new = "json"
        set_setting("output_mode", new)
        labels = {"json": "📄 JSON", "formatted": "🎨 Formatted", "both": "🔀 Both"}
        bot.send_message(cid, f"🎨 <b>Output Mode: {labels[new]}</b>", parse_mode='HTML')
        audit(uid, "output_mode", details=new)
        safe_ans(call, f"✅ {labels[new]}"); return

    if d == "adm_back":
        if not is_admin: return
        try: bot.delete_message(cid, call.message.message_id)
        except: pass
        bot.send_message(cid, "👑 Admin Panel", reply_markup=admin_kb()); return
    if d == "adm_svc_back":
        try: bot.edit_message_text("🔧 Services", cid, call.message.message_id, reply_markup=services_kb())
        except: pass
        safe_ans(call); return

    if d == "adm_dash_refresh":
        p, a, r, rev, rf = pay_stats()
        txt = (f"📊 <b>{fancy('dashboard')}</b>\n{div()}\n\n"
               f"👥 ᴜꜱᴇʀꜱ: <b>{total_users()}</b>\n🆕 24ʜ: <b>{new_users_24h()}</b>\n"
               f"👥 ɢʀᴏᴜᴘꜱ: <b>{group_count()}</b>\n"
               f"🔍 ꜱᴇᴀʀᴄʜᴇꜱ: <b>{total_searches()}</b> | 🔥 1ʜ: <b>{searches_1h()}</b>\n\n"
               f"💰 ᴘᴇɴᴅɪɴɢ: <b>{p}</b> | ✅ <b>{a}</b> | ❌ <b>{r}</b> | 💸 <b>{rf}</b>\n"
               f"💵 ʀᴇᴠᴇɴᴜᴇ: <b>₹{rev}</b>\n"
               f"📅 ᴛᴏᴅᴀʏ: <b>₹{revenue_today()}</b> | ᴋᴀʟ: <b>₹{revenue_yesterday()}</b>\n"
               f"🎯 ᴄᴏɴᴠᴇʀꜱɪᴏɴ: <b>{conversion_rate()}%</b>")
        try: bot.edit_message_text(txt, cid, call.message.message_id, parse_mode='HTML', reply_markup=dashboard_kb())
        except: pass
        safe_ans(call, "✅"); return
    if d == "adm_dash_export":
        csv_d = export_csv()
        if csv_d:
            try:
                bio = io.BytesIO(csv_d.encode('utf-8')); bio.name = "users.csv"
                bot.send_document(cid, bio, caption="📥")
            except: pass
        safe_ans(call); return
    if d == "adm_dash_revgraph":
        chart = revenue_daily_chart(7)
        if not chart: bot.send_message(cid, "No data."); safe_ans(call); return
        max_amt = max(a for _, a in chart) or 1
        txt = "📈 <b>Revenue (7d)</b>\n\n"
        for date, amt in chart:
            bar_len = int((amt / max_amt) * 20) if max_amt > 0 else 0
            bar = "█" * bar_len + "░" * (20 - bar_len)
            txt += f"<code>{date}</code> {bar} ₹{amt}\n"
        txt += f"\n💰 Total: <b>₹{sum(a for _, a in chart)}</b>"
        bot.send_message(cid, txt, parse_mode='HTML'); safe_ans(call); return
    if d == "adm_dash_svcstatus":
        txt = f"🎛 <b>Service Status</b>\n{div()}\n\n"
        for svc in SERVICE_KEYS:
            emoji = SERVICE_EMOJI.get(svc, "🔹")
            st = "🟢 ON" if is_service_enabled(svc) else "🔴 OFF"
            sr = api_success_rate(svc)
            sr_s = f"{sr}%" if sr is not None else "N/A"
            txt += f"{emoji} {svc.title()}: {st} | ✅ {sr_s}\n"
        bot.send_message(cid, txt, parse_mode='HTML'); safe_ans(call); return
    if d == "adm_dash_alerts":
        lines = [f"🚨 <b>Active Alerts</b>\n{div()}\n"]
        p, _, _, _, _ = pay_stats()
        if p > 10: lines.append(f"⚠️ {p} pending payments")
        for svc in SERVICE_KEYS:
            sr = api_success_rate(svc)
            if sr is not None and sr < 60:
                lines.append(f"🔴 {svc.title()} API: {sr}%")
        fs = failed_searches_24h(); ts = total_searches_24h()
        if ts > 0 and (fs / ts) > 0.3:
            lines.append(f"⚠️ High fail: {fs}/{ts}")
        if len(lines) == 2: lines.append("✅ No alerts.")
        bot.send_message(cid, "\n".join(lines), parse_mode='HTML')
        safe_ans(call); return
    if d == "adm_dash_detailed":
        p, a, r, rev, rf = pay_stats()
        txt = (f"📊 <b>Detailed</b>\n{div()}\n\n"
               f"👥 Users: {total_users()}\n🚫 Banned: {users_col.count_documents({'banned':1})}\n"
               f"👻 Shadow: {users_col.count_documents({'shadow_banned':1})}\n"
               f"🆕 24h: {new_users_24h()}\n💾 Cached: {tg_users_col.count_documents({})}\n"
               f"👥 Groups: {group_count()}\n\n"
               f"💰 Pending: {p}\n✅ Approved: {a}\n❌ Rejected: {r}\n💸 Refunded: {rf}\n"
               f"💵 Revenue: ₹{rev}\n💎 Credits: {total_credits_sold()}\n\n"
               f"🔍 Searches: {total_searches()}\n🎟 Promos: {promo_col.count_documents({})}\n"
               f"🔒 Audit: {audit_count()}")
        bot.send_message(cid, txt, parse_mode='HTML'); safe_ans(call); return

    if d == "adm_user_search": states[uid] = {'state': 'user_search'}; bot.send_message(cid, "🔍 user_id/@username:"); safe_ans(call); return
    if d == "adm_user_ban": states[uid] = {'state': 'ban'}; bot.send_message(cid, "🚫 user_id/@username:"); safe_ans(call); return
    if d == "adm_user_unban": states[uid] = {'state': 'unban'}; bot.send_message(cid, "✅ user_id/@username:"); safe_ans(call); return
    if d == "adm_user_shadowban": states[uid] = {'state': 'shadow_ban'}; bot.send_message(cid, "👻 user_id/@username:"); safe_ans(call); return
    if d == "adm_user_banned_list":
        banned = list(users_col.find({"banned": 1}).limit(50))
        if not banned: bot.send_message(cid, "None."); safe_ans(call); return
        txt = f"🚫 <b>Banned ({len(banned)})</b>\n\n"
        for b in banned: txt += f"<code>{b.get('user_id')}</code>\n"
        bot.send_message(cid, txt, parse_mode='HTML'); safe_ans(call); return
    if d == "adm_user_addcr": states[uid] = {'state': 'user_addcr'}; bot.send_message(cid, "💎 <id> <amt>"); safe_ans(call); return
    if d == "adm_user_remcr": states[uid] = {'state': 'user_remcr'}; bot.send_message(cid, "➖ <id> <amt>"); safe_ans(call); return
    if d == "adm_user_setcr": states[uid] = {'state': 'user_setcr'}; bot.send_message(cid, "💰 <id> <bal>"); safe_ans(call); return
    if d == "adm_user_fullinfo": states[uid] = {'state': 'user_fullinfo'}; bot.send_message(cid, "👤 Send user_id:"); safe_ans(call); return
    if d == "adm_user_notes":
        states[uid] = {'state': 'user_notes', 'tid': None}
        bot.send_message(cid, "📝 Send user_id:"); safe_ans(call); return
    if d == "adm_user_history":
        states[uid] = {'state': 'user_search'}
        bot.send_message(cid, "📜 Send user_id:"); safe_ans(call); return
    if d == "adm_user_export":
        csv_d = export_csv()
        if csv_d:
            try:
                bio = io.BytesIO(csv_d.encode('utf-8')); bio.name = "users.csv"
                bot.send_document(cid, bio, caption=f"📥 {total_users()}")
            except: pass
        safe_ans(call); return

    if d == "adm_pay_pending":
        ps = get_pending()
        if not ps: bot.send_message(cid, "None."); safe_ans(call); return
        kb = InlineKeyboardMarkup(row_width=1)
        for p in ps[:20]:
            ic = "⚡" if p.get("pay_mode")=="auto" else "📋"
            kb.add(InlineKeyboardButton(f"{ic} ₹{p['amount']} → {p['credits']}cr | U{p['user_id']}",
                callback_data=f"pv_{str(p['_id'])}"))
        kb.add(InlineKeyboardButton("🔙 Back", callback_data="adm_back_pay"))
        bot.send_message(cid, f"💰 <b>Pending ({len(ps)})</b>", parse_mode='HTML', reply_markup=kb)
        safe_ans(call); return
    if d == "adm_pay_approved":
        bot.send_message(cid, f"✅ {payments_col.count_documents({'status': 'approved'})}"); safe_ans(call); return
    if d == "adm_pay_rejected":
        bot.send_message(cid, f"❌ {payments_col.count_documents({'status': 'rejected'})}"); safe_ans(call); return
    if d == "adm_pay_refunded":
        bot.send_message(cid, f"💸 {payments_col.count_documents({'status': 'refunded'})}"); safe_ans(call); return
    if d == "adm_pay_revenue":
        p, a, r, rev, rf = pay_stats()
        bot.send_message(cid, f"💰 Total: ₹{rev}\n24h: ₹{revenue_24h()}\n7d: ₹{revenue_7d()}\n"
                              f"Today: ₹{revenue_today()}\nYest: ₹{revenue_yesterday()}\nRefunded: {rf}")
        safe_ans(call); return
    if d == "adm_pay_search":
        states[uid] = {'state': 'pay_search'}
        bot.send_message(cid, "🔍 Send UTR / order_id / user_id / payment_id:"); safe_ans(call); return
    if d == "adm_pay_revgraph":
        chart = revenue_daily_chart(7)
        if not chart: bot.send_message(cid, "No data."); safe_ans(call); return
        max_amt = max(a for _, a in chart) or 1
        txt = "📈 <b>Revenue</b>\n\n"
        for date, amt in chart:
            bar_len = int((amt / max_amt) * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            txt += f"<code>{date}</code> {bar} ₹{amt}\n"
        bot.send_message(cid, txt, parse_mode='HTML'); safe_ans(call); return
    if d == "adm_pay_manual":
        states[uid] = {'state': 'manual_credit'}
        bot.send_message(cid, "💎 <id> <amt>"); safe_ans(call); return
    if d == "adm_pay_recent":
        ps = list(payments_col.find().sort("created_at", -1).limit(15))
        if not ps: bot.send_message(cid, "None."); safe_ans(call); return
        txt = "🧾 <b>Recent</b>\n\n"
        for p in ps:
            emoji = {"pending":"⏳","approved":"✅","rejected":"❌",
                     "expired":"⌛","refunded":"💸"}.get(p.get("status"),"❓")
            txt += f"{emoji} ₹{p['amount']} → {p['credits']}cr | U{p['user_id']}\n"
        bot.send_message(cid, txt[:4000], parse_mode='HTML'); safe_ans(call); return
    if d == "adm_back_pay":
        try: bot.delete_message(cid, call.message.message_id)
        except: pass
        bot.send_message(cid, "💳 Payment", reply_markup=payments_kb()); safe_ans(call); return

    if d == "adm_svc_numcost":
        states[uid] = {'state': 'ads_input', 'field': 'search_cost', 'panel': 'main'}
        bot.send_message(cid, "📞 Number cost:"); safe_ans(call); return
    if d == "adm_svc_tgcost":
        states[uid] = {'state': 'ads_input', 'field': 'tg2num_cost', 'panel': 'main'}
        bot.send_message(cid, "🔒 Username cost:"); safe_ans(call); return
    if d == "adm_svc_aadhaarcost":
        states[uid] = {'state': 'ads_input', 'field': 'aadhaar_cost', 'panel': 'main'}
        bot.send_message(cid, "🆔 Aadhaar cost:"); safe_ans(call); return
    if d == "adm_svc_vehiclecost":
        states[uid] = {'state': 'ads_input', 'field': 'vehicle_cost', 'panel': 'main'}
        bot.send_message(cid, "🚗 Vehicle cost:"); safe_ans(call); return
    if d == "adm_svc_test":
        results = []
        for svc in SERVICE_KEYS:
            emoji = SERVICE_EMOJI.get(svc, "🔹")
            st = "🟢 ON" if is_service_enabled(svc) else "🔴 OFF"
            sr = api_success_rate(svc)
            sr_s = f"{sr}%" if sr is not None else "N/A"
            results.append(f"{emoji} {svc.title()}: {st} | ✅ {sr_s}")
        results.append(f"🛰️ Pyro: {'✅' if _pyro_ready else '❌'}")
        bot.send_message(cid, "🧪 <b>Health</b>\n\n" + "\n".join(results), parse_mode='HTML')
        safe_ans(call); return

    ep_map = {
        'adm_ep_numurl': 'api_url_env', 'adm_ep_numkey': 'api_key_env',
        'adm_ep_tgurl': 'tg2num_url_env', 'adm_ep_tgkey': 'tg2num_key_env',
        'adm_ep_aadhaarurl': 'aadhaar_url_env', 'adm_ep_aadhaarkey': 'aadhaar_key_env',
        'adm_ep_vehicleurl': 'vehicle_url_env', 'adm_ep_vehiclekey': 'vehicle_key_env',
    }
    if d in ep_map:
        field = ep_map[d]
        label, is_secret = ep_labels.get(field, (field, False))
        current = get_setting(field, "") or "(not set)"
        if is_secret and len(str(current)) > 4: current = "***" + str(current)[-4:]
        txt = (f"🔗 <b>{label}</b>\n\n<b>Current:</b>\n<code>{html_module.escape(str(current)[:200])}</code>")
        try:
            bot.edit_message_text(txt, cid, call.message.message_id, parse_mode='HTML', reply_markup=ep_edit_kb(field))
        except:
            bot.send_message(cid, txt, parse_mode='HTML', reply_markup=ep_edit_kb(field))
        safe_ans(call); return
    if d == "adm_ep_viewall":
        vals = []
        for k, label in [("api_url_env","Number URL"),("api_key_env","Number Key"),
            ("tg2num_url_env","TG2Num URL"),("tg2num_key_env","TG2Num Key"),
            ("aadhaar_url_env","Aadhaar URL"),("aadhaar_key_env","Aadhaar Key"),
            ("vehicle_url_env","Vehicle URL"),("vehicle_key_env","Vehicle Key")]:
            v = get_setting(k, "") or "not set"
            if "key" in k and len(str(v)) > 4: v = "***" + str(v)[-4:]
            vals.append(f"<b>{label}</b>:\n<code>{html_module.escape(str(v)[:150])}</code>")
        bot.send_message(cid, "🔗 <b>All Endpoints</b>\n\n" + "\n\n".join(vals), parse_mode='HTML')
        safe_ans(call); return

    if d == "adm_promo_gen": states[uid] = {'state': 'promo1'}; bot.send_message(cid, "🎟 Credits?"); safe_ans(call); return
    if d == "adm_promo_list":
        cs = all_promos()
        if not cs: bot.send_message(cid, "None."); safe_ans(call); return
        r = "🎟 <b>Promos</b>\n\n"
        for c in cs[:20]: r += f"<code>{c['code']}</code> – {c['reward_credits']}cr, {c['used_count']}/{c['max_users']}\n"
        bot.send_message(cid, r, parse_mode='HTML'); safe_ans(call); return
    if d == "adm_promo_stats":
        cs = all_promos(); used = sum(c.get("used_count", 0) for c in cs)
        bot.send_message(cid, f"🎟 Promos: {len(cs)}\nRedeems: {used}"); safe_ans(call); return

    if d == "adm_bc_text": states[uid] = {'state': 'broadcast'}; bot.send_message(cid, "📝 Send text:"); safe_ans(call); return
    if d == "adm_bc_photo": states[uid] = {'state': 'broadcast'}; bot.send_message(cid, "📸 Send photo:"); safe_ans(call); return
    if d == "adm_bc_video": states[uid] = {'state': 'broadcast'}; bot.send_message(cid, "🎬 Send video:"); safe_ans(call); return
    if d == "adm_bc_filtered":
        try: bot.edit_message_text("🎯 Filtered:", cid, call.message.message_id, parse_mode='HTML', reply_markup=broadcast_filtered_kb())
        except: pass
        safe_ans(call); return
    if d.startswith("adm_bcf_"):
        mode = d.replace("adm_bcf_", "")
        if mode == "all": targets = all_users()
        elif mode == "active": targets = active_users_24h()
        elif mode == "paid": targets = paying_users()
        elif mode == "nonpaid": targets = non_paying_users()
        else: targets = all_users()
        states[uid] = {'state': 'bc_filtered_custom', 'targets': targets}
        bot.send_message(cid, f"📢 Send for {len(targets)} users:"); safe_ans(call); return
    if d == "adm_bc_groups":
        groups = all_groups()
        if not groups: bot.send_message(cid, "None."); safe_ans(call); return
        states[uid] = {'state': 'bc_custom', 'targets': [g["chat_id"] for g in groups]}
        bot.send_message(cid, f"📢 Send to {len(groups)} groups:"); safe_ans(call); return
    if d == "adm_bc_settings":
        try: bot.edit_message_text("⚙️ BC Settings", cid, call.message.message_id, reply_markup=broadcast_settings_kb())
        except: pass
        safe_ans(call); return
    if d == "adm_bc_tog_pin":
        cur = int(get_setting("broadcast_pin", 0)); set_setting("broadcast_pin", 0 if cur else 1)
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=broadcast_settings_kb())
        except: pass
        safe_ans(call); return
    if d == "adm_bc_tog_fwd":
        cur = int(get_setting("broadcast_forward", 0)); set_setting("broadcast_forward", 0 if cur else 1)
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=broadcast_settings_kb())
        except: pass
        safe_ans(call); return
    if d == "adm_bc_back":
        try: bot.edit_message_text("📢 Broadcast", cid, call.message.message_id, reply_markup=broadcast_kb())
        except: pass
        safe_ans(call); return

    if d == "adm_grp_toggle":
        cur = int(get_setting("group_enabled", 1)); set_setting("group_enabled", 0 if cur else 1)
        audit(uid, "group_mode_toggle", details=str(0 if cur else 1))
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=groups_kb())
        except: pass
        safe_ans(call); return
    if d == "adm_grp_tog_autodel":
        cur = int(get_setting("group_auto_delete", 1)); set_setting("group_auto_delete", 0 if cur else 1)
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=groups_kb())
        except: pass
        safe_ans(call); return
    if d == "adm_grp_set_deltime":
        states[uid] = {'state': 'ads_input', 'field': 'group_auto_delete_seconds', 'panel': 'groups'}
        cur = group_auto_delete_seconds()
        bot.send_message(cid, f"⏱ Current: {cur}s\nSend seconds:"); safe_ans(call); return
    if d == "adm_grp_list":
        gs = all_groups()
        if not gs: bot.send_message(cid, "None."); safe_ans(call); return
        txt = f"👥 <b>Groups ({len(gs)})</b>\n\n"
        for g in gs[:30]: txt += f"📌 <b>{g.get('title','?')}</b>\n   <code>{g.get('chat_id')}</code>\n"
        bot.send_message(cid, txt, parse_mode='HTML'); safe_ans(call); return
    if d == "adm_grp_bc":
        gs = all_groups()
        if not gs: bot.send_message(cid, "None."); safe_ans(call); return
        states[uid] = {'state': 'bc_custom', 'targets': [g["chat_id"] for g in gs]}
        bot.send_message(cid, f"📢 Send to {len(gs)} groups:"); safe_ans(call); return
    if d == "adm_grp_welcome":
        states[uid] = {'state': 'grp_welcome'}
        cur = get_setting('group_welcome', '') or '(default)'
        bot.send_message(cid, f"📝 Current: {cur[:200]}\n\nSend new:"); safe_ans(call); return
    if d == "adm_grp_leave_all":
        gs = all_groups(); count = 0
        for g in gs:
            try:
                bot.leave_chat(g["chat_id"]); remove_group(g["chat_id"]); count += 1; time.sleep(0.3)
            except: pass
        bot.send_message(cid, f"✅ Left {count}"); safe_ans(call); return

    if d == "adm_sec_banned":
        bot.send_message(cid, f"🚫 {users_col.count_documents({'banned': 1})}"); safe_ans(call); return
    if d == "adm_sec_shadow_banned":
        arr = list(users_col.find({"shadow_banned": 1}).limit(30))
        if not arr: bot.send_message(cid, "None."); safe_ans(call); return
        txt = f"👻 <b>Shadow Banned ({len(arr)})</b>\n\n"
        for u in arr: txt += f"<code>{u.get('user_id')}</code>\n"
        bot.send_message(cid, txt, parse_mode='HTML'); safe_ans(call); return
    if d == "adm_sec_maint":
        cur = int(get_setting("maintenance_mode", 0)); set_setting("maintenance_mode", 0 if cur else 1)
        audit(uid, "maintenance_toggle", details=str(0 if cur else 1))
        bot.send_message(cid, f"🔧 {'ON' if not cur else 'OFF'}"); safe_ans(call); return
    if d == "adm_sec_subadmins":
        try: bot.edit_message_text("👑 Sub-Admins", cid, call.message.message_id, reply_markup=subadmins_kb())
        except: pass
        safe_ans(call); return
    if d == "adm_sec_back":
        try: bot.edit_message_text("🛡️ Security", cid, call.message.message_id, reply_markup=security_kb())
        except: pass
        safe_ans(call); return
    if d == "adm_sec_adminlimit":
        states[uid] = {'state': 'cd_input', 'field': 'admin_rate_limit_sec'}
        cur = get_setting("admin_rate_limit_sec", 0)
        bot.send_message(cid, f"⏱ Admin rate limit (sec, 0=off)\nCurrent: {cur}s\n\nSend new:")
        safe_ans(call); return
    if d == "adm_sec_audit":
        send_audit_panel(uid, cid); safe_ans(call); return
    if d == "adm_sub_add":
        if not is_main_admin(uid): safe_ans(call, "❌ Main only", True); return
        states[uid] = {'state': 'sub_add'}; bot.send_message(cid, "👑 Send id:"); safe_ans(call); return
    if d == "adm_sub_remove":
        if not is_main_admin(uid): safe_ans(call, "❌", True); return
        states[uid] = {'state': 'sub_remove'}; bot.send_message(cid, "Send user_id:"); safe_ans(call); return
    if d == "adm_sub_list":
        subs = list(admins_col.find())
        if not subs: bot.send_message(cid, "None."); safe_ans(call); return
        r = "👑 <b>Sub-Admins</b>\n\n"
        for s in subs: r += f"<code>{s['user_id']}</code>\n"
        bot.send_message(cid, r, parse_mode='HTML'); safe_ans(call); return

    if d == "adm_an_growth":
        days = []
        for i in range(7):
            day = now() - timedelta(days=i)
            start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            cnt = users_col.count_documents({"joined_at": {"$gte": start, "$lt": end}})
            days.append(f"{start.strftime('%d-%b')}: {cnt}")
        bot.send_message(cid, "📊 <b>7d Growth</b>\n\n" + "\n".join(reversed(days)), parse_mode='HTML')
        safe_ans(call); return
    if d == "adm_an_searches":
        tops = top_services_24h(5)
        txt = f"🔍 <b>Search Trends (24h)</b>\n\nTotal: {total_searches_24h()}\nFailed: {failed_searches_24h()}\n\n"
        for svc, cnt in tops: txt += f"• {svc}: {cnt}\n"
        if not tops: txt += "No data."
        bot.send_message(cid, txt, parse_mode='HTML'); safe_ans(call); return
    if d == "adm_an_revenue":
        p, a, r, rev, rf = pay_stats()
        bot.send_message(cid, f"💰 ₹{rev}\n24h: ₹{revenue_24h()}\n7d: ₹{revenue_7d()}\n"
                              f"Today: ₹{revenue_today()}\nYest: ₹{revenue_yesterday()}\nConv: {conversion_rate()}%")
        safe_ans(call); return
    if d == "adm_an_top":
        tops = list(users_col.find().sort("searches",-1).limit(5))
        r = "🏆 <b>Top</b>\n\n"
        for u in tops: r += f"<code>{u['user_id']}</code> — 🔍{u.get('searches',0)}\n"
        bot.send_message(cid, r, parse_mode='HTML'); safe_ans(call); return
    if d == "adm_an_refboard":
        tops = list(users_col.find({"total_referrals":{"$gt":0}}).sort("total_referrals",-1).limit(10))
        if not tops: bot.send_message(cid, "None."); safe_ans(call); return
        r = "🏆 <b>Referral Board</b>\n\n"
        for i, u in enumerate(tops, 1):
            r += f"{i}. <code>{u['user_id']}</code> — 🎁 {u.get('total_referrals',0)}\n"
        bot.send_message(cid, r, parse_mode='HTML'); safe_ans(call); return
    if d == "adm_an_api_health":
        txt = f"📡 <b>API Health</b>\n\n"
        for svc in SERVICE_KEYS:
            sr = api_success_rate(svc)
            emoji = SERVICE_EMOJI.get(svc, "🔹")
            sr_s = f"{sr}%" if sr is not None else "N/A"
            txt += f"{emoji} {svc.title()}: {sr_s}\n"
        bot.send_message(cid, txt, parse_mode='HTML'); safe_ans(call); return

    if d == "adm_bk_users":
        csv_d = export_csv()
        if csv_d:
            try:
                bio = io.BytesIO(csv_d.encode('utf-8')); bio.name = "users.csv"
                bot.send_document(cid, bio, caption="📤")
            except: pass
        safe_ans(call); return
    if d == "adm_bk_payments":
        try:
            ps = list(payments_col.find({}))
            o = io.StringIO(); w = csv.writer(o)
            w.writerow(["ID","User","Amount","Credits","Status","Created"])
            for p in ps:
                w.writerow([str(p.get("_id")),p.get("user_id"),p.get("amount"),p.get("credits"),p.get("status"),p.get("created_at","")])
            bio = io.BytesIO(o.getvalue().encode('utf-8')); bio.name = "payments.csv"
            bot.send_document(cid, bio, caption="📤")
        except: pass
        safe_ans(call); return
    if d == "adm_bk_full":
        try:
            data = {"users": list(users_col.find({}, {"_id": 0})),
                "payments": list(payments_col.find({}, {"_id": 0})),
                "promos": list(promo_col.find({}, {"_id": 0})),
                "groups": list(groups_col.find({}, {"_id": 0})),
                "settings": list(settings_col.find({}, {"_id": 0})),
                "feedback": list(feedback_col.find({}, {"_id": 0})),
                "notes": list(notes_col.find({}, {"_id": 0})),
                "audit": list(audit_col.find({}, {"_id": 0})),
                "exported_at": now().isoformat()}
            bio = io.BytesIO(json.dumps(data, default=str, indent=2).encode('utf-8'))
            bio.name = f"backup_{now().strftime('%Y%m%d_%H%M')}.json"
            bot.send_document(cid, bio, caption="💾 Backup")
        except Exception as e: bot.send_message(cid, f"❌ {e}")
        safe_ans(call); return
    if d == "adm_bk_feedback":
        try:
            fbs = list(feedback_col.find({}, {"_id": 0}))
            bio = io.BytesIO(json.dumps(fbs, default=str, indent=2).encode('utf-8'))
            bio.name = "feedback.json"
            bot.send_document(cid, bio, caption=f"📮 {len(fbs)}")
        except: pass
        safe_ans(call); return
    if d == "adm_bk_notes":
        try:
            ns = list(notes_col.find({}, {"_id": 0}))
            bio = io.BytesIO(json.dumps(ns, default=str, indent=2).encode('utf-8'))
            bio.name = "notes.json"
            bot.send_document(cid, bio, caption=f"📝 {len(ns)}")
        except: pass
        safe_ans(call); return
    if d == "adm_bk_audit":
        try:
            arr = list(audit_col.find({}, {"_id": 0}))
            bio = io.BytesIO(json.dumps(arr, default=str, indent=2).encode('utf-8'))
            bio.name = "audit_log.json"
            bot.send_document(cid, bio, caption=f"🔒 {len(arr)} entries")
        except: pass
        safe_ans(call); return

    if d == "adm_info_refresh":
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=botinfo_kb())
        except: pass
        safe_ans(call); return

    if d == "adm_fb_view":
        fbs = list(feedback_col.find().sort("at", -1).limit(10))
        if not fbs: bot.send_message(cid, "None."); safe_ans(call); return
        txt = "📮 <b>Feedback</b>\n\n"
        for f in fbs:
            t = f.get("at", "").strftime("%d-%b %H:%M") if f.get("at") else "?"
            txt += f"<code>{t}</code> | <code>{f.get('user_id')}</code>\n{f.get('text','')[:200]}\n{div_soft()}\n"
        bot.send_message(cid, txt[:4000], parse_mode='HTML'); safe_ans(call); return
    if d == "adm_fb_reply":
        states[uid] = {'state': 'fb_reply'}
        bot.send_message(cid, "💬 Format: <code>USER_ID|MESSAGE</code>", parse_mode='HTML')
        safe_ans(call); return
    if d == "adm_fb_clear":
        cnt = feedback_col.count_documents({}); feedback_col.delete_many({})
        bot.send_message(cid, f"✅ Cleared {cnt}"); safe_ans(call); return

    if d == "adm_audit_refresh":
        send_audit_panel(uid, cid); safe_ans(call); return
    if d == "adm_audit_export":
        try:
            arr = list(audit_col.find({}, {"_id": 0}))
            bio = io.BytesIO(json.dumps(arr, default=str, indent=2).encode('utf-8'))
            bio.name = "audit.json"
            bot.send_document(cid, bio, caption=f"🔒 {len(arr)} entries")
        except: pass
        safe_ans(call); return

    # FJ
    if d == "force_verify": manager.verify_cb(call); return
    if d.startswith('fj_'):
        if d == 'fj_toggle':
            manager.toggle()
            try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=force_kb())
            except: pass
            audit(uid, "fj_toggle")
            safe_ans(call); return
        if d == 'fj_list':
            chs = channel_list()
            txt = "📋 <b>Channels</b>\n\n" + "\n".join(
                f"<code>{c['channel_id']}</code> — {c['channel_link']}" for c in chs) if chs else "None"
            try:
                bot.edit_message_text(txt, cid, call.message.message_id, parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙", callback_data="adm_back")))
            except: pass
            safe_ans(call); return
        if d == 'fj_add':
            states[uid] = {'state': 'fj_add'}
            try: bot.edit_message_text("Send ID/@username:", cid, call.message.message_id)
            except: pass
            safe_ans(call); return
        if d == 'fj_remove':
            chs = channel_list()
            if not chs: safe_ans(call); return
            kb = InlineKeyboardMarkup(row_width=1)
            for c in chs: kb.add(InlineKeyboardButton(f"❌ {c['channel_id']}", callback_data=f"fj_del_{c['channel_id']}"))
            kb.add(InlineKeyboardButton("🔙", callback_data="adm_back"))
            try: bot.edit_message_text("Remove:", cid, call.message.message_id, reply_markup=kb)
            except: pass
            safe_ans(call); return
        if d.startswith('fj_del_'):
            manager.rm(int(d.split('_')[2])); audit(uid, "fj_del", target=d.split('_')[2])
            safe_ans(call, "Removed"); return
        if d == 'fj_stats':
            s = manager.stats()
            txt = (f"📊 <b>FJ Stats</b>\n\n🚫 Blocks: <b>{s['blocks']}</b>\n✅ Verifies: <b>{s['verifies']}</b>\n"
                   f"📢 Channels: <b>{len(manager.channels)}</b>\n"
                   f"🔀 Enabled: <b>{'Yes' if manager.global_enabled else 'No'}</b>")
            bot.send_message(cid, txt, parse_mode='HTML'); safe_ans(call); return
        if d == 'fj_set_msg':
            states[uid] = {'state': 'fj_custom_msg'}
            cur = get_setting("fj_custom_msg", "") or "(default)"
            bot.send_message(cid, f"✏️ Current:\n<code>{html_module.escape(str(cur)[:300])}</code>\n\nSend new or 'reset':",
                parse_mode='HTML')
            safe_ans(call); return
        if d == 'fj_test':
            kb_test = InlineKeyboardMarkup(row_width=1)
            for i, (ch, lk) in enumerate(manager.channels[:10]):
                kb_test.add(InlineKeyboardButton(f"📢 Channel {i+1}", url=lk))
            kb_test.add(InlineKeyboardButton("✅ Verify", callback_data="ps_noop"))
            custom = get_setting("fj_custom_msg", "")
            preview = custom if custom else f"⚠️ <b>{fancy('please join channels')}</b>"
            bot.send_message(cid, f"🧪 Preview\n\n{preview}", parse_mode='HTML', reply_markup=kb_test)
            safe_ans(call); return

    if d.startswith('ads_'):
        if d == 'ads_back':
            try: bot.edit_message_text("⚙️ Settings", cid, call.message.message_id, reply_markup=settings_main_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_eco':
            try: bot.edit_message_text("💎 Economics", cid, call.message.message_id, parse_mode='HTML', reply_markup=admin_economics_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_costs':
            try: bot.edit_message_text("🔍 Costs", cid, call.message.message_id, parse_mode='HTML', reply_markup=admin_costs_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_tries':
            try: bot.edit_message_text("🎯 Tries", cid, call.message.message_id, parse_mode='HTML', reply_markup=admin_tries_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_pay':
            try: bot.edit_message_text("💳 Payment", cid, call.message.message_id, parse_mode='HTML', reply_markup=admin_pay_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_sys':
            try: bot.edit_message_text("⚙️ System", cid, call.message.message_id, parse_mode='HTML', reply_markup=admin_sys_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_custom':
            try: bot.edit_message_text("🎨 Custom", cid, call.message.message_id, parse_mode='HTML', reply_markup=admin_custom_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_tog_ref':
            cur = int(get_setting("referral_enabled", 1)); set_setting("referral_enabled", 0 if cur else 1)
            try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=admin_economics_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_tog_mm':
            cur = int(get_setting("maintenance_mode", 0)); set_setting("maintenance_mode", 0 if cur else 1)
            audit(uid, "maintenance_toggle", details=str(0 if cur else 1))
            try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=admin_sys_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_tog_gw':
            cur = int(get_setting("gateway_enabled", 0)); set_setting("gateway_enabled", 0 if cur else 1)
            try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=admin_pay_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_tog_manual':
            cur = int(get_setting("upi_manual_enabled", 1)); set_setting("upi_manual_enabled", 0 if cur else 1)
            try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=admin_pay_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_tog_backup':
            cur = int(get_setting("auto_backup_enabled", 0)); set_setting("auto_backup_enabled", 0 if cur else 1)
            audit(uid, "toggle_auto_backup")
            try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=admin_sys_kb())
            except: pass
            safe_ans(call); return
        if d == 'ads_set_backup_hour':
            states[uid] = {'state': 'backup_hour'}
            cur = get_setting("auto_backup_hour", 3)
            bot.send_message(cid, f"⏰ Current: {cur}:00\nSend hour (0–23):"); safe_ans(call); return
        if d == 'ads_backup_now':
            bot.send_message(cid, "💾 Creating backup...")
            threading.Thread(target=lambda: (do_auto_backup(), None), daemon=True).start()
            audit(uid, "manual_backup")
            safe_ans(call); return
        if d == 'ads_set_alert':
            states[uid] = {'state': 'alert_set'}
            cur = get_setting("large_payment_alert", 500)
            bot.send_message(cid, f"🚨 Current: ₹{cur}\nSend new (0=off):"); safe_ans(call); return
        if d == 'ads_tries_unlimited':
            set_setting("daily_tries", 0)
            audit(uid, "daily_tries_unlimited")
            try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=admin_tries_kb())
            except: pass
            safe_ans(call, "✅ Unlimited"); return
        if d == 'ads_tries_reset_all':
            users_col.update_many({}, {"$set": {"tries_used": 0, "tries_date": today_str()}})
            audit(uid, "reset_all_tries")
            safe_ans(call, "✅ Reset", True); return
        if d == 'ads_export':
            csv_d = export_csv()
            if csv_d:
                try:
                    bio = io.BytesIO(csv_d.encode('utf-8')); bio.name = "users.csv"
                    bot.send_document(cid, bio, caption="📤")
                except: pass
            safe_ans(call); return
        if d == 'ads_cleancache':
            cnt = clean_old_cache()
            bot.send_message(cid, f"🧹 Cleaned {cnt}"); safe_ans(call); return
        if d == 'ads_pyro':
            info = [f"🛰️ Pyro", f"Ready: {'✅' if _pyro_ready else '❌'}",
                    f"Error: <code>{_pyro_error or 'none'}</code>"]
            bot.send_message(cid, "\n".join(info), parse_mode='HTML'); safe_ans(call); return
        if d == 'ads_mongo':
            try:
                mongo_client.admin.command("ping")
                bot.send_message(cid, f"✅ Mongo OK\nUsers: {users_col.count_documents({})}")
            except Exception as e: bot.send_message(cid, f"❌ {e}")
            safe_ans(call); return

        setter_map = {
            'ads_set_welcome': ('welcome_bonus','eco','Welcome bonus:'),
            'ads_set_refbonus': ('referral_bonus','eco','Referral bonus:'),
            'ads_set_rate': ('credits_per_rupee','eco','Rate (₹1 = X cr):'),
            'ads_set_scost': ('search_cost','costs','Number cost:'),
            'ads_set_acost': ('aadhaar_cost','costs','Aadhaar cost:'),
            'ads_set_tcost': ('tg2num_cost','costs','Username cost:'),
            'ads_set_vcost': ('vehicle_cost','costs','Vehicle cost:'),
            'ads_set_minpay': ('min_payment','costs','Min ₹:'),
            'ads_set_maxpay': ('max_payment','costs','Max ₹:'),
            'ads_set_tries': ('daily_tries','tries','Daily tries:'),
            'ads_set_gwkey': ('gateway_api_key','pay','API key:'),
            'ads_set_gwcreate': ('gateway_create_url','pay','Create URL:'),
            'ads_set_gwstatus': ('gateway_checkout_status_url','pay','Status URL:'),
            'ads_set_gwredirect': ('gateway_redirect_url','pay','Redirect:'),
            'ads_set_upiid': ('upi_manual_id','pay','UPI:'),
            'ads_set_upiqr': ('upi_manual_qr','pay','QR URL:'),
            'ads_set_powered': ('powered_by','custom','Powered by:'),
            'ads_set_about': ('about_text','custom','About:'),
            'ads_set_welcome_emoji': ('welcome_emoji','custom','Emoji:'),
            'ads_set_support': ('support_link','custom','Support:'),
        }
        if d in setter_map:
            field, panel, prompt = setter_map[d]
            current = get_setting(field, "") or "not set"
            states[uid] = {'state': 'ads_input', 'field': field, 'panel': panel}
            bot.send_message(cid, f"✏️ {prompt}\nCurrent: <code>{html_module.escape(str(current)[:100])}</code>",
                parse_mode='HTML')
            safe_ans(call); return

        if d == 'ads_set_quick':
            states[uid] = {'state': 'quick_amounts_edit'}
            cur = ",".join(str(x) for x in get_quick_amounts())
            bot.send_message(cid, f"⚡ <b>Quick Amounts</b>\n\nCurrent: <code>{cur}</code>\n\nSend comma-separated:")
            safe_ans(call); return

        if d == 'ads_set_watermark':
            states[uid] = {'state': 'wm_input'}
            cur = get_setting("watermark_text", "") or "(not set)"
            bot.send_message(cid, f"💧 Watermark:\nCurrent: <code>{html_module.escape(str(cur)[:100])}</code>", parse_mode='HTML')
            safe_ans(call); return
        if d == 'ads_set_bannedwords':
            states[uid] = {'state': 'banned_words'}
            cur = get_setting("banned_words", "") or "(not set)"
            bot.send_message(cid, f"🚫 Comma-separated:\nCurrent: <code>{html_module.escape(str(cur)[:200])}</code>", parse_mode='HTML')
            safe_ans(call); return
        if d == 'ads_set_maintmsg':
            states[uid] = {'state': 'maint_msg'}
            bot.send_message(cid, f"⚙️ Send msg or 'reset':", parse_mode='HTML')
            safe_ans(call); return
        return

    if d == "ps_noop": return

    if d.startswith('ap_'):
        if not is_admin: safe_ans(call, "❌", True); return
        pid = d.replace('ap_','',1)
        ok, p = approve_atomic(pid, uid)
        if not ok: safe_ans(call, "Processed", True); return
        add_credits(p["user_id"], p["credits"])
        try:
            users_col.update_one({"user_id": p["user_id"]},
                {"$inc": {"total_spent": p.get("amount", 0), "total_purchased": p.get("credits", 0)}})
        except: pass
        audit(uid, "payment_approve", target=p["user_id"],
              details=f"pid={pid} amt=₹{p.get('amount')} cr={p.get('credits')}")
        try:
            if call.message.caption:
                bot.edit_message_caption(cid, call.message.message_id,
                    caption=call.message.caption + "\n\n✅ Approved", parse_mode='HTML', reply_markup=None)
        except: pass
        try:
            bot.send_message(p["user_id"], f"✅ <b>Approved</b>\n💎 +{p['credits']}\n💰 {get_credits(p['user_id'])}",
                parse_mode='HTML')
        except: pass
        safe_ans(call, "✅"); return

    if d.startswith('rj_'):
        if not is_admin: safe_ans(call, "❌", True); return
        pid = d.replace('rj_','',1)
        ok, p = reject_atomic(pid, uid)
        if not ok: safe_ans(call, "Processed", True); return
        audit(uid, "payment_reject", target=p["user_id"], details=f"pid={pid}")
        try:
            if call.message.caption:
                bot.edit_message_caption(cid, call.message.message_id,
                    caption=call.message.caption + "\n\n❌ Rejected", parse_mode='HTML', reply_markup=None)
        except: pass
        try: bot.send_message(p["user_id"], "❌ Payment Rejected")
        except: pass
        safe_ans(call, "❌"); return

    if d.startswith('pv_'):
        if not is_admin: safe_ans(call, "❌", True); return
        pid = d.replace('pv_','',1)
        p = get_payment(pid)
        if not p: safe_ans(call, "Not found"); return
        status = p.get("status", "pending")
        mode = "⚡ Auto" if p.get("pay_mode")=="auto" else "📋 Manual"
        txt = (f"💰 <b>{mode}</b>\n{div()}\n\n"
               f"👤 <code>{p['user_id']}</code>\n₹{p['amount']}\n💎 {p['credits']}\n"
               f"📊 Status: <b>{status}</b>\n🆔 <code>{pid}</code>")
        if p.get("utr"): txt += f"\n🧾 UTR: <code>{p['utr']}</code>"
        kb = InlineKeyboardMarkup(row_width=2)
        if status == "pending":
            kb.row(InlineKeyboardButton("✅ Approve", callback_data=f"ap_{pid}"),
                   InlineKeyboardButton("❌ Reject", callback_data=f"rj_{pid}"))
        elif status == "approved":
            kb.row(InlineKeyboardButton("💸 Refund", callback_data=f"refund_{pid}"))
        kb.row(InlineKeyboardButton("🔙 Back", callback_data="adm_back_pay"))
        try: bot.edit_message_text(txt, cid, call.message.message_id, parse_mode='HTML', reply_markup=kb)
        except: pass
        safe_ans(call); return

    if d.startswith('refund_'):
        if not is_admin: safe_ans(call, "❌", True); return
        pid = d.replace('refund_','',1)
        p = get_payment(pid)
        if not p: safe_ans(call, "Not found"); return
        txt = (f"💸 <b>Confirm Refund?</b>\n\n👤 <code>{p['user_id']}</code>\n"
               f"₹{p.get('amount')} → {p.get('credits')}cr\n\n"
               f"⚠️ Credits deducted. Cannot undo.")
        try:
            bot.edit_message_text(txt, cid, call.message.message_id, parse_mode='HTML',
                reply_markup=refund_confirm_kb(pid))
        except: pass
        safe_ans(call); return

    if d.startswith("refund_yes_"):
        if not is_admin: safe_ans(call, "❌", True); return
        pid = d.replace("refund_yes_", "")
        ok, p, msg = refund_payment(pid, uid)
        if ok:
            audit(uid, "refund", target=p.get("user_id"), details=f"pid={pid}")
            try:
                bot.send_message(p["user_id"],
                    f"💸 <b>Refund Processed</b>\n\n₹{p.get('amount')} refunded.", parse_mode='HTML')
            except: pass
            safe_ans(call, f"✅ {msg}", True)
            try: bot.edit_message_text(f"💸 Refunded: {msg}", cid, call.message.message_id, parse_mode='HTML')
            except: pass
        else:
            safe_ans(call, f"❌ {msg}", True)
        return

    if d == "home":
        bot.send_message(cid, "🏠", reply_markup=main_kb(uid)); safe_ans(call); return
    if d == "close":
        try: bot.delete_message(cid, call.message.message_id)
        except: pass
        safe_ans(call); return
    if d.startswith("copyref_"):
        try: tgt = int(d.split("_")[1])
        except: tgt = uid
        link = f"https://t.me/{BOT_USERNAME.replace('@','')}?start=ref_{tgt}"
        bot.send_message(cid, f"🔗 <b>Referral</b>\n\n<code>{link}</code>", parse_mode='HTML')
        safe_ans(call); return
    safe_ans(call)

# =================================================================
#  ENTRY
# =================================================================
if __name__ == "__main__":
    init_db()
    manager = FJManager(bot)
    logger.info("🚀 Bot v28.2 FINAL starting...")
    init_pyrogram()
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info(f"🛰️ Pyrogram: {'READY' if _pyro_ready else 'DISABLED'}")
    logger.info(f"💱 Rate: ₹1 = {get_rate()} credits")
    logger.info(f"⚡ Quick amounts: {get_quick_amounts()}")
    logger.info(f"📢 FJ: {'ON' if str(get_setting('force_enabled','1'))=='1' else 'OFF'}")
    resume_pending_orders()

    try:
        bot.set_my_commands([
            BotCommand("start", "🏠 Main Menu / Group Help"),
            BotCommand("buy", "🛒 Buy Credits"),
            BotCommand("my_tries", "🎯 My Tries"),
            BotCommand("feedback", "📮 Feedback"),
            BotCommand("help", "❓ Help"),
            BotCommand("addgroup", "➕ Add to Group"),
            BotCommand("cancel", "❌ Cancel"),
            BotCommand("num", "📞 Number search"),
            BotCommand("aadhar", "🆔 Aadhaar search"),
            BotCommand("tg", "🔒 Username search"),
            BotCommand("vehicle", "🚗 Vehicle search"),
        ])
    except: pass

    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.critical(f"Crashed: {e}")