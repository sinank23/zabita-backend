from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- KULLANICI (USER) ŞEMALARI ---

# Ortak özellikler (Hem kayıt olurken hem de veri okurken kullanılacak alanlar)
class UserBase(BaseModel):
    full_name: str
    email: str
    role: Optional[str] = "zabita"

# API'ye kullanıcı eklerken beklediğimiz JSON formatı
class UserCreate(UserBase):
    password: str # API'ye düz şifre gelir, arkada hash'lenip veritabanına yazılır.

# Veritabanından mobil uygulamaya veri gönderirken kullanacağımız format (Şifre yok, ID var)
class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        # SQLAlchemy modellerini doğrudan okuyabilmesi için bu ayarı açıyoruz
        from_attributes = True 

# --- İŞLETME (BUSINESS) ŞEMALARI ---

class BusinessBase(BaseModel):
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    owner_name: Optional[str] = None
    contact_info: Optional[str] = None
    category_id: int

class BusinessCreate(BusinessBase):
    pass # Ekstra bir alana ihtiyaç yok, Base'deki her şey geçerli

class BusinessResponse(BusinessBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- KATEGORİ (CATEGORY) ŞEMALARI ---

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- DENETİM MADDELERİ (CRITERIA) ŞEMALARI ---

class CriteriaBase(BaseModel):
    category_id: int
    question_text: str
    max_score: Optional[int] = 10

class CriteriaCreate(CriteriaBase):
    pass

class CriteriaResponse(CriteriaBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- DENETİM (INSPECTION) ŞEMALARI ---

class InspectionBase(BaseModel):
    business_id: int
    zabita_id: int
    zabita_notes: Optional[str] = None
    status: Optional[str] = "pending"

class InspectionCreate(InspectionBase):
    pass

class InspectionResponse(InspectionBase):
    id: int
    ai_calculated_score: Optional[float] = None
    final_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- DENETİM CEVAPLARI (ANSWERS) ŞEMALARI ---

class AnswerBase(BaseModel):
    inspection_id: int
    criteria_id: int
    is_compliant: bool # True (Evet/Uygun) veya False (Hayır/Uygun Değil)

class AnswerCreate(AnswerBase):
    pass

class AnswerResponse(AnswerBase):
    id: int

    class Config:
        from_attributes = True



# DENETİM FOTOĞRAFLARI TABLOSU

