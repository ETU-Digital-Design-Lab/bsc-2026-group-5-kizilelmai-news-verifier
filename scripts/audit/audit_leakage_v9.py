"""Leakage audit for v9 run against the 139 newly injected corpus records.

Audits:
1. Identifies the 139 records injected into local_csv_20260913_v2 compared to v1.
2. Identifies the subset of 29 records coming from fact-checking websites (teyit.org, malumatfurus.org).
3. Reads results/facturk_full_v9/predictions.csv and determines how many times
   selected_source_id falls into the 139 injected records, and specifically into the 29 fact-checking records.
4. Outputs detailed CSV and JSON reports to results/leakage_audit_v1/.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
V1_CORPUS_PATH = ROOT / "data" / "corpus_snapshots" / "local_csv_20260909_v1" / "corpus.csv"
V2_CORPUS_PATH = ROOT / "data" / "corpus_snapshots" / "local_csv_20260913_v2" / "corpus.csv"
BENCHMARK_PATH = ROOT / "data" / "external_benchmark" / "facturk_binary_500.csv"
V9_PRED_PATH = ROOT / "results" / "facturk_full_v9" / "predictions.csv"
OUT_DIR = ROOT / "results" / "leakage_audit_v1"

FACTCHECKING_DOMAINS = {"teyit.org", "malumatfurus.org"}


def run_audit():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading corpus v1: {V1_CORPUS_PATH}")
    df_v1 = pd.read_csv(V1_CORPUS_PATH, keep_default_na=False)
    print(f"Reading corpus v2: {V2_CORPUS_PATH}")
    df_v2 = pd.read_csv(V2_CORPUS_PATH, keep_default_na=False)
    
    v1_ids = set(df_v1["id"].astype(int))
    v2_ids = set(df_v2["id"].astype(int))
    injected_ids = sorted(list(v2_ids - v1_ids))
    
    print(f"Total v1 records: {len(v1_ids)}")
    print(f"Total v2 records: {len(v2_ids)}")
    print(f"Total injected records in v2: {len(injected_ids)}")
    
    df_injected = df_v2[df_v2["id"].astype(int).isin(injected_ids)].copy()
    
    # Flag fact-checking sites
    def is_fc(row):
        pub = str(row.get("publisher", "")).lower()
        url = str(row.get("source_url", "")).lower()
        for dom in FACTCHECKING_DOMAINS:
            if dom in pub or dom in url:
                return True
        return False
    
    df_injected["is_factchecking_site"] = df_injected.apply(is_fc, axis=1)
    fc_ids = set(df_injected[df_injected["is_factchecking_site"]]["id"].astype(int))
    print(f"Injected fact-checking site records (teyit.org + malumatfurus.org): {len(fc_ids)}")
    
    # Save injected records list
    injected_csv_path = OUT_DIR / "injected_records_list.csv"
    df_injected.to_csv(injected_csv_path, index=False, encoding="utf-8")
    print(f"Saved injected records list: {injected_csv_path}")
    
    # Publisher distribution of injected records
    pub_counts = df_injected["publisher"].value_counts().to_dict()
    print(f"Injected publisher breakdown: {pub_counts}")
    
    # Now read v9 predictions
    if not V9_PRED_PATH.exists():
        print(f"ERROR: v9 predictions file not found: {V9_PRED_PATH}")
        return
    
    df_v9 = pd.read_csv(V9_PRED_PATH, keep_default_na=False)
    df_bm = pd.read_csv(BENCHMARK_PATH, keep_default_na=False)
    bm_map = {r["benchmark_id"]: r["claim"] for _, r in df_bm.iterrows()}
    
    injected_map = {int(r["id"]): r.to_dict() for _, r in df_injected.iterrows()}
    
    hits = []
    fc_hits = []
    
    for _, row in df_v9.iterrows():
        sel_id_raw = row.get("selected_source_id")
        try:
            sel_id = int(float(sel_id_raw)) if sel_id_raw and str(sel_id_raw).strip() != "" else None
        except (ValueError, TypeError):
            sel_id = None
        
        if sel_id is not None and sel_id in injected_map:
            inj_rec = injected_map[sel_id]
            is_fact_check = sel_id in fc_ids
            hit_item = {
                "claim_id": row["claim_id"],
                "claim_text": bm_map.get(row["claim_id"], ""),
                "gold_verdict": row["gold_verdict"],
                "final_verdict": row["final_verdict"],
                "raw_status": row.get("raw_status", ""),
                "abstained": row.get("abstained", ""),
                "selected_source_id": sel_id,
                "injected_publisher": inj_rec.get("publisher", ""),
                "injected_source_url": inj_rec.get("source_url", ""),
                "is_factchecking_site": is_fact_check,
                "is_correct": row["gold_verdict"] == row["final_verdict"] if row["final_verdict"] in {"DOĞRU", "YALAN"} else False
            }
            hits.append(hit_item)
            if is_fact_check:
                fc_hits.append(hit_item)
    
    # Save hits
    hits_csv_path = OUT_DIR / "v9_leakage_hits.csv"
    if hits:
        pd.DataFrame(hits).to_csv(hits_csv_path, index=False, encoding="utf-8")
    else:
        pd.DataFrame(columns=["claim_id", "selected_source_id"]).to_csv(hits_csv_path, index=False)
    print(f"Saved leakage hits: {hits_csv_path} (Total hits: {len(hits)}, FC hits: {len(fc_hits)})")
    
    # Summary metrics
    total_claims = len(df_v9)
    answered_claims = len(df_v9[df_v9["final_verdict"].isin(["DOĞRU", "YALAN"])])
    
    summary = {
        "total_claims": total_claims,
        "answered_claims": answered_claims,
        "total_injected_records": len(injected_ids),
        "injected_factchecking_records": len(fc_ids),
        "injected_publisher_distribution": pub_counts,
        "v9_total_leakage_hits": len(hits),
        "v9_total_leakage_hit_rate": len(hits) / total_claims if total_claims else 0.0,
        "v9_factchecking_leakage_hits": len(fc_hits),
        "v9_factchecking_leakage_hit_rate": len(fc_hits) / total_claims if total_claims else 0.0,
        "hits_detail": hits
    }
    
    summary_json_path = OUT_DIR / "leakage_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Saved summary JSON: {summary_json_path}")
    
    # Generate Markdown Report
    report_md_path = OUT_DIR / "leakage_report.md"
    md_content = f"""# Sızıntı Denetimi Raporu (Leakage Audit v1)

**Tarih:** 2026-09-14  
**Değerlendirilen Koşum:** v9 (`results/facturk_full_v9/`)  
**İncelenen Korpus Snapshot:** `local_csv_20260913_v2` (30.487 kayıt)  
**Referans Taban Korpus:** `local_csv_20260909_v1` (30.347 kayıt)  

---

## 1. Enjekte Edilen Kayıtlar Özeti

Taban korpus (v1) ile güncel donuk korpus (v2) karşılaştırıldığında sisteme **{len(injected_ids)} yeni kaydın** eklendiği doğrulanmıştır.

| Kaynak / Yayıncı | Kayıt Sayısı | Kategori |
| :--- | :---: | :--- |
| **aa.com.tr** | {pub_counts.get('aa.com.tr', 0)} | Birincil Haber Ajansı |
| **trthaber.com** | {pub_counts.get('trthaber.com', 0)} | Kamu Yayıncısı Haber |
| **malumatfurus.org** | {pub_counts.get('malumatfurus.org', 0)} | Doğrulama / Fact-checking Sitesi ⚠️ |
| **teyit.org** | {pub_counts.get('teyit.org', 0)} | Doğrulama / Fact-checking Sitesi ⚠️ |
| **Toplam** | **{len(injected_ids)}** | (29 adet Doğrulama Sitesi) |

> [!WARNING]
> Danışmanımızın belirttiği üzere `teyit.org` ve `malumatfurus.org` gibi doğrulama sitelerinden gelen **29 kayıt**, FACTurk benchmark'ının türetildiği teyit kuruluşları olduğu için doğrudan bilgi sızıntısı (label/answer leakage) riski taşımaktadır.

---

## 2. v9 Koşumunda Sızıntı Tespiti

v9 `predictions.csv` dosyasındaki 500 iddiaya ait `selected_source_id` (nihai karara giren kanıt belgesi) incelenmiştir:

- **Toplam İddia:** {total_claims}
- **Cevaplanan İddia:** {answered_claims}
- **Enjekte Edilen 139 Kayıttan Seçilen Kaynak Sayısı:** **{len(hits)}** (%{len(hits)/total_claims*100:.2f})
- **Teyit Sitelerinden (29 Kayıt) Seçilen Kaynak Sayısı:** **{len(fc_hits)}** (%{len(fc_hits)/total_claims*100:.2f})

### 2.1. Teyit Sitelerine Denk Gelen İddialar (Detaylı Döküm)
"""
    if fc_hits:
        md_content += "\n| İddia ID | İddia Metni | Altın Etiket | v9 Kararı | Seçilen Kaynak ID | Yayıncı | Doğru mu? |\n| :--- | :--- | :---: | :---: | :---: | :--- | :---: |\n"
        for h in fc_hits:
            cor = "✅ Evet" if h["is_correct"] else "❌ Hayır"
            claim_trunc = (h["claim_text"][:50] + "...") if len(h["claim_text"]) > 50 else h["claim_text"]
            md_content += f"| `{h['claim_id']}` | {claim_trunc} | {h['gold_verdict']} | {h['final_verdict']} | `{h['selected_source_id']}` | {h['injected_publisher']} | {cor} |\n"
    else:
        md_content += "\n*Teyit sitelerinden (teyit.org / malumatfurus.org) hiçbir kayıt nihai karara kaynak olarak seçilmemiştir (0 sızıntı).*\n"

    md_content += f"""
---

## 3. Bilimsel Değerlendirme ve Sonuç

1. **Sızıntı Boyutu:** Enjekte edilen 139 kaydın v9 kararlarındaki etkisi toplamda {len(hits)} iddia ile sınırlıdır (%{len(hits)/total_claims*100:.2f}).
2. **Doğrulama Kuruluşu Sızıntısı:** Teyit kuruluşlarından gelen 29 kayıttan kaynak seçilme sayısı {len(fc_hits)} adettir.
3. Bu denetim, depoda `results/leakage_audit_v1/` altında mühürlenmiş olup makale savunmasında metodolojik şeffaflık olarak sunulacaktır.
"""
    report_md_path.write_text(md_content, encoding="utf-8")
    print(f"Saved leakage report Markdown: {report_md_path}")


if __name__ == "__main__":
    run_audit()
