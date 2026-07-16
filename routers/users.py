from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
import schemas
from database import SessionLocal

# Router'ımızı oluşturuyoruz (Danışmanın yönlendireceği departman)
router = APIRouter(
    prefix="/users",
    tags=["Kullanıcı İşlemleri"]
)

# Veritabanı bağlantısı için bağımlılık
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dikkat: prefix="/users" olduğu için buraya sadece "/" yazıyoruz.
# Yani adres otomatik olarak "/users/" oluyor.
@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Bu email adresi zaten kayıtlı.")
    
    fake_hashed_password = user.password + "_hashed" 
    
    new_user = models.User(
        full_name=user.full_name,
        email=user.email,
        password_hash=fake_hashed_password,
        role=user.role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user