import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from newspaper import Article
import schedule
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
FILE_DIR = Path(__file__).parent
ROOT_DIR = FILE_DIR.parent.parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from src.ai_core.engine.engine import KizilelmaEngine
except ImportError:
    try:
        from ai_core.engine.engine import KizilelmaEngine
    except Exception as e:
        print(f"❌ Kritik Hata: Gerekli Kızılelma modülleri yüklenemedi: {e}")
        sys.exit(1)

# Configuration
SOURCES = [
    {"name": "TRT Haber", "url": "https://www.trthaber.com/"},
    {"name": "İletişim Başkanlığı", "url": "https://www.iletisim.gov.tr/turkce/"},
    {"name": "TBMM", "url": "https://www.tbmm.gov.tr/"},
    {"name": "DHA", "url": "https://www.dha.com.tr/"},
    {"name": "İHA", "url": "https://www.iha.com.tr/"}
]

DATA_DIR = os.path.join(ROOT_DIR, "data", "processed")
os.makedirs(DATA_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(DATA_DIR, "scraped_urls.txt")
MAX_ARTICLES_PER_RUN = 50

# Load history to prevent duplicates
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def save_to_history(url):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{url}\n")

def get_links(source_url):
    """Basic link extraction from homepage."""
    links = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(source_url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Basic validation for news links
            if href.startswith('/'):
                href = source_url.rstrip('/') + href
            if href.startswith('http') and source_url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0] in href:
                # Exclude obvious non-news links
                if not any(x in href.lower() for x in ['/iletisim', '/hakkimizda', '/kategori', '/video', '/foto']):
                    links.append(href)
    except Exception as e:
        print(f"⚠️ Link çekme hatası ({source_url}): {e}")
    
    # Remove duplicates but keep order
    return list(dict.fromkeys(links))

def scrape_and_inject():
    print("\n" + "="*50)
    print("[KizilelmAI] Otomatik Veri Toplayici Basladi")
    print(time.strftime("%Y-%m-%d %H:%M:%S"))
    print("="*50)
    
    history = load_history()
    engine = KizilelmaEngine(lazy_load=True)
    
    total_injected = 0
    
    for source in SOURCES:
        if total_injected >= MAX_ARTICLES_PER_RUN:
            break
            
        print(f"\n[+] Kaynak taraniyor: {source['name']}")
        links = get_links(source['url'])
        
        for link in links:
            if total_injected >= MAX_ARTICLES_PER_RUN:
                break
                
            if link in history:
                continue
                
            try:
                article = Article(link, language='tr')
                article.download()
                article.parse()
                
                text = article.text.strip()
                title = article.title.strip()
                
                if len(text) > 100: # Ignore very short texts
                    # Construct a solid text for KB with source name prefix
                    full_text = f"[Kaynak: {source['name']}] {title}. {text}"
                    # Keep it concise for RAG (e.g. first 1000 chars)
                    full_text = full_text[:1000] 
                    
                    # Inject knowledge directly as TRUE (1) with High Authority (0.95) since these are official sources
                    print(f"   [-] Yeni Haber: {title[:50]}...")
                    inserted = engine.inject_knowledge(
                        full_text, label=1, authority=0.95, source_url=link, publisher=source['name'],
                        published_at=article.publish_date.isoformat() if article.publish_date else None,
                        label_provenance="publisher_assumed_true_not_fact_checked",
                    )
                    if not inserted:
                        continue
                    
                    save_to_history(link)
                    history.add(link)
                    total_injected += 1
            except Exception as e:
                print(f"⚠️ Makale işleme/enjeksiyon hatası ({link[:50]}): {e}")
                
    print("\n" + "="*50)
    print(f"[OK] Islem Tamamlandi. Toplam asilanan yeni bilgi sayisi: {total_injected}")
    print("="*50)
    
    # Clean up memory
    del engine
    import gc
    gc.collect()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KizilelmAI Auto Scraper")
    parser.add_argument("--run-now", action="store_true", help="Zamanlamayi beklemeden hemen bir kez calistir.")
    args = parser.parse_args()
    
    if args.run_now:
        scrape_and_inject()
    else:
        print("[Bekleniyor] KizilelmAI Arka Plan Scraper Servisi Baslatildi (4 Saatte Bir Calisacak)")
        schedule.every(4).hours.do(scrape_and_inject)
        
        # İlk başlangıçta bir kez çalıştır
        scrape_and_inject()
        
        while True:
            schedule.run_pending()
            time.sleep(60)
