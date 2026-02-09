"""Metin ön işleme: HTML, boşluk, Türkçe stop words, kelime çapası. Liste proje içinde."""
from __future__ import annotations

import re
from typing import Optional

# Türkçe stop words (genişletilebilir)
TURKISH_STOP_WORDS = frozenset({
    "acaba", "altı", "altmış", "ama", "ancak", "arada", "aslında", "aslında", "ayrıca",
    "bana", "bazı", "bazıları", "belki", "ben", "benden", "beni", "benim", "beri",
    "beş", "bile", "bin", "bir", "biri", "birine", "birini", "birisi", "birkaç",
    "birkez", "birşey", "birşeyi", "birçok", "biz", "bize", "bizi", "bizim", "bu",
    "buna", "bunda", "bundan", "bunlar", "bunları", "bunların", "bunu", "bunun",
    "burada", "böyle", "böylece", "bütün", "da", "daha", "dahi", "de", "defa",
    "değil", "diğer", "diye", "dokuz", "dolayı", "dolayısıyla", "dört", "eden",
    "ederek", "edilecek", "ediliyor", "edilmesi", "ediyor", "elli", "en", "etmesi",
    "etti", "ettiği", "ettiğini", "eğer", "gibi", "göre", "halbuki", "halen",
    "hangi", "hani", "hatta", "hem", "henüz", "hep", "hepsi", "her", "herhangi",
    "herkes", "hiç", "hiçbir", "için", "içinde", "işte", "ise", "ilk", "ilk",
    "itibaren", "itibariyle", "kadar", "kanımca", "karşı", "karşın", "katrilyon",
    "kendi", "kendilerine", "kendini", "kendisi", "kendisine", "kendisini", "kez",
    "ki", "kim", "kimden", "kime", "kimi", "kimse", "kırk", "mı", "mı", "mi",
    "mu", "mü", "milyar", "milyon", "mu", "mü", "mı", "nasıl", "ne", "neden",
    "nedenle", "nerde", "nereye", "niye", "niçin", "o", "olan", "olarak", "oldu",
    "olduğu", "olduğunu", "olduklarını", "olmadı", "olmadığı", "olmak", "olması",
    "olmayan", "olmaz", "olsa", "olsun", "olup", "olur", "olursa", "oluyor",
    "on", "ona", "ondan", "onlar", "onlara", "onlardan", "onları", "onların",
    "onu", "onun", "otuz", "oysa", "önce", "önce", "ötürü", "öyle", "pek",
    "rağmen", "sadece", "sanki", "sekiz", "seksen", "sen", "sana", "saniye",
    "seksen", "senin", "siz", "size", "sizi", "sizin", "sonra", "sonradan",
    "sonunda", "şayet", "şey", "şeyden", "şeyi", "şeyler", "şu", "şuna", "şunda",
    "şunları", "şunu", "tarafından", "trilyon", "tüm", "üzere", "var", "vardı",
    "ve", "veya", "ya", "yani", "yapacak", "yapılan", "yapılması", "yapıyor",
    "yapıyor", "yedi", "yerine", "yetmiş", "yine", "yirmi", "yok", "zaten", "zaten",
})


def strip_html(text: str) -> str:
    """HTML etiketlerini kaldırır."""
    if not text or not isinstance(text, str):
        return ""
    return re.sub(r"<[^>]+>", " ", text)


def normalize_whitespace(text: str) -> str:
    """Birden fazla boşluğu tek boşluğa indirir, baş/son trim."""
    if not text or not isinstance(text, str):
        return ""
    return " ".join(str(text).split())


def remove_stopwords(text: str, stop_words: Optional[frozenset] = None) -> str:
    """Türkçe stop word'leri çıkarır; kelimeler boşlukla ayrılmış döner."""
    if not text or not isinstance(text, str):
        return ""
    stop = stop_words or TURKISH_STOP_WORDS
    words = text.split()
    return " ".join(w for w in words if w.lower() not in stop)


def kelime_capasi(text: str, stop_words: Optional[frozenset] = None) -> list:
    """Anlam taşıyan sözcükleri (stopword dışı) listeler."""
    if not text or not isinstance(text, str):
        return []
    stop = stop_words or TURKISH_STOP_WORDS
    words = re.findall(r"\b[\wğüşıöçĞÜŞİÖÇ]+\b", text)
    return [w for w in words if w.lower() not in stop]


def preprocess(
    text: str,
    *,
    strip_html_tags: bool = True,
    normalize_ws: bool = True,
    remove_stopwords_flag: bool = False,
    stop_words: Optional[frozenset] = None,
) -> str:
    """HTML + boşluk + isteğe bağlı stopword."""
    if not text or not isinstance(text, str):
        return ""
    s = text
    if strip_html_tags:
        s = strip_html(s)
    if normalize_ws:
        s = normalize_whitespace(s)
    if remove_stopwords_flag:
        s = remove_stopwords(s, stop_words)
    return s.strip()
