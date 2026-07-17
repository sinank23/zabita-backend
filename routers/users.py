from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import models
import schemas
from database import SessionLocal
from services.security import get_password_hash

# Router'ımızı oluşturuyoruz (Danışmanın yönlendireceği departman)
router = APIRouter(
    prefix="/users",
    tags=["Kullanıcı İşlemleri"]
)

# GÜVENLİK KİLİDİ: Sisteme giriş yapılıp token alınacak kapının adresini tanımlıyoruz
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Veritabanı bağlantısı için bağımlılık
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        # 1. E-posta adresi sistemde zaten var mı kontrolü
        db_user = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Bu email adresi zaten kayıtlı.")
        
        # 2. Şifreyi güvenlik motorumuzla gerçek anlamda kriptoluyoruz
        real_hashed_password = get_password_hash(user.password) 
        
        # 3. Yeni kullanıcıyı şifrelenmiş parola ile oluşturuyoruz
        new_user = models.User(
            full_name=user.full_name,
            email=user.email,
            password_hash=real_hashed_password,
            role=user.role
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
        
    except Exception as e:
        # HATA OLURSA ÇÖKME, HATANIN NE OLDUĞUNU SWAGGER'A GÖNDER!
        raise HTTPException(status_code=500, detail=f"SİSTEM HATASI: {str(e)}")

# KİLİTLİ ODA TESTİ (Sadece Token ile girilebilir)
@router.get("/me")
def test_guvenli_alan(token: str = Depends(oauth2_scheme)):
    return {
        "mesaj": "Tebrikler! Güvenlik duvarını aştınız ve güvenli alana girdiniz.",
        "sizin_dijital_kimliginiz": token
    }