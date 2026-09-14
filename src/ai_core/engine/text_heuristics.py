"""
Text Heuristics & Analysis Modülü.

KızılelmAI için Türkçe metin normalizasyonu, anahtar kelime/çapa kontrolü,
semantik ve leksikal fark analizi, zaman ve sayı çelişkisi tespiti ve olumsuzluk analizleri.
"""

from __future__ import annotations

import re
import numpy as np


def turkish_lower(text):
    """Türkçe İ/ı karakter dönüşümünü koruyarak küçük harfe çevirir."""
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return text.replace('İ', 'i').replace('I', 'ı').lower()


def to_ascii_tr(text):
    """Türkçe özel karakterleri ASCII karşılıklarına dönüştürür (encoding güvenliği için)."""
    if not text:
        return ""
    tr_map = str.maketrans(
        'çÇğĞıIİöÖşŞüÜâÂêÊîÎûÛ',
        'cCgGiIioosSuUaAeEiIuU'
    )
    return text.translate(tr_map).lower()


def split_numbers_letters(text):
    """Bitişik yazılmış sayı ve harfleri ayırır (örn: 25saatte -> 25 saatte)."""
    if not text:
        return ""
    text = re.sub(r'(\d+)([^\d\s\W]+)', r'\1 \2', text)
    text = re.sub(r'([^\d\s\W]+)(\d+)', r'\1 \2', text)
    return text


class TextAnalysisMixin:
    """KizilelmaEngine için metin analizi, fark tespiti ve normalizasyon yetenekleri."""

    def temizle_ve_normallestir(self, query):
        q = turkish_lower(query)
        q = re.sub(r'[^\w\s]', '', q)
        q = re.sub(r'\s+(mi|mı|mu|mü)$', '', q)
        return q.strip()

    def intent_analyzer(self, query):
        """Kullanıcın niyetini belirler: Selamlaşma mı, Proje Tanıtımı mı yoksa İddia mı?"""
        query_norm = turkish_lower(query)
        query_ascii = to_ascii_tr(query)

        kizil_variants = ["kızılelma", "kizilelma", "kizilelmA", "kzlelma"]
        has_kizil = any(v in query_norm for v in kizil_variants) or "kizilelma" in query_ascii
        if has_kizil:
            about_keywords = {"nedir", "ne", "kim", "amac", "gelistir", "yapan", "yapmistir", "kimdir", "hakkinda", "hakkında", "anlat", "tanitim"}
            tokens_ascii = re.findall(r'\b\w+\b', query_ascii)
            tokens_norm = re.findall(r'\b\w+\b', query_norm)
            all_tokens = set(tokens_ascii) | set(tokens_norm)
            if any(token in about_keywords for token in all_tokens):
                return "ABOUT"

        greetings_list = self.kb.get("greetings", [])
        tokens_norm = query_norm.split()
        for token in tokens_norm:
            if token in greetings_list:
                return "GREETING"
        return "CLAIM"

    def query_expander(self, query):
        """Sözlük tabanlı sorgu genişletme (Örn: Maraş -> Kahramanmaraş)."""
        expanded_terms = []
        tokens = turkish_lower(query).split()
        
        for token in tokens:
            expanded_terms.append(token)
            synonyms_dict = self.kb.get("synonyms", {})
            if isinstance(synonyms_dict, dict) and token in synonyms_dict:
                syns = synonyms_dict.get(token, [])
                if syns:
                    expanded_terms.extend(syns)
        
        return " ".join(list(dict.fromkeys(expanded_terms)))

    def kelime_capasi_kontrolu(self, query, source, sim_score, sig_rerank=0.0):
        def get_keywords(text, is_query=False):
            words = re.findall(r'\w+', turkish_lower(text))
            ignored = self.STOP_WORDS
            if is_query:
                ignored = ignored.union(self.SKEPTIC_KEYWORDS)
            return set([w for w in words if w not in ignored and len(w) > 2])

        if sim_score > self.SAFE_SIMILARITY_ZONE or sig_rerank > 0.70:
            return True, []

        q_keys = get_keywords(query, is_query=True)
        s_keys = get_keywords(source)
        if not q_keys:
            return True, [] 

        required_matches = 1
        if len(q_keys) >= 3:
            required_matches = max(2, int(len(q_keys) * 0.35))

        matches = []
        for q_word in q_keys:
            for s_word in s_keys:
                if q_word in s_word or s_word in q_word:
                    matches.append(q_word)
                    break

        if len(matches) >= required_matches:
            return True, []
        else:
            missing_words = list(q_keys - set(matches))
            if not missing_words:
                missing_words = list(q_keys)
            return False, missing_words

    def find_matching_source_number(self, q_num, user_query, db_source, s_nums):
        """Kullanıcı sorgusundaki hatalı sayının kaynaktaki hangi sayı ile çeliştiğini bağlam penceresiyle bulur."""
        q_tokens = re.findall(r'\b\w+\b', turkish_lower(user_query))
        try:
            q_idx = q_tokens.index(q_num)
            start = max(0, q_idx - 3)
            end = min(len(q_tokens), q_idx + 4)
            q_context = set(q_tokens[start:q_idx] + q_tokens[q_idx+1:end])
        except ValueError:
            q_context = set()

        best_s_num = None
        max_overlap = -1
        
        s_tokens = re.findall(r'\b\w+\b', turkish_lower(db_source))
        
        for s_num in s_nums:
            s_indices = [i for i, x in enumerate(s_tokens) if x == str(s_num)]
            for s_idx in s_indices:
                start_s = max(0, s_idx - 3)
                end_s = min(len(s_tokens), s_idx + 4)
                s_context = set(s_tokens[start_s:s_idx] + s_tokens[s_idx+1:end_s])
                
                s_context_clean = s_context - self.STOP_WORDS
                q_context_clean = q_context - self.STOP_WORDS
                
                overlap = len(q_context_clean.intersection(s_context_clean))
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_s_num = s_num
        return best_s_num

    def get_original_case(self, word, text):
        """Metin içerisindeki kelimenin orijinal cased (büyük/küçük harf) halini bulur."""
        pattern = r'\b' + re.escape(word) + r'\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0]
        return word

    def find_best_matching_word(self, q_word, user_query, db_source, s_words):
        """
        Sorgudaki bir kelimenin kaynaktaki hangi kelime ile çeliştiğini 
        hem semantik benzerlik, hem bağlam örtüşmesi, hem de göreceli pozisyon kullanarak bulur.
        """
        def share_stem_helper(w1, w2):
            w1_clean = re.sub(r'[^a-zA-ZçÇğĞıİöÖşŞüÜ]', '', w1).lower()
            w2_clean = re.sub(r'[^a-zA-ZçÇğĞıİöÖşŞüÜ]', '', w2).lower()
            min_len = min(len(w1_clean), len(w2_clean))
            if min_len < 3:
                return w1_clean == w2_clean
            common_len = 0
            for c1, c2 in zip(w1_clean, w2_clean):
                if c1 == c2:
                    common_len += 1
                else:
                    break
            required_len = min_len - 1 if min_len <= 5 else min_len - 2
            return common_len >= required_len

        for s_word in s_words:
            if turkish_lower(q_word) == turkish_lower(s_word) or share_stem_helper(q_word, s_word):
                return s_word

        q_tokens = re.findall(r'\b\w+\b', turkish_lower(user_query))
        try:
            q_idx = q_tokens.index(turkish_lower(q_word))
            rel_q = q_idx / len(q_tokens) if q_tokens else 0.0
            start = max(0, q_idx - 3)
            end = min(len(q_tokens), q_idx + 4)
            q_context = set(q_tokens[start:q_idx] + q_tokens[q_idx+1:end]) - self.STOP_WORDS
        except ValueError:
            q_idx = 0
            q_context = set()
            rel_q = 0.0

        s_tokens = re.findall(r'\b\w+\b', turkish_lower(db_source))
        
        best_word = None
        best_score = -1.0
        
        try:
            q_emb = self.search_model.encode([q_word], convert_to_numpy=True)[0]
            s_embs = self.search_model.encode(s_words, convert_to_numpy=True)
        except Exception:
            q_emb = np.zeros(384)
            s_embs = [np.zeros(384)] * len(s_words)
        
        for idx, s_word in enumerate(s_words):
            norm_q = np.linalg.norm(q_emb)
            norm_s = np.linalg.norm(s_embs[idx])
            if norm_q > 0 and norm_s > 0:
                sem_sim = np.dot(q_emb, s_embs[idx]) / (norm_q * norm_s)
            else:
                sem_sim = 0.0
            sem_sim = max(0.1, float(sem_sim))
            
            s_indices = [i for i, x in enumerate(s_tokens) if x == turkish_lower(s_word)]
            best_word_score = -1.0
            for s_idx in s_indices:
                start_s = max(0, s_idx - 3)
                end_s = min(len(s_tokens), s_idx + 4)
                s_context = set(s_tokens[start_s:s_idx] + s_tokens[s_idx+1:end_s]) - self.STOP_WORDS
                overlap = len(q_context.intersection(s_context))
                
                rel_s = s_idx / len(s_tokens) if s_tokens else 0.0
                pos_sim = 1.0 - abs(rel_q - rel_s)
                abs_pos_sim = 1.0 / (1.0 + abs(q_idx - s_idx))
                
                combined_pos_sim = (pos_sim + abs_pos_sim) / 2.0
                score = sem_sim * (1.0 + overlap) * (combined_pos_sim ** 2)
                
                if score > best_word_score:
                    best_word_score = score
            
            if best_word_score > best_score:
                best_score = best_word_score
                best_word = s_word
                
        return best_word

    def get_relevant_sentences(self, query, document, top_n=1):
        """Metin içerisinden sorgu ile en çok örtüşen cümle(leri) seçer."""
        if not document or document == '-':
            return document
            
        sentences = re.split(r'(?<=[.!?])\s+', document.strip())
        if not sentences:
            return document
            
        q_words = set(re.findall(r'\w+', turkish_lower(query)))
        scored_sentences = []
        for sent in sentences:
            sent_words = set(re.findall(r'\w+', turkish_lower(sent)))
            overlap = len(q_words.intersection(sent_words))
            scored_sentences.append((overlap, sent))
            
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        selected = [s[1] for s in scored_sentences[:top_n]]
        return " ".join(selected)

    def get_local_context_window(self, query, document):
        if not document or document == '-':
            return document
            
        sentences = re.split(r'(?<=[.!?])\s+', document.strip())
        if not sentences:
            return document
            
        q_words = set(re.findall(r'\w+', self.temizle_ve_normallestir(query)))
        best_idx = 0
        max_overlap = -1
        
        for idx, sent in enumerate(sentences):
            sent_words = set(re.findall(r'\w+', self.temizle_ve_normallestir(sent)))
            overlap = len(q_words.intersection(sent_words))
            if overlap > max_overlap:
                max_overlap = overlap
                best_idx = idx
                
        start_idx = max(0, best_idx - 1)
        end_idx = min(len(sentences), best_idx + 2)
        
        selected_sentences = sentences[start_idx:end_idx]
        return " ".join(selected_sentences)

    def akilli_fark_analizi(self, user_query, db_source):
        """
        Kişi, Yer, Tarih, Sayı, Unvan ve Olay farklarını yakalar.
        6 Kritik Problem Odaklı Analiz.
        Returns: (diff_user, diff_source, score, category)
        """
        db_source = re.sub(r'^\[Kaynak:[^\]]+\]\s*', '', db_source)
        db_source = self.get_local_context_window(user_query, db_source)

        user_query = split_numbers_letters(user_query)
        db_source = split_numbers_letters(db_source)

        # 1. TARİH ANALİZİ
        date_pattern = r'\b\d{1,4}[./-]\d{1,2}[./-]\d{2,4}\b|\b\d{4}\b'
        q_dates = set(re.findall(date_pattern, user_query))
        s_dates = set(re.findall(date_pattern, db_source))
        
        diff_q_dates = list(q_dates - s_dates)
        diff_s_dates = list(s_dates - q_dates)
        if diff_q_dates:
            s_date_val = diff_s_dates[0] if diff_s_dates else (list(s_dates)[0] if s_dates else "KAYIT")
            return diff_q_dates[0], s_date_val, 0.05, "ZAMAN AŞIMI"

        # 2. SAYISAL FARK KONTROLÜ
        q_nums = set(re.findall(r'\b\d+\b', user_query))
        s_nums = set(re.findall(r'\b\d+\b', db_source))
        q_nums = q_nums - q_dates
        s_nums = s_nums - s_dates

        if q_nums - s_nums:
            mismatched_q_num = list(q_nums - s_nums)[0]
            s_val = self.find_matching_source_number(mismatched_q_num, user_query, db_source, s_nums)
            if not s_val:
                s_val = list(s_nums)[0] if s_nums else "DEĞER"
            return str(mismatched_q_num), str(s_val), 0.1, "SAYI"

        # 3. KELİME VE ÖZEL İSİM FARK KONTROLÜ
        def get_words_lower(text):
            words = re.findall(r'\b\w+\b', self.temizle_ve_normallestir(text))
            return set([w for w in words if w not in self.STOP_WORDS and len(w) > 1])

        q_words = get_words_lower(user_query) - q_nums - q_dates
        s_words = get_words_lower(db_source) - s_nums - s_dates

        user_diff = list(q_words - s_words)
        source_diff = list(s_words - q_words)

        if not user_diff or not source_diff:
            return None, None, 1.0, "GENEL"

        found_red_titles = [t for t in self.RED_LIST_TITLES if re.search(r'\b' + t + r'\b', turkish_lower(user_query))]
        source_red_titles = [t for t in self.RED_LIST_TITLES if re.search(r'\b' + t + r'\b', turkish_lower(db_source))]
        
        missing_titles = set(found_red_titles) - set(source_red_titles)
        if missing_titles:
            diff_t = list(missing_titles)[0]
            src_t = source_red_titles[0] if source_red_titles else "BİLİNMİYOR"
            return diff_t.upper(), src_t.upper(), 0.01, "KRİTİK UNVAN"

        filtered_user_diff = []
        mismatch_details = {}

        def share_stem(w1, w2):
            w1_clean = re.sub(r'[^a-zA-ZçÇğĞıİöÖşŞüÜ]', '', w1).lower()
            w2_clean = re.sub(r'[^a-zA-ZçÇğĞıİöÖşŞüÜ]', '', w2).lower()
            min_len = min(len(w1_clean), len(w2_clean))
            if min_len < 3:
                return w1_clean == w2_clean
            common_len = 0
            for c1, c2 in zip(w1_clean, w2_clean):
                if c1 == c2:
                    common_len += 1
                else:
                    break
            required_len = min_len - 1 if min_len <= 5 else min_len - 2
            return common_len >= required_len

        def is_explicit_synonym(w1, w2):
            syns = self.kb.get("synonyms", {})
            if w1 in syns and w2 in syns[w1]:
                return True
            if w2 in syns and w1 in syns[w2]:
                return True
            for key, val_list in syns.items():
                if w1 == key or w1 in val_list:
                    if w2 == key or w2 in val_list:
                        return True
            return False

        for q_word in user_diff:
            s_word = self.find_best_matching_word(q_word, user_query, db_source, source_diff)
            if not s_word:
                s_word = source_diff[0] if source_diff else "DEĞER"

            if share_stem(q_word, s_word):
                continue
            if is_explicit_synonym(q_word, s_word):
                continue

            filtered_user_diff.append(q_word)
            mismatch_details[q_word] = (s_word, 0.0)
            
        if not filtered_user_diff:
            return None, None, 1.0, "GENEL"
            
        filtered_user_diff.sort(key=lambda w: mismatch_details[w][1])
        mismatched_q_lower = filtered_user_diff[0]
        mismatched_s_lower, score = mismatch_details[mismatched_q_lower]

        diff_user = self.get_original_case(mismatched_q_lower, user_query)
        diff_source = self.get_original_case(mismatched_s_lower, db_source)

        def is_originally_capitalized(word, text):
            pattern = r'\b' + re.escape(word) + r'\b'
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                if m and m[0].isupper():
                    return True
            return False

        is_entity = is_originally_capitalized(mismatched_q_lower, user_query) or is_originally_capitalized(mismatched_s_lower, db_source)

        if is_entity:
            cat = "KİŞİ/YER/UNVAN"
            if any(w in user_query.upper() for w in ['ŞEHİR', 'ÜLKE', 'YER', 'KÖY', 'İL', 'GAZZE', 'İSRAİL', 'ABD']):
                cat = "YER"
            elif any(w in user_query.upper() for w in ['KİM', 'KİŞİ', 'ADAM', 'KADIN', 'CUMHURBAŞKANI', 'BAKAN']):
                cat = "KİŞİ"
            return diff_user, diff_source, 0.2, cat

        if score < self.IRRELEVANT_THRESHOLD:
            return diff_user, diff_source, score, "OLAY"
            
        return diff_user, diff_source, score, "DETAY"

    def detect_negation(self, text):
        """Metindeki Türkçe olumsuzluk yapılarını tespit eder."""
        text_lower = re.sub(r'[^\w\s]', '', turkish_lower(text))
        
        neg_words = {'değil', 'yok', 'asla', 'hiçbir'}
        for word in neg_words:
            if re.search(r'\b' + word + r'\b', text_lower):
                return True
                
        neg_patterns = [
            r'\w+ma(?:dı|dılar|dığı|dık|mış|yacak|makta|malı)\b',
            r'\w+me(?:di|diler|diği|dik|miş|yecek|mekte|meli)\b',
            r'\w+ma(?:z|zlar)\b',
            r'\w+me(?:z|zler)\b',
            r'\w+m(?:ı|i|u|ü)yor\b'
        ]
        for pat in neg_patterns:
            matches = re.findall(pat, text_lower)
            for match in matches:
                false_positives = {
                    'malzeme', 'mama', 'maliyet', 'mavi', 'maya', 'mayıs', 'memnun', 'mermer', 
                    'memur', 'merkez', 'mesaj', 'metal', 'meyve', 'mezun', 'memleket', 'medya', 
                    'medeni', 'melodi', 'melek', 'merak', 'mezarlık'
                }
                if not any(fp in match for fp in false_positives):
                    return True
        return False
