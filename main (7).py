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
from flask import Flask, request
import logging

# ===== CẤU HÌNH =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "8363711905,8030294480").split(",")]

BANK_ID = os.getenv("BANK_ID", "970422")
ACCOUNT_NO = os.getenv("ACCOUNT_NO", "101072011")
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME", "NGUYEN VAN GIA HUY")

USERS_FILE = "users.json"
ORDERS_FILE = "orders.json"
BACKUP_DIR = "backups"

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

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

user_states = {}
auto_tasks = {}

# ===== HÀM TIỆN ÍCH =====
def ensure_backup_dir():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return default
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    save_json(ORDERS_FILE, orders)

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
        response = requests.get(url)
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
            pattern_text = "T" if last_3[0] == 1 else "X"
            analysis += f" [3 liên tiếp {pattern_text}]"

    recent_5_text = " → ".join(["T" if x == 1 else "X" for x in results[-5:]])

    return prediction, confidence, recent_5_text, analysis

def send_prediction(chat_id, game_id, type_, prediction, confidence, recent_5_text, analysis, auto_mode=False):
    if prediction is None:
        text = f"🎰 **{game_id.upper()} ({type_.upper()})**\n\n❌ Không có dữ liệu lịch sử. Vui lòng chờ..."
    else:
        emoji = "🟢" if prediction == "Tài" else "🔴"
        text = f"""🎰 **{game_id.upper()} ({type_.upper()})**

{emoji} **Dự đoán: {prediction}**
📊 **Độ tin cậy: {confidence:.1f}%**
📈 5 phiên gần nhất: {recent_5_text}

{analysis}

⏰ Cập nhật: {get_vietnam_time().strftime('%H:%M:%S')}
{"🤖 Auto Mode" if auto_mode else ""}"""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Cập nhật", callback_data=f"refresh_{game_id}_{type_}"))
    
    try:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
    except:
        pass

# ===== XỬ LÝ LỆNH /start =====
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    users, user_data = get_user_data(user_id)
    
    fullname = message.from_user.first_name or "Bạn"
    username = message.from_user.username or "Không có"
    
    user_data["fullname"] = fullname
    user_data["username"] = username
    save_json(USERS_FILE, users)
    
    text = f"""👋 **Chào mừng {fullname}!**

🎮 **Công cụ dự đoán Tài/Xỉu**

📊 **Tính năng:**
✅ Dự đoán Tài/Xỉu bằng Markov Chain
✅ Hỗ trợ 10+ sàn game
✅ Auto mode theo dõi liên tục
✅ Lịch sử giao dịch

💳 **Quản lý tài khoản:**
- /balance - Xem số dư
- /deposit - Nạp tiền
- /orders - Lịch sử đơn nạp
- /export - Xuất dữ liệu
- /import - Nhập dữ liệu

📌 **Liên hệ:** @HuyDaiXuVN"""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎰 789", "🎰 B52", "🎰 BetVip")
    markup.add("🎰 HayWin", "🎰 HitClub", "🎰 LC79")
    markup.add("🎰 Luck8", "🎰 Max789", "🎰 XocDia88")
    markup.add("🎰 SumClub", "🎰 Sunwin", "🎰 Son789")
    
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=markup)

# ===== LỆNH EXPORT DỮ LIỆU =====
@bot.message_handler(commands=['export'])
def handle_export(message):
    user_id = message.from_user.id
    
    export_data = {
        "exported_at": get_vietnam_time().isoformat(),
        "users": load_json(USERS_FILE, {}),
        "orders": load_json(ORDERS_FILE, {})
    }
    
    filename = f"backup_{get_vietnam_time().strftime('%Y%m%d_%H%M%S')}.json"
    ensure_backup_dir()
    filepath = os.path.join(BACKUP_DIR, filename)
    
    save_json(filepath, export_data)
    
    try:
        with open(filepath, 'rb') as f:
            bot.send_document(
                message.chat.id,
                f,
                caption=f"📦 **Full Backup Data**\n\nThời gian: {export_data['exported_at']}\n\n✅ Toàn bộ dữ liệu user và orders"
            )
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi export: {str(e)}")

# ===== LỆNH IMPORT DỮ LIỆU =====
@bot.message_handler(commands=['import'])
def handle_import_start(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Chỉ admin mới có quyền import data")
        return
    
    user_states[user_id] = {"state": "waiting_for_import_file"}
    bot.reply_to(message, "📤 **Gửi file JSON để import dữ liệu vào hệ thống**\n\nFile phải có cấu trúc:\n```json\n{\n  \"users\": {...},\n  \"orders\": {...}\n}\n```", parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    
    if user_id in user_states and user_states[user_id].get("state") == "waiting_for_import_file":
        if not message.document.file_name.endswith('.json'):
            bot.reply_to(message, "❌ Vui lòng gửi file JSON")
            return
        
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            import_data = json.loads(downloaded_file.decode('utf-8'))
            
            if "users" not in import_data or "orders" not in import_data:
                bot.reply_to(message, "❌ File không có cấu trúc đúng. Cần có 'users' và 'orders'")
                return
            
            save_json(USERS_FILE, import_data.get("users", {}))
            save_json(ORDERS_FILE, import_data.get("orders", {}))
            
            user_states.pop(user_id, None)
            bot.reply_to(message, f"""✅ **Import thành công!**
            
📊 Dữ liệu đã được restore:
- Users: {len(import_data.get('users', {}))} tài khoản
- Orders: {len(import_data.get('orders', {}))} đơn hàng

⏰ Thời gian: {get_vietnam_time().strftime('%d/%m/%Y %H:%M:%S')}""", parse_mode="Markdown")
            
        except json.JSONDecodeError:
            bot.reply_to(message, "❌ File JSON không hợp lệ")
        except Exception as e:
            bot.reply_to(message, f"❌ Lỗi: {str(e)}")
    else:
        bot.reply_to(message, "❌ Bạn không trong chế độ import")

# ===== LỆNH /balance =====
@bot.message_handler(commands=['balance'])
def handle_balance(message):
    user_id = message.from_user.id
    users, user_data = get_user_data(user_id)
    
    balance = user_data.get("balance", 0)
    vip = "✅ VIP" if user_data.get("vip") else "❌ Normal"
    
    text = f"""💰 **THÔNG TIN TÀI KHOẢN**
========================
👤 Tên: {user_data.get('fullname', 'N/A')}
🆔 ID: {user_id}
📊 Số dư: {balance:,} VND
🎖️ Trạng thái: {vip}

📌 Lệnh:
/deposit - Nạp tiền
/orders - Xem đơn nạp"""
    
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== LỆNH /deposit =====
@bot.message_handler(commands=['deposit'])
def handle_deposit(message):
    user_id = message.from_user.id
    user_states[user_id] = {"state": "waiting_for_amount"}
    
    text = """💳 **NẠP TIỀN VÀO TÀI KHOẢN**
========================
Vui lòng nhập **số tiền** (VND):
- Tối thiểu: 10.000 VND
- Tối đa: không giới hạn

Ví dụ: `50000`"""
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("toi_da_chuyen_"))
def handle_payment_confirm(call):
    user_id = call.from_user.id
    order_id = call.data.replace("toi_da_chuyen_", "")
    
    orders = get_orders()
    if order_id not in orders:
        bot.answer_callback_query(call.id, "❌ Đơn không tồn tại", show_alert=True)
        return
    
    order = orders[order_id]
    if order["user_id"] != user_id:
        bot.answer_callback_query(call.id, "❌ Đơn này không phải của bạn", show_alert=True)
        return
    
    if order["status"] == "approved":
        bot.answer_callback_query(call.id, "✅ Đơn đã được duyệt rồi", show_alert=True)
        return
    
    if order["status"] not in ["awaiting_receipt", "created"]:
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

# ===== WEBHOOK SETUP =====
@app.route("/")
def webhook_home():
    return "Bot is running!"

@app.route("/webhook", methods=['POST'])
def webhook():
    try:
        json_data = request.get_json()
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return "Error", 500

@app.route("/set_webhook", methods=['GET'])
def set_webhook():
    webhook_url = os.getenv("WEBHOOK_URL", "")
    if webhook_url:
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        return f"Webhook set to {webhook_url}"
    return "WEBHOOK_URL not set"

# ===== CHẠY APP =====
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Lỗi: BOT_TOKEN không được cấu hình!")
        exit(1)
    
    ensure_backup_dir()
    port = int(os.getenv("PORT", 5000))
    
    # Kiểm tra environment
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        # Chế độ webhook (Render)
        print(f"🚀 Chạy webhook mode với URL: {webhook_url}")
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        # Chế độ local
        print("🚀 Chạy local mode (polling)...")
        bot.infinity_polling()
