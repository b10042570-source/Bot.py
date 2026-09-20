import os
import re
import time
import json
import urllib.parse
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import telebot

# ====== الإعدادات ======
TOKEN = os.environ.get('BOT_TOKEN', '8802065988:AAG2yL7xkxlufanIWhitySYrn0GTFv5D-FA')
ADMINS = [6843321125]

# ====== البيانات ======
VIP_USERS = {}
BANNED_USERS = {}
ALL_USERS = set()
API_KEYS = ["a65409df-86c7-4d26-9510-3aea809bd8e6"]
stop_users = {}

DATA_FILE = "dorker_data.json"

try:
    with open(DATA_FILE, 'r') as f:
        saved_data = json.load(f)
        saved_keys = saved_data.get("api_keys", [])
        for k in saved_keys:
            if k not in API_KEYS:
                API_KEYS.append(k)
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

# ====== البوت ======
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# ====== دالة إرسال أزرار ملونة ======
def make_button(text, callback_data=None, url=None, style=None):
    btn = {"text": text}
    if callback_data:
        btn["callback_data"] = callback_data
    if url:
        btn["url"] = url
    if style:
        btn["style"] = style
    return btn

def send_colored(chat_id, text, buttons, parse_mode="HTML"):
    """إرسال رسالة جديدة بأزرار ملونة"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "reply_markup": json.dumps({"inline_keyboard": buttons})
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.json()
    except Exception as e:
        print(f"send_colored error: {e}")
        return None

def edit_colored(chat_id, message_id, text, buttons=None, parse_mode="HTML"):
    """تعديل رسالة موجودة بأزرار ملونة"""
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.json()
    except Exception as e:
        print(f"edit_colored error: {e}")
        return None

# ====== Semaphore (للتحكم في عدد الطلبات) ======
MAX_WORKERS = 50

# ====== الفلاتر ======
BLOCKED_DOMAINS = [
    'google.com', 'google.co', 'googleapis.com', 'googleusercontent.com',
    'google-analytics.com', 'googletagmanager.com', 'googleadservices.com',
    'doubleclick.net', 'bing.com', 'msn.com', 'yahoo.com', 'yimg.com',
    'yahooapis.com', 'oath.com', 'verizonmedia.com', 'duckduckgo.com',
    'yandex.com', 'yandex.ru', 'yastatic.net', 'yandex.net',
    'baidu.com', 'bdstatic.com', 'bcebos.com', 'bdimg.com',
    'brave.com', 'startpage.com', 'ecosia.org', 'mojeek.com',
    'ask.com', 'aol.com',
    'youtube.com', 'youtu.be', 'ytimg.com', 'ggpht.com',
    'facebook.com', 'fb.com', 'fbcdn.net', 'facebook.net',
    'twitter.com', 'x.com', 'linkedin.com', 'instagram.com',
    'pinterest.com', 'tiktok.com', 'reddit.com', 'tumblr.com',
    'snapchat.com', 'telegram.org', 't.me', 'whatsapp.com',
    'wa.me', 'discord.com', 'discord.gg',
    'wikipedia.org', 'wikimedia.org', 'amazon.com', 'ebay.com',
    'apple.com', 'microsoft.com', 'windows.com', 'windowsupdate.com',
    'azure.com', 'azurewebsites.net', 'cloudapp.azure.com',
    'microsoftonline.com', 'sharepoint.com', 'onedrive.live.com',
    'outlook.com', 'office.com', 'office365.com',
    'login.live.com', 'account.microsoft.com',
    'brightdata.com', 'brdtest.com', 'medium.com', 'quora.com',
    'wix.com', 'wordpress.com', 'blogger.com', 'blogspot.com',
    'shopify.com', 'github.com', 'gitlab.com', 'stackoverflow.com',
    'stackexchange.com', 'cloudflare.com', 'w3.org', 'schema.org',
    'trustpilot.com', 'yelp.com', 'bbb.org', 'glassdoor.com',
    'indeed.com', 'ziprecruiter.com', 'monster.com', 'careerbuilder.com',
    'dice.com',
    'akamaihd.net', 'cloudfront.net', 'cdnjs.cloudflare.com',
    'jsdelivr.net', 'unpkg.com', 'bootstrapcdn.com', 'jquery.com',
    'fontawesome.com', 'getbootstrap.com', 'wixstatic.com', 'wp.com',
    'cloudinary.com', 'imgix.net', 'fastly.net', 'maxcdn.com',
    'stackpath.com', 'keycdn.com', 'statically.io', 'gitcdn.xyz',
    'rawgit.com',
    'onetrust.com', 'cookiebot.com', 'trustarc.com',
    'usercentrics.com', 'quantcast.com', 'cookielaw.org',
    'cookieyes.com', 'termly.io', 'iubenda.com', 'osano.com',
    'adsense.google.com', 'adservice.google.com', 'googleads.com',
    'hotjar.com', 'mixpanel.com', 'segment.com', 'amplitude.com',
    'sentry.io', 'newrelic.com', 'datadoghq.com', 'bugsnag.com',
    'rollbar.com', 'logrocket.com', 'fullstory.com', 'clarity.ms',
    'mouseflow.com', 'crazyegg.com', 'optimizely.com', 'vwo.com',
    'hubspot.com', 'marketo.com', 'mailchimp.com',
    'goo.gl', 'bit.ly', 'tinyurl.com', 'shorturl.at', 'ow.ly',
    'buff.ly', 'is.gd', 'v.gd', 'rb.gy', 'cutt.ly',
    'paypal.com', 'stripe.com', 'square.com', 'venmo.com',
    'cash.app', 'wise.com', 'revolut.com',
    'gmail.com', 'mail.google.com', 'protonmail.com',
    'proton.me', 'zoho.com', 'yandex.mail', 'mail.ru',
]

BLOCKED_PATTERNS = [
    r'\{.*\}', r'%7B.*%7D', r'profilephoto', r'usertile', r'expressionprofile',
    r'profilepicture', r'avatar', r'\.css$', r'\.js$', r'\.json$', r'\.xml$',
    r'\.txt$', r'\.pdf$', r'\.png$', r'\.jpg$', r'\.jpeg$', r'\.gif$', r'\.svg$',
    r'\.ico$', r'\.webp$', r'\.bmp$', r'\.tiff$', r'\.woff', r'\.woff2', r'\.ttf',
    r'\.eot', r'\.otf', r'\.mp4$', r'\.mp3$', r'\.wav$', r'\.avi$', r'\.mov$',
    r'\.webm$', r'/static/', r'/assets/', r'/cdn/', r'/cache/', r'/fonts/',
    r'/images/', r'/img/', r'/css/', r'/js/', r'\.min\.', r'\.map$', r'\.zip$',
    r'\.tar\.', r'\.gz$', r'/api/', r'/ajax/', r'/graphql', r'/webhook', r'/rpc/',
    r'/track', r'/pixel', r'/beacon', r'/collect', r'/analytics', r'/gtm', r'/gtag',
]

def extract_urls(html):
    urls = []
    seen = set()
    if not html:
        return urls
    pattern = r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s"<>()\[\]]*'
    found = re.findall(pattern, html)
    for url in found:
        url = url.rstrip('.,;:!?()[]{}')
        url = url.split('&')[0]
        url = url.rstrip('/')
        if url in seen:
            continue
        try:
            domain = urllib.parse.urlparse(url).netloc.lower()
        except:
            continue
        url_lower = url.lower()
        if len(domain) <= 4:
            continue
        if any(d in domain for d in BLOCKED_DOMAINS):
            continue
        if any(re.search(p, url_lower) for p in BLOCKED_PATTERNS):
            continue
        try:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path.strip('/')
        except:
            continue
        if not path and len(domain) > 30:
            continue
        seen.add(url)
        urls.append(url)
    return urls

# ====== جلب الصفحات ======
def fetch_url(api_key, url):
    try:
        payload = {'zone': "web_unlocker1", 'url': url, 'format': 'raw'}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        r = requests.post('https://api.brightdata.com/request', headers=headers, json=payload, timeout=25, verify=False)
        if r.status_code == 200:
            try:
                data = r.json()
                return data.get('body', data.get('html', ''))
            except:
                return r.text
        return ""
    except:
        return ""

# ====== محركات البحث ======
def search_google(api_key, dork, pages=30):
    all_urls = []
    tasks = []
    for page in range(pages):
        start = page * 10
        url = f'https://www.google.com/search?q={urllib.parse.quote(dork)}&num=10&start={start}&hl=en&gl=us&pws=0&filter=0'
        tasks.append(url)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(fetch_url, api_key, u) for u in tasks]
        for f in as_completed(futures):
            try:
                html = f.result()
                if html:
                    all_urls.extend(extract_urls(html))
            except:
                pass
    return list(set(all_urls))

def search_bing(api_key, dork, pages=50):
    all_urls = []
    tasks = []
    for page in range(pages):
        start = page * 10 + 1
        url = f'https://www.bing.com/search?q={urllib.parse.quote(dork)}&count=10&first={start}'
        tasks.append(url)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(fetch_url, api_key, u) for u in tasks]
        for f in as_completed(futures):
            try:
                html = f.result()
                if html:
                    all_urls.extend(extract_urls(html))
            except:
                pass
    return list(set(all_urls))

def search_ddg(api_key, dork, pages=50):
    all_urls = []
    tasks = []
    for page in range(pages):
        start = page * 30
        url = f'https://html.duckduckgo.com/html/?q={urllib.parse.quote(dork)}&s={start}'
        tasks.append(url)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(fetch_url, api_key, u) for u in tasks]
        for f in as_completed(futures):
            try:
                html = f.result()
                if html:
                    all_urls.extend(extract_urls(html))
            except:
                pass
    return list(set(all_urls))

def search_yahoo(api_key, dork, pages=20):
    all_urls = []
    tasks = []
    for page in range(pages):
        start = page * 10 + 1
        url = f'https://search.yahoo.com/search?p={urllib.parse.quote(dork)}&n=10&b={start}'
        tasks.append(url)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(fetch_url, api_key, u) for u in tasks]
        for f in as_completed(futures):
            try:
                html = f.result()
                if html:
                    all_urls.extend(extract_urls(html))
            except:
                pass
    return list(set(all_urls))

def search_all_engines(api_key, dork):
    all_urls = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [
            ex.submit(search_google, api_key, dork, 30),
            ex.submit(search_bing, api_key, dork, 50),
            ex.submit(search_ddg, api_key, dork, 50),
            ex.submit(search_yahoo, api_key, dork, 20),
        ]
        for f in as_completed(futures):
            try:
                result = f.result()
                if isinstance(result, list):
                    all_urls.extend(result)
            except:
                pass
    return list(set(all_urls))

# ====== فحص Cloudflare و Captcha ======
def check_cf_captcha(url, api_key):
    try:
        payload = {'zone': "web_unlocker1", 'url': url, 'format': 'raw'}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        r = requests.post('https://api.brightdata.com/request', headers=headers, json=payload, timeout=30, verify=False)
        html = ""
        if r.status_code == 200:
            try:
                data = r.json()
                html = data.get('body', '') or data.get('html', '') or data.get('data', '')
            except:
                html = r.text
        else:
            html = r.text
        if not html:
            return url, False, False
        html_lower = html.lower()
        cf_keywords = [
            'cloudflare', 'cf-browser-verification', 'cf_chl_opt',
            'cf-challenge', 'cf-wrapper', 'challenge-platform',
            'just a moment', 'checking your browser',
            'attention required!', 'cf-error-details',
            'cf-ray', 'turnstile', 'cf-turnstile',
            'ddos protection by cloudflare', 'you have been blocked',
            'enable javascript and cookies to continue',
            'verifying you are human', '__cf_chl_f_tk', 'cf_clearance',
            '__cfduid', 'cf-chl-', 'challenges.cloudflare.com'
        ]
        captcha_keywords = [
            'captcha', 'recaptcha', 'hcaptcha', 'g-recaptcha',
            'h-captcha', 'grecaptcha', 'verify you are human',
            'i am not a robot', 'prove you are human',
            'complete the security check', 'security check',
            'data-sitekey', 'recaptcha/api',
            'challenges.cloudflare.com/turnstile',
            'www.google.com/recaptcha',
            'hcaptcha.com/1/api.js',
            'g-recaptcha-response', 'h-captcha-response'
        ]
        has_cf = any(kw in html_lower for kw in cf_keywords)
        has_captcha = any(kw in html_lower for kw in captcha_keywords)
        if has_cf:
            has_captcha = False
        return url, has_cf, has_captcha
    except:
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

# ====== البحث الجماعي ======
def run_mass_search(chat_id, message_id, user_id, dorks):
    stop_users[user_id] = False
    if not API_KEYS:
        edit_colored(chat_id, message_id, premium_emoji("❌ No API keys available."))
        return
    api_key = API_KEYS[0]
    all_urls = []
    total_dorks = len(dorks)
    processed_dorks = 0
    total_links_found = 0
    for dork in dorks:
        if stop_users.get(user_id):
            break
        try:
            urls = search_all_engines(api_key, dork)
            all_urls.extend(urls)
            total_links_found += len(urls)
            processed_dorks += 1
            progress = (processed_dorks / total_dorks * 100)
            bar_length = 20
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            try:
                edit_colored(
                    chat_id, message_id,
                    premium_emoji(f"👁 Mass Dork Search\n\n📊 Dorks: {processed_dorks}/{total_dorks}\n🔗 Links: {total_links_found}\n\n⏱ Progress: {int(progress)}% {bar}"),
                    buttons=[[make_button("🛑 Stop", callback_data='stop_search', style="danger")]]
                )
            except:
                pass
        except Exception as e:
            print(f"Error on dork: {e}")
            continue
    all_urls = list(set(all_urls))
    stop_users[user_id] = False
    if all_urls:
        filename = f"results_{user_id}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_urls))
        with open(filename, 'rb') as f:
            bot.send_document(chat_id, f, visible_file_name="dork_results.txt")
        try:
            os.remove(filename)
        except:
            pass

# ====== الفحص (/sex) ======
def run_sex_check(chat_id, message_id, user_id, urls):
    stop_users[user_id] = False
    if not API_KEYS:
        edit_colored(chat_id, message_id, premium_emoji("❌ No API keys available."))
        return
    api_key = API_KEYS[0]
    all_clean = []
    all_cf = []
    all_captcha = []
    total_links = len(urls)
    processed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(check_cf_captcha, u, api_key): u for u in urls}
        for f in as_completed(futures):
            if stop_users.get(user_id):
                break
            try:
                url, has_cf, has_captcha = f.result()
            except:
                url, has_cf, has_captcha = "", False, False
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
                if processed % 5 == 0 or processed == total_links:
                    try:
                        edit_colored(
                            chat_id, message_id,
                            premium_emoji(f"🔥 Filter Links\n\n🔗 Clean: {len(all_clean)}\n🛡 Cloudflare: {len(all_cf)}\n👁 Captcha: {len(all_captcha)}\n\n⏱ Progress: {int(progress)}% {bar}"),
                            buttons=[[make_button("🛑 Stop", callback_data='stop_search', style="danger")]]
                        )
                    except:
                        pass
    stop_users[user_id] = False
    if all_clean:
        filename = f"clean_{user_id}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_clean))
        with open(filename, 'rb') as f:
            bot.send_document(chat_id, f, visible_file_name="clean_urls.txt")
        try:
            os.remove(filename)
        except:
            pass
    if all_cf:
        filename = f"cf_{user_id}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_cf))
        with open(filename, 'rb') as f:
            bot.send_document(chat_id, f, visible_file_name="cloudflare_urls.txt")
        try:
            os.remove(filename)
        except:
            pass
    if all_captcha:
        filename = f"captcha_{user_id}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_captcha))
        with open(filename, 'rb') as f:
            bot.send_document(chat_id, f, visible_file_name="captcha_urls.txt")
        try:
            os.remove(filename)
        except:
            pass

# ====== أوامر البوت ======
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    ALL_USERS.add(user_id)
    username = message.from_user.username or message.from_user.first_name or "Unknown"

    buttons = [
        [
            make_button("🔗 Single Dork", callback_data='menu_single', style="primary"),
            make_button("🚀 Mass Dork", callback_data='menu_mass', style="success")
        ],
        [make_button("🔥 Filter Links", callback_data='menu_sex', style="danger")],
        [
            make_button("💳 Keys", callback_data='menu_keys', style="primary"),
            make_button("👥 Users", callback_data='menu_users', style="primary")
        ],
        [make_button("📁 Send .txt", callback_data='menu_file', style="success")]
    ]

    welcome_text = f"""⚡ 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 𝐃𝐎𝐑𝐊𝐄𝐑

🤖 𝐒𝐭𝐚𝐭𝐮𝐬 ➛ 𝐎𝐧𝐥𝐢𝐧𝐞
👥 𝐔𝐬𝐞𝐫𝐬 ➛ {len(ALL_USERS)}

👤 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 @{username}
🔗 /dork - 𝐒𝐢𝐧𝐠𝐥𝐞 𝐒𝐞𝐚𝐫𝐜𝐡
🚀 /mdork - 𝐌𝐚𝐬𝐬 𝐒𝐞𝐚𝐫𝐜𝐡 (𝐔𝐩 𝐭𝐨 𝟏𝟒𝟎)
🔥 /sex - 𝐅𝐢𝐥𝐭𝐞𝐫 𝐋𝐢𝐧𝐤𝐬 (𝐂𝐥𝐨𝐮𝐝𝐟𝐥𝐚𝐫𝐞 & 𝐂𝐚𝐩𝐭𝐜𝐡𝐚)

📁 𝐒𝐞𝐧𝐝 .𝐭𝐱𝐭

🛠 𝐃𝐞𝐯 ➛ @FAWZY30"""

    send_colored(message.chat.id, premium_emoji(welcome_text), buttons)


@bot.message_handler(commands=['dork'])
def dork_command(message):
    user_id = message.from_user.id
    ALL_USERS.add(user_id)
    if not can_use_dork(user_id):
        return
    parts = message.text.split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, premium_emoji("💡 Usage: <code>/dork intext:\"payment\" inurl:donate</code>"), parse_mode="HTML")
        return
    dork = parts[1].strip()
    if not API_KEYS:
        bot.reply_to(message, premium_emoji("❌ No API keys available."), parse_mode="HTML")
        return
    status_msg = bot.reply_to(message, premium_emoji("🚀 Searching..."), parse_mode="HTML")
    api_key = API_KEYS[0]
    urls = search_all_engines(api_key, dork)
    if urls:
        filename = f"dork_{user_id}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(urls))
        try:
            bot.delete_message(message.chat.id, status_msg.message_id)
        except:
            pass
        bot.reply_to(message, premium_emoji(f"✅ Search Complete!\n🔗 {len(urls)} links found"), parse_mode="HTML")
        with open(filename, 'rb') as f:
            bot.send_document(message.chat.id, f, visible_file_name="dork_results.txt")
        try:
            os.remove(filename)
        except:
            pass
    else:
        try:
            bot.edit_message_text(
                premium_emoji("❌ No results found"),
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                parse_mode="HTML"
            )
        except:
            pass


@bot.message_handler(commands=['mdork'])
def mdork_command(message):
    user_id = message.from_user.id
    ALL_USERS.add(user_id)
    if not can_use_mass(user_id):
        bot.reply_to(message, premium_emoji("❌ You cannot use this command because you are not a VIP user."), parse_mode="HTML")
        return
    lines = message.text.split('\n')
    dorks = [line.strip() for line in lines[1:] if line.strip() and not line.startswith('/')]
    if not dorks:
        parts = message.text.split(' ', 1)
        if len(parts) > 1 and parts[1].strip():
            dorks = [parts[1].strip()]
    if not dorks:
        bot.reply_to(message, premium_emoji("❌ Please send dorks after /mdork command.\nMax 140 dorks."), parse_mode="HTML")
        return
    if len(dorks) > 140:
        bot.reply_to(message, premium_emoji("❌ Maximum 140 dorks allowed."), parse_mode="HTML")
        return

    init_text = premium_emoji(f"👁 Mass Dork Search\n\n📊 Dorks: 0/{len(dorks)}\n🔗 Links: 0\n\n⏱ Progress: 0% ░░░░░░░░░░░░░░░░░░░░")
    buttons = [[make_button("🛑 Stop", callback_data='stop_search', style="danger")]]
    resp = send_colored(message.chat.id, init_text, buttons)
    if not resp or not resp.get("ok"):
        return
    msg_id = resp["result"]["message_id"]

    from threading import Thread
    t = Thread(target=run_mass_search, args=(message.chat.id, msg_id, user_id, dorks), daemon=True)
    t.start()


@bot.message_handler(commands=['sex'])
def sex_command(message):
    user_id = message.from_user.id
    ALL_USERS.add(user_id)
    if not can_use_mass(user_id):
        bot.reply_to(message, premium_emoji("❌ You cannot use this command because you are not a VIP user."), parse_mode="HTML")
        return
    urls = []
    if message.reply_to_message and message.reply_to_message.document:
        try:
            file_info = bot.get_file(message.reply_to_message.document.file_id)
            file_content = bot.download_file(file_info.file_path)
            text = file_content.decode('utf-8', errors='ignore')
            urls = [line.strip() for line in text.split('\n') if line.strip() and line.strip().startswith('http')]
        except Exception as e:
            print(f"File read error: {e}")
    else:
        parts = message.text.split(' ', 1)
        if len(parts) > 1:
            urls = [a.strip() for a in parts[1].split() if a.strip().startswith('http')]
    if not urls:
        bot.reply_to(
            message,
            premium_emoji("💡 Usage:\n• Reply to .txt file with /sex\n• Or: /sex https://url1 https://url2"),
            parse_mode="HTML"
        )
        return

    init_text = premium_emoji(f"🔥 Filter Links\n\n🔗 Clean: 0\n🛡 Cloudflare: 0\n👁 Captcha: 0\n\n⏱ Progress: 0% ░░░░░░░░░░░░░░░░░░░░")
    buttons = [[make_button("🛑 Stop", callback_data='stop_search', style="danger")]]
    resp = send_colored(message.chat.id, init_text, buttons)
    if not resp or not resp.get("ok"):
        return
    msg_id = resp["result"]["message_id"]

    from threading import Thread
    t = Thread(target=run_sex_check, args=(message.chat.id, msg_id, user_id, urls), daemon=True)
    t.start()


@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    ALL_USERS.add(user_id)
    if not can_use_file(user_id):
        bot.reply_to(message, premium_emoji("❌ You cannot use this command because you are not a VIP user."), parse_mode="HTML")
        return
    document = message.document
    if not document.file_name.endswith('.txt'):
        return
    try:
        file_info = bot.get_file(document.file_id)
        file_content = bot.download_file(file_info.file_path)
        text = file_content.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Download error: {e}")
        return
    dorks = [line.strip() for line in text.split('\n') if line.strip() and not line.startswith('#')]
    if not dorks:
        bot.reply_to(message, premium_emoji("❌ No dorks found in file."), parse_mode="HTML")
        return

    init_text = premium_emoji(f"👁 Mass Dork Search\n\n📊 Dorks: 0/{len(dorks)}\n🔗 Links: 0\n\n⏱ Progress: 0% ░░░░░░░░░░░░░░░░░░░░")
    buttons = [[make_button("🛑 Stop", callback_data='stop_search', style="danger")]]
    resp = send_colored(message.chat.id, init_text, buttons)
    if not resp or not resp.get("ok"):
        return
    msg_id = resp["result"]["message_id"]

    from threading import Thread
    t = Thread(target=run_mass_search, args=(message.chat.id, msg_id, user_id, dorks), daemon=True)
    t.start()
    
    # ====== أوامر الأدمن ======
@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        bot.reply_to(message, premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    help_text = """👑 𝐀𝐝𝐦𝐢𝐧 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬

⚡ /dork - 𝐒𝐢𝐧𝐠𝐥𝐞 𝐒𝐞𝐚𝐫𝐜𝐡
🚀 /mdork - 𝐌𝐚𝐬𝐬 𝐒𝐞𝐚𝐫𝐜𝐡 (𝐔𝐩 𝐭𝐨 𝟏𝟒𝟎)
🔥 /sex - 𝐅𝐢𝐥𝐭𝐞𝐫 𝐋𝐢𝐧𝐤𝐬 (𝐂𝐥𝐨𝐮𝐝𝐟𝐥𝐚𝐫𝐞 & 𝐂𝐚𝐩𝐭𝐜𝐡𝐚)
📁 𝐒𝐞𝐧𝐝 .𝐭𝐱𝐭 - 𝐅𝐢𝐥𝐞 𝐒𝐞𝐚𝐫𝐜𝐡

💳 /addkey - 𝐀𝐝𝐝 𝐖𝐞𝐛 𝐔𝐧𝐥𝐨𝐜𝐤𝐞𝐫 𝐊𝐞𝐲
🔗 /showkey - 𝐒𝐡𝐨𝐰 𝐀𝐥𝐥 𝐊𝐞𝐲𝐬
👥 /show_users - 𝐒𝐡𝐨𝐰 𝐀𝐥𝐥 𝐔𝐬𝐞𝐫𝐬
🌟 /addpr - 𝐀𝐝𝐝 𝐕𝐈𝐏 (𝐔𝐬𝐞𝐫/𝐈𝐃 + 𝐃𝐚𝐲𝐬)
💸 /rmpr - 𝐑𝐞𝐦𝐨𝐯𝐞 𝐕𝐈𝐏 𝐃𝐚𝐲𝐬"""
    bot.reply_to(message, premium_emoji(help_text), parse_mode="HTML")


@bot.message_handler(commands=['addkey'])
def addkey_command(message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        bot.reply_to(message, premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    parts = message.text.split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, premium_emoji("💡 Usage: /addkey your_web_unlocker_key"), parse_mode="HTML")
        return
    key = parts[1].strip()
    if key not in API_KEYS:
        API_KEYS.append(key)
        save_data()
        bot.reply_to(message, premium_emoji("✅ Key added successfully!"), parse_mode="HTML")
    else:
        bot.reply_to(message, premium_emoji("❌ Key already exists!"), parse_mode="HTML")


@bot.message_handler(commands=['showkey'])
def showkey_command(message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        bot.reply_to(message, premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    if not API_KEYS:
        bot.reply_to(message, premium_emoji("❌ No keys found."), parse_mode="HTML")
        return
    buttons = [[make_button(f"💳 Key #{i+1}", callback_data=f"key_{i}", style="primary")] for i in range(len(API_KEYS))]
    send_colored(message.chat.id, premium_emoji(f"💳 Available Keys: {len(API_KEYS)}"), buttons)


@bot.message_handler(commands=['show_users'])
def show_users_command(message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        bot.reply_to(message, premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    users = list(ALL_USERS)
    if not users:
        bot.reply_to(message, premium_emoji("❌ No users found."), parse_mode="HTML")
        return
    buttons = []
    for uid in users[:20]:
        role = "👑" if uid in ADMINS else "🌟" if str(uid) in VIP_USERS else "👤"
        buttons.append([make_button(f"{role} {uid}", callback_data=f"user_{uid}", style="primary")])
    send_colored(message.chat.id, premium_emoji(f"👥 Total Users: {len(users)}"), buttons)


@bot.message_handler(commands=['addpr'])
def addpr_command(message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        bot.reply_to(message, premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, premium_emoji("💡 Usage: /addpr user_id days"), parse_mode="HTML")
        return
    try:
        target_user = str(parts[1])
        days = int(parts[2])
    except:
        bot.reply_to(message, premium_emoji("❌ Invalid input."), parse_mode="HTML")
        return
    expiry = datetime.now() + timedelta(days=days)
    VIP_USERS[target_user] = expiry.isoformat()
    save_data()
    bot.reply_to(message, premium_emoji(f"✅ VIP added!\n👤 User: {target_user}\n⏱ Days: {days}"), parse_mode="HTML")


@bot.message_handler(commands=['rmpr'])
def rmpr_command(message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        bot.reply_to(message, premium_emoji("❌ You cannot use this command because it is only for admin."), parse_mode="HTML")
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, premium_emoji("💡 Usage: /rmpr user_id days"), parse_mode="HTML")
        return
    try:
        target_user = str(parts[1])
        days = int(parts[2])
    except:
        bot.reply_to(message, premium_emoji("❌ Invalid input."), parse_mode="HTML")
        return
    if target_user in VIP_USERS:
        try:
            expiry = datetime.fromisoformat(VIP_USERS[target_user])
            new_expiry = expiry - timedelta(days=days)
            if new_expiry <= datetime.now():
                del VIP_USERS[target_user]
            else:
                VIP_USERS[target_user] = new_expiry.isoformat()
            save_data()
        except:
            pass
    bot.reply_to(message, premium_emoji(f"✅ VIP days removed!\n👤 User: {target_user}\n⏱ Days removed: {days}"), parse_mode="HTML")


# ====== معالج الأزرار ======
@bot.callback_query_handler(func=lambda call: True)
def button_callback(call):
    user_id = call.from_user.id
    data = call.data
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    if data == "menu_single":
        bot.send_message(call.message.chat.id, premium_emoji("🔗 Send your dork:\n<code>/dork intext:\"payment\" inurl:donate</code>"), parse_mode="HTML")

    elif data == "menu_mass":
        bot.send_message(call.message.chat.id, premium_emoji("🚀 Send dorks after /mdork command:\nMax 140 dorks\n\nExample:\n/mdork\ndork1\ndork2\ndork3"), parse_mode="HTML")

    elif data == "menu_file":
        bot.send_message(call.message.chat.id, premium_emoji("📁 Send a .txt file with dorks (one per line)"), parse_mode="HTML")

    elif data == "menu_sex":
        bot.send_message(call.message.chat.id, premium_emoji("🔥 Filter Links\n\nSend .txt file with links (reply + /sex)\nOr: /sex https://url1 https://url2\n\nResult: 3 files (clean + cloudflare + captcha)"), parse_mode="HTML")

    elif data == "stop_search":
        chat_id = call.message.chat.id
        stop_users[chat_id] = True
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
        except:
            pass
        bot.send_message(chat_id, premium_emoji("🛑 Stopping..."), parse_mode="HTML")

    elif data == "menu_users":
        if user_id not in ADMINS:
            bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            return
        users = list(ALL_USERS)
        buttons = []
        for uid in users[:20]:
            buttons.append([make_button(f"👤 {uid}", callback_data=f"user_{uid}", style="primary")])
        buttons.append([make_button("🔙 Back", callback_data="back_main", style="primary")])
        try:
            bot.edit_message_text(
                premium_emoji(f"👥 Total Users: {len(users)}"),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=json.dumps({"inline_keyboard": buttons})
            )
        except Exception as e:
            print(f"menu_users error: {e}")

    elif data.startswith("user_"):
        if user_id not in ADMINS:
            return
        target_id = data.split('_', 1)[1]
        buttons = [[
            make_button("🚫 Ban", callback_data=f"ban_{target_id}", style="danger"),
            make_button("🔙 Back", callback_data="menu_users", style="primary")
        ]]
        try:
            bot.edit_message_text(
                premium_emoji(f"👤 User: {target_id}"),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=json.dumps({"inline_keyboard": buttons})
            )
        except Exception as e:
            print(f"user_ error: {e}")

    elif data.startswith("ban_"):
        if user_id not in ADMINS:
            return
        target_id = data.split('_', 1)[1]
        BANNED_USERS[target_id] = True
        save_data()
        try:
            bot.edit_message_text(
                premium_emoji("✅ User banned!"),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )
        except:
            pass

    elif data == "menu_keys":
        if user_id not in ADMINS:
            bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            return
        buttons = []
        for i in range(len(API_KEYS)):
            buttons.append([make_button(f"💳 Key #{i+1}", callback_data=f"key_{i}", style="primary")])
        buttons.append([make_button("🔙 Back", callback_data="back_main", style="primary")])
        try:
            bot.edit_message_text(
                premium_emoji(f"💳 Available Keys: {len(API_KEYS)}"),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=json.dumps({"inline_keyboard": buttons})
            )
        except Exception as e:
            print(f"menu_keys error: {e}")

    elif data.startswith("key_"):
        if user_id not in ADMINS:
            return
        try:
            key_index = int(data.split('_')[1])
        except:
            return
        if key_index < len(API_KEYS):
            key = API_KEYS[key_index]
            buttons = [[
                make_button("🗑 Delete", callback_data=f"delete_key_{key_index}", style="danger"),
                make_button("🔙 Back", callback_data="menu_keys", style="primary")
            ]]
            try:
                bot.edit_message_text(
                    premium_emoji(f"💳 Key #{key_index + 1}\n🔗 {key}"),
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=json.dumps({"inline_keyboard": buttons})
                )
            except Exception as e:
                print(f"key_ error: {e}")

    elif data.startswith("delete_key_"):
        if user_id not in ADMINS:
            return
        try:
            key_index = int(data.split('_')[2])
        except:
            return
        if key_index < len(API_KEYS):
            API_KEYS.pop(key_index)
            save_data()
            try:
                bot.edit_message_text(
                    premium_emoji("✅ Key deleted!"),
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML"
                )
            except:
                pass

    elif data == "back_main":
        if user_id not in ADMINS:
            return
        buttons = [[
            make_button("💳 Keys", callback_data='menu_keys', style="primary"),
            make_button("👥 Users", callback_data='menu_users', style="primary")
        ]]
        try:
            bot.edit_message_text(
                premium_emoji("👑 Admin Panel"),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=json.dumps({"inline_keyboard": buttons})
            )
        except:
            pass


# ====== التشغيل ======
def main():
    print("⚡ ULTIMATE DORKER Bot Started!")
    while True:
        try:
            bot.polling(none_stop=True, skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
