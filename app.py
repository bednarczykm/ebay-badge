"""
EuroFrance eBay Trust Badge - Render.com (v3 - rectangular)
"""
import io, re, time, math, os
from threading import Lock
from flask import Flask, Response, request
from PIL import Image, ImageDraw, ImageFont
import requests as http_requests

app = Flask(__name__)

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
# EBAY DATA
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

RIBBON_TEXTS = {
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

def fetch_feedback(seller, locale='fr'):
    cache_key = f"{seller}:{locale}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    url = EBAY_URLS.get(locale, EBAY_URLS['fr']).format(seller)
    data = {'seller': seller, 'score': 0, 'percent': '0', 'stars': 5}

    try:
        resp = http_requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        text = resp.text

        if m := re.search(re.escape(seller) + r'\s*\((\d[\d\s,.]*)', text, re.I):
            data['score'] = int(re.sub(r'[\s.,]', '', m.group(1)))
        elif m := re.search(r'(\d[\d\s,.]*)\s*(?:Feedback|évaluation|Bewertung|valutazion)', text, re.I):
            data['score'] = int(re.sub(r'[\s.,]', '', m.group(1)))

        if m := re.search(r'([\d][,.\d]*)\s*%\s*(?:positive|positif|positiv|positivo|positief)', text, re.I):
            data['percent'] = m.group(1).replace('.', ',')
        elif m := re.search(r'([\d][,.\d]*)\s*%', text, re.I):
            data['percent'] = m.group(1).replace('.', ',')

        pct = float(data['percent'].replace(',', '.'))
        data['stars'] = 5 if pct >= 99 else 4 if pct >= 97 else 3 if pct >= 95 else 2 if pct >= 90 else 1
    except:
        pass

    set_cached(cache_key, data)
    return data

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
def text_left(d, font_path, size, x, cy, text, color):
    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    d.text((x, cy - th/2), text, fill=color, font=font)
    return tw, th

def text_right(d, font_path, size, x, cy, text, color):
    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    d.text((x - tw, cy - th/2), text, fill=color, font=font)
    return tw, th

# ============================================================
# BADGE DRAWING - Rectangular Concept A
# ============================================================
def draw_badge(data, width=700, locale='fr'):
    # Render at 2x for sharpness
    W = width * 2
    H = int(W * 200 / 700)  # aspect ratio 700:200
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Colors
    GOLD = (245, 212, 66)
    WHITE = (255, 255, 255)
    GRAY = (140, 140, 140)
    BG = (26, 26, 26)
    SEP = (60, 60, 60)

    # Background
    d.rounded_rectangle([0, 0, W-1, H-1], radius=28, fill=BG)

    # Gold accent bar (left)
    d.rounded_rectangle([0, 0, 20, H-1], radius=14, fill=GOLD)
    d.rectangle([10, 0, 20, H-1], fill=GOLD)

    # --- LEFT SIDE ---
    left_x = 70

    # eBay logo
    font_ebay = ImageFont.truetype(FONT_BOLD, 76)
    x = left_x
    for letter, col in [('e',(229,50,56)), ('b',(0,100,210)), ('a',(245,175,2)), ('y',(134,184,23))]:
        d.text((x, int(H*0.10)), letter, fill=col, font=font_ebay)
        x += font_ebay.getbbox(letter)[2] - font_ebay.getbbox(letter)[0]

    # Seller name
    text_left(d, FONT_BOLD, 44, left_x, int(H*0.48), data['seller'], WHITE)

    # Score
    score_text = f"{data['score']:,}".replace(',', '.') + ' ' + REVIEWS_WORD.get(locale, 'avis')
    text_left(d, FONT_BOLD, 36, left_x, int(H*0.66), score_text, GOLD)

    # Stars
    stars = '\u2605' * data['stars'] + '\u2606' * (5 - data['stars'])
    text_left(d, FONT_REG, 36, left_x, int(H*0.84), stars, GOLD)

    # --- SEPARATOR ---
    sep_x = int(W * 0.47)
    d.line([(sep_x, 60), (sep_x, H-60)], fill=SEP, width=3)

    # --- RIGHT SIDE ---
    right_x = W - 70

    # Big percentage
    percent_text = f"{data['percent']}%"
    text_right(d, FONT_BOLD, 164, right_x, int(H*0.42), percent_text, WHITE)

    # Label
    label = RIBBON_TEXTS.get(locale, RIBBON_TEXTS['fr'])
    tw, _ = text_right(d, FONT_BOLD, 26, right_x, int(H*0.74), label, GRAY)

    # Gold decorative line under label
    line_y = int(H * 0.84)
    d.rounded_rectangle([right_x - tw, line_y, right_x, line_y + 6], radius=3, fill=GOLD)

    # Downscale for sharpness
    final_w = width
    final_h = int(width * 200 / 700)
    final = img.resize((final_w, final_h), Image.LANCZOS)
    return final

# ============================================================
# ROUTES
# ============================================================
@app.route('/badge/<seller_id>')
def badge(seller_id):
    seller_id = re.sub(r'[^a-zA-Z0-9._-]', '', seller_id)
    locale = re.sub(r'[^a-z]', '', request.args.get('locale', 'fr'))
    width = min(max(int(request.args.get('width', 700)), 200), 1400)

    if request.args.get('debug') is not None:
        import json
        return Response(json.dumps(fetch_feedback(seller_id, locale), indent=2, ensure_ascii=False),
                       mimetype='application/json')

    data = fetch_feedback(seller_id, locale)
    img = draw_badge(data, width, locale)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png',
                   headers={'Cache-Control': f'public, max-age={CACHE_TTL}'})

@app.route('/')
def index():
    return '''<h1>EuroFrance Badge</h1>
    <p>Usage: /badge/eurofrance1</p>
    <p>Params: ?locale=fr|de|it|es|uk|us|nl|be &amp; ?width=700 &amp; ?debug</p>
    <h3>French:</h3>
    <img src="/badge/eurofrance1" width="350">
    <h3>German:</h3>
    <img src="/badge/eurofrance1?locale=de" width="350">
    '''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
