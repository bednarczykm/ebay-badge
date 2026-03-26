"""
EuroFrance eBay Trust Badge - Render.com
"""
import io, re, time, math, os
from threading import Lock
from flask import Flask, Response, request
from PIL import Image, ImageDraw, ImageFont
import requests as http_requests
from bs4 import BeautifulSoup

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
    'fr': 'VENDEUR DE CONFIANCE', 'de': 'VERTRAUENSWÜRDIGER VERKÄUFER',
    'it': 'VENDITORE AFFIDABILE', 'es': 'VENDEDOR DE CONFIANZA',
    'uk': 'TRUSTED SELLER', 'us': 'TRUSTED SELLER',
    'nl': 'BETROUWBARE VERKOPER', 'be': 'VENDEUR DE CONFIANCE',
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
# BADGE DRAWING
# ============================================================
FONT_PATHS = [
    os.path.join(os.path.dirname(__file__), 'DejaVuSans-Bold.ttf'),
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
]
FONT_PATH = next((p for p in FONT_PATHS if os.path.exists(p)), None)

def text_centered(draw, font_size, cx, cy, text, color):
    font = ImageFont.truetype(FONT_PATH, font_size) if FONT_PATH else ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw/2, cy - th/2), text, fill=color, font=font)

def draw_badge(data, size=460, ribbon_text='VENDEUR DE CONFIANCE'):
    S = size * 2
    cx = cy = S // 2
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Colors
    GL, GM, GD = (245,212,66), (200,150,12), (166,124,0)
    DBG, DDBG = (26,26,26), (17,17,17)
    W, LG = (255,255,255), (224,224,224)

    # Ribbons behind badge
    for rx in [cx - int(S*0.22), cx + int(S*0.22)]:
        ry = int(cy + S*0.38)
        rw, rh = int(S*0.12), int(S*0.12)
        d.polygon([(rx-rw, ry-rh//3), (rx+rw, ry-rh//3), (rx+rw//2, ry+rh), (rx, int(ry+rh*0.6)), (rx-rw//2, ry+rh)], fill=GD)

    # Serrated outer ring
    outer_r, bumps, depth = S*0.44, 28, S*0.035
    for dd, col in [(depth+4, GD), (depth, GM), (depth-3, GL)]:
        pts = []
        for i in range(bumps*2):
            a = (2*math.pi*i)/(bumps*2) - math.pi/2
            r = outer_r + dd if i%2==0 else outer_r - dd + depth
            pts.append((int(cx + r*math.cos(a)), int(cy + r*math.sin(a))))
        d.polygon(pts, fill=col)

    # Inner rings
    for r, c in [(0.40, GM), (0.37, GD), (0.35, DBG), (0.30, DDBG)]:
        ri = int(S*r)
        d.ellipse([cx-ri, cy-ri, cx+ri, cy+ri], fill=c)
    d.ellipse([cx-int(S*0.28), cy-int(S*0.32), cx+int(S*0.28), cy-int(S*0.06)], fill=(30,30,30))

    # eBay logo
    if FONT_PATH:
        fs = S//10
        font = ImageFont.truetype(FONT_PATH, fs)
        letters = [('e',(229,50,56)), ('b',(0,100,210)), ('a',(245,175,2)), ('y',(134,184,23))]
        widths = [font.getbbox(l)[2] - font.getbbox(l)[0] for l,_ in letters]
        x = cx - sum(widths)//2
        ey = cy - int(S*0.22)
        for i, (letter, col) in enumerate(letters):
            bbox = font.getbbox(letter)
            d.text((x, ey), letter, fill=col, font=font)
            x += widths[i]

    # Seller + score
    seller_text = f"{data['seller']} ({data['score']:,}★)".replace(',', '.')
    text_centered(d, S//22, cx, cy - int(S*0.09), seller_text, LG)

    # Percent
    text_centered(d, S//7, cx, cy + int(S*0.02), f"{data['percent']}%", W)

    # Stars
    stars = '★' * data['stars'] + '☆' * (5 - data['stars'])
    text_centered(d, S//14, cx, cy + int(S*0.14), stars, GL)

    # FEEDBACK label
    if FONT_PATH:
        fs = S//12
        font = ImageFont.truetype(FONT_PATH, fs)
        bbox = font.getbbox('FEEDBACK')
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        fy = cy + int(S*0.24)
        d.rounded_rectangle([cx-tw//2-20, fy-th//2-10, cx+tw//2+20, fy+th//2+10], radius=8, fill=(40,35,10))
        text_centered(d, fs, cx, fy, 'FEEDBACK', GL)

    # Bottom ribbon
    if FONT_PATH:
        fs = S//24
        font = ImageFont.truetype(FONT_PATH, fs)
        bbox = font.getbbox(ribbon_text)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        ry = cy + int(S*0.38)
        d.rounded_rectangle([cx-tw//2-30, ry-th//2-10, cx+tw//2+30, ry+th//2+10], radius=6, fill=GL)
        text_centered(d, fs, cx, ry, ribbon_text, DBG)

    # Downscale
    return img.resize((size, size), Image.LANCZOS)

# ============================================================
# ROUTES
# ============================================================
@app.route('/badge/<seller_id>')
def badge(seller_id):
    seller_id = re.sub(r'[^a-zA-Z0-9._-]', '', seller_id)
    locale = re.sub(r'[^a-z]', '', request.args.get('locale', 'fr'))
    size = min(max(int(request.args.get('size', 460)), 100), 1000)
    ribbon = request.args.get('ribbon', RIBBON_TEXTS.get(locale, RIBBON_TEXTS['fr']))

    if request.args.get('debug'):
        import json
        return Response(json.dumps(fetch_feedback(seller_id, locale), indent=2, ensure_ascii=False),
                       mimetype='application/json')

    data = fetch_feedback(seller_id, locale)
    img = draw_badge(data, size, ribbon)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png',
                   headers={'Cache-Control': f'public, max-age={CACHE_TTL}'})

@app.route('/')
def index():
    return '<h1>EuroFrance Badge</h1><p>Usage: /badge/eurofrance1</p><img src="/badge/eurofrance1" width="230">'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
