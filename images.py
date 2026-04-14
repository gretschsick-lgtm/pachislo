import io, re, time, requests
from PIL import Image
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
OUTPUT_DIR = Path("images")
OUTPUT_DIR.mkdir(exist_ok=True)

EVENT_SELECTORS = [".eventDetail__image img",".event-detail img",".p-event-detail__img img",".eventImage img","main article img",".content img","article img"]
OGP_ATTRS = [('meta[property="og:image"]',"content"),('meta[name="twitter:image"]',"content")]

def _download(url, min_w=200, min_h=150):
    if not url: return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        if img.size[0] >= min_w and img.size[1] >= min_h: return img
    except Exception as e:
        print(f"[images] DL失敗: {e}")
    return None

def _scrape_page(url, selectors):
    if not url: return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        candidates = []
        for sel in selectors:
            for el in soup.select(sel):
                src = el.get("src") or el.get("data-src") or ""
                if src and not src.startswith("data:"): candidates.append(urljoin(url, src))
        for sel, attr in OGP_ATTRS:
            el = soup.select_one(sel)
            if el and el.get(attr): candidates.append(el[attr])
        best, best_area = None, 0
        for src in candidates[:8]:
            img = _download(src)
            if img:
                area = img.size[0] * img.size[1]
                if area > best_area: best, best_area = img, area
            time.sleep(0.2)
        return best
    except Exception as e:
        print(f"[images] ページ取得失敗: {e}")
    return None

def _to_x_size(img):
    w, h = img.size
    r = w / h
    if r > 16/9:
        nw = int(h * 16/9)
        img = img.crop(((w-nw)//2, 0, (w+nw)//2, h))
    elif r < 16/9:
        nh = int(w * 9/16)
        img = img.crop((0, (h-nh)//2, w, (h+nh)//2))
    return img.resize((1200, 675), Image.LANCZOS)

def _save(img, prefix, name):
    img = _to_x_size(img)
    slug = re.sub(r"[^\w]", "_", name)[:20]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{prefix}_{slug}_{ts}.jpg"
    img.save(path, "JPEG", quality=90)
    print(f"[images] 保存: {path}")
    return str(path)

def get_event_image(event):
    img = _scrape_page(event.get("url",""), EVENT_SELECTORS)
    if img is None: return None
    return _save(img, "event", event.get("event_name","event"))

def get_raiten_image(raiten):
    img = _download(raiten.get("img_url",""))
    if img is None: img = _scrape_page(raiten.get("detail_url",""), EVENT_SELECTORS)
    if img is None: return None
    return _save(img, "raiten", raiten.get("talent_name","raiten"))
