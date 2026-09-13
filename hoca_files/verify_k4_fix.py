#!/usr/bin/env python3
"""
K-4 düzeltmesinin DOĞRULAMA KOŞUMU.

Amaç: pipeline'ı baştan sona koşturmadan önce NLI katmanının gerçekten
çalıştığını kanıtlamak. İki kapı var; ikisi de geçilmeden yeniden koşum
yapılmamalıdır.

  KAPI 1 — Bilinen çiftler.  İlişkisi elle belirlenmiş 12 Türkçe
           premise/hypothesis çifti. Düzgün çalışan bir NLI modeli
           en az 10'unu bilmelidir. Eski zero-shot çağrısı bu kapıdan
           geçemez; neredeyse hepsine "neutral" der.

  KAPI 2 — Gerçek veri.  FACTurk koşusundaki iddia/kanıt çiftlerinden bir
           örneklem. Eski koşuda neutral oranı %68, neutral medyanı 0.962'ydi.
           Düzeltmeden sonra neutral hakimiyetinin belirgin biçimde
           düşmesi beklenir. Düşmüyorsa sorun çağrı biçiminde değil,
           modelin Türkçe NLI yeteneğindedir — o zaman model değiştirilir
           (ve bu makalede dürüstçe raporlanır).

Kullanım:
  python verify_k4_fix.py --model joeddav/xlm-roberta-large-xnli --device 0 \
      --predictions results/facturk_full_v5/predictions.csv \
      --corpus data/corpus_snapshots/local_csv_20260909_v1/corpus.csv \
      --claims results/facturk_baseline_k6/k6_predictions.csv --sample 100
"""
import argparse, csv, json, random, statistics, sys
from k4_nli import load_nli_model, run_nli_batch, dominant_nli_label, should_abstain

# (premise = kanıt/bağlam, hypothesis = iddia, beklenen)
GOLD_PAIRS = [
    ("Ankara Türkiye'nin başkentidir.", "Türkiye'nin başkenti Ankara'dır.", "entailment"),
    ("Ankara Türkiye'nin başkentidir.", "Türkiye'nin başkenti İstanbul'dur.", "contradiction"),
    ("Toplantı saat 14.00'te başladı ve iki saat sürdü.", "Toplantı öğleden sonra başladı.", "entailment"),
    ("Toplantı saat 14.00'te başladı ve iki saat sürdü.", "Toplantı hiç yapılmadı.", "contradiction"),
    ("Bakanlık, yeni düzenlemenin ocak ayında yürürlüğe gireceğini açıkladı.",
     "Düzenleme ocak ayında yürürlüğe girecek.", "entailment"),
    ("Bakanlık, yeni düzenlemenin ocak ayında yürürlüğe gireceğini açıkladı.",
     "Düzenleme tamamen iptal edildi.", "contradiction"),
    ("Kadın futbol takımı maçı 3-1 kazandı.", "Takım maçı kazandı.", "entailment"),
    ("Kadın futbol takımı maçı 3-1 kazandı.", "Takım maçı kaybetti.", "contradiction"),
    ("Şirket geçen yıl 200 kişi istihdam etti.", "Şirketin genel müdürü istifa etti.", "neutral"),
    ("Kar yağışı nedeniyle okullar tatil edildi.", "Öğrenciler okula gitmedi.", "entailment"),
    ("Kar yağışı nedeniyle okullar tatil edildi.", "Hava sıcaklığı 30 dereceydi.", "contradiction"),
    ("İstanbul'da metro seferleri sabah 06.00'da başlıyor.", "Metro bileti 20 lira.", "neutral"),
]


def gate1(model, verbose=True):
    probs = run_nli_batch([(h, p) for p, h, _ in GOLD_PAIRS], model)  # (claim, evidence)
    ok = 0
    rows = []
    for (p, h, want), pr in zip(GOLD_PAIRS, probs):
        got, conf = dominant_nli_label(pr)
        hit = got == want
        ok += hit
        rows.append({"hypothesis": h, "expected": want, "got": got,
                     "confidence": round(conf, 4), "pass": hit})
        if verbose:
            print(f"  [{'OK ' if hit else 'HATA'}] bekleniyor={want:14s} gelen={got:14s} "
                  f"({conf:.3f})  «{h[:52]}»")
    return ok, rows


def gate2(model, predictions, corpus, claims, sample, seed=20260908):
    corp = {}
    for r in csv.DictReader(open(corpus, encoding="utf-8")):
        if r.get("id"):
            corp[str(r["id"]).strip()] = (r.get("text") or "").strip()
    ctext = {r["benchmark_id"]: r["claim"] for r in csv.DictReader(open(claims, encoding="utf-8"))}
    preds = list(csv.DictReader(open(predictions, encoding="utf-8")))

    old_top, old_neu = [], []
    pairs, kept = [], []
    for r in preds:
        if r["nli_probs"] and r["nli_probs"] != "null":
            d = json.loads(r["nli_probs"])
            old_top.append(["entailment", "neutral", "contradiction"][max(range(3), key=lambda i: d[i])])
            old_neu.append(d[1])
        ids = json.loads(r["retrieved_source_ids"])
        sc = json.loads(r["rerank_scores"])
        if not ids or r["claim_id"] not in ctext:
            continue
        best = str(ids[max(range(len(sc)), key=lambda i: sc[i])])
        ev = corp.get(best)
        if ev:
            pairs.append((ctext[r["claim_id"]], ev))
            kept.append(r["claim_id"])

    random.seed(seed)
    if sample and len(pairs) > sample:
        idx = random.sample(range(len(pairs)), sample)
        pairs = [pairs[i] for i in idx]; kept = [kept[i] for i in idx]
    if not pairs:
        return {"error": "hiç iddia/kanıt çifti kurulamadı — id eşleşmiyor olabilir"}

    new = run_nli_batch(pairs, model)
    new_top = [dominant_nli_label(p)[0] for p in new]
    return {
        "n_pairs_scored": len(pairs),
        "eski_neutral_orani": round(old_top.count("neutral") / len(old_top), 4) if old_top else None,
        "eski_neutral_medyan": round(statistics.median(old_neu), 4) if old_neu else None,
        "yeni_neutral_orani": round(new_top.count("neutral") / len(new_top), 4),
        "yeni_neutral_medyan": round(statistics.median([p[1] for p in new]), 4),
        "yeni_dagilim": {k: new_top.count(k) for k in ("entailment", "neutral", "contradiction")},
        "yeni_abstain_orani": round(sum(should_abstain(p) for p in new) / len(new), 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="joeddav/xlm-roberta-large-xnli")
    ap.add_argument("--device", type=int, default=-1)
    ap.add_argument("--predictions"); ap.add_argument("--corpus"); ap.add_argument("--claims")
    ap.add_argument("--sample", type=int, default=100)
    ap.add_argument("--out", default="k4_fix_verification.json")
    a = ap.parse_args()

    print(f"Model yükleniyor: {a.model}")
    model = load_nli_model(a.model, a.device)
    print("Model içi sınıf sırası -> kanonik eşleme:", model.order,
          "(model.config.id2label'dan okundu)\n")

    print("KAPI 1 — bilinen çiftler")
    ok, rows = gate1(model)
    print(f"\n  sonuç: {ok}/12  ({'GEÇTİ' if ok >= 10 else 'KALDI'})\n")

    report = {"model": a.model, "class_order_in_model": model.order,
              "gate1_score": ok, "gate1_pass": ok >= 10, "gate1_detail": rows}

    if a.predictions and a.corpus and a.claims:
        print("KAPI 2 — gerçek veri")
        g2 = gate2(model, a.predictions, a.corpus, a.claims, a.sample)
        report["gate2"] = g2
        print(json.dumps(g2, ensure_ascii=False, indent=2))
        if "error" not in g2 and g2["eski_neutral_orani"] is not None:
            better = g2["yeni_neutral_orani"] < g2["eski_neutral_orani"] - 0.15
            report["gate2_pass"] = bool(better)
            print(f"\n  neutral hakimiyeti {g2['eski_neutral_orani']:.1%} -> "
                  f"{g2['yeni_neutral_orani']:.1%}  ({'GEÇTİ' if better else 'KALDI'})")
    else:
        print("KAPI 2 atlandı (--predictions/--corpus/--claims verilmedi)")

    json.dump(report, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n-> {a.out}")
    both = report.get("gate1_pass") and report.get("gate2_pass", True)
    print("\n" + ("HER İKİ KAPI GEÇİLDİ — pipeline yeniden koşulabilir."
                  if both else "KAPI GEÇİLEMEDİ — yeniden koşum yapmayın, önce sebebini bildirin."))
    return 0 if both else 1


if __name__ == "__main__":
    sys.exit(main())
