import os
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext   # şifre doğrulama işlemleri
import jwt
from dotenv import load_dotenv

load_dotenv()        # env dosyasını okur

# Şifreleme algosu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# .env dosyasından gizli anahtarı çekiyoruz.


                        #bulursa bunu       # bulamazsa bunu kullanacak
SECRET_KEY = os.getenv("SECRET_KEY", "yedek-gizli-anahtar-123")
ALGORITHM = "HS256"         #HS256, aynı gizli anahtarın hem token oluştururken hem de doğrularken kullanıldığı simetrik bir algoritmadır.
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # TOKEN 1 GÜN GEÇERLİ OLSUN

# sistemdeki şifre ile veritabanındanki şifreli metni karşılaştır
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# yeni kayıt olan birinin şifresini karmaşık hale getir yani hashleme işlemi
def get_password_hash(password):
    return pwd_context.hash(password)

# giriş başarılıysa memura dijital kimlik JWT üretir
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15) 
        to_encode.update({"exp": expire})
        
        # burada gerçek token oluşturuluyor
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)     
    return encoded_jwt

# expires_delta tokenin ne kadar süreli geçerli olduğunu söyler.