import os
import re
import time
import json
import asyncio
import httpx
import urllib.parse
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ====== الإعدادات ======
TOKEN = os.environ.get('BOT_TOKEN', '8802065988:AAG2yL7xkxlufanIWhitySYrn0GTFv5D-FA')
ADMINS = [6843321125]

# ====== البيانات ======
VIP_USERS = {}
BANNED_USERS = {}
ALL_USERS = set()
API_KEYS = []
stop_users = {}

DATA_FILE = "dorker_data.json"

try:
    with open(DATA_FILE, 'r') as f:
        saved_data = json.load(f)
        API_KEYS = saved_data.get("api_keys", [])
        VIP_USERS = saved_data.get("vip_users", {})
        BANNED_USERS = saved_data.get("banned_users", {})
except:
    pass

def save_data():
    data = {
        "api_keys": API_KEYS,
        "vip_users": VIP_USERS,
        "banned_users": BANNED_USERS
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ====== الإيموجات البرميوم ======
PREMIUM_EMOJI_IDS = {
    "⚡": "6037229996622225123",
    "🤖": "6039619012051082706",
    "🔥": "5206607081334906820",
    "💳": "5445353829304387411",
    "❌": "6039615816595414817",
    "⏱": "5382194935057372936",
    "🌐": "5447410659077661506",
    "👤": "6041709716231429926",
    "🛡": "5197288647275071607",
    "👑": "6041702032534936873",
    "🔗": "5933844889652432294",
    "📊": "5231200819986047254",
    "🚀": "5195033767969839232",
    "💎": "6039601162167000043",
    "✅": "6034891730526935918",
    "👥": "6046639187636003094",
    "🌟": "5956369596528204273",
    "👁": "5976794472418121581",
    "🛑": "5260293700088511294",
    "📁": "5260293700088511294",
    "💸": "5231449120635370684",
}

def premium_emoji(text):
    if not text:
        return text
    result = text
    for emoji, doc_id in PREMIUM_EMOJI_IDS.items():
        if emoji in result:
            result = result.replace(emoji, f'<tg-emoji emoji-id="{doc_id}">{emoji}</tg-emoji>')
    return result

# ====== البحث السريع ======
async def fetch_url(api_key, url):
    try:
        payload = {'zone': "google_search", 'url': url, 'format': 'raw'}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        async with httpx.AsyncClient(timeout=20, verify=False, limits=httpx.Limits(max_connections=100)) as client:
            response = await client.post('https://api.brightdata.com/request', headers=headers, json=payload)
            if response.status_code == 200:
                try:
                    data = response.json()
                    return data.get('body', data.get('html', ''))
                except:
                    return response.text
        return ""
    except:
        return ""

def extract_urls(html):
    urls = []
    seen = set()
    
    if not html:
        return urls
    
    pattern = r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s"<>()\[\]]*'
    found = re.findall(pattern, html)
    
    blocked = [
        'google', 'gstatic', 'youtube', 'facebook', 'twitter', 'linkedin',
        'instagram', 'pinterest', 'tiktok', 'reddit', 'wikipedia', 'amazon',
        'ebay', 'apple', 'microsoft', 'bing', 'msn', 'brightdata', 'brdtest',
        'medium', 'quora', 'wix.com', 'wordpress.com', 'blogger', 'shopify',
        'github', 'stackoverflow', 'cloudflare', 'w3.org', 'schema.org'
    ]
    
    for url in found:
        url = url.rstrip('.,;:!?()[]{}')
        url = url.split('&')[0]
        url = url.rstrip('/')
        
        if url not in seen:
            domain = urllib.parse.urlparse(url).netloc.lower()
            if len(domain) > 4 and not any(d in domain for d in blocked):
                seen.add(url)
                urls.append(url)
    
    return urls

async def search_bing(api_key, dork, pages=50):
    all_urls = []
    tasks = []
    
    for page in range(pages):
        start = page * 10 + 1
        url = f'https://www.bing.com/search?q={urllib.parse.quote(dork)}&count=10&first={start}'
        tasks.append(fetch_url(api_key, url))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for html in results:
        if isinstance(html, str) and html:
            urls = extract_urls(html)
            all_urls.extend(urls)
    
    return list(set(all_urls))

async def search_google(api_key, dork, pages=30):
    all_urls = []
    tasks = []
    
    for page in range(pages):
        start = page * 10
        url = f'https://www.google.com/search?q={urllib.parse.quote(dork)}&num=10&start={start}&hl=en&gl=us&pws=0&filter=0'
        tasks.append(fetch_url(api_key, url))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for html in results:
        if isinstance(html, str) and html:
            urls = extract_urls(html)
            all_urls.extend(urls)
    
    return list(set(all_urls))

async def search_ddg(api_key, dork, pages=20):
    all_urls = []
    tasks = []
    
    for page in range(pages):
        start = page * 30
        url = f'https://html.duckduckgo.com/html/?q={urllib.parse.quote(dork)}&s={start}'
        tasks.append(fetch_url(api_key, url))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for html in results:
        if isinstance(html, str) and html:
            urls = extract_urls(html)
            all_urls.extend(urls)
    
    return list(set(all_urls))

async def search_all_engines(api_key, dork):
    google_task = search_google(api_key, dork, pages=30)
    bing_task = search_bing(api_key, dork, pages=50)
    ddg_task = search_ddg(api_key, dork, pages=20)
    
    google_results, bing_results, ddg_results = await asyncio.gather(
        google_task, bing_task, ddg_task
    )
    
    return list(set(google_results + bing_results + ddg_results))

async def check_cf_captcha(url, api_key):
    try:
        payload = {'zone': "google_search", 'url': url, 'format': 'raw'}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            response = await client.post('https://api.brightdata.com/request', headers=headers, json=payload)
            if response.status_code == 200:
                try:
                    data = response.json()
                    html = data.get('body', data.get('html', ''))
                except:
                    html = response.text
                
                has_cf = 'cloudflare' in html.lower() or 'cf-browser-verification' in html.lower()
                has_captcha = 'captcha' in html.lower() or 'recaptcha' in html.lower() or 'hcaptcha' in html.lower()
                
                return url, has_cf, has_captcha
    except:
        pass
    
    return url, False, False

# ====== الصلاحيات ======
def can_use_dork(user_id):
    if user_id in ADMINS:
        return True
    if BANNED_USERS.get(str(user_id)):
        return False
    return True

def can_use_mass(user_id):
    if user_id in ADMINS:
        return True
    if BANNED_USERS.get(str(user_id)):
        return False
    if str(user_id) in VIP_USERS:
        expiry = VIP_USERS[str(user_id)]
        if isinstance(expiry, str):
            try:
                expiry = datetime.fromisoformat(expiry)
                if expiry > datetime.now():
                    return True
            except:
                return False
        elif isinstance(expiry, (int, float)):
            if expiry > time.time():
                return True
    return False

def can_use_file(user_id):
    return can_use_mass(user_id)

# ====== البحث المتوازي ======
async def run_mass_search(message, context, dorks, check_cf):
    user_id = message.chat.id
    
    if not API_KEYS:
        await message.edit_text(premium_emoji("❌ No API keys available."), parse_mode="HTML")
        return
    
    api_key = API_KEYS[0]
    all_clean = []
    all_cf = []
    all_captcha = []
    
    # كل الدروكات بالتوازي
    tasks = [search_all_engines(api_key, dork) for dork in dorks]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_urls = []
    for result in results:
        if isinstance(result, list):
            all_urls.extend(result)
    
    all_urls = list(set(all_urls))
    
    if check_cf:
        total_links = len(all_urls)
        processed = 0
        
        check_tasks = [check_cf_captcha(url, api_key) for url in all_urls]
        
        for coro in asyncio.as_completed(check_tasks):
            if context.user_data.get('stop_requested'):
                break
            
            url, has_cf, has_captcha = await coro
            
            if has_cf:
                all_cf.append(url)
            elif has_captcha:
                all_captcha.append(url)
            else:
                all_clean.append(url)
            
            processed += 1
            
            if total_links > 0:
                progress = (processed / total_links * 100)
                bar_length = 20
                filled = int(bar_length * progress / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                try:
                    await message.edit_text(
                        premium_emoji(f"👁 Mass Dork Search\n\n🔗 Links: {len(all_clean)}\n🛡 Cloudflare: {len(all_cf)}\n👁 Captcha: {len(all_captcha)}\n\n⏱ Progress: {int(progress)}% {bar}"),
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Stop", callback_data='stop_search')]])
                    )
                except:
                    pass
    else:
        all_clean = all_urls
    
    context.user_data['stop_requested'] = False
    
    if check_cf:
        if all_clean:
            filename = f"clean_{user_id}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_clean))
            with open(filename, 'rb') as f:
                await message.reply_document(document=f, filename="clean_urls.txt")
            os.remove(filename)
        
        if all_cf:
            filename = f"cf_{user_id}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_cf))
            with open(filename, 'rb') as f:
                await message.reply_document(document=f, filename="cloudflare_urls.txt")
            os.remove(filename)
        
        if all_captcha:
            filename = f"captcha_{user_id}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_captcha))
            with open(filename, 'rb') as f:
                await message.reply_document(document=f, filename="captcha_urls.txt")
            os.remove(filename)
    else:
        if all_clean:
            filename = f"results_{user_id}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_clean))
            with open(filename, 'rb') as f:
                await message.reply_document(document=f, filename="dork_results.txt")
            os.remove(filename)

# ====== الأوامر ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    username = update.effective_user.username or update.effective_user.first_name or "Unknown"
    
    keyboard = [
        [InlineKeyboardButton("🔗 Single Dork", callback_data='menu_single'),
         InlineKeyboardButton("🚀 Mass Dork", callback_data='menu_mass')],
        [InlineKeyboardButton("💳 Keys", callback_data='menu_keys'),
         InlineKeyboardButton("👥 Users", callback_data='menu_users')],
        [InlineKeyboardButton("📁 Send .txt", callback_data='menu_file')]
    ]
    
    welcome_text = f"""⚡ 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 𝐃𝐎𝐑𝐊𝐄𝐑

🤖 𝐒𝐭𝐚𝐭𝐮𝐬 ➛ 𝐎𝐧𝐥𝐢𝐧𝐞
👥 𝐔𝐬𝐞𝐫𝐬 ➛ {len(ALL_USERS)}

👤 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 @{username}
🔗 /dork - 𝐒𝐢𝐧𝐠𝐥𝐞 𝐒𝐞𝐚𝐫𝐜𝐡
🚀 /mdork - 𝐌𝐚𝐬𝐬 𝐒𝐞𝐚𝐫𝐜𝐡 (𝐔𝐩 𝐭𝐨 𝟏𝟒𝟎)

📁 𝐒𝐞𝐧𝐝 .𝐭𝐱𝐭

🛠 𝐃𝐞𝐯 ➛ @FAWZY30"""
    
    await update.message.reply_text(premium_emoji(welcome_text), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def dork_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    
    if not can_use_dork(user_id):
        return
    
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/dork intext:\"payment\" inurl:donate</code>"), parse_mode="HTML")
        return
    
    dork = ' '.join(context.args)
    
    if not API_KEYS:
        await update.message.reply_text(premium_emoji("❌ No API keys available."), parse_mode="HTML")
        return
    
    status_msg = await update.message.reply_text(premium_emoji("🚀 Searching..."), parse_mode="HTML")
    
    api_key = API_KEYS[0]
    urls = await search_all_engines(api_key, dork)
    
    if urls:
        filename = f"dork_{user_id}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(urls))
        
        await status_msg.delete()
        await update.message.reply_text(premium_emoji(f"✅ Search Complete!\n🔗 {len(urls)} links found"), parse_mode="HTML")
        
        with open(filename, 'rb') as f:
            await update.message.reply_document(document=f, filename="dork_results.txt")
        
        os.remove(filename)
    else:
        await status_msg.edit_text(premium_emoji("❌ No results found"), parse_mode="HTML")

async def mdork_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    
    if not can_use_mass(user_id):
        await update.message.reply_text(premium_emoji("❌ You cannot use this command because you are not a VIP user."), parse_mode="HTML")
        return
    
    message_text = update.message.text
    lines = message_text.split('\n')
    
    dorks = [line.strip() for line in lines[1:] if line.strip() and not line.startswith('/')]
    
    if not dorks:
        parts = message_text.split(' ', 1)
        if len(parts) > 1:
            dorks = [parts[1]]
    
    if not dorks:
        await update.message.reply_text(premium_emoji("❌ Please send dorks after /mdork command.\nMax 140 dorks."), parse_mode="HTML")
        return
    
    if len(dorks) > 140:
        await update.message.reply_text(premium_emoji("❌ Maximum 140 dorks allowed."), parse_mode="HTML")
        return
    
    context.user_data['dorks'] = dorks
    
    keyboard = [[InlineKeyboardButton("✅ Yes", callback_data='check_yes'),
                 InlineKeyboardButton("❌ No", callback_data='check_no')]]
    
    await update.message.reply_text(premium_emoji("🛡 Do you want to check for Cloudflare and Captcha?"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    
    if not can_use_file(user_id):
        await update.message.reply_text(premium_emoji("❌ You cannot use this command because you are not a VIP user."), parse_mode="HTML")
        return
    
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        return
    
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()
    
    dorks = [line.strip() for line in file_content.decode('utf-8', errors='ignore').split('\n') if line.strip() and not line.startswith('#')]
    
    if not dorks:
        await update.message.reply_text(premium_emoji("❌ No dorks found in file."), parse_mode="HTML")
        return
    
    context.user_data['dorks'] = dorks
    
    keyboard = [[InlineKeyboardButton("✅ Yes", callback_data='check_yes'),
                 InlineKeyboardButton("❌ No", callback_data='check_no')]]
    
    await update.message.reply_text(premium_emoji("🛡 Do you want to check for Cloudflare and Captcha?"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_single":
        await query.message.reply_text(premium_emoji("🔗 Send your dork:\n<code>/dork intext:\"payment\" inurl:donate</code>"), parse_mode="HTML")
    
    elif data == "menu_mass":
        await query.message.reply_text(premium_emoji("🚀 Send dorks after /mdork command:\nMax 140 dorks\n\nExample:\n/mdork\ndork1\ndork2\ndork3"), parse_mode="HTML")
    
    elif data == "menu_file":
        await query.message.reply_text(premium_emoji("📁 Send a .txt file with dorks (one per line)"), parse_mode="HTML")
    
    elif data in ["check_yes", "check_no"]:
        dorks = context.user_data.get('dorks', [])
        
        if not dorks:
            await query.message.reply_text(premium_emoji("❌ No dorks found."), parse_mode="HTML")
            return
        
        check_cf = data == "check_yes"
        
        await query.message.edit_text(
            premium_emoji("👁 Mass Dork Search\n\n🔗 Links: 0\n🛡 Cloudflare: 0\n👁 Captcha: 0\n\n⏱ Progress: 0% ░░░░░░░░░░░░░░░░░░░░"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Stop", callback_data='stop_search')]])
        )
        
        await run_mass_search(query.message, context, dorks, check_cf)
    
    elif data == "stop_search":
        context.user_data['stop_requested'] = True
        await query.message.reply_text(premium_emoji("🛑 Stopping..."), parse_mode="HTML")
    
    elif data == "menu_users":
        if user_id not in ADMINS:
            await query.answer("Admin only!", show_alert=True)
            return
        users = list(ALL_USERS)
        keyboard = []
        for uid in users[:20]:
            keyboard.append([InlineKeyboardButton(f"👤 {uid}", callback_data=f"user_{uid}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
        await query.edit_message_text(premium_emoji(f"👥 Total Users: {len(users)}"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("user_"):
        if user_id not in ADMINS:
            return
        target_id = data.split('_')[1]
        keyboard = [[InlineKeyboardButton("🚫 Ban", callback_data=f"ban_{target_id}"),
                     InlineKeyboardButton("🔙 Back", callback_data="menu_users")]]
        await query.edit_message_text(premium_emoji(f"👤 User: {target_id}"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("ban_"):
        if user_id not in ADMINS:
            return
        target_id = data.split('_')[1]
        BANNED_USERS[target_id] = True
        save_data()
        await query.edit_message_text(premium_emoji("✅ User banned!"), parse_mode="HTML")
    
    elif data == "menu_keys":
        if user_id not in ADMINS:
            await query.answer("Admin only!", show_alert=True)
            return
        keyboard = []
        for i, key in enumerate(API_KEYS):
            keyboard.append([InlineKeyboardButton(f"💳 Key #{i+1}", callback_data=f"key_{i}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
        await query.edit_message_text(premium_emoji(f"💳 Available Keys: {len(API_KEYS)}"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("key_"):
        if user_id not in ADMINS:
            return
        key_index = int(data.split('_')[1])
        if key_index < len(API_KEYS):
            key = API_KEYS[key_index]
            keyboard = [[InlineKeyboardButton("🗑 Delete", callback_data=f"delete_key_{key_index}"),
                         InlineKeyboardButton("🔙 Back", callback_data="menu_keys")]]
            await query.edit_message_text(premium_emoji(f"💳 Key #{key_index + 1}\n🔗 {key}"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("delete_key_"):
        if user_id not in ADMINS:
            return
        key_index = int(data.split('_')[2])
        if key_index < len(API_KEYS):
            API_KEYS.pop(key_index)
            save_data()
            await query.edit_message_text(premium_emoji("✅ Key deleted!"), parse_mode="HTML")
    
    elif data == "back_main":
        if user_id not in ADMINS:
            return
        keyboard = [[InlineKeyboardButton("💳 Keys", callback_data='menu_keys'),
                     InlineKeyboardButton("👥 Users", callback_data='menu_users')]]
        await query.edit_message_text(premium_emoji("👑 Admin Panel"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text(premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    
    help_text = """👑 𝐀𝐝𝐦𝐢𝐧 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬

⚡ /dork - 𝐒𝐢𝐧𝐠𝐥𝐞 𝐒𝐞𝐚𝐫𝐜𝐡
🚀 /mdork - 𝐌𝐚𝐬𝐬 𝐒𝐞𝐚𝐫𝐜𝐡 (𝐔𝐩 𝐭𝐨 𝟏𝟒𝟎)
📁 𝐒𝐞𝐧𝐝 .𝐭𝐱𝐭 - 𝐅𝐢𝐥𝐞 𝐒𝐞𝐚𝐫𝐜𝐡

💳 /addkey - 𝐀𝐝𝐝 𝐖𝐞𝐛 𝐔𝐧𝐥𝐨𝐜𝐤𝐞𝐫 𝐊𝐞𝐲
🔗 /showkey - 𝐒𝐡𝐨𝐰 𝐀𝐥𝐥 𝐊𝐞𝐲𝐬
👥 /show_users - 𝐒𝐡𝐨𝐰 𝐀𝐥𝐥 𝐔𝐬𝐞𝐫𝐬
🌟 /addpr - 𝐀𝐝𝐝 𝐕𝐈𝐏 (𝐔𝐬𝐞𝐫/𝐈𝐃 + 𝐃𝐚𝐲𝐬)
💸 /rmpr - 𝐑𝐞𝐦𝐨𝐯𝐞 𝐕𝐈𝐏 𝐃𝐚𝐲𝐬"""
    
    await update.message.reply_text(premium_emoji(help_text), parse_mode="HTML")

async def addkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text(premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: /addkey your_web_unlocker_key"), parse_mode="HTML")
        return
    
    key = context.args[0]
    
    if key not in API_KEYS:
        API_KEYS.append(key)
        save_data()
        await update.message.reply_text(premium_emoji("✅ Key added successfully!"), parse_mode="HTML")
    else:
        await update.message.reply_text(premium_emoji("❌ Key already exists!"), parse_mode="HTML")

async def showkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text(premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    
    if not API_KEYS:
        await update.message.reply_text(premium_emoji("❌ No keys found."), parse_mode="HTML")
        return
    
    keyboard = [[InlineKeyboardButton(f"💳 Key #{i+1}", callback_data=f"key_{i}")] for i in range(len(API_KEYS))]
    
    await update.message.reply_text(premium_emoji(f"💳 Available Keys: {len(API_KEYS)}"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text(premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    
    users = list(ALL_USERS)
    
    if not users:
        await update.message.reply_text(premium_emoji("❌ No users found."), parse_mode="HTML")
        return
    
    keyboard = []
    for uid in users[:20]:
        role = "👑" if uid in ADMINS else "🌟" if str(uid) in VIP_USERS else "👤"
        keyboard.append([InlineKeyboardButton(f"{role} {uid}", callback_data=f"user_{uid}")])
    
    await update.message.reply_text(premium_emoji(f"👥 Total Users: {len(users)}"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def addpr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text(premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(premium_emoji("💡 Usage: /addpr user_id days"), parse_mode="HTML")
        return
    
    target_user = str(context.args[0])
    days = int(context.args[1])
    
    expiry = datetime.now() + timedelta(days=days)
    VIP_USERS[target_user] = expiry.isoformat()
    save_data()
    
    await update.message.reply_text(premium_emoji(f"✅ VIP added!\n👤 User: {target_user}\n⏱ Days: {days}"), parse_mode="HTML")

async def rmpr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text(premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(premium_emoji("💡 Usage: /rmpr user_id days"), parse_mode="HTML")
        return
    
    target_user = str(context.args[0])
    days = int(context.args[1])
    
    if target_user in VIP_USERS:
        expiry = datetime.fromisoformat(VIP_USERS[target_user])
        new_expiry = expiry - timedelta(days=days)
        if new_expiry <= datetime.now():
            del VIP_USERS[target_user]
        else:
            VIP_USERS[target_user] = new_expiry.isoformat()
        save_data()
    
    await update.message.reply_text(premium_emoji(f"✅ VIP days removed!\n👤 User: {target_user}\n⏱ Days removed: {days}"), parse_mode="HTML")

async def error_handler(update, context):
    pass

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dork", dork_command))
    app.add_handler(CommandHandler("mdork", mdork_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addkey", addkey_command))
    app.add_handler(CommandHandler("showkey", showkey_command))
    app.add_handler(CommandHandler("show_users", show_users_command))
    app.add_handler(CommandHandler("addpr", addpr_command))
    app.add_handler(CommandHandler("rmpr", rmpr_command))
    
    app.add_handler(MessageHandler(filters.Document.TEXT, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("⚡ ULTIMATE DORKER Bot Started!")
    app.run_polling()

if __name__ == "__main__":
    main()
