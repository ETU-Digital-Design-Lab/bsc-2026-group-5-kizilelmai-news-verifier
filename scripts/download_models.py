import os
from sentence_transformers import SentenceTransformer, CrossEncoder

def download_models():
    print("🚀 KızılelmAI Model İndirme Başlatılıyor...")
    
    # 1. Base Embedding Model (E5)
    print("\n📦 [1/3] Base Embedding Model indiriliyor: intfloat/multilingual-e5-small")
    SentenceTransformer('intfloat/multilingual-e5-small')
    
    # 2. NLI Model (XLM-RoBERTa)
    print("\n📦 [2/3] NLI Model indiriliyor: joeddav/xlm-roberta-large-xnli")
    CrossEncoder('joeddav/xlm-roberta-large-xnli')
    
    # 3. Layer 3 Re-Ranker (BGE)
    print("\n📦 [3/3] Layer 3 Re-Ranker indiriliyor: BAAI/bge-reranker-v2-m3")
    CrossEncoder('BAAI/bge-reranker-v2-m3')
    
    print("\n✅ Tüm modeller başarıyla indirildi ve önbelleğe (cache) alındı!")

if __name__ == "__main__":
    download_models()
