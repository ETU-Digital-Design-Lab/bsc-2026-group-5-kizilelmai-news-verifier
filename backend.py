"""KızılelmAI Backend – Veri seti tabanlı yalan haber doğrulama.

v2 vizyonu: sadece benzerlik değil, hibrit bir mantık motoru:
- Bi-Encoder ile hızlı aday çekme
- Anahtar kelime / fiil kökü filtreleri ile halüsinasyon önleme
- (Opsiyonel) Cross-Encoder NLI katmanı ile mantıksal doğrulama
"""
import os
import warnings
from flask import Flask, jsonify, make_response, request
from flask_cors import CORS
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from preprocess import preprocess, kelime_capasi

warnings.filterwarnings("ignore")

# --- Anlamsal fiil grupları (v2.0 mantığı) ---
SEMANTIC_VERB_GROUPS = {
    "communication": {
        "açıkla",
        "duyur",
        "belirt",
        "söyle",
        "ifade",
        "aktar",
        "bildir",
        "konuş",
        "yaz",
        "iddia",
        "paylaş",
        "değin",
    },
    "action": {
        "yap",
        "et",
        "gerçekleş",
        "başla",
        "uygula",
        "düzenle",
        "git",
        "katıl",
        "imza",
    },
    "movement": {
        "git",
        "gel",
        "ulaş",
        "var",
        "kalk",
        "in",
        "yürü",
        "koş",
        "seyahat",
    },
    "negative": {
        "red",
        "yalanla",
        "tekzip",
        "kabul etme",
        "yok",
        "değil",
    },
    "event": {
        "ol",
        "meydana",
        "yaşan",
        "gerçekleş",
        "patla",
        "çök",
    },
}

# --- Konfigürasyon (ortam değişkenleri) ---
CSV_PATH = os.environ.get("KIZILELMAI_CSV_PATH", "egitim_verisi_final.csv")
EMBEDDING_MODEL = os.environ.get(
    "KIZILELMAI_EMBEDDING_MODEL",
    "dbmdz/bert-base-turkish-cased",
)

HOST = os.environ.get("KIZILELMAI_HOST", "127.0.0.1")
PORT = int(os.environ.get("KIZILELMAI_PORT", "5000"))
MAX_QUERY_LENGTH = int(os.environ.get("KIZILELMAI_MAX_QUERY_LENGTH", "2000"))
USE_PREPROCESS = os.environ.get("KIZILELMAI_USE_PREPROCESS", "1") == "1"
REMOVE_STOPWORDS = os.environ.get("KIZILELMAI_REMOVE_STOPWORDS", "0") == "1"

# Eşikler (v2.0 "anayasa"):
# - SIMILARITY_THRESHOLD altı: bulunamadı
# - HIGH_SIMILARITY_BYPASS üstü: typo olsa bile filtreleme yok
SIMILARITY_THRESHOLD = float(os.environ.get("KIZILELMAI_SIMILARITY_THRESHOLD", "0.81"))
HIGH_SIMILARITY_BYPASS = float(os.environ.get("KIZILELMAI_HIGH_SIMILARITY_BYPASS", "0.89"))
# Production'da örn: CORS_ORIGINS=https://app.example.com
CORS_ORIGINS_RAW = os.environ.get("KIZILELMAI_CORS_ORIGINS", "*").strip()
CORS_ORIGINS = (
    [x.strip() for x in CORS_ORIGINS_RAW.split(",") if x.strip()]
    if CORS_ORIGINS_RAW != "*"
    else "*"
)

app = Flask(__name__)
CORS(
    app,
    resources={
        r"/*": {
            "origins": CORS_ORIGINS,
            "allow_headers": ["Content-Type"],
        }
    },
    supports_credentials=(CORS_ORIGINS_RAW != "*"),
)

# --- Veri ve model (başlangıçta bir kez) ---
if not os.path.isfile(CSV_PATH):
    raise FileNotFoundError(f"Veri dosyası bulunamadı: {CSV_PATH}. Önce 01_veri_hazirla.py çalıştırılmalı.")

df = pd.read_csv(CSV_PATH)


def _prepare_text(s: str) -> str:
    """Metni ön işleme ile hazırlar (HTML, boşluk, isteğe bağlı stopword)."""
    if not isinstance(s, str):
        return ""
    if not USE_PREPROCESS:
        return s.strip()
    return preprocess(
        s,
        strip_html_tags=True,
        normalize_ws=True,
        remove_stopwords_flag=REMOVE_STOPWORDS,
    )


raw_texts = df["text"].tolist()
texts = [_prepare_text(t) for t in raw_texts]
print(f"Embedding modeli yükleniyor: {EMBEDDING_MODEL} ... (ilk seferde indirme sürebilir)")
model = SentenceTransformer(EMBEDDING_MODEL)
print("BERTurk (dbmdz) model hazır!")
text_embeddings = model.encode(texts, show_progress_bar=True)
print(f"{len(texts)} cümle embedding'e çevrildi. Ön işleme: {'açık' if USE_PREPROCESS else 'kapalı'} (stopword: {'açık' if REMOVE_STOPWORDS else 'kapalı'}). Sistem hazır!")


def _detect_verb_group(text: str) -> tuple[str | None, str | None]:
    """Metin içinden anlamsal fiil grubunu bul.

    Basit yaklaşım: kelime köklerinde SEMANTIC_VERB_GROUPS'taki kökleri arar,
    sondan başa doğru ilk eşleşmeyi döner.
    """
    try:
        words = [w.lower() for w in kelime_capasi(text)]
    except Exception:
        words = str(text).lower().split()
    for w in reversed(words):
        for group, roots in SEMANTIC_VERB_GROUPS.items():
            for root in roots:
                if root in w or w in root:
                    return group, root
    return None, None


def _check_semantic_verb_match(
    query_text: str, candidate_text: str
) -> tuple[bool, str | None, str | None, str | None, str | None]:
    """Sorgu ve aday cümledeki fiiller anlamsal olarak uyumlu mu?

    Kurallar:
    - Her iki cümlede de fiil grubu bulunursa ve grup aynaysa → MATCH
    - Fiil bulunamazsa (parse edilemezse) → MATCH (skora güven)
    - Farklı gruplar bulunursa → MISMATCH
    """
    q_group, q_verb = _detect_verb_group(query_text)
    c_group, c_verb = _detect_verb_group(candidate_text)
    if q_group is None or c_group is None:
        return True, q_verb, c_verb, q_group, c_group
    return q_group == c_group, q_verb, c_verb, q_group, c_group


def _build_response(label: int, candidate_text: str):
    """Label'e göre son kullanıcıya gösterilecek mesajı üret."""
    if label == 1:
        sonuc = f"✅ Evet, bu haber doğru.\nKaynak: {candidate_text}"
    else:
        sonuc = f"❌ Hayır, bu haber yanlış.\nDoğrusu: {candidate_text}"
    return jsonify({"result": sonuc})

@app.route("/api/veri")
def getir_veri():
    try:
        return jsonify(df.to_dict(orient="records"))
    except Exception as e:
        app.logger.error(f"CSV okunamadı: {e}")
        return make_response(jsonify({"error": "Veri okunamadı."}), 500)


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        resp = make_response()
        if CORS_ORIGINS == "*":
            resp.headers["Access-Control-Allow-Origin"] = "*"
        else:
            req_origin = request.headers.get("Origin", "")
            resp.headers["Access-Control-Allow-Origin"] = (
                req_origin if req_origin in CORS_ORIGINS else CORS_ORIGINS[0]
            )
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return resp

    # Input validasyonu
    if request.json is None:
        return make_response(
            jsonify({"error": "Geçersiz istek: JSON gövde gerekli."}), 400
        )
    data = request.json
    if not isinstance(data, dict):
        return make_response(
            jsonify({"error": "Geçersiz istek: Gövde nesne olmalı."}), 400
        )
    query = data.get("query")
    if query is None:
        return jsonify({"result": "Lütfen bir soru girin."})
    if not isinstance(query, str):
        return make_response(
            jsonify({"error": "Geçersiz istek: 'query' metin olmalı."}), 400
        )
    query = query.strip()
    if not query:
        return jsonify({"result": "Lütfen bir soru girin."})
    if len(query) > MAX_QUERY_LENGTH:
        return make_response(
            jsonify({
                "error": f"Soru en fazla {MAX_QUERY_LENGTH} karakter olabilir."
            }),
            400,
        )

    query_clean = _prepare_text(query)
    if not query_clean:
        return jsonify({"result": "Lütfen anlamlı bir soru girin."})

    # ADIM 1 – Retrieval: tek en iyi adayı bul
    query_embedding = model.encode([query_clean], show_progress_bar=False)
    similarities = cosine_similarity(query_embedding, text_embeddings)[0]
    best_idx = int(similarities.argmax())
    best_score = float(similarities[best_idx])

    if best_score < SIMILARITY_THRESHOLD:
        return jsonify({"result": "Bu konuda veri setinde bir bilgi bulunamadı."})

    rec = df.iloc[best_idx]
    candidate_text = str(rec["text"])
    label = int(rec["label"])

    # ADIM 2 – Yüksek Skor Bypass (Typo Gate)
    if best_score >= HIGH_SIMILARITY_BYPASS:
        print(
            f"DEBUG: Score={best_score:.4f}, QueryVerb=None, CandidateVerb=None, Match=True (bypass)"
        )
        return _build_response(label, candidate_text)

    # ADIM 3 – Fiil ve Anlam Kontrolü (Semantic Verb Gate)
    is_match, q_verb, c_verb, q_group, c_group = _check_semantic_verb_match(
        query, candidate_text
    )
    print(
        f"DEBUG: Score={best_score:.4f}, QueryVerb={q_verb}, CandidateVerb={c_verb}, "
        f"QueryGroup={q_group}, CandidateGroup={c_group}, Match={is_match}"
    )
    if not is_match:
        return jsonify({"result": "Bu konuda veri setinde bir bilgi bulunamadı."})

    # ADIM 4 – Cevap oluşturma
    return _build_response(label, candidate_text)


if __name__ == "__main__":
    app.run(debug=False, host=HOST, port=PORT)
