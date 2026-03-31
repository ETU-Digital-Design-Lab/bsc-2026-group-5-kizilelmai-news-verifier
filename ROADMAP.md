# 🧭 KızılelmAI Gelecek Yol Haritası (v4.0 Roadmap)

Bu dosya, KızılelmAI projesinin bir "Akademik Prototip"ten "Uluslararası Ölçekli Bir Doğrulama Platformu"na geçişi için gereken stratejik teknik adımları içerir.

## 🧠 Analitik Motor Bakımı & Geliştirme (Engine)
- [ ] **ONNX Runtime Geçişi**: Modellerin 8-bit quantization ile CPU üzerinde 3-9 kat hızlandırılması.
- [ ] **Düşünce Zinciri (CoT)**: Yanıt üretmeden önce modelin kendi kendine mantık yürütmesini sağlayan bir "Reasoning Step" eklenmesi.
- [ ] **Hibrit NER**: SpaCy ve Stanza ile derinlemesine varlık tanıma ve unvan kontrolü.
- [ ] **Bilgi Grafiği Entegrasyonu**: Neo4j ile olaylar ve kişiler arası anlamsal bağların kurulması.

## 💾 Veri Mimarisi & Ölçeklenebilirlik (Database)
- [ ] **Vektör Veri Tabanı (Vector DB)**: ChromaDB veya Pinecone ile milyonlarca kayıt kapasitesine ulaşılması.
- [ ] **Redis Caching**: Sık sorulan iddialar için milisaniyelik yanıt süresi sağlayan önbellek katmanı.
- [ ] **Canlı Crawler**: Resmi Gazete, Anadolu Ajansı ve TRT Haber gibi kaynaklardan anlık bilgi beslemesi.

## 🎨 Kullanıcı Deneyimi & Arayüz (UI/UX)
- [ ] **Kaynak Görselleştirme**: Doğruluğu etkileyen kaynakların birbirleriyle olan tutarlılığını gösteren etkileşimli grafikler.
- [ ] **Dark/Light Mode Desteği**: Flutter dashboard üzerinde kullanıcıya özel tema seçenekleri.
- [ ] **Çoklu Dil Desteği (i18n)**: Sistemin İngilizce ve diğer dillerde de doğrulama yapabilmesi.

## 🛡️ Güvenlik & Şeffaflık (Trust)
- [ ] **Explainable AI (XAI)**: Yapay zekanın "neden bu kararı verdiğini" kanıtlarla gösteren şeffaflık arayüzü.
- [ ] **Deepfake Tespiti**: Haberlerdeki fotoğraf ve videoların AI tarafından üretilip üretilmediğinin kontrolü.
- [ ] **Admin Paneli**: Doğrulanmış verileri manuel onaylama ve red listesini yönetme arayüzü.

## 🚀 Dağıtım & Altyapı (DevOps)
- [ ] **Dockerization**: Tüm backend ve veri tabanının tek komutla (docker-compose) her yerde çalıştırılabilmesi.
- [ ] **CI/CD Pipeline**: GitHub Actions ile otomatik test ve deploy süreçlerinin kurulması.
- [ ] **API Gateway**: Binlerce eşzamanlı kullanıcıyı yönetmek için Nginx veya Traefik konfigürasyonu.

---

