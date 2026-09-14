"""
K-2 Web Retrieval: Zamana Duyarlı Birincil Kanıt Getirim Modülü.

Statik korpusun yetersiz kaldığı veya güncel iddialarda,
iddia tarihine uygun birincil haber ve resmi kaynaklardan kanıt toplar.
Google News RSS ve DuckDuckGo motorlarını hibrit kullanır.
Teyit siteleri (teyit.org, malumatfurus.org vb.) filtrelenir;
yalnızca ham haber metinleri ve resmi bildiriler NLI katmanına sunulur.
"""

from __future__ import annotations

import os
import re
import logging
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4

import requests
import trafilatura

try:
    from googlenewsdecoder import gnewsdecoder
except ImportError:
    gnewsdecoder = None

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

logger = logging.getLogger("kizilelma.k2_web")

# Öncelikli ve güvenilir birincil kaynaklar (Beyaz Liste)
WHITELIST_DOMAINS = [
    "aa.com.tr",
    "dha.com.tr",
    "iha.com.tr",
    "anka.com.tr",
    "trthaber.com",
    "bbc.com/turkce",
    "bbc.co.uk/turkce",
    "dw.com/tr",
    "hurriyet.com.tr",
    "milliyet.com.tr",
    "haberturk.com",
    "cumhuriyet.com.tr",
    "ntv.com.tr",
    "sozcu.com.tr",
    "sabah.com.tr",
    "resmigazete.gov.tr",
    "tbmm.gov.tr",
    "tccb.gov.tr",
    "tuik.gov.tr",
    "saglik.gov.tr",
    "icisleri.gov.tr",
    "adalet.gov.tr",
    "meb.gov.tr",
]

# Doğrudan etiket sızıntısını önlemek için engellenen teyit siteleri (Kara Liste)
BLACKLIST_DOMAINS = [
    "teyit.org",
    "malumatfurus.org",
    "dogrulukpayi.com",
    "dogrula.org",
    "evrimagaci.org",
    "factcheck.org",
    "politifact.com",
    "snopes.com",
]

# Türkçe arama için gürültülü bağlaçlar
TURKISH_STOPWORDS = {
    "acaba", "ama", "ancak", "artik", "aslinda", "bana", "belki", "ben", "benden", 
    "beni", "benim", "beri", "biri", "birkac", "biz", "bizden", "bize", "bizi", 
    "bizim", "bu", "buna", "bunda", "bundan", "bunu", "bunun", "burada", "cok", 
    "cunku", "da", "daha", "dahi", "de", "defa", "diye", "eger", "en", "gibi", 
    "hem", "hep", "hepsi", "her", "hic", "icin", "ile", "ise", "kadar", "kez", 
    "ki", "kim", "mu", "mi", "mu", "mu", "nasil", "ne", "neden", "nerde", 
    "nerede", "nereye", "nicin", "o", "ona", "ondan", "onlar", "onlardan", 
    "onlari", "onlarin", "onu", "onun", "oysa", "oysaki", "pek", "sey", "siz", 
    "sizden", "size", "sizi", "sizin", "su", "suna", "sunda", "sundan", "sunu", 
    "tumu", "ve", "veya", "ya", "yani", "yoksa"
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class TemporalWebRetriever:
    """Zamana duyarlı birincil haber ve resmi kaynak arama modülü."""

    def __init__(
        self,
        request_timeout: int = 5,
        max_search_results: int = 5,
        max_chunks_per_doc: int = 3,
        min_chunk_length: int = 60,
        max_chunk_length: int = 600,
    ):
        self.timeout = request_timeout
        self.max_search_results = max_search_results
        self.max_chunks_per_doc = max_chunks_per_doc
        self.min_chunk_length = min_chunk_length
        self.max_chunk_length = max_chunk_length
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

    def extract_clean_query(self, claim_text: str) -> str:
        """Arama sorgusunu hazırlar: dolgu kalıplarını, noktalama ve gereksiz bağlaçları temizler."""
        if not claim_text:
            return ""

        text = claim_text
        # Sosyal medya ve teyit framing kalıplarını temizle
        meta_prefixes = [
            r'^(?:sosyal medyada|bir x hesab[ıi]|bir instagram hesab[ıi]|bir twitter hesab[ıi]|payla[şs][ıi]lan|videonun|foto[ğg]raf[ıi]n|iddian[ıi]n|iddias[ıi]|g[öo]r[üu]nt[üu]lerin|haberlerde yer alan)\s+',
            r'^(?:bir x kullan[ıi]c[ıi]s[ıi]|kullan[ıi]c[ıi]lar[ıi]n|baz[ıi] hesaplar[ıi]n)\s+'
        ]
        for p in meta_prefixes:
            text = re.sub(p, ' ', text, flags=re.IGNORECASE)

        meta_suffixes = [
            r'\s+(?:iddias[ıi]|iddia edildi|oldu[ğg]u iddia edildi|g[öo]sterdi[ğg]i|[öo]ne s[üu]r[üu]ld[üu]|belirtildi|a[çc][ıi]kland[ıi]|payla[şs][ıi]ld[ıi])$',
            r'\s+(?:yans[ıi]tt[ıi][ğg][ıi]|anla[şs][ıi]ld[ıi][ğg][ıi])$'
        ]
        for s in meta_suffixes:
            text = re.sub(s, ' ', text, flags=re.IGNORECASE)

        clean = re.sub(r'[^\w\s\d]', ' ', text, flags=re.UNICODE)
        words = clean.strip().split()
        filtered = [w for w in words if w.lower() not in TURKISH_STOPWORDS and len(w) > 1]

        if not filtered:
            return " ".join(words[:4])

        # Google News RSS için ideal uzunluk 3 ila 5 kelimedir.
        return " ".join(filtered[:5])

    def extract_fallback_query(self, claim_text: str) -> str:
        """Genişletilmiş yedek arama sorgusu: En karakteristik 2-3 terimi seçer."""
        clean_q = self.extract_clean_query(claim_text)
        words = clean_q.split()
        if len(words) <= 3:
            return clean_q
        return " ".join(words[:3])

    def is_blacklisted(self, url: str) -> bool:
        """URL teyit sitesi veya yasaklı domain içeriyor mu?"""
        lowered = url.lower()
        for b_dom in BLACKLIST_DOMAINS:
            if b_dom in lowered:
                return True
        return False

    def get_domain_authority(self, url: str) -> float:
        """Kaynak alan adına göre temel güvenilirlik puanı belirler."""
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower().replace("www.", "")
        
        if any(netloc.endswith(gov) for gov in [".gov.tr", ".edu.tr"]):
            return 0.98
            
        for w_dom in WHITELIST_DOMAINS:
            if w_dom in netloc or netloc in w_dom:
                return 0.92
                
        return 0.80

    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Tarih dizgisini UTC datetime nesnesine dönüştürür."""
        if not date_str or not date_parser:
            return None
        try:
            dt = date_parser.parse(str(date_str))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    def search_google_news_rss(self, query: str, claim_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Google News RSS akışından haberleri çeker ve decode eder."""
        results = []
        try:
            # Tarih kısıtı varsa query'e ekle (t+7 gün kuralı)
            search_query = query
            if claim_date:
                c_dt = self.parse_date(claim_date)
                if c_dt:
                    start_date = c_dt - timedelta(days=2) # 2 gün öncesinden
                    end_date = c_dt + timedelta(days=7) # 7 gün sonrasına kadar
                    search_query += f" after:{start_date.strftime('%Y-%m-%d')} before:{end_date.strftime('%Y-%m-%d')}"
                    
            encoded_q = urllib.parse.quote(search_query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=tr&gl=TR&ceid=TR:tr"
            resp = self.session.get(rss_url, timeout=self.timeout)
            if resp.status_code != 200:
                return []

            root = ET.fromstring(resp.content)
            items = root.findall(".//item")

            for item in items[:self.max_search_results * 2]:
                title = item.find("title").text if item.find("title") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                raw_link = item.find("link").text if item.find("link") is not None else ""
                source = item.find("source").text if item.find("source") is not None else ""

                if not raw_link:
                    continue

                # URL decode et
                final_url = raw_link
                if gnewsdecoder:
                    try:
                        decoded = gnewsdecoder(raw_link)
                        if decoded.get("status") and decoded.get("decoded_url"):
                            final_url = decoded["decoded_url"]
                    except Exception:
                        pass

                if self.is_blacklisted(final_url):
                    continue

                results.append({
                    "url": final_url,
                    "title": title,
                    "snippet": title,
                    "date": pub_date,
                    "source": source or urllib.parse.urlparse(final_url).netloc
                })

                if len(results) >= self.max_search_results:
                    break

        except Exception as e:
            logger.debug(f"Google News RSS search failed: {e}")

        return results

    def search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """DuckDuckGo üzerinden haber/web araması yapar (yedek)."""
        if DDGS is None:
            return []
        results = []
        try:
            with DDGS() as ddgs:
                try:
                    news_res = list(ddgs.news(query, max_results=self.max_search_results))
                    for r in news_res:
                        url = r.get("url", "")
                        if not url or self.is_blacklisted(url):
                            continue
                        results.append({
                            "url": url,
                            "title": r.get("title", ""),
                            "snippet": r.get("body", ""),
                            "date": r.get("date"),
                            "source": r.get("source", "")
                        })
                except Exception:
                    pass
        except Exception:
            pass
        return results

    def search_news(
        self, query: str, claim_date: Optional[str] = None, fallback_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Hibrit haber araması: Önce Google News RSS, yetersizse fallback sorgusu veya DuckDuckGo."""
        if not query:
            return []

        search_results = self.search_google_news_rss(query, claim_date)
        if len(search_results) < 2 and fallback_query and fallback_query != query:
            fb_hits = self.search_google_news_rss(fallback_query, claim_date)
            for hit in fb_hits:
                if not any(x["url"] == hit["url"] for x in search_results):
                    search_results.append(hit)

        if len(search_results) < 2:
            ddg_hits = self.search_duckduckgo(query)
            for hit in ddg_hits:
                if not any(x["url"] == hit["url"] for x in search_results):
                    search_results.append(hit)

        if claim_date:
            c_dt = self.parse_date(claim_date)
            if c_dt:
                cutoff_future = c_dt + timedelta(days=7)
                filtered = []
                for r in search_results:
                    art_dt = self.parse_date(r.get("date"))
                    if art_dt and art_dt > cutoff_future:
                        continue
                    filtered.append(r)
                if filtered:
                    search_results = filtered

        return search_results[:self.max_search_results]

    def fetch_and_extract_content(self, url: str) -> Optional[str]:
        """Verilen URL'den temiz metin çıkarır (trafilatura ile)."""
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200 and resp.text:
                extracted = trafilatura.extract(
                    resp.text,
                    include_links=False,
                    include_comments=False,
                    no_fallback=False
                )
                if extracted and len(extracted.strip()) > self.min_chunk_length:
                    return extracted.strip()
        except Exception as e:
            logger.debug(f"Content extraction failed for {url}: {e}")
        return None

    def chunk_text(self, text: str) -> List[str]:
        """Metni mantıklı paragraflara / kanıt parçalarına böler."""
        if not text:
            return []
            
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        chunks: List[str] = []
        
        current_chunk = []
        current_len = 0
        
        for p in paragraphs:
            if len(p) < 30:
                continue
            p_len = len(p)
            if current_len + p_len < self.max_chunk_length:
                current_chunk.append(p)
                current_len += p_len + 1
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [p]
                current_len = p_len
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return [c for c in chunks if len(c) >= self.min_chunk_length][:self.max_chunks_per_doc]

    def search_evidence(
        self, claim_text: str, claim_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        İddia için web üzerinden birincil kanıt parçaları toplar.
        
        Returns:
            engine.py'deki 'candidates' sözlük yapısıyla %100 uyumlu liste.
        """
        query = self.extract_clean_query(claim_text)
        fallback_query = self.extract_fallback_query(claim_text)
        if not query:
            return []

        search_hits = self.search_news(query, claim_date=claim_date, fallback_query=fallback_query)
        if not search_hits:
            return []

        candidates: List[Dict[str, Any]] = []

        for hit in search_hits:
            url = hit["url"]
            publisher = hit.get("source") or urllib.parse.urlparse(url).netloc
            published_at = hit.get("date") or ""
            authority = self.get_domain_authority(url)

            content = self.fetch_and_extract_content(url)
            
            chunks = []
            if content:
                chunks = self.chunk_text(content)
            
            if not chunks and hit.get("snippet") and len(hit["snippet"]) >= self.min_chunk_length:
                chunks = [hit["snippet"]]

            for i, chunk in enumerate(chunks):
                doc_uuid = uuid4().hex[:8]
                candidates.append({
                    "id": f"web_{doc_uuid}_{i}",
                    "text": chunk,
                    "label": 1,  # Birincil haber/resmi kaynak doğru olgu kabul edilir
                    "sim": 0.85,
                    "rerank_score": 1.5,
                    "sig_rerank": 0.82,
                    "authority": authority,
                    "source_url": url,
                    "publisher": publisher,
                    "published_at": published_at,
                    "evidence_id": f"web_{doc_uuid}",
                    "label_provenance": "temporal_web_retrieval",
                    "ingested_at": datetime.now(timezone.utc).isoformat()
                })

        return candidates
