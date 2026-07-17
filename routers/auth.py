from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

import models
from database import SessionLocal
from services.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

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
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # 4. Üretilen kimliği mobil uygulamaya geri gönder
    return {"access_token": access_token, "token_type": "bearer"}