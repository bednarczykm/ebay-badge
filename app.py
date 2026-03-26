"""
EuroFrance eBay Trust Badge - Render.com (v8 - compact 250x100)
"""
import io, re, time, os
from threading import Lock
from flask import Flask, Response, request
from PIL import Image, ImageDraw, ImageFont
import requests as http_requests

app = Flask(__name__)

# ============================================================
# ★★★ TWOJE DANE — EDYTUJ TUTAJ ★★★
# Aby zaktualizować: zmień liczby → commit na GitHub → Render auto-deploy
# ============================================================
SELLER_DATA = {
    'eurofrance1': {
        'fr': {'score': 20585, 'percent': '98,5', 'stars': 4},
        'de': {'score': 20585, 'percent': '98,5', 'stars': 4},
        'it': {'score': 20585, 'percent': '98,5', 'stars': 4},
        'es': {'score': 20585, 'percent': '98,5', 'stars': 4},
        'uk': {'score': 20585, 'percent': '98,5', 'stars': 4},
        'us': {'score': 20585, 'percent': '98,5', 'stars': 4},
        'nl': {'score': 20585, 'percent': '98,5', 'stars': 4},
        'be': {'score': 20585, 'percent': '98,5', 'stars': 4},
    },
}

# ============================================================
# CACHE
# ============================================================
cache = {}
cache_lock = Lock()
CACHE_TTL = 3600

def get_cached(key):
    with cache_lock:
        if key in cache:
            data, ts = cache[key]
            if time.time() - ts < CACHE_TTL:
                return data
    return None

def set_cached(key, data):
    with cache_lock:
        cache[key] = (data, time.time())

# ============================================================
# EBAY SCRAPING (fallback do SELLER_DATA)
# ============================================================
EBAY_URLS = {
    'fr': 'https://www.ebay.fr/fdbk/feedback_profile/{}',
    'de': 'https://www.ebay.de/fdbk/feedback_profile/{}',
    'it': 'https://www.ebay.it/fdbk/feedback_profile/{}',
    'es': 'https://www.ebay.es/fdbk/feedback_profile/{}',
    'uk': 'https://www.ebay.co.uk/fdbk/feedback_profile/{}',
    'us': 'https://www.ebay.com/fdbk/feedback_profile/{}',
    'nl': 'https://www.ebay.nl/fdbk/feedback_profile/{}',
    'be': 'https://www.ebay.be/fdbk/feedback_profile/{}',
}

LABEL_TEXTS = {
    'fr': 'FEEDBACK POSITIF', 'de': 'POSITIVES FEEDBACK',
    'it': 'FEEDBACK POSITIVO', 'es': 'FEEDBACK POSITIVO',
    'uk': 'POSITIVE FEEDBACK', 'us': 'POSITIVE FEEDBACK',
    'nl': 'POSITIEVE FEEDBACK', 'be': 'FEEDBACK POSITIF',
}

REVIEWS_WORD = {
    'fr': 'avis', 'de': 'Bewertungen', 'it': 'valutazioni',
    'es': 'opiniones', 'uk': 'reviews', 'us': 'reviews',
    'nl': 'beoordelingen', 'be': 'avis',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
}


def try_scrape(seller, locale='fr'):
    url = EBAY_URLS.get(locale, EBAY_URLS['fr']).format(seller)
    try:
        resp = http_requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        text = resp.text
        score = 0
        percent = '0'
        if m := re.search(re.escape(seller) + r'\s*\((\d[\d\s,.]*)', text, re.I):
            score = int(re.sub(r'[\s.,]', '', m.group(1)))
        elif m := re.search(r'(\d[\d\s,.]*)\s*(?:Feedback|évaluation|Bewertung|valutazion)', text, re.I):
            score = int(re.sub(r'[\s.,]', '', m.group(1)))
        if m := re.search(r'([\d][,.\d]*)\s*%\s*(?:positive|positif|positiv|positivo|positief)', text, re.I):
            percent = m.group(1).replace('.', ',')
        if score > 0:
            pct = float(percent.replace(',', '.'))
            stars = 5 if pct >= 99 else 4 if pct >= 97 else 3 if pct >= 95 else 2 if pct >= 90 else 1
            return {'score': score, 'percent': percent, 'stars': stars}
    except:
        pass
    return None


def get_data(seller, locale='fr'):
    cache_key = f"{seller}:{locale}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    scraped = try_scrape(seller, locale)
    if scraped:
        data = {'seller': seller, 'source': 'ebay', **scraped}
        set_cached(cache_key, data)
        return data

    if seller in SELLER_DATA:
        config = SELLER_DATA[seller].get(locale, SELLER_DATA[seller].get('fr', {}))
        if config:
            data = {'seller': seller, 'source': 'config', **config}
            set_cached(cache_key, data)
            return data

    return {'seller': seller, 'source': 'fallback', 'score': 0, 'percent': '0', 'stars': 0}


# ============================================================
# FONTS
# ============================================================
FONT_PATHS_BOLD = [
    os.path.join(os.path.dirname(__file__), 'DejaVuSans-Bold.ttf'),
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
]
FONT_PATHS_REG = [
    os.path.join(os.path.dirname(__file__), 'DejaVuSans.ttf'),
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]
FONT_BOLD = next((p for p in FONT_PATHS_BOLD if os.path.exists(p)), None)
FONT_REG = next((p for p in FONT_PATHS_REG if os.path.exists(p)), FONT_BOLD)

# ============================================================
# DRAWING HELPERS
# ============================================================
def text_centered(d, font_path, size, cx, cy, text, color):
    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    d.text((cx - tw/2, cy - th/2), text, fill=color, font=font)

def text_left(d, font_path, size, x, cy, text, color):
    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    d.text((x, cy - th/2), text, fill=color, font=font)

def text_right(d, font_path, size, x, cy, text, color):
    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    d.text((x - tw, cy - th/2), text, fill=color, font=font)

# ============================================================
# BADGE DRAWING - 250x100 compact
# ============================================================
def draw_badge(data, width=250, locale='fr'):
    scale = 2
    s = scale
    W = 500 * s
    H = 200 * s
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    NAVY = (43, 45, 66)
    GRAY_TEXT = (120, 120, 120)
    GOLD_STAR = (245, 185, 0)
    BORDER = (210, 210, 210)

    # Border
    d.rounded_rectangle([0, 0, W-1, H-1], radius=14*s, fill=None, outline=BORDER, width=2*s)

    # Navy accent bar left
    bar_w = 10 * s
    d.rounded_rectangle([0, 0, bar_w, H-1], radius=5*s, fill=NAVY)
    d.rectangle([bar_w//2, 0, bar_w, H-1], fill=NAVY)

    left_x = 28 * s

    # eBay logo + seller
    font_ebay = ImageFont.truetype(FONT_BOLD, 26 * s)
    x = left_x
    for letter, col in [('e',(229,50,56)), ('b',(0,100,210)), ('a',(245,175,2)), ('y',(134,184,23))]:
        d.text((x, 10*s), letter, fill=col, font=font_ebay)
        x += font_ebay.getbbox(letter)[2] - font_ebay.getbbox(letter)[0]
    text_left(d, FONT_BOLD, 19*s, x + 8*s, 22*s, data['seller'], NAVY)

    # Horizontal separator
    d.line([(left_x, 46*s), (W - 28*s, 46*s)], fill=BORDER, width=2*s)

    # Big percentage
    percent_text = f"{data['percent']}%"
    text_centered(d, FONT_BOLD, 44*s, W//2, 88*s, percent_text, NAVY)

    # Stars left, score right
    text_left(d, FONT_REG, 20*s, left_x, 148*s,
              '\u2605' * data['stars'] + '\u2606' * (5 - data['stars']), GOLD_STAR)
    score_text = f"{data['score']:,}".replace(',', '.') + ' ' + REVIEWS_WORD.get(locale, 'avis')
    text_right(d, FONT_BOLD, 15*s, W - 28*s, 148*s, score_text, GRAY_TEXT)

    # Label
    label = LABEL_TEXTS.get(locale, LABEL_TEXTS['fr'])
    text_centered(d, FONT_BOLD, 13*s, W//2, 178*s, label, GRAY_TEXT)

    # Downscale
    final_w = width
    final_h = int(width * 200 / 500)
    return img.resize((final_w, final_h), Image.LANCZOS)

# ============================================================
# ROUTES
# ============================================================
@app.route('/badge/<seller_id>')
def badge(seller_id):
    seller_id = re.sub(r'[^a-zA-Z0-9._-]', '', seller_id)
    locale = re.sub(r'[^a-z]', '', request.args.get('locale', 'fr'))
    width = min(max(int(request.args.get('width', 250)), 100), 1000)

    override_score = request.args.get('score')
    override_percent = request.args.get('percent')

    if request.args.get('debug') is not None:
        import json
        data = get_data(seller_id, locale)
        if override_score:
            data['score'] = int(override_score)
        if override_percent:
            data['percent'] = override_percent
        return Response(json.dumps(data, indent=2, ensure_ascii=False),
                       mimetype='application/json')

    data = get_data(seller_id, locale)
    if override_score:
        data['score'] = int(override_score)
    if override_percent:
        data['percent'] = override_percent
        pct = float(override_percent.replace(',', '.'))
        data['stars'] = 5 if pct >= 99 else 4 if pct >= 97 else 3 if pct >= 95 else 2 if pct >= 90 else 1

    img = draw_badge(data, width, locale)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png',
                   headers={'Cache-Control': f'public, max-age={CACHE_TTL}'})

@app.route('/')
def index():
    return '''<html><body style="background:#f0f0f0; padding:40px; font-family:Arial;">
    <h1>EuroFrance Trust Badge v8</h1>
    <p>Usage: <code>/badge/{seller_id}?locale=fr</code></p>
    <p>Params: <code>?locale=fr|de|it|es|uk|us|nl|be</code> · <code>?width=250</code> · <code>?debug</code></p>
    <h3>FR:</h3>
    <div style="background:white; display:inline-block; padding:20px; border-radius:8px;">
        <img src="/badge/eurofrance1?locale=fr">
    </div>
    <h3>DE:</h3>
    <div style="background:white; display:inline-block; padding:20px; border-radius:8px;">
        <img src="/badge/eurofrance1?locale=de">
    </div>
    <h3>IT:</h3>
    <div style="background:white; display:inline-block; padding:20px; border-radius:8px;">
        <img src="/badge/eurofrance1?locale=it">
    </div>
    <h3>ES:</h3>
    <div style="background:white; display:inline-block; padding:20px; border-radius:8px;">
        <img src="/badge/eurofrance1?locale=es">
    </div>
    </body></html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
