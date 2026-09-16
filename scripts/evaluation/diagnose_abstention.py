import os
import json
import pandas as pd
import numpy as np

def main():
    path = os.path.join("results", "facturk_full_v17", "predictions.csv")
    df = pd.read_csv(path)
    abstained = df[df["abstained"] == True]

    def parse_list(val):
        if not val or pd.isna(val) or val == "null": return []
        try: return json.loads(val)
        except: return []

    records = []
    for _, r in abstained.iterrows():
        gold = r["gold_verdict"]
        rrs = parse_list(r["rerank_scores"])
        max_rr = max(rrs) if rrs else 0.0
        
        nli = parse_list(r["nli_probs"])
        p_ent = nli[0] if len(nli) == 3 else np.nan
        p_neu = nli[1] if len(nli) == 3 else np.nan
        p_con = nli[2] if len(nli) == 3 else np.nan
        
        records.append({
            "gold": gold,
            "max_rr": max_rr,
            "has_nli": len(nli) == 3,
            "p_neu": p_neu,
            "p_con": p_con,
            "p_ent": p_ent
        })

    adf = pd.DataFrame(records)
    print("Abstention counts by class:")
    print(adf["gold"].value_counts())

    print("\nRetrieval stats (max rerank score):")
    for g in ["DOĞRU", "YALAN"]:
        sub = adf[adf["gold"] == g]
        print(f"{g}: mean max_rr = {sub['max_rr'].mean():.4f}, median max_rr = {sub['max_rr'].median():.4f}, nli_evaluated = {sub['has_nli'].sum()}/{len(sub)}")

    print("\nNLI stats (for claims that reached NLI before abstaining):")
    for g in ["DOĞRU", "YALAN"]:
        sub = adf[(adf["gold"] == g) & (adf["has_nli"])]
        print(f"{g} (n={len(sub)}): mean p_neu = {sub['p_neu'].mean():.4f}, mean p_con = {sub['p_con'].mean():.4f}, mean p_ent = {sub['p_ent'].mean():.4f}")

if __name__ == "__main__":
    main()
