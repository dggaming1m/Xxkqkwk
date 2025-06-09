from telegram import Update, ChatMemberUpdated
from telegram.ext import Application, CommandHandler, ContextTypes, filters
import requests
from datetime import datetime, timedelta, time
from flask import Flask, jsonify
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Your bot token
BOT_TOKEN = '8196438767:AAHYtJWs6lKOsPHtdWFvSF00HX9EMBVNjt0'

#Group Free Request
group_free_requests = {}  # {chat_id: free_requests}

# Admin IDs who are allowed to use admin commands
ADMIN_IDS = [5670174770]
admin_expiry = {}

# Default values for user requests
user_data = {}
group_admins = {}  # {chat_id: {user_id: expiry_date}}
# Biến toàn cục để lưu thông tin promotion theo nhóm
group_promotions = {}
# Biến toàn cục lưu username tùy chỉnh theo từng nhóm
group_custom_usernames = {}  # Dạng {chat_id: "@custom_username"}
# Biến lưu thông tin số lượt/ngày và thời hạn sử dụng bot của các nhóm
allowed_groups_info = {}

# List of groups allowed to use the bot
allowed_groups = set([-1002535466570,-1002483810359,-1002600201998])  # Automatically allow this group
# Flask App
app = Flask(__name__)

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "Bot is running", "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
# Function to reset daily requests for all users
def reset_daily_requests():
    now = datetime.now()
    for user_id, data in user_data.items():
        if not data['vip']:
            data['daily_requests'] = 1
        elif data['expiry_date'] < now:
            data['vip'] = False
            data['daily_requests'] = 1

# Function to allow a group to use the bo
# Function to allow a group to use the bot
async def allow_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Kiểm tra quyền admin (admin chính thức hoặc admin tạm thời)
    if user_id not in ADMIN_IDS and (chat_id not in group_admins or user_id not in group_admins[chat_id]):
        await update.message.reply_text("You do not have permission to use this command.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /allow <daily_limit> <days>")
        return

    try:
        daily_limit = int(context.args[0])
        days = int(context.args[1])
        allowed_groups.add(chat_id)
        expiry_date = datetime.now() + timedelta(days=days)
        allowed_groups_info[chat_id] = {
            "daily_limit": daily_limit,
            "expiry_date": expiry_date,
            "remaining_today": daily_limit,
        }

        await update.message.reply_text(
            f"✅ This group is now allowed to use the bot.\n"
            f"💫Daily Limit: {daily_limit} requests/day\n"
            f"⚡Valid for: {days} days (Expires on {expiry_date.strftime('%Y-%m-%d')})\n"
            f"❤️‍🩹OWNER - ☠️ @dg_gaming_1m ✔️"
        )
    except ValueError:
        await update.message.reply_text("Please provide valid numbers for daily limit and days.")
# Command to check user's remaining daily requests and VIP status
async def set_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Kiểm tra quyền admin
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You do not have permission to use this command.")
        return

    # Kiểm tra tham số đầu vào
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /set <@username>")
        return

    custom_username = context.args[0].strip()
    if not custom_username.startswith("@"):
        await update.message.reply_text("Please provide a valid username starting with '@'.")
        return

    # Cập nhật username tùy chỉnh cho nhóm
    group_custom_usernames[chat_id] = custom_username
    await update.message.reply_text(f"Custom username has been set to {custom_username} for this group.")
async def check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_info = user_data.get(user_id, None)

    if not user_info:
        # Initialize user as free user
        user_data[user_id] = {'likes': 0, 'daily_requests': 1, 'expiry_date': None, 'vip': False}
        user_info = user_data[user_id]

    # Free request status
    free_request_status = f"✅ {user_info['daily_requests']}/1" if user_info['daily_requests'] > 0 else "❌ 0/1"
    
    # VIP status and daily limits
    vip_status = "✅ Yes" if user_info['vip'] else "❌ NO"
    remaining_requests = f"✅ {user_info['likes']}/99" if user_info['vip'] else "❌ 0/0"

    # Reset time for daily requests (Sri Lanka Time)
    reset_time = "1:30 AM Sri Lankan Time"

    message = (
        f"📊 Daily Free Request: {free_request_status}\n"
        f"🔹 Likes Access: {vip_status}\n"
        f"🕒 Next Reset Time: {reset_time}\n\n"
        f"🔸 Admin Allowed Amount: {remaining_requests}\n"
        f"📅 Access Expires At: {user_info['expiry_date'].strftime('%d/%m/%Y') if user_info['vip'] else 'N/A'}"
    )

    await update.message.reply_text(message)

# Command to set promotion text for a group
async def set_promotion_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS and (chat_id not in group_admins or user_id not in group_admins[chat_id]):
        await update.message.reply_text("You do not have permission to use this command.")
        return

    chat_id = update.effective_chat.id

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /setpromotion <text>")
        return

    promotion_text = update.message.text.split(" ", 1)[1]

    # Tạo một cấu trúc để lưu nội dung văn bản và nút URL
    if "[SUBSCRIBE]" in promotion_text:
        button_url = promotion_text.split("buttonurl:")[-1].strip()
        group_promotions[chat_id] = {
            "https://t.me/dg_gaming_1m0": promotion_text.split("[𝗝𝗼𝗶𝗻 𝗖𝗵𝗮𝗻𝗻𝗲𝗹]")[0].strip(),
            "button_url": button_url
        }
    else:
        group_promotions[chat_id] = {"text": promotion_text, "button_url": None}

    await update.message.reply_text(f"Promotion text has been set:\n{promotion_text}")
# Hàm /add để cấp quyền VIP cho người dùng
async def add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Kiểm tra nếu người dùng là admin toàn cục hoặc admin nhóm
    if user_id not in ADMIN_IDS and user_id not in group_admins.get(chat_id, {}):
        custom_username = group_custom_usernames.get(chat_id, "@dg_gaming_1m")
        await update.message.reply_text(f"You do not have permission to use this command.\n BUY ACCESS FROM ☠️ {custom_username} ✔️")
        return

    # Kiểm tra nếu quyền admin nhóm đã hết hạn
    if user_id in group_admins.get(chat_id, {}):
        if group_admins[chat_id][user_id] < datetime.now():
            del group_admins[chat_id][user_id]
            await update.message.reply_text("Your admin privileges in this group have expired.")
            return

    try:
        # Lấy thông tin từ tham số đầu vào
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
        days = int(context.args[2])

        # Nếu người dùng chưa tồn tại trong dữ liệu, khởi tạo
        if target_user_id not in user_data:
            user_data[target_user_id] = {'likes': 0, 'daily_requests': 1, 'expiry_date': None, 'vip': False}

        # Cập nhật trạng thái VIP cho người dùng
        user_data[target_user_id]['vip'] = True
        user_data[target_user_id]['likes'] = amount
        user_data[target_user_id]['expiry_date'] = datetime.now() + timedelta(days=days)

        # Gửi thông báo thành công
        await update.message.reply_text(
            f"✅ User ID {target_user_id} has been given {amount} requests per day for {days} days. VIP access granted."
        )
    except (IndexError, ValueError):
        # Thông báo lỗi nếu nhập sai tham số
        await update.message.reply_text("Usage: /add <user_id> <amount> <days>")
#reset
async def reset_handler(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now()
    # Reset số lượt của nhóm
    for chat_id, info in allowed_groups_info.items():
        if info["expiry_date"] > now:
            info["remaining_today"] = info["daily_limit"]
    # Reset số lượt của người dùng
    for user_id, data in user_data.items():
        if not data['vip']:
            data['daily_requests'] = 1
        elif data['expiry_date'] < now:
            data['vip'] = False
            data['daily_requests'] = 1
 #/out
async def out_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ADMIN_IDS:  # Phải có thụt lề ở đây
        await update.message.reply_text("You do not have permission to use this command.")
        return

    try:
        user_id = int(context.args[0])
        if user_id in user_data:
            user_data[user_id]['vip'] = False
            user_data[user_id]['likes'] = 0
            user_data[user_id]['expiry_date'] = None
            await update.message.reply_text(f"✅ User ID {user_id} has been removed from VIP💔")
        else:
            await update.message.reply_text(f"User ID {user_id} is not in the VIP list.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /out <user_id>")
# Command to remove an admin from the admin list
async def kick_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Kiểm tra quyền admin (admin chính thức hoặc admin tạm thời)
    if user_id not in ADMIN_IDS and (chat_id not in group_admins or user_id not in group_admins[chat_id]):
        await update.message.reply_text("You do not have permission to use this command.")
        return

    try:
        target_user_id = int(context.args[0])
        if target_user_id in ADMIN_IDS:
            ADMIN_IDS.remove(target_user_id)
            await update.message.reply_text(f"✅ User ID {target_user_id} has been removed from the admin list💔")
        else:
            await update.message.reply_text(f"User ID {target_user_id} is not an admin.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /kick <user_id>")
# Command to remove a group from the allowed list
async def remove_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Kiểm tra quyền admin (admin chính thức hoặc admin tạm thời)
    if user_id not in ADMIN_IDS and (chat_id not in group_admins or user_id not in group_admins[chat_id]):
        # Lấy username tùy chỉnh cho nhóm, mặc định là "@Nishantsarkar10k"
        custom_username = group_custom_usernames.get(chat_id, "@dg_gaming_1m")
        await update.message.reply_text(f"You do not have permission to use this command.\n BUY ACCESS FROM {custom_username} 🖤")
        return

    # Kiểm tra nếu nhóm có trong danh sách được phép
    if chat_id in allowed_groups:
        # Xóa nhóm khỏi danh sách và thông tin nhóm
        allowed_groups.remove(chat_id)
        allowed_groups_info.pop(chat_id, None)
        await update.message.reply_text(f"✅ Group {chat_id} has been removed from the allowed list 💔.")
    else:
        # Thông báo nếu nhóm không nằm trong danh sách
        await update.message.reply_text("This group is not in the allowed list.")
# Hàm để thêm admin với quyền giới hạn trong nhóm cụ thể
async def addadmin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You do not have permission to use this command.")
        return

    try:
        chat_id = update.effective_chat.id
        user_id = int(context.args[0])
        days = int(context.args[1])
        expiry_date = datetime.now() + timedelta(days=days)

        # Cấp quyền admin giới hạn cho nhóm cụ thể
        if chat_id not in group_admins:
            group_admins[chat_id] = {}
        group_admins[chat_id][user_id] = expiry_date

        await update.message.reply_text(f"✅ User {user_id} is now an admin in this group for {days} days.")
    except:
        await update.message.reply_text("Usage: /addadmin <user_id> <days>")
        
  # Command to handle the like request
# Update the like_handler to include promotion
async def like_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if chat_id not in allowed_groups:
        custom_username = group_custom_usernames.get(chat_id, "@dg_gaming_1m")
        await update.message.reply_text(
            f"This group is not allowed to use the bot.\nBUY ACCESS FROM {custom_username} 🩵"
        )
        return

    group_info = allowed_groups_info.get(chat_id, None)
    if group_info and group_info["remaining_today"] <= 0:
        custom_username = group_custom_usernames.get(chat_id, "@dg_gaming_1m")
        await update.message.reply_text(
            f"The Daily Request Limit is Over. Please wait for the reset or contact {custom_username} to upgrade your package!"
        )
        return

    user_info = user_data.get(user_id, {'likes': 0, 'daily_requests': 1, 'vip': False, 'last_request_date': None})
    now = datetime.now()

    if not user_info['vip']:
        if user_info['daily_requests'] <= 0:
            custom_username = group_custom_usernames.get(chat_id, "@dg_gaming_1m")
            if user_info.get('last_request_date') and now - user_info['last_request_date'] < timedelta(days=1):
                await update.message.reply_text(
                    f"❌ You have reached your daily request limit. 😎 Please wait for reset or contact {custom_username} to upgrade your package!"
                )
                return
            else:
                user_info['daily_requests'] = 1
        user_info['daily_requests'] -= 1

    user_info['last_request_date'] = now
    user_data[user_id] = user_info

    if len(context.args) != 2:
        await update.message.reply_text(
            "Please provide a valid region and UID. Example: /like ind 10000001"
        )
        return

    region = context.args[0]
    uid = context.args[1]
    api_url = f"https://al-like-save-trt.vercel.app/like?server_name=ind&uid={uid}"  # replace this with your actual API
    response = requests.get(api_url)

    if response.status_code == 200:
        response_data = response.json()

        uid = response_data.get("UID", uid)
        player_name = response_data.get("PlayerNickname", "Unknown")
        
        likes_before_command = response_data.get("LikesbeforeCommand", 0)
        
        likes_after_command = response_data.get("LikesafterCommand", 0)
        
        likes_given = response_data.get("LikesGivenByAPI", 0)
        
        status = response_data.get("status", 0)
        

        # Important check
        if status == 2 and likes_given == 0:
            await update.message.reply_text(
                f"💔 UID {uid} ({player_name}) has already received max likes for today 😢. Try again tomorrow!"
            )
            return

        # Decrease VIP user likes if needed
        if user_info['vip']:
            user_info['likes'] -= 1

        # Decrease group daily limit
        if chat_id in allowed_groups_info:
            allowed_groups_info[chat_id]["remaining_today"] -= 1

        # Promotion
        promotion = group_promotions.get(chat_id, {})
        promotion_text = promotion.get("https://t.me/dg_gaming_1m0", "")
        button_url = promotion.get("button_url", None)

        reply_markup = None
        if button_url:
            keyboard = [[InlineKeyboardButton("𝗝𝗼𝗶𝗻 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", url=button_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

        result_message = (
            f"🔹 Player Name: {player_name}\n"
            
            f"🔸 Player UID: {uid}\n"
            
            f"🔸 Likes at start of Day: {likes_before_command}\n"
            
            f"🔸 Likes Before Command: {likes_before_command}\n"
            
            f"🔸 Likes After Command: {likes_after_command}\n"
            
            f"🔸 Likes Given by Bot: {likes_given}\n"
            
            f"𝗣𝘂𝗿𝗰𝗵𝗮𝘀𝗲 𝘃𝗶𝗽 𝗗𝗺 @dg_gaming_1m ."
            
            f"{promotion_text}"
        )

        await update.message.reply_text(result_message, reply_markup=reply_markup)

    else:
        await update.message.reply_text(
            f"❌ An error occurred (HTTP {response.status_code}). Please check account region or try again later! Note: This Is Only For India."
        )
 # Command to check remaining requests and days for a group
async def reset_admin_expiry(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now()
    for chat_id, admins in list(group_admins.items()):
        for user_id, expiry_date in list(admins.items()):
            if expiry_date < now:
                del group_admins[chat_id][user_id]
                
async def remain_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    # Kiểm tra nếu nhóm có trong danh sách được phép
    if chat_id not in allowed_groups_info:
        # Lấy username tùy chỉnh cho nhóm, mặc định là "@Nishantsarkar10k"
        custom_username = group_custom_usernames.get(chat_id, "@dg_gaming_1m")
        await update.message.reply_text(
            f"This group is not allowed to use the bot.\n"
            f"USE VIP GROUP https://t.me/freefirelikesbot655.\n"
            f"BUY ACCESS FROM 🖤 {custom_username} ✔️"
        )
        return

    group_info = allowed_groups_info[chat_id]
    now = datetime.now()

    # Tính số ngày còn lại
    remaining_days = (group_info["expiry_date"] - now).days
    if remaining_days < 0:
        # Lấy username tùy chỉnh cho nhóm, mặc định là "@Nishantsarkar10k"
        custom_username = group_custom_usernames.get(chat_id, "@dg_gaming_1m")
        await update.message.reply_text(
            f"The Daily Request Amount has been Over💔.\n"
            f"Please Wait till Cycle Reset or Contact ☠️ {custom_username} ✔️ to Upgrade Your Package!"
        )
        return

    # Lấy thông tin số lượt còn lại
    remaining_requests = group_info.get("remaining_today", 0)
    daily_limit = group_info.get("daily_limit", 0)

    # Gửi thông báo chi tiết về lượt và thời hạn còn lại
    message = (
        f"Remaining requests: {remaining_requests}/{daily_limit}\n"
        f"Remaining days: {remaining_days}"
    )
    await update.message.reply_text(message)
    # Lệnh /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_name = user.first_name
    current_time = datetime.now().strftime("%I:%M:%S %p")
    current_date = datetime.now().strftime("%Y-%m-%d")

    welcome_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ Welcome, {user_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 User Details:
╭───────────────╮
├ 🆔 User ID: {user_id}
├ ⏰ Time: {current_time}
├ 📅 Date: {current_date}
╰───────────────╯

📖 Commands:
╭───────────────╮
├ 📜 /help: View all available commands
├ 🔄 /start: Restart the bot
├ 🚙 /info <vehicle number>: Get Vehicle Info
╰───────────────╯

🇬🇧 English: First, you have to join our support group. Then you can use the bot.

🇮🇳 हिंदी: सबसे पहले आपको हमारे सहायता समूह से जुड़ना होगा। उसके बाद आप इस बॉट का उपयोग कर सकते हैं.

🔗 Join Us: 
Click here to join our channel/group!

━━━━━━━━━━━━━━━━━━━━━━━━━━
😊 Enjoy your experience with the bot!
━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    keyboard = [
        [InlineKeyboardButton("🩵 SUBSCRIBE ON YT", url="https://youtube.com/@d
