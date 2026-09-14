import os
import pickle
import numpy as np

class LearnedDecisionClassifier:
    """Adım C: Öğrenilmiş Karar Katmanı (Scikit-learn tabanlı)"""
    
    def __init__(self, model_path=None):
        if model_path is None:
            # Default path: same directory as this file
            base_dir = os.path.dirname(__file__)
            model_path = os.path.join(base_dir, "decision_model.pkl")
            
        self.model = None
        self.is_loaded = False
        
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
                self.is_loaded = True
                print(f"✅ Öğrenilmiş Karar Modeli (Adım C) Yüklendi: {model_path}")
            except Exception as e:
                print(f"⚠️ Karar modeli yüklenemedi: {e}")
                
    def predict(self, entailment_prob, contradiction_prob, neutral_prob, max_rerank):
        """
        Öğrenilmiş modele göre karar üretir.
        Return: (predicted_label, probability)
        predicted_label: 1 (DOĞRU), 0 (YALAN), -1 (ÇEKİMSER/BİLİNMİYOR)
        """
        if not self.is_loaded or self.model is None:
            return -1, 0.0
            
        features = np.array([[entailment_prob, contradiction_prob, neutral_prob, max_rerank]])
        try:
            pred = self.model.predict(features)[0]
            probs = self.model.predict_proba(features)[0]
            confidence = float(max(probs))
            
            # Öğrenilmiş modelin güvenilirliği düşükse çekimser kal
            if confidence < 0.55:
                return -1, confidence
                
            return int(pred), confidence
        except Exception as e:
            print(f"Tahmin hatası: {e}")
            return -1, 0.0
