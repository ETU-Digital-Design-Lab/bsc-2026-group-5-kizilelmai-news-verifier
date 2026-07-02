import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor

# Load env variables for SMTP
load_dotenv()

# JWT Config
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "kizilelma_super_secret_jwt_key_please_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 1 week

# Passlib Config
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# DB Connection String
DB_DSN = os.environ.get("DATABASE_URL", "postgresql://kizilelmai_user:kizilelmai_pass@localhost:5433/kizilelmai")

def get_db_connection():
    conn = psycopg2.connect(DB_DSN, cursor_factory=DictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            is_verified BOOLEAN DEFAULT FALSE,
            verify_code TEXT,
            first_name TEXT,
            last_name TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_logs (
            id SERIAL PRIMARY KEY,
            user_email TEXT,
            query TEXT NOT NULL,
            response_status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            user_email TEXT,
            news_query TEXT NOT NULL,
            news_details TEXT,
            report_reason TEXT NOT NULL,
            admin_response TEXT,
            status TEXT DEFAULT 'pending',
            source_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Varsayılan admin hesabını ekle (eğer yoksa)
    cursor.execute("SELECT * FROM users WHERE email = 'admin'")
    if not cursor.fetchone():
        hashed_pw = pwd_context.hash("1234")
        cursor.execute('''
            INSERT INTO users (email, password_hash, role, is_verified, first_name, last_name)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', ("admin", hashed_pw, "admin", True, "Sistem", "Yöneticisi"))
        
    conn.commit()
    conn.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_verification_email(to_email: str, code: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_email = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    if not smtp_email or not smtp_password:
        print(f"⚠️ SMTP Ayarları eksik! {to_email} adresine mail atılamadı. Doğrulama kodu: {code}")
        return False
        
    try:
        msg = MIMEMultipart('related')
        msg['From'] = smtp_email
        msg['To'] = to_email
        msg['Subject'] = "KızılelmAI - Hesap Doğrulama Kodunuz"
        
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)
        
        # Plain text fallback
        body_plain = f"Merhaba,\nKızılelmAI sistemine kayıt olduğunuz için teşekkürler.\nDoğrulama kodunuz: {code}\nSisteme girerek kaydınızı tamamlayabilirsiniz."
        msg_alternative.attach(MIMEText(body_plain, 'plain', 'utf-8'))
        
        # HTML version
        body_html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f4f4f5; padding: 20px; text-align: center;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
              <img src="cid:logo_image" alt="KızılelmAI Logo" style="width: 150px; height: auto; margin-bottom: 20px;" />
              <h2 style="color: #333333; margin-bottom: 10px;">Hoş Geldiniz!</h2>
              <p style="color: #666666; font-size: 16px; line-height: 1.5; margin-bottom: 20px;">
                KızılelmAI sistemine kayıt olduğunuz için teşekkür ederiz. Hesabınızı güvenle aktifleştirmek için aşağıdaki doğrulama kodunu kullanabilirsiniz.
              </p>
              <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h1 style="color: #e63946; margin: 0; font-size: 32px; letter-spacing: 5px;">{code}</h1>
              </div>
              <p style="color: #999999; font-size: 14px;">
                Eğer bu isteği siz yapmadıysanız lütfen bu e-postayı dikkate almayın.
              </p>
            </div>
          </body>
        </html>
        """
        msg_alternative.attach(MIMEText(body_html, 'html', 'utf-8'))
        
        # Attach Image
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "public", "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', '<logo_image>')
                img.add_header('Content-Disposition', 'inline', filename='logo.png')
                msg.attach(img)
        else:
            print(f"⚠️ Uyarı: Logo dosyası bulunamadı ({logo_path}), maile logo eklenemedi.")
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Mail gönderme hatası: {e}")
        return False

# Veritabanını başlat
init_db()
