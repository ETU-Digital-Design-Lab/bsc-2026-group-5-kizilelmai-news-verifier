# KızılelmAI Doctor - Sistem Teşhis ve Onarım Betiği
# Bu betik, terminalin açılmaması veya backend'in başlamaması durumlarını çözer.

echo "🔍 KızılelmAI Sistemi Kontrol Ediliyor..."

# 1. Port 5000 Kontrolü (TCP/UDP)
$port = 5000
$process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue

if ($process) {
    echo "⚠️ Port $port şu an meşgul (PID: $($process.OwningProcess)). Temizleniyor..."
    Stop-Process -Id $process.OwningProcess -Force
    echo "✅ Port $port serbest bırakıldı."
} else {
    echo "✅ Port $port şu an boş, backend başlatılabilir."
}

# 2. Hayalet Python Süreçlerini Temizle
$pythonProcs = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($pythonProcs) {
    echo "⚠️ Arka planda $($pythonProcs.Count) adet Python süreci bulundu. Kapatılıyor..."
    Stop-Process -Name "python" -Force
}

# 3. .venv Kontrolü
if (Test-Path ".venv") {
    echo "✅ .venv klasörü bulundu."
} else {
    echo "❌ HATA: .venv bulunamadı! 'python -m venv .venv' komutunu çalıştırmanız gerekebilir."
}

echo "🚀 Sistem Hazır! Şimdi 'python src/backend/app.py' komutunu deneyebilirsiniz."
