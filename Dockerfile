FROM python:3.10-slim

WORKDIR /app

# Sistem bağımlılıklarını kur (psycopg2 ve diğer C kütüphaneleri için)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY . .

# Portu aç
EXPOSE 5000

# Backend'i başlat
CMD ["uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "5000"]
