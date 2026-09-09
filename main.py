import telebot
from telebot import types
import json
import os
import random
import string
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
import threading
import sys

# ===== CẤU HÌNH =====
BOT_TOKEN = "8990113148:AAH1wgUusu_Z3AW2JNF4JwivXAvCDOFLO8U"
ADMIN_IDS = [8363711905, 8030294480]  # Hai admin

# Thông tin ngân hàng MB Bank
BANK_ID = "970422"
ACCOUNT_NO = "101072011"
ACCOUNT_NAME = "NGUYEN VAN GIA HUY"

# File lưu dữ liệu
USERS_FILE = "users.json"
ORDERS_FILE = "orders.json"

# ===== API ENDPOINTS =====
API_BASE = "https://carter-learned-locked-stadium.trycloudflare.com/api"
API_ENDPOINTS = {
    "789_tx": f"{API_BASE}/789/history",
    "b52_tx": f"{API_BASE}/b52_tx/history",
    "b52_md5": f"{API_BASE}/b52_md5/history",
    "betvip_tx": f"{API_BASE}/bet_tx/history",
    "betvip_md5": f"{API_BASE}/bet_md5/history",
    "haywin_tx": f"{API_BASE}/hay_tx/history",
    "haywin_md5": f"{API_BASE}/hay_md5/history",
    "hitclub_tx": f"{API_BASE}/hit_tx/history",
    "hitclub_md5": f"{API_BASE}/hit_md5/history",
    "lc79_tx": f"{API_BASE}/lc_tx/history",
    "lc79_md5": f"{API_BASE}/lc_md5/history",
    "luck8_tx": f"{API_BASE}/luck8_tx/history",
    "luck8_md5": f"{API_BASE}/luck8_md5/history",
    "max789_tx": f"{API_BASE}/max_tx/history",
    "max789_md5": f"{API_BASE}/max_md5/history",
    "xocdia88_tx": f"{API_BASE}/xocdia88_tx/history",
    "xocdia88_md5": f"{API_BASE}/xocdia88_md5/history",
    "sumclub_tx": f"{API_BASE}/sumclub_tx/history",
    "sumclub_md5": f"{API_BASE}/sumclub_md5/history",
    "sunwin_tx": f"{API_BASE}/sunwin/history",
    "son789_tx": f"{API_BASE}/son789/history",
}

# ===== KHỞI TẠO BOT =====
bot = telebot.TeleBot(BOT_TOKEN)

# ===== DỮ LIỆU TẠM =====
user_states = {}
auto_tasks = {}  # user_id -> threading.Event (dừng)

# ===== HÀM TIỆN ÍCH =====
def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Lỗi đọc file {filename}: {e}")
            return default
    return default

def save_json(filename, data):
    try:
        # Tạo bản sao lưu trước khi ghi
        if os.path.exists(filename):
            backup_filename = f"{filename}.backup"
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    backup_data = f.read()
                with open(backup_filename, "w", encoding="utf-8") as f:
                    f.write(backup_data)
            except:
                pass
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Lỗi ghi file {filename}: {e}")
        return False

def export_all_data():
    """Xuất tất cả dữ liệu ra file JSON"""
    data = {
        "users": load_json(USERS_FILE, {}),
        "orders": load_json(ORDERS_FILE, {}),
        "export_time": get_vietnam_time().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0"
    }
    filename = f"backup_data_{get_vietnam_time().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename

def import_all_data(json_file_path):
    """Nhập dữ liệu từ file JSON"""
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "users" in data:
            save_json(USERS_FILE, data["users"])
            print(f"Đã nhập {len(data['users'])} user")
        if "orders" in data:
            save_json(ORDERS_FILE, data["orders"])
            print(f"Đã nhập {len(data['orders'])} đơn hàng")
        return True
    except Exception as e:
        print(f"Lỗi import dữ liệu: {e}")
        return False

def get_user_data(user_id):
    users = load_json(USERS_FILE, {})
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            "balance": 0,
            "vip": False,
            "fullname": "",
            "username": "",
            "key_expiry": None
        }
        save_json(USERS_FILE, users)
    return users, users[user_id_str]

def get_orders():
    return load_json(ORDERS_FILE, {})

def save_orders(orders):
    return save_json(ORDERS_FILE, orders)

def generate_order_id():
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"TGTX247{random_part}"

def get_vietnam_time():
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

def create_qr_image(amount, order_id):
    add_info = order_id
    url = (
        f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact2.png"
        f"?amount={amount}&addInfo={add_info}&accountName={ACCOUNT_NAME}"
    )
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
        else:
            return None
    except:
        return None

def is_key_valid(user_data):
    expiry = user_data.get("key_expiry")
    if expiry is None:
        return False
    if expiry == "forever":
        return True
    try:
        expiry_dt = datetime.fromisoformat(expiry)
        return expiry_dt > get_vietnam_time()
    except:
        return False

def fetch_game_history(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "history" in data and isinstance(data["history"], list):
                return data["history"]
    except:
        pass
    return None

def predict_tai_xiu_advanced(history_list):
    if not history_list:
        return None, None, None, None

    recent = history_list[:100]

    results = []
    for item in reversed(recent):
        if item.get("ket_qua") == "Tài":
            results.append(1)
        else:
            results.append(0)

    if len(results) < 2:
        tai_count = sum(results)
        total = len(results)
        xiu_count = total - tai_count
        if tai_count >= xiu_count:
            prediction = "Tài"
            confidence = (tai_count / total) * 100
        else:
            prediction = "Xỉu"
            confidence = (xiu_count / total) * 100
        analysis = "Dữ liệu ít, dự đoán theo tần suất tổng."
    else:
        transition = [[0, 0], [0, 0]]
        count_transition = [[0, 0], [0, 0]]

        for i in range(len(results) - 1):
            prev = results[i]
            nxt = results[i+1]
            count_transition[prev][nxt] += 1

        total_from_0 = sum(count_transition[0])
        total_from_1 = sum(count_transition[1])

        if total_from_0 > 0:
            transition[0][0] = count_transition[0][0] / total_from_0
            transition[0][1] = count_transition[0][1] / total_from_0
        else:
            transition[0] = [0.5, 0.5]

        if total_from_1 > 0:
            transition[1][0] = count_transition[1][0] / total_from_1
            transition[1][1] = count_transition[1][1] / total_from_1
        else:
            transition[1] = [0.5, 0.5]

        current_state = results[-1]
        prob_next_tai = transition[current_state][1]
        prob_next_xiu = transition[current_state][0]

        last_3 = results[-3:] if len(results) >= 3 else results
        if len(last_3) == 3 and all(x == last_3[0] for x in last_3):
            bet_count = 0
            break_count = 0
            for i in range(len(results) - 3):
                if results[i] == last_3[0] and results[i+1] == last_3[0] and results[i+2] == last_3[0]:
                    if i+3 < len(results):
                        if results[i+3] == last_3[0]:
                            bet_count += 1
                        else:
                            break_count += 1
            if bet_count + break_count > 0:
                bet_ratio = bet_count / (bet_count + break_count)
                if last_3[0] == 1:
                    prob_next_tai = prob_next_tai * 0.6 + bet_ratio * 0.4
                    prob_next_xiu = 1 - prob_next_tai
                else:
                    prob_next_xiu = prob_next_xiu * 0.6 + bet_ratio * 0.4
                    prob_next_tai = 1 - prob_next_xiu

        if prob_next_tai >= prob_next_xiu:
            prediction = "Tài"
            confidence = prob_next_tai * 100
        else:
            prediction = "Xỉu"
            confidence = prob_next_xiu * 100

        analysis = f"📈 Markov: P(T|{'T' if current_state==1 else 'X'})={prob_next_tai:.2%}, P(X|{'T' if current_state==1 else 'X'})={prob_next_xiu:.2%}"
        if len(last_3) == 3 and all(x == last_3[0] for x in last_3):
            analysis += f"\n🔁 Bệt 3 {'Tài' if last_3[0]==1 else 'Xỉu'}: tỉ lệ bệt tiếp {bet_ratio:.0%} (dựa trên {bet_count+break_count} lần)"

    latest_5 = recent[:5]
    recent_5_text = "\n".join(
        [f"#{item['phien']} - {'🟢 Tài' if item['ket_qua']=='Tài' else '🔴 Xỉu'} (Tổng {item['tong']})" for item in latest_5]
    )

    return prediction, confidence, recent_5_text, analysis

def send_prediction(chat_id, game_id, type_, prediction, confidence, recent_5_text, analysis, auto_mode=False):
    if prediction == "Tài":
        prediction_icon = "🟢"
        prediction_emoji = "🔥"
    else:
        prediction_icon = "🔴"
        prediction_emoji = "💧"

    result_text = f"""✨🌟💎 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗗𝗨̛̣ Đ𝗢𝗔́𝗡 💎🌟✨
━━━━━━━━━━━━━━━━━
🎮 𝗚𝗮𝗺𝗲: {game_id.upper()} ({'TX' if type_=='tx' else 'MD5'})
{prediction_icon} 𝗗𝘂̛̣ đ𝗼𝗮́𝗻: {prediction_emoji} {prediction}
📊 𝗧𝘆̉ 𝗹𝗲̣̂ 𝘁𝗶𝗻 𝗰𝗮̣̂𝘆: {confidence:.1f}%
━━━━━━━━━━━━━━━━━
🔍 𝗣𝗵𝗮̂𝗻 𝘁𝗶́𝗰𝗵 𝗰𝗮̂̀𝘂:
{analysis}
━━━━━━━━━━━━━━━━━
📜 𝟱 𝗽𝗵𝗶𝗲̂𝗻 𝗴𝗮̂̀𝗻 𝗻𝗵𝗮̂́𝘁:
{recent_5_text}
━━━━━━━━━━━━━━━━━
⚠️ 𝗗𝘂̛̣ đ𝗼𝗮́𝗻 𝗰𝗵𝗶̉ 𝗺𝗮𝗻𝗴 𝘁𝗶́𝗻𝗵 𝘁𝗵𝗮𝗺 𝗸𝗵𝗮̉𝗼"""

    markup = types.InlineKeyboardMarkup()
    if auto_mode:
        btn_stop = types.InlineKeyboardButton("⏹️ Dừng Auto", callback_data="stop_auto")
        markup.add(btn_stop)
    bot.send_message(chat_id, result_text, reply_markup=markup)

# ===== AUTO DETECT =====
def auto_worker(user_id, chat_id, game_id, type_, stop_event):
    endpoint_key = f"{game_id}_{type_}"
    url = API_ENDPOINTS.get(endpoint_key)
    if not url:
        return

    last_phien = None
    # Lấy phiên mới nhất ban đầu
    history = fetch_game_history(url)
    if history:
        last_phien = history[0]["phien"]

    while not stop_event.is_set():
        try:
            time.sleep(5)  # Kiểm tra mỗi 5 giây
            history = fetch_game_history(url)
            if history:
                newest_phien = history[0]["phien"]
                if newest_phien != last_phien:
                    last_phien = newest_phien
                    # Có phiên mới, dự đoán
                    prediction, confidence, recent_5_text, analysis = predict_tai_xiu_advanced(history)
                    if prediction:
                        send_prediction(chat_id, game_id, type_, prediction, confidence, recent_5_text, analysis, auto_mode=True)
        except Exception as e:
            print(f"Auto worker error: {e}")
    # Khi dừng, xóa khỏi auto_tasks
    auto_tasks.pop(user_id, None)

def start_auto(user_id, chat_id, game_id, type_):
    # Nếu đã có auto đang chạy, dừng cũ trước
    if user_id in auto_tasks:
        auto_tasks[user_id].set()
        time.sleep(0.1)
    stop_event = threading.Event()
    auto_tasks[user_id] = stop_event
    t = threading.Thread(target=auto_worker, args=(user_id, chat_id, game_id, type_, stop_event))
    t.daemon = True
    t.start()

def stop_auto(user_id):
    if user_id in auto_tasks:
        auto_tasks[user_id].set()
        # Không cần xóa ngay, worker sẽ xóa

# ===== XỬ LÝ LỆNH /start =====
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    fullname = message.from_user.full_name
    username = message.from_user.username or "Không có"

    users, user_data = get_user_data(user_id)
    user_data["fullname"] = fullname
    user_data["username"] = username
    save_json(USERS_FILE, users)

    vip_status = "Chưa Kích Hoạt Vip ‼️"
    if is_key_valid(user_data):
        expiry = user_data.get("key_expiry")
        vip_status = f"✅ Đã Kích Hoạt (Hết hạn: {expiry})"

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_nap = types.InlineKeyboardButton("💳 𝗡𝗔̣𝗣 𝗧𝗜𝗘̂̀𝗡", callback_data="nap_tien")
    btn_muakey = types.InlineKeyboardButton("🔒 𝗠𝗨𝗔 𝗞𝗘𝗬", callback_data="mua_key")
    btn_dungtool = types.InlineKeyboardButton("🎮 𝗗𝗨̀𝗡𝗚 𝗧𝗢𝗢𝗟", callback_data="dung_tool")
    markup.add(btn_nap, btn_muakey, btn_dungtool)

    text = f"""🔰 𝗧𝗢𝗢𝗟𝗚𝗔𝗠𝗘𝗧𝗫 𝟮𝟰𝟳     🔰
=============================
👋 Xin Chào , {fullname}
🆔 𝗨𝗦𝗘𝗥 𝗜𝗗 : {user_id}
👤 𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘 : {username}
💳 𝗦𝗢̂́ 𝗗𝗨̛ 𝗖𝗢̀𝗡 𝗟𝗔̣𝗜 : {user_data['balance']} VND
🔐 𝗩𝗜𝗣 : {vip_status}
=============================
📢 𝗞𝗘̂𝗡𝗛 𝗧𝗛𝗢̂𝗡𝗚 𝗕𝗔́𝗢 : @ThongBaoH11
👤 𝗔𝗗𝗠𝗜𝗡 𝗛𝗢̂̃ 𝗧𝗥𝗢̛̣ : @HuyDaiXuVN 
========================
💓 𝗖𝗛𝗨́𝗖 𝗠𝗢̣𝗜 𝗡𝗚𝗨̛𝗢̛̀𝗜 𝗦𝗨̛̉ 𝗗𝗨̣𝗡𝗚 𝗕𝗢𝗧 𝗩𝗨𝗜 𝗩𝗘̉ 💓"""

    bot.send_message(message.chat.id, text, reply_markup=markup)

# ===== ADMIN COMMANDS =====
@bot.message_handler(commands=['exportdata'])
def handle_export_data(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "**Bạn không có quyền sử dụng lệnh này.**", parse_mode="Markdown")
        return
    
    filename = export_all_data()
    with open(filename, "rb") as f:
        bot.send_document(message.chat.id, f, caption=f"📦 Dữ liệu backup ngày {get_vietnam_time().strftime('%Y-%m-%d %H:%M:%S')}")

@bot.message_handler(commands=['importdata'])
def handle_import_data(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "**Bạn không có quyền sử dụng lệnh này.**", parse_mode="Markdown")
        return
    
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, "**Vui lòng reply file JSON backup với lệnh /importdata**", parse_mode="Markdown")
        return
    
    try:
        file_info = bot.get_file(message.reply_to_message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Lưu file tạm
        temp_file = "temp_import.json"
        with open(temp_file, "wb") as f:
            f.write(downloaded_file)
        
        if import_all_data(temp_file):
            bot.reply_to(message, "✅ **Import dữ liệu thành công!**", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ **Import dữ liệu thất bại!**", parse_mode="Markdown")
        
        os.remove(temp_file)
    except Exception as e:
        bot.reply_to(message, f"❌ **Lỗi: {str(e)}**", parse_mode="Markdown")

@bot.message_handler(commands=['viewdata'])
def handle_view_data(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "**Bạn không có quyền sử dụng lệnh này.**", parse_mode="Markdown")
        return
    
    users = load_json(USERS_FILE, {})
    orders = load_json(ORDERS_FILE, {})
    
    total_users = len(users)
    total_orders = len(orders)
    pending_orders = len([o for o in orders.values() if o.get("status") == "pending_approval"])
    total_balance = sum(u.get("balance", 0) for u in users.values())
    
    msg = f"""📊 **THỐNG KÊ DỮ LIỆU**
========================
👤 Tổng người dùng: {total_users}
📦 Tổng đơn hàng: {total_orders}
⏳ Đơn chờ duyệt: {pending_orders}
💰 Tổng số dư: {total_balance:,} VND
========================
📅 {get_vietnam_time().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    bot.reply_to(message, msg, parse_mode="Markdown")

# ===== XỬ LÝ CALLBACK =====
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data

    if data == "nap_tien":
        user_states[user_id] = {"state": "waiting_for_amount", "order_id": None, "attempts": 0}
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "**- VUI LÒNG NHẬP SỐ TIỀN CẦN NẠP ( Tối Thiểu 10000 VND )**", parse_mode="Markdown")

    elif data == "mua_key":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_1d = types.InlineKeyboardButton("Key 1 Ngày - 40,000 VND", callback_data="buy_key_1")
        btn_3d = types.InlineKeyboardButton("Key 3 Ngày - 70,000 VND", callback_data="buy_key_3")
        btn_1w = types.InlineKeyboardButton("Key 1 Tuần - 100,000 VND", callback_data="buy_key_7")
        btn_1m = types.InlineKeyboardButton("Key 1 Tháng - 200,000 VND", callback_data="buy_key_30")
        btn_forever = types.InlineKeyboardButton("Key Vĩnh Viễn - 350,000 VND", callback_data="buy_key_forever")
        btn_back = types.InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_to_start")
        markup.add(btn_1d, btn_3d, btn_1w, btn_1m, btn_forever, btn_back)

        text = """🔰 𝗕𝗔̉𝗡𝗚 𝗚𝗜𝗔́ 𝗞𝗘𝗬 𝗧𝗢𝗢𝗟 🔰
=============================
📅 Key 1 Ngày - 40,000 VND
📅 Key 3 Ngày - 70,000 VND
📅 Key 1 Tuần - 100,000 VND
📅 Key 1 Tháng - 200,000 VND
👑 Key Vĩnh Viễn - 350,000 VND
=============================
Chọn gói Key bạn muốn mua bên dưới 👇"""

        bot.send_message(call.message.chat.id, text, reply_markup=markup)

    elif data.startswith("buy_key_"):
        users, user_data = get_user_data(user_id)
        balance = user_data.get("balance", 0)

        key_prices = {
            "buy_key_1": (1, 40000),
            "buy_key_3": (3, 70000),
            "buy_key_7": (7, 100000),
            "buy_key_30": (30, 200000),
            "buy_key_forever": (None, 350000)
        }
        days, price = key_prices.get(data, (None, 0))

        if balance < price:
            bot.answer_callback_query(call.id, f"Số dư không đủ! Bạn cần {price:,} VND, hiện có {balance:,} VND.", show_alert=True)
            return

        user_data["balance"] = balance - price

        if days is None:
            expiry_str = "forever"
        else:
            expiry_dt = get_vietnam_time() + timedelta(days=days)
            expiry_str = expiry_dt.isoformat()

        user_data["key_expiry"] = expiry_str
        save_json(USERS_FILE, users)

        bot.answer_callback_query(call.id, f"✅ Mua Key thành công! Đã trừ {price:,} VND.", show_alert=True)

        expiry_display = "Vĩnh Viễn" if days is None else expiry_str
        msg = f"""🎉 𝗠𝗨𝗔 𝗞𝗘𝗬 𝗧𝗛𝗔̀𝗡𝗛 𝗖𝗢̂𝗡𝗚 🎉
=============================
📦 Gói: {key_prices[data][0] if days else 'Vĩnh Viễn'}
💰 Giá: {price:,} VND
💳 Số dư còn lại: {user_data['balance']:,} VND
⏰ Hết hạn: {expiry_display}
=============================
Bạn có thể sử dụng Tool ngay bây giờ!"""

        markup = types.InlineKeyboardMarkup()
        btn_start = types.InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_to_start")
        markup.add(btn_start)
        bot.send_message(call.message.chat.id, msg, reply_markup=markup)

    elif data == "back_to_start":
        bot.answer_callback_query(call.id)
        class FakeMsg:
            pass
        fake = FakeMsg()
        fake.chat = call.message.chat
        fake.from_user = call.from_user
        handle_start(fake)

    elif data == "dung_tool":
        users, user_data = get_user_data(user_id)
        if is_key_valid(user_data):
            bot.answer_callback_query(call.id, "Key hợp lệ. Chọn game bên dưới.", show_alert=False)
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_sunwin_tx = types.InlineKeyboardButton("☀️ SunWin - TX", callback_data="tool_sunwin_tx")
            btn_son789_tx = types.InlineKeyboardButton("🌟 Son789 - TX", callback_data="tool_son789_tx")
            btn_789_tx = types.InlineKeyboardButton("🎯 789 Club - TX", callback_data="tool_789_tx")
            markup.add(btn_sunwin_tx, btn_son789_tx, btn_789_tx)

            btn_b52_tx = types.InlineKeyboardButton("💣 B52 - TX", callback_data="tool_b52_tx")
            btn_b52_md5 = types.InlineKeyboardButton("💣 B52 - MD5", callback_data="tool_b52_md5")
            markup.add(btn_b52_tx, btn_b52_md5)

            btn_betvip_tx = types.InlineKeyboardButton("💎 BetVip - TX", callback_data="tool_betvip_tx")
            btn_betvip_md5 = types.InlineKeyboardButton("💎 BetVip - MD5", callback_data="tool_betvip_md5")
            markup.add(btn_betvip_tx, btn_betvip_md5)

            btn_hitclub_tx = types.InlineKeyboardButton("🎪 HitClub - TX", callback_data="tool_hitclub_tx")
            btn_hitclub_md5 = types.InlineKeyboardButton("🎪 HitClub - MD5", callback_data="tool_hitclub_md5")
            markup.add(btn_hitclub_tx, btn_hitclub_md5)

            btn_lc79_tx = types.InlineKeyboardButton("🦀 LC79 - TX", callback_data="tool_lc79_tx")
            btn_lc79_md5 = types.InlineKeyboardButton("🦀 LC79 - MD5", callback_data="tool_lc79_md5")
            markup.add(btn_lc79_tx, btn_lc79_md5)

            btn_luck8_tx = types.InlineKeyboardButton("🍀 Luck8 - TX", callback_data="tool_luck8_tx")
            btn_luck8_md5 = types.InlineKeyboardButton("🍀 Luck8 - MD5", callback_data="tool_luck8_md5")
            markup.add(btn_luck8_tx, btn_luck8_md5)

            btn_max789_tx = types.InlineKeyboardButton("🔱 Max789 - TX", callback_data="tool_max789_tx")
            btn_max789_md5 = types.InlineKeyboardButton("🔱 Max789 - MD5", callback_data="tool_max789_md5")
            markup.add(btn_max789_tx, btn_max789_md5)

            btn_xocdia88_tx = types.InlineKeyboardButton("🎰 XocDia88 - TX", callback_data="tool_xocdia88_tx")
            btn_xocdia88_md5 = types.InlineKeyboardButton("🎰 XocDia88 - MD5", callback_data="tool_xocdia88_md5")
            markup.add(btn_xocdia88_tx, btn_xocdia88_md5)

            btn_sumclub_tx = types.InlineKeyboardButton("🌞 SumClub - TX", callback_data="tool_sumclub_tx")
            btn_sumclub_md5 = types.InlineKeyboardButton("🌞 SumClub - MD5", callback_data="tool_sumclub_md5")
            markup.add(btn_sumclub_tx, btn_sumclub_md5)

            btn_haywin_tx = types.InlineKeyboardButton("🍒 HayWin - TX", callback_data="tool_haywin_tx")
            btn_haywin_md5 = types.InlineKeyboardButton("🍒 HayWin - MD5", callback_data="tool_haywin_md5")
            markup.add(btn_haywin_tx, btn_haywin_md5)

            text = "👇 𝗖𝗵𝗼̣𝗻 𝗚𝗮𝗺𝗲 𝗖𝗮̂̀𝗻 𝗗𝘂̀𝗻𝗴:"
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "Bạn chưa có Key hoặc Key đã hết hạn!", show_alert=True)
            tool_list = """👇 𝗖𝗵𝗼̣𝗻 𝗧𝗼𝗼𝗹 𝗖𝗮̂̀𝗻 𝗗𝘂̀𝗻𝗴:

☀️ 𝗦𝘂𝗻𝗪𝗶𝗻 — TX
🔱 𝗠𝗮𝘅𝟳𝟴𝟵 — TX, MD5
🎯 𝗛𝗶𝘁𝗖𝗹𝘂𝗯 — TX, MD5
💣 𝗕𝟱𝟮 — TX, MD5
💎 𝗕𝗲𝘁𝗩𝗶𝗽 — TX, MD5
🦀 𝗟𝗖𝟳𝟵 — TX, MD5
🌟 𝗦𝘂𝗺𝗖𝗹𝘂𝗯 — TX, MD5
🎪 𝗫𝗼𝗰𝗗𝗶𝗮𝟴𝟴 — TX, MD5
🍀 𝗛𝗮𝘆𝗪𝗶𝗻 — TX, MD5
🍒 𝟳𝟴𝟵𝗖𝗹𝘂𝗯 — TX
🍀 𝗟𝘂𝗰𝗸𝟴 — TX, MD5
🌟 𝗦𝗼𝗻𝟳𝟴𝟵 — TX

⚠️ 𝗕𝗮̣𝗻 𝗰𝗵𝘂̛𝗮 𝗰𝗼́ 𝗞𝗲𝘆! 𝗩𝘂𝗶 𝗹𝗼̀𝗻𝗴 𝗺𝘂𝗮 𝗞𝗲𝘆 đ𝗲̂̉ 𝘀𝘂̛̉ 𝗱𝘂̣𝗻𝗴."""
            bot.send_message(call.message.chat.id, tool_list)

    elif data.startswith("tool_"):
        users, user_data = get_user_data(user_id)
        if not is_key_valid(user_data):
            bot.answer_callback_query(call.id, "Key đã hết hạn. Vui lòng mua key mới.", show_alert=True)
            return

        parts = data.split("_")
        if len(parts) >= 3:
            game_id = "_".join(parts[1:-1])
            type_ = parts[-1]
            endpoint_key = f"{game_id}_{type_}"
        else:
            bot.answer_callback_query(call.id, "Dữ liệu không hợp lệ.", show_alert=True)
            return

        if endpoint_key not in API_ENDPOINTS:
            bot.answer_callback_query(call.id, "Không tìm thấy API cho game này.", show_alert=True)
            return

        if user_id in auto_tasks:
            stop_auto(user_id)

        bot.answer_callback_query(call.id, "Đang bắt đầu auto dự đoán...")
        loading_msg = bot.send_message(call.message.chat.id, "⏳ Đang tải dữ liệu và bắt đầu auto...")

        url = API_ENDPOINTS[endpoint_key]
        history = fetch_game_history(url)
        if history is None:
            bot.edit_message_text("❌ Lỗi khi tải dữ liệu từ server. Vui lòng thử lại sau.", call.message.chat.id, loading_msg.message_id)
            return

        prediction, confidence, recent_5_text, analysis = predict_tai_xiu_advanced(history)
        if prediction is None:
            bot.edit_message_text("❌ Không có dữ liệu lịch sử để dự đoán.", call.message.chat.id, loading_msg.message_id)
            return

        bot.delete_message(call.message.chat.id, loading_msg.message_id)
        send_prediction(call.message.chat.id, game_id, type_, prediction, confidence, recent_5_text, analysis, auto_mode=True)
        start_auto(user_id, call.message.chat.id, game_id, type_)

    elif data == "stop_auto":
        if user_id in auto_tasks:
            stop_auto(user_id)
            bot.answer_callback_query(call.id, "Đã dừng auto dự đoán.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Không có auto nào đang chạy.", show_alert=True)

    elif data.startswith("toi_da_chuyen_"):
        order_id = data.replace("toi_da_chuyen_", "")
        orders = get_orders()
        if order_id in orders and orders[order_id]["user_id"] == user_id and orders[order_id]["status"] == "created":
            orders[order_id]["status"] = "awaiting_receipt"
            save_orders(orders)
            user_states[user_id] = {"state": "waiting_for_receipt", "order_id": order_id, "attempts": 0}
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "**- VUI LÒNG GỬI BIÊN LAI BẠN ĐÃ CHUYỂN KHOẢN ĐỂ CHÚNG TÔI DUYỆT NHANH NHẤT**", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "Đơn nạp không hợp lệ hoặc đã xử lý", show_alert=True)

# ===== XỬ LÝ TIN NHẮN VĂN BẢN =====
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if text.startswith("/duyet"):
        handle_admin_duyet(message)
        return

    if user_id in user_states:
        state_info = user_states[user_id]
        if state_info["state"] == "waiting_for_amount":
            try:
                amount = int(text)
            except:
                bot.reply_to(message, "**Vui lòng nhập số tiền hợp lệ (số nguyên)**", parse_mode="Markdown")
                return

            if amount < 10000:
                bot.reply_to(message, "**Số tiền tối thiểu là 10.000 VND. Vui lòng nhập lại.**", parse_mode="Markdown")
                return

            order_id = generate_order_id()
            orders = get_orders()
            orders[order_id] = {
                "order_id": order_id,
                "user_id": user_id,
                "amount": amount,
                "status": "created",
                "created_at": get_vietnam_time().strftime("%Y-%m-%d %H:%M:%S"),
                "receipt_file_id": None,
                "approved_at": None
            }
            save_orders(orders)

            qr_bytes = create_qr_image(amount, order_id)
            if qr_bytes is None:
                bot.reply_to(message, "**Lỗi tạo mã QR. Vui lòng thử lại sau.**", parse_mode="Markdown")
                orders.pop(order_id, None)
                save_orders(orders)
                return

            caption = f"""- Vui Lòng Quét QR Để Được Xử Lý Giao Dịch Nhanh Nhất ‼️
- Sau Khi Đã Chuyển Khoản , Vui Lòng Đợi 1-5 Phút Để Hệ Thống Kiểm Tra Đơn Nạp
========================
Mã đơn: #{order_id}
Số tiền: {amount} VND
Nội dung chuyển khoản: {order_id}"""
            markup = types.InlineKeyboardMarkup()
            btn_da_chuyen = types.InlineKeyboardButton("Tôi Đã Chuyển Khoản", callback_data=f"toi_da_chuyen_{order_id}")
            markup.add(btn_da_chuyen)

            bot.send_photo(message.chat.id, qr_bytes, caption=caption, reply_markup=markup)

            user_states[user_id] = {"state": None, "order_id": order_id, "attempts": 0}
            return

        elif state_info["state"] == "waiting_for_receipt":
            state_info["attempts"] += 1
            if state_info["attempts"] >= 3:
                order_id = state_info["order_id"]
                orders = get_orders()
                if order_id in orders:
                    orders[order_id]["status"] = "cancelled"
                    save_orders(orders)
                user_states.pop(user_id, None)
                bot.reply_to(message, "**Đơn nạp đã bị huỷ vì gửi sai quá 3 lần. Vui lòng liên hệ admin @HuyDaiXuVN**", parse_mode="Markdown")
            else:
                bot.reply_to(message, "**Vui Lòng gửi lại ảnh biên lai (ảnh chụp màn hình chuyển khoản)**", parse_mode="Markdown")
            return

    bot.reply_to(message, "Bạn hãy dùng /start để bắt đầu.")

# ===== XỬ LÝ ẢNH (BIÊN LAI) =====
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id

    if user_id in user_states and user_states[user_id]["state"] == "waiting_for_receipt":
        state_info = user_states[user_id]
        order_id = state_info["order_id"]
        orders = get_orders()
        if order_id not in orders or orders[order_id]["user_id"] != user_id:
            user_states.pop(user_id, None)
            bot.reply_to(message, "**Không tìm thấy đơn nạp đang chờ. Vui lòng tạo đơn mới.**", parse_mode="Markdown")
            return

        if orders[order_id]["status"] != "awaiting_receipt":
            bot.reply_to(message, "**Đơn nạp đã được xử lý hoặc bị hủy.**", parse_mode="Markdown")
            user_states.pop(user_id, None)
            return

        file_id = message.photo[-1].file_id

        orders[order_id]["receipt_file_id"] = file_id
        orders[order_id]["status"] = "pending_approval"
        save_orders(orders)

        bot.reply_to(message, "**Đã nhận biên lai. Đơn nạp đang chờ admin duyệt.**", parse_mode="Markdown")

        try:
            user_info = bot.get_chat(user_id)
            fullname = user_info.full_name
            username = user_info.username or "Không có"

            admin_caption = f"""📥 ĐƠN NẠP MỚI CẦN DUYỆT
========================
Mã đơn: #{order_id}
Người nạp: {fullname} (ID: {user_id})
Username: @{username}
Số tiền: {orders[order_id]['amount']} VND
Thời gian: {orders[order_id]['created_at']}
Trạng thái: Chờ duyệt
========================
Duyệt bằng lệnh: /duyet {order_id}"""

            for admin_id in ADMIN_IDS:
                bot.send_photo(admin_id, file_id, caption=admin_caption)
        except Exception as e:
            print(f"Lỗi gửi thông báo cho admin: {e}")

        user_states.pop(user_id, None)
    else:
        bot.reply_to(message, "**Bạn không có đơn nạp nào đang chờ biên lai.**", parse_mode="Markdown")

# ===== XỬ LÝ LỆNH /duyet (ADMIN) =====
def handle_admin_duyet(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "**Bạn không có quyền sử dụng lệnh này.**", parse_mode="Markdown")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "**Cú pháp: /duyet <mã đơn>**", parse_mode="Markdown")
        return

    order_id_input = parts[1].strip()
    if order_id_input.startswith("#"):
        order_id_input = order_id_input[1:]

    orders = get_orders()
    if order_id_input not in orders:
        bot.reply_to(message, f"**Không tìm thấy đơn nạp với mã: {order_id_input}**", parse_mode="Markdown")
        return

    order = orders[order_id_input]
    if order["status"] != "pending_approval":
        bot.reply_to(message, f"**Đơn nạp {order_id_input} không ở trạng thái chờ duyệt (hiện tại: {order['status']})**", parse_mode="Markdown")
        return

    target_user_id = order["user_id"]
    amount = order["amount"]

    users, user_data = get_user_data(target_user_id)
    user_data["balance"] = user_data.get("balance", 0) + amount
    save_json(USERS_FILE, users)

    order["status"] = "approved"
    order["approved_at"] = get_vietnam_time().strftime("%Y-%m-%d %H:%M:%S")
    save_orders(orders)

    try:
        bot.send_message(
            target_user_id,
            f"✅ Đơn nạp #{order_id_input} đã được duyệt.\n"
            f"Số tiền cộng: +{amount} VND\n"
            f"Số dư hiện tại: {user_data['balance']} VND"
        )
    except Exception as e:
        print(f"Không thể gửi thông báo cho user {target_user_id}: {e}")

    bot.reply_to(message, f"**Đã duyệt đơn {order_id_input}. Đã cộng {amount} VND cho user {target_user_id}.**", parse_mode="Markdown")

# ===== CHẠY BOT =====
if __name__ == "__main__":
    print("Bot đang chạy...")
    print("Commands:")
    print("  /exportdata - Export all data")
    print("  /importdata - Import data from JSON file (reply to file)")
    print("  /viewdata   - View statistics")
    
    # Khởi tạo file rỗng nếu chưa có
    if not os.path.exists(USERS_FILE):
        save_json(USERS_FILE, {})
    if not os.path.exists(ORDERS_FILE):
        save_json(ORDERS_FILE, {})
    
    bot.infinity_polling(skip_pending=True)
