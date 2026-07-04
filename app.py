# app.py - Simplified Telegram Canteen Bot Application
import os
import db_manager
import telebot
from telebot.types import Message
from dotenv import load_dotenv
from pathlib import Path
import qrcode
import uuid
import json
from datetime import datetime
import traceback
import logging

# --- PROJECT CONFIGURATION & .ENV LOADING ---
BASE_DIR = Path(__file__).resolve().parent
DOTENV_PATH = BASE_DIR / '.env'

# Load environment variables
load_dotenv(dotenv_path=DOTENV_PATH)

# --- TELEGRAM SETUP ---
TOKEN = os.getenv('BOT_TOKEN')

if not TOKEN:
    print("❌ ERROR: Missing required environment variable (BOT_TOKEN).")
    exit(1)

print(f"✅ Telegram Bot Token loaded successfully.")
try:
    logger = telebot.logger
    telebot.logger.setLevel(logging.INFO)
    bot = telebot.TeleBot(TOKEN)
except Exception as e:
    raise RuntimeError(f"❌ Error initializing TeleBot: {e}")

# --- CONFIGURATION ---
# Use a simple list of admin chat IDs for basic command access
ADMIN_CHAT_IDS = [int(num.strip()) for num in os.getenv('ADMIN_CHAT_IDS', '').split(',') if num.strip().isdigit()]


# --- QR CODE GENERATION (Only for Pickup) ---

def generate_pickup_qr_code(order_id, student_phone, items_summary):
    """Generate pickup QR code for order verification."""
    try:
        # Simple verification code (Order ID + current minute)
        verification_code = f"{order_id}{datetime.now().strftime('%M')}"

        pickup_data = {
            'order_id': order_id,
            'phone': student_phone,
            'items': items_summary,
            'verification_code': verification_code,
        }

        pickup_json = json.dumps(pickup_data, separators=(',', ':'))
        filename = f"pickup_{order_id}_{uuid.uuid4().hex[:8]}.png"

        static_dir = BASE_DIR / 'static'
        # Ensure directory exists
        static_dir.mkdir(exist_ok=True, parents=True)
        filepath = static_dir / filename

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(pickup_json)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="darkgreen", back_color="white")
        qr_img.save(filepath)

        print(f"🎫 Pickup QR code generated: {filename}")
        return str(filepath), verification_code

    except Exception as e:
        print(f"❌ Error generating pickup QR code: {e}")
        return None, None


# --- HELPER UTILITIES ---

def send_student_message(text, chat_id, media_path=None, parse_mode='Markdown'):
    """Send message to student with optional media."""
    if not bot: return

    if media_path and Path(media_path).exists():
        try:
            with open(media_path, 'rb') as photo:
                bot.send_photo(chat_id, photo, caption=text, parse_mode=parse_mode)
            print(f"📸 Photo sent: {Path(media_path).name}")
        except Exception as e:
            print(f"❌ Error sending photo via Telegram API: {e}")
            bot.send_message(chat_id, text, parse_mode=parse_mode) # Fallback to text
    else:
        bot.send_message(chat_id, text, parse_mode=parse_mode)


def send_admin_notification(order_details, verification_code):
    """Send basic notification message to all admin chat IDs."""
    if not bot: return

    try:
        items_list = db_manager.parse_order_items(order_details['items'])
        food_summary = "\n".join([
            f"• {item['name'].title()} x {item['qty']}"
            for item in items_list
        ])

        notification_msg = (
            f"🚨 *NEW ORDER PLACED & CONFIRMED!* 🚨\n\n"
            f"🆔 *Order ID:* #{order_details['id']}\n"
            f"🔢 *Verification Code:* `{verification_code}`\n"
            f"📞 *Student Chat ID:* `{order_details['student_phone']}`\n\n"
            f"🍽️ *Ordered Items:*\n{food_summary}\n\n"
            f"🟢 *STATUS: Ready for Preparation*\n"
        )

        for admin_id in ADMIN_CHAT_IDS:
            try:
                bot.send_message(admin_id, notification_msg, parse_mode='Markdown')
            except Exception as e:
                print(f"❌ Error sending notification to admin {admin_id}: {e}")

    except Exception as e:
        print(f"❌ Error in admin notification: {e}")


# --- TELEGRAM BOT HANDLERS ---

if bot:
    @bot.message_handler(func=lambda message: True)
    def handle_incoming_message(message: Message):
        """Process all incoming Telegram messages."""
        try:
            incoming_msg = message.text.strip().lower() if message.text else ''
            from_chat_id = message.chat.id
            student_db_id = str(from_chat_id)

            print(f"📨 Message from {from_chat_id}: '{incoming_msg}'")

            if from_chat_id in ADMIN_CHAT_IDS:
                handle_admin_commands(incoming_msg, from_chat_id)
            else:
                handle_student_flow(incoming_msg, student_db_id, from_chat_id)

        except Exception as e:
            print(f"❌ Error handling incoming message: {e}")
            traceback.print_exc()
            bot.send_message(message.chat.id,
                             "❌ Sorry, there was an error processing your request. Please try again or reply 'menu'.")


def handle_admin_commands(msg, chat_id):
    """Handle basic admin menu commands."""
    if not bot: return

    try:
        parts = msg.lower().split()
        command = parts[0] if parts else ''

        def send_admin_message(text, parse_mode='Markdown'):
            bot.send_message(chat_id, text, parse_mode=parse_mode)

        if command == 'add' and len(parts) >= 3:
            # Add menu item: "add item name price"
            item_name = ' '.join(parts[1:-1])
            try:
                price = float(parts[-1])
                result = db_manager.add_menu_item(item_name, price)
                send_admin_message(result)
            except ValueError:
                send_admin_message("❌ Invalid price format. Please use a number.")

        elif command == 'delete' and len(parts) == 2:
            # Delete menu item: "delete id"
            try:
                item_id = int(parts[1])
                result = db_manager.delete_menu_item(item_id)
                send_admin_message(result)
            except ValueError:
                send_admin_message("❌ Invalid format. Use: `delete <id>`")

        elif command == 'admin' and len(parts) >= 2 and parts[1] == 'menu':
            # Show current menu
            menu = db_manager.get_menu()
            if menu:
                menu_text = "📋 *Current Menu Items:*\n\n"
                for item in menu:
                    menu_text += f"**ID {item['id']}:** {item['name'].title()} - ₹{item['price']:.2f}\n"
                send_admin_message(menu_text)
            else:
                send_admin_message("📋 The menu is currently empty.")

        else:
            send_admin_message(
                "❌ Unknown command. Use:\n"
                "• `admin menu`\n"
                "• `add <item name> <price>` (e.g., `add Bread Butter 30`)\n"
                "• `delete <id>` (e.g., `delete 5`)"
            )

    except Exception as e:
        print(f"❌ Error handling admin command: {e}")
        bot.send_message(chat_id, "❌ Error processing admin command.")


def handle_student_flow(msg, student_id, chat_id):
    """Handle the student ordering flow."""
    if not bot: return

    try:
        user_state = db_manager.get_session_state(student_id)

        # Helper function redefined locally
        def send_student_message_local(text, media_path=None, parse_mode='Markdown'):
            send_student_message(text, chat_id, media_path, parse_mode)

        # === INITIAL STATE - Show Menu ===
        if msg in ['menu', 'hi', 'hello', 'start', 'restart', '/start']:
            db_manager.set_session_state(student_id, 'initial')
            menu = db_manager.get_menu()

            if menu:
                menu_text = (
                    f"🍽️ *Welcome to Digital Canteen!*\n\n"
                    f"📋 *Today's Menu:*\n\n"
                )

                for item in menu:
                    menu_text += f"**ID {item['id']}:** {item['name'].title()} - ₹{item['price']:.2f}\n"

                menu_text += (
                    f"\n💡 *How to order:*\n"
                    f"Reply with: `<item_id> <quantity>`\n\n"
                    f"**Example:** `1 2` (orders 2 of item ID 1)"
                )

                send_student_message_local(menu_text)
                db_manager.set_session_state(student_id, 'selecting_items')
                return
            else:
                send_student_message_local(
                    "😔 Sorry, the menu is currently empty."
                )
                return

        # === SELECTING ITEMS STATE ===
        elif user_state == 'selecting_items':
            parts = msg.split()
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                item_id = int(parts[0])
                quantity = int(parts[1])

                if quantity <= 0 or quantity > 50:
                    send_student_message_local("⚠️ Quantity must be between 1 and 50. Please try again.")
                    return

                item = db_manager.get_menu_item(item_id)
                if item:
                    total_amount = item['price'] * quantity
                    order_details = [{'id': item['id'], 'name': item['name'], 'price': item['price'], 'qty': quantity}]

                    order_id = db_manager.create_order(student_id, order_details, total_amount, 'pending')
                    if order_id:
                        db_manager.set_session_state(student_id, 'confirming_order', order_id)

                        confirmation_msg = (
                            f"📝 *Order Summary:*\n\n"
                            f"🍽️ **Item:** {item['name'].title()}\n"
                            f"📦 **Quantity:** {quantity}\n"
                            f"💰 **Total Amount:** ₹{total_amount:.2f}\n\n"
                            f"✅ Reply `confirm` to place your order\n"
                            f"❌ Reply `cancel` to start over"
                        )
                        send_student_message_local(confirmation_msg)
                        return
                    else:
                        send_student_message_local("❌ Error creating order. Please try again.")
                        return
                else:
                    send_student_message_local("❌ Invalid item ID. Please check the menu and try again.")
                    return
            else:
                send_student_message_local(
                    "❌ Invalid format! **Correct format:** `<item_id> <quantity>`\n"
                    "Reply `menu` to see available items."
                )
                return

        # === CONFIRMING ORDER STATE (Simplified: Confirmation is immediate) ===
        elif user_state == 'confirming_order':
            current_order_id_obj = db_manager.get_session_order_id(student_id)
            if current_order_id_obj is None:
                send_student_message_local("❌ No active order found. Reply `menu` to start a new order.")
                return
            current_order_id = int(current_order_id_obj)

            if msg == 'confirm':
                order = db_manager.get_order_details(current_order_id)
                if order:
                    # 1. Update status and generate pickup code/QR
                    db_manager.update_order_status(current_order_id, 'confirmed')

                    items_data = db_manager.parse_order_items(order['items'])
                    items_summary = [{'name': item['name'], 'qty': item['qty']} for item in items_data]

                    pickup_qr_path, verification_code = generate_pickup_qr_code(
                        current_order_id, student_id, items_summary
                    )
                    db_manager.update_order_pickup_code(current_order_id, verification_code)
                    db_manager.set_session_state(student_id, 'pickup_ready', current_order_id)
                    
                    # 2. Notify Admin
                    send_admin_notification(order, verification_code)

                    # 3. Notify Student
                    pickup_msg = (
                        f"🎉 **Order Placed Successfully!** (Order ID: #{current_order_id})\n\n"
                        f"🔢 **Verification Code:** `{verification_code}`\n"
                        f"💰 **Amount to Pay at Counter:** ₹{order['total_amount']:.2f}\n\n"
                        f"📱 **For Pickup:** Show the QR code below at the canteen counter."
                    )

                    send_student_message_local(pickup_msg, media_path=pickup_qr_path)
                    print(f"✅ Order {current_order_id} confirmed and pickup info sent.")
                    return
                else:
                    send_student_message_local("❌ Order details not found. Reply `menu` to start a new order.")
                    return

            elif msg == 'cancel':
                db_manager.update_order_status(current_order_id, 'cancelled')
                db_manager.set_session_state(student_id, 'initial')
                send_student_message_local("❌ Order cancelled. Reply `menu` to start a new order.")
                return
            else:
                send_student_message_local(
                    "Please choose one of the following:\n"
                    "✅ Reply `confirm` to place your order\n"
                    "❌ Reply `cancel` to cancel this order"
                )
                return

        # === PICKUP READY STATE (User can check status or start a new order) ===
        elif user_state == 'pickup_ready':
            if msg in ['status', 'order status']:
                current_order_id_obj = db_manager.get_session_order_id(student_id)
                current_order_id = int(current_order_id_obj) if current_order_id_obj else None
                order_details = db_manager.get_order_details(current_order_id)

                if order_details and order_details['status'] in ['confirmed', 'picked_up']:
                    status_msg = (
                        f"📊 **Order Status**\n"
                        f"🆔 **Order ID:** #{current_order_id}\n"
                        f"📋 **Status:** {order_details['status'].title()}\n"
                        f"🔢 **Pickup Code:** `{order_details.get('pickup_code', 'N/A')}`\n\n"
                        f"📍 **Visit the canteen counter for pickup!**"
                    )
                    send_student_message_local(status_msg)
                else:
                    send_student_message_local("❌ Your last order is no longer active. Reply `menu` to place a new order.")
                    db_manager.set_session_state(student_id, 'initial')
                return
            else:
                send_student_message_local(
                    "🎉 **Your order is confirmed and awaiting pickup!**\n"
                    "📍 Show your QR code/code at the canteen counter\n"
                    "📱 Reply `menu` for a new order\n"
                    "📊 Reply `status` to check order status"
                )
                return

        # === DEFAULT STATE ===
        else:
            send_student_message_local("💬 I didn't understand that command. Reply `menu` to see available options.")
            return

    except Exception as e:
        print(f"❌ Error handling student flow: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "❌ Sorry, there was an error. Please reply `menu` to start over.")


# --- MAIN APPLICATION STARTUP ---

if __name__ == '__main__':
    try:
        # NOTE: If you are running into Conflict: Error code 409 (as seen in the previous question), 
        # uncomment the line below to delete any existing webhook configuration before polling.
        # bot.delete_webhook() 
        
        print("🔧 Initializing Simple Telegram Canteen Bot...")
        print("=" * 50)

        # Initialize database
        print("🗃️  Setting up database...")
        if db_manager.create_tables():
            db_manager.add_default_menu_items()
            print("✅ Database setup complete.")
        else:
            print("❌ Database initialization failed!")
            exit(1)

        # Display configuration
        print("\n🔧 Bot Configuration:")
        print(f"  👨‍💼 Admin Chat IDs: {ADMIN_CHAT_IDS}")
        print(f"  💾 Database: {db_manager.DATABASE_PATH}")

        print("\n🚀 Starting Telegram Bot Polling...")
        print("  📡 Bot is now listening for messages...")
        print("  ⏹️  Press Ctrl+C to stop\n")
        print("=" * 50)

        # Start bot polling
        # Note: 'none_stop' is deprecated. Use 'non_stop=True' instead.
        bot.polling(non_stop=True, interval=3)

    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user.")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        traceback.print_exc()
