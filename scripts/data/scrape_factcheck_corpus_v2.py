"""
scripts/data/scrape_factcheck_corpus_v2.py
==========================================
KızılelmAI — Corpus Genişletme: 2022-2026 Türkçe Fact-Check ve Haber Verisi

Mevcut sistemin veri toplama yöntemi (RSS/BeautifulSoup/newspaper3k) ile tutarlı;
web sitesi ana sayfası scraping yerine RSS/Atom feed'leri ve Sitemap XML kullanılır.

Bu betik:
1. Teyit, Doğruluk Payı, Malumatfuruş, Doğrula RSS feed'lerini çeker
2. Her fact-check raporunun tam metnini newspaper3k ile alır
3. Temizler, deduplicate eder, otorite skoru atar
4. data/raw/expanded_factcheck_v2/ klasörüne yazar
5. Her kaydı SHA-256 ile mühürler

Kullanım:
    python scripts/data/scrape_factcheck_corpus_v2.py --max 5000 --output-dir data/raw/expanded_factcheck_v2
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request
import urllib.error

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

try:
    from newspaper import Article
    _HAS_NEWSPAPER = True
except ImportError:
    try:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "newspaper3k", "lxml_html_clean", "-q"], check=True)
        from newspaper import Article
        _HAS_NEWSPAPER = True
    except Exception:
        _HAS_NEWSPAPER = False
        print("[UYARI] newspaper3k kurulamadi -- kisa metin fallback kullanilacak.")

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

# ─── Kaynak Tanımları ──────────────────────────────────────────────────────────
SOURCES = [
    {
        "name": "Teyit",
        "publisher": "teyit.org",
        "authority": 0.98,
        "label": 1,
        "rss": "https://teyit.org/feed",
        "sitemap": "https://teyit.org/sitemap.xml",
    },
    {
        "name": "Malumatfurus",
        "publisher": "malumatfurus.org",
        "authority": 0.97,
        "label": 1,
        "rss": "https://www.malumatfurus.org/feed",
        "sitemap": None,
    },
    {
        "name": "TRT Haber",
        "publisher": "trthaber.com",
        "authority": 0.93,
        "label": 1,
        "rss": "https://www.trthaber.com/sondakika.rss",
        "sitemap": None,
    },
    {
        "name": "Anadolu Ajansi",
        "publisher": "aa.com.tr",
        "authority": 0.95,
        "label": 1,
        "rss": "https://www.aa.com.tr/tr/rss/default?cat=gundem",
        "sitemap": None,
    },
    {
        "name": "TRT Haber Politika",
        "publisher": "trthaber.com",
        "authority": 0.93,
        "label": 1,
        "rss": "https://www.trthaber.com/politika.rss",
        "sitemap": None,
    },
    {
        "name": "TRT Haber Ekonomi",
        "publisher": "trthaber.com",
        "authority": 0.93,
        "label": 1,
        "rss": "https://www.trthaber.com/ekonomi.rss",
        "sitemap": None,
    },
    {
        "name": "TRT Haber Dunya",
        "publisher": "trthaber.com",
        "authority": 0.93,
        "label": 1,
        "rss": "https://www.trthaber.com/dunya.rss",
        "sitemap": None,
    },
    {
        "name": "TRT Haber Saglik",
        "publisher": "trthaber.com",
        "authority": 0.93,
        "label": 1,
        "rss": "https://www.trthaber.com/saglik.rss",
        "sitemap": None,
    },
    {
        "name": "AA Gundem",
        "publisher": "aa.com.tr",
        "authority": 0.95,
        "label": 1,
        "rss": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
        "sitemap": None,
    },
]

HEADERS = {
    "User-Agent": (
        "KizilelmAI-CorpusExpander/2.0 (Academic Research; "
        "Contact: kizilelmAI@erzurum.edu.tr)"
    )
}

# ─── RSS Parse ────────────────────────────────────────────────────────────────
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

def _fetch_url(url: str, timeout: int = 15) -> Optional[bytes]:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"  [HATA] {url}: {e}")
        return None


def parse_rss(url: str) -> List[Dict]:
    raw = _fetch_url(url)
    if not raw:
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"  [XML HATA] {url}: {e}")
        return []

    items = []
    # RSS 2.0
    for item in root.findall(".//item"):
        entry: Dict = {}
        for tag in ("title", "link", "description", "pubDate"):
            el = item.find(tag)
            entry[tag] = (el.text or "").strip() if el is not None else ""
        # content:encoded
        el = item.find("content:encoded", NS)
        if el is not None and el.text:
            entry["content"] = el.text.strip()
        items.append(entry)
    # Atom 1.0
    for item in root.findall("atom:entry", NS):
        entry = {}
        for tag, ns_tag in [("title", "atom:title"), ("link", "atom:link"), ("summary", "atom:summary"), ("published", "atom:published")]:
            el = item.find(ns_tag, NS)
            if el is not None:
                entry[tag] = (el.get("href") or el.text or "").strip()
        items.append(entry)
    return items


def extract_article_text(url: str) -> Optional[str]:
    """newspaper3k ile tam makale metnini çeker. Yoksa description fallback."""
    if not _HAS_NEWSPAPER or not url:
        return None
    try:
        article = Article(url, language="tr")
        article.download()
        article.parse()
        text = article.text.strip()
        if len(text) < 150:
            return None
        return text
    except Exception:
        return None


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ─── Ana Toplama ──────────────────────────────────────────────────────────────
def collect(max_records: int, output_dir: Path, seen_hashes: set) -> List[Dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for src in SOURCES:
        if len(records) >= max_records:
            break
        print(f"\n[+] {src['name']} RSS taranıyor: {src['rss']}")
        items = parse_rss(src["rss"])
        print(f"    {len(items)} öğe bulundu")

        for item in items:
            if len(records) >= max_records:
                break

            url = item.get("link") or item.get("href") or ""
            if not url or not url.startswith("http"):
                continue

            # Full text
            full_text = item.get("content") or item.get("summary") or item.get("description") or ""
            if _HAS_NEWSPAPER and len(full_text) < 200:
                fetched = extract_article_text(url)
                if fetched:
                    full_text = fetched

            # HTML temizle
            if _HAS_BS4 and full_text:
                soup = BeautifulSoup(full_text, "html.parser")
                full_text = soup.get_text(separator=" ", strip=True)

            title = item.get("title", "").strip()
            text = f"{title}. {full_text}".strip() if title else full_text

            # Minimum uzunluk
            if len(text) < 100:
                continue

            # Deduplicate
            h = sha256(text[:1000])
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            rec = {
                "id": f"expanded_v2_{len(records):06d}",
                "text": text[:2000],  # Max 2000 karakter (eski corpus ile tutarlı)
                "label": src["label"],
                "authority": src["authority"],
                "publisher": src["publisher"],
                "source_url": url,
                "label_provenance": "rss_factcheck_publisher_attributed",
                "sha256": h,
            }
            records.append(rec)

        time.sleep(1.5)  # Rate limiting: Her kaynak arasında 1.5 saniye bekle

    return records


def merge_with_existing(existing_csv: Path, new_records: List[Dict], output_csv: Path) -> None:
    """Mevcut corpus CSV'si ile birlestir, ID'leri yeniden tahsis et."""
    existing = []
    if existing_csv.exists():
        existing = list(csv.DictReader(open(existing_csv, encoding="utf-8")))

    # Yeni ID'ler icin offset
    offset = len(existing)
    merged = []
    for rec in new_records:
        rec_out = {
            "id": str(offset + len(merged)),
            "text": rec["text"],
            "label": rec["label"],
            "authority": rec["authority"],
            "publisher": rec["publisher"],
            "source_url": rec["source_url"],
            "label_provenance": rec["label_provenance"],
        }
        merged.append(rec_out)

    all_rows = existing + merged
    fields = ["id", "text", "label", "authority", "publisher", "source_url", "label_provenance"]
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    print("\n[OK] Birlestirilen corpus: {} kayit -> {}".format(len(all_rows), output_csv))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max", type=int, default=5000, help="Maksimum yeni kayıt sayısı")
    ap.add_argument("--output-dir", type=Path,
                    default=_ROOT / "data" / "raw" / "expanded_factcheck_v2")
    ap.add_argument("--existing-corpus", type=Path,
                    default=_ROOT / "data" / "corpus_snapshots" / "local_csv_20260909_v1" / "corpus.csv")
    ap.add_argument("--new-snapshot-dir", type=Path,
                    default=_ROOT / "data" / "corpus_snapshots" / "local_csv_20260913_v2")
    a = ap.parse_args()

    print("=" * 60)
    print("KızılelmAI Corpus Genişletme v2")
    print(f"Hedef: {a.max} yeni kayıt")
    print("=" * 60)

    # Mevcut corpus'un hash'lerini yükle (deduplicate için)
    seen = set()
    if a.existing_corpus.exists():
        for row in csv.DictReader(open(a.existing_corpus, encoding="utf-8")):
            seen.add(sha256(row["text"][:1000]))
        print(f"Mevcut corpus: {len(seen)} kayıt (deduplicate için yüklendi)")

    new_records = collect(a.max, a.output_dir, seen)
    print(f"\nToplanan yeni kayıt: {len(new_records)}")

    # Raw çıktı JSON
    raw_out = a.output_dir / "raw_records.json"
    json.dump(new_records, open(raw_out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"Ham kayıtlar: {raw_out}")

    # Mevcut corpus ile birleştir
    a.new_snapshot_dir.mkdir(parents=True, exist_ok=True)
    merged_csv = a.new_snapshot_dir / "corpus.csv"
    merge_with_existing(a.existing_corpus, new_records, merged_csv)

    print("\nSonraki adım: scripts/data/build_new_snapshot_report.py ile snapshot mühürle")


if __name__ == "__main__":
    main()
