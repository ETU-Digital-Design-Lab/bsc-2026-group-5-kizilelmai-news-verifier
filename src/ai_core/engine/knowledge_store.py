"""
Knowledge Store & Sync Modülü.

KızılelmAI için PostgreSQL / SQLite / Yerel CSV tabanlı bilgi tabanı (Knowledge Base)
yönetimi: veri senkronizasyonu, canlı bilgi enjeksiyonu (injection), silme ve güncelleme işlemleri.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi
from sqlalchemy import text

from .text_heuristics import turkish_lower

PROVENANCE_FIELDS = ("source_url", "publisher", "published_at", "evidence_id", "label_provenance", "ingested_at")


class KnowledgeStoreMixin:
    """KizilelmaEngine için bilgi tabanı CRUD ve senkronizasyon yetenekleri."""

    def sync_db(self):
        """
        Veritabanındaki yeni kayıtları bellekle senkronize eder.
        Throttle: En fazla her 60 saniyede bir çalışır.
        """
        if getattr(self, "frozen_corpus_path", None):
            return
        now = time.time()
        with self._sync_lock:
            if now - self._last_sync_time < self.SYNC_INTERVAL:
                return
            self._last_sync_time = now

        if getattr(self, 'db_connected', False):
            try:
                max_id = int(self.df['id'].max()) if not self.df.empty else 0
                with self.db_engine.connect() as conn:
                    sql_new = text("SELECT * FROM knowledge_base WHERE id > :max_id ORDER BY id")
                    new_rows = pd.read_sql(sql_new, conn, params={"max_id": max_id}).drop(columns=["embedding"], errors="ignore")

                if not new_rows.empty:
                    print(f"[Sync] Veritabanindan {len(new_rows)} yeni kayit belleğe yukleniyor...")
                    self.df = pd.concat([self.df, new_rows], ignore_index=True)
                    self.texts = self.df['text'].tolist()

                    def tokenize(t): return re.findall(r'\w+', turkish_lower(str(t)))
                    tokenized_corpus = [tokenize(doc) for doc in self.texts]
                    self.bm25 = BM25Okapi(tokenized_corpus)
                    print(f"✅ [Sync] BM25 indeksi güncellendi. Toplam kayıt: {len(self.df)}")
            except Exception as e:
                print(f"⚠️ [Sync] Veritabanı senkronizasyon hatası: {e}")
        else:
            try:
                if os.path.exists(self.csv_path):
                    csv_df = pd.read_csv(self.csv_path)
                    if len(csv_df) > len(self.df):
                        new_rows = csv_df.iloc[len(self.df):]
                        print(f"🔄 [Sync-Offline] CSV dosyasından {len(new_rows)} yeni kayıt belleğe yükleniyor...")
                        
                        if 'id' not in new_rows.columns:
                            new_rows['id'] = range(len(self.df) + 1, len(csv_df) + 1)
                        if 'authority' not in new_rows.columns:
                            new_rows['authority'] = 0.85
                        if 'label' not in new_rows.columns:
                            new_rows['label'] = 1
                            
                        self.df = pd.concat([self.df, new_rows], ignore_index=True)
                        new_texts = new_rows['text'].astype(str).tolist()
                        self.texts.extend(new_texts)
                        
                        def tokenize(t): return re.findall(r'\w+', str(t).lower())
                        tokenized_corpus = [tokenize(doc) for doc in self.texts]
                        self.bm25 = BM25Okapi(tokenized_corpus)
                        
                        if new_texts:
                            self.load_search_model()
                            passage_texts = ["passage: " + str(t) for t in new_texts]
                            new_embs = self.search_model.encode(passage_texts, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
                            
                            if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                                self.text_embeddings = np.vstack([self.text_embeddings, new_embs])
                            else:
                                self.text_embeddings = new_embs
                                
                        print(f"✅ [Sync-Offline] BM25 ve Vektörler güncellendi. Toplam kayıt: {len(self.df)}")
            except Exception as e:
                print(f"⚠️ [Sync-Offline] CSV senkronizasyon hatası: {e}")

    def inject_knowledge(self, input_text, label, authority=0.95, *, source_url=None, publisher=None,
                         published_at=None, evidence_id=None, label_provenance="unknown"):
        """
        Katman 10: Çalışma zamanında yeni bilgi enjekte eder (PostgreSQL ve/veya CSV).
        """
        if getattr(self, "frozen_corpus_path", None):
            raise RuntimeError("Cannot inject into a frozen evaluation corpus.")
        self.load_search_model()
        new_emb = self.search_model.encode([f"passage: {input_text}"], convert_to_numpy=True)[0].astype(np.float32)
        provenance = {"source_url": source_url or "", "publisher": publisher or "", "published_at": published_at or None,
                      "evidence_id": evidence_id or str(uuid.uuid4()), "label_provenance": label_provenance or "unknown",
                      "ingested_at": datetime.now(timezone.utc).isoformat()}
        new_id = int(self.df["id"].max()) + 1 if not self.df.empty else 1
        
        if getattr(self, 'db_connected', False):
            try:
                with self.db_engine.connect() as conn:
                    query_emb_str = "[" + ",".join(map(str, new_emb.tolist())) + "]"
                    sql = text("INSERT INTO knowledge_base (text, label, authority, embedding, source_url, publisher, published_at, evidence_id, label_provenance, ingested_at) VALUES (:t, :l, :a, :e, :source_url, :publisher, :published_at, :evidence_id, :label_provenance, :ingested_at) RETURNING id")
                    result = conn.execute(sql, {"t": input_text, "l": int(label), "a": float(authority), "e": query_emb_str, **provenance})
                    new_id = result.scalar()
                    conn.commit()
            except Exception as e:
                print(f"⚠️ Veritabanına enjeksiyon hatası: {e}")
                return False

        new_data = {'id': new_id, 'text': input_text, 'label': int(label), 'authority': float(authority), **provenance}
        new_row = pd.DataFrame([new_data])
        
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self.texts.append(input_text)
        
        if not getattr(self, 'db_connected', False):
            try:
                self.df.to_csv(self.csv_path, index=False, encoding='utf-8')
                if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                    self.text_embeddings = np.vstack([self.text_embeddings, new_emb])
                else:
                    self.text_embeddings = np.array([new_emb])
                print("💾 Çevrimdışı Mod: Yeni bilgi yerel CSV dosyasına kaydedildi.")
            except Exception as csv_err:
                print(f"⚠️ Yerel CSV güncellenirken hata oluştu: {csv_err}")
        
        def tokenize(t): return re.findall(r'\w+', str(t).lower())
        tokenized_corpus = [tokenize(doc) for doc in self.texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        print(f"💉 Katman 10 (Enjeksiyon): Yeni bilgi enjekte edildi -> {input_text[:30]}...")
        return True

    def delete_knowledge(self, record_id):
        """
        Katman 10 (Admin): Belirli bir kaydı veritabanından veya yerel CSV'den ve bellekten siler.
        """
        if getattr(self, "frozen_corpus_path", None):
            raise RuntimeError("Cannot delete from a frozen evaluation corpus.")
        deleted_from_db = False
        if getattr(self, 'db_connected', False):
            try:
                with self.db_engine.connect() as conn:
                    result = conn.execute(text("DELETE FROM knowledge_base WHERE id = :id"), {"id": int(record_id)})
                    conn.commit()
                    if result.rowcount > 0:
                        deleted_from_db = True
            except Exception as e:
                print(f"⚠️ Veritabanından silme hatası: {e}")
            
        try:
            if 'id' in self.df.columns:
                idx = self.df.index[self.df['id'] == int(record_id)].tolist()
                if idx:
                    deleted_text = self.df.iloc[idx[0]]['text']
                    self.df = self.df[self.df['id'] != int(record_id)].reset_index(drop=True)
                    
                    if deleted_text in self.texts:
                        idx_text = self.texts.index(deleted_text)
                        self.texts.remove(deleted_text)
                        if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                            self.text_embeddings = np.delete(self.text_embeddings, idx_text, axis=0)
                            
                    def tokenize(t): return re.findall(r'\w+', str(t).lower())
                    tokenized_corpus = [tokenize(doc) for doc in self.texts]
                    if tokenized_corpus:
                        self.bm25 = BM25Okapi(tokenized_corpus)
                    else:
                        self.bm25 = None
                    
                    if not getattr(self, 'db_connected', False):
                        self.df.to_csv(self.csv_path, index=False, encoding='utf-8')
                        
                    print(f"🗑️ Katman 10 (Admin): {record_id} numaralı bilgi silindi.")
                    return True
        except Exception as e:
            print(f"❌ Hata (Silme): {e}")
            return False
            
        return deleted_from_db

    def update_knowledge(self, record_id, input_text, label, authority, *, source_url=None, publisher=None,
                         published_at=None, evidence_id=None, label_provenance="unknown"):
        """
        Katman 10 (Admin): Belirli bir kaydın içeriğini, etiketini ve otoritesini günceller.
        """
        if getattr(self, "frozen_corpus_path", None):
            raise RuntimeError("Cannot update a frozen evaluation corpus.")
        self.load_search_model()
        provenance = {"source_url": source_url or "", "publisher": publisher or "", "published_at": published_at or None,
                      "evidence_id": evidence_id or str(uuid.uuid4()), "label_provenance": label_provenance or "unknown",
                      "ingested_at": datetime.now(timezone.utc).isoformat()}
        new_emb = self.search_model.encode([f"passage: {input_text}"], convert_to_numpy=True)[0]
        updated_in_db = False
        
        if getattr(self, 'db_connected', False):
            try:
                query_emb_str = "[" + ",".join(map(str, new_emb.tolist())) + "]"
                with self.db_engine.connect() as conn:
                    sql = text("UPDATE knowledge_base SET text = :t, label = :l, authority = :a, embedding = :e, source_url = :source_url, publisher = :publisher, published_at = :published_at, evidence_id = :evidence_id, label_provenance = :label_provenance, ingested_at = :ingested_at WHERE id = :id")
                    result = conn.execute(sql, {"t": input_text, "l": int(label), "a": float(authority), "e": query_emb_str, "id": int(record_id), **provenance})
                    conn.commit()
                    if result.rowcount > 0:
                        updated_in_db = True
            except Exception as e:
                print(f"⚠️ Veritabanı güncelleme hatası: {e}")
                    
        try:
            if 'id' in self.df.columns:
                idx = self.df.index[self.df['id'] == int(record_id)].tolist()
                if idx:
                    old_text = self.df.at[idx[0], 'text']
                    self.df.at[idx[0], 'text'] = input_text
                    self.df.at[idx[0], 'label'] = int(label)
                    self.df.at[idx[0], 'authority'] = float(authority)
                    for field, value in provenance.items():
                        self.df.at[idx[0], field] = value
                    
                    if old_text in self.texts:
                        idx_text = self.texts.index(old_text)
                        self.texts[idx_text] = input_text
                        if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                            self.text_embeddings[idx_text] = new_emb
                    
                    def tokenize(t): return re.findall(r'\w+', str(t).lower())
                    tokenized_corpus = [tokenize(doc) for doc in self.texts]
                    self.bm25 = BM25Okapi(tokenized_corpus)
                    
                    if not getattr(self, 'db_connected', False):
                        self.df.to_csv(self.csv_path, index=False, encoding='utf-8')
                        
                    print(f"🔄 Katman 10 (Admin): {record_id} numaralı bilgi güncellendi.")
                    return True
        except Exception as e:
            print(f"❌ Hata (Güncelleme): {e}")
            return False
            
        return updated_in_db
