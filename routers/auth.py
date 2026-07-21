from fastapi import APIRouter, Depends, HTTPException, status
# OAuth2PasswordBearer eksikti, eklendi
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import timedelta
# Token çözmek için gereken kütüphane eklendi
from jose import JWTError, jwt

import models
from database import SessionLocal
# Şifreleme servislerinden gereken her şey (SECRET_KEY ve ALGORITHM dahil) eklendi
from services.security import (
    verify_password, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM
)

# Token'ın alınacağı uç nokta. main.py'de auth router'ını prefix="/auth" ile eklediğini varsayıyoruz.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(
    tags=["Authentication"]
)

# Veritabanı bağlantısı için bağımlılık
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Veritabanından kullanıcıyı e-posta (username) ile bul
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # 2. Kullanıcı yoksa veya şifre yanlışsa hata fırlat
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. Şifre doğruysa memura dijital kimlik (token) üret
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        # Burada token içine "sub" olarak kullanıcının email'ini koyuyoruz
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # 4. Üretilen kimliği mobil/frontend uygulamaya geri gönder
    return {"access_token": access_token, "token_type": "bearer"}

# --- EKSİK OLAN VE IMPORTERROR VERDİREN FONKSİYON ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz kimlik bilgileri (Token doğrulanamadı veya süresi doldu)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Token'ı gizli anahtarımızla çözüyoruz
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Login'de sub içine email koyduğumuz için, email'i geri okuyoruz
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # Çözülen email ile veritabanında zabıta personelini (User) arıyoruz
    user = db.query(models.User).filter(models.User.email == email).first() 
# 



    if user is None:                 
        raise credentials_exception
    

        
    return user