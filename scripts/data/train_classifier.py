import os
import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import pickle
import ast

def main():
    print("--- Adım C: Öğrenilmiş Karar Katmanı Eğitimi ---")
    results_dir = os.path.join("results", "facturk_full_v13")
    preds_path = os.path.join(results_dir, "predictions.csv")
    
    if not os.path.exists(preds_path):
        print(f"Hata: {preds_path} bulunamadı.")
        return
        
    df = pd.read_csv(preds_path)
    print(f"Yüklenen veri sayısı: {len(df)}")
    
    features = []
    labels = []
    
    for idx, row in df.iterrows():
        gold = row.get("gold_verdict", "").strip()
        if gold == "DOĞRU":
            label = 1
        elif gold == "YALAN":
            label = 0
        else:
            continue
            
        try:
            nli_probs = ast.literal_eval(row["nli_probs"])
            rerank_scores = ast.literal_eval(row["rerank_scores"])
            
            entail = float(nli_probs[0])
            neutral = float(nli_probs[1])
            contradict = float(nli_probs[2])
            
            max_rerank = max(rerank_scores) if rerank_scores else 0.0
            
            features.append([entail, contradict, neutral, max_rerank])
            labels.append(label)
        except Exception as e:
            continue
            
    X = np.array(features)
    y = np.array(labels)
    
    print(f"Eğitim için geçerli veri sayısı: {len(X)}")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    clf.fit(X_train, y_train)
    
    y_pred = clf.predict(X_test)
    print("\nDoğruluk:", accuracy_score(y_test, y_pred))
    print(classification_report(y_test, y_pred, target_names=["YALAN", "DOĞRU"]))
    
    model_path = os.path.join("src", "ai_core", "engine", "decision_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(clf, f)
        
    print(f"\nModel başarıyla kaydedildi: {model_path}")

if __name__ == "__main__":
    main()
