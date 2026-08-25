from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- KULLANICI (USER) ŞEMALARI ---
class UserBase(BaseModel):
    full_name: str
    email: str
    role: Optional[str] = "zabita"

# yeni kullanıcı oluşturulurken istemciden gelen veri.
class UserCreate(UserBase):
    password: str 

    #24.08.2026
# Süper Admin tarafından kullanıcı bilgilerini güncellemek için
class UserUpdate(BaseModel):
    full_name: str
    email: str
    role: str
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}  # pydanticin json verisini okuması için

# --- KATEGORİ (CATEGORY) ŞEMALARI ---
class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}

# --- İŞLETME (BUSINESS) ŞEMALARI ---
class BusinessBase(BaseModel):
    name: str
    category_id: int 
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    owner_name: Optional[str] = None
    contact_info: Optional[str] = None

class BusinessCreate(BusinessBase):
    pass
    google_place_id: Optional[str] = None   

class BusinessResponse(BusinessBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}

# --- DENETİM KRİTERLERİ (CRITERIA) ŞEMALARI ---
class CriterionBase(BaseModel):
    category_id: int | None = None
    question_text: str

class CriterionCreate(CriterionBase):
    pass

class CriterionResponse(CriterionBase):
    id: int
    model_config = {"from_attributes": True}

# --- DENETİM CEVAPLARI (ANSWERS) ŞEMALARI ---
class AnswerBase(BaseModel):
    criterion_id: int
    is_yes: bool

class AnswerCreate(AnswerBase):
    pass

class AnswerResponse(AnswerBase):
    id: int
    inspection_id: int
    model_config = {"from_attributes": True}

class InspectionAnswerCreate(BaseModel):
    criterion_id: int
    is_yes: bool

# --- DENETİM (INSPECTION) ŞEMALARI ---
class InspectionCreate(BaseModel):
    businessName: str
    address: str
    answers: list[bool]
    answer_records: list[InspectionAnswerCreate] = []

    #30.07.2026 tarihinde eklenen not
    inspector_notes: Optional[str] = None
    business_id: int | None = None

    # 31.07.2026
    latitude: float | None = None
    longitude: float | None = None

# güncelleme 04.08.2026
class InspectionResponse(BaseModel):
    id: int
    businessName: str
    address: str | None = None
    answers: list[bool]

    inspector_notes: str | None = None
    inspector_id: int | None = None
    business_id: int | None = None
    category_name: str | None = None
    owner_name: str | None = None
    contact_info: str | None = None
    # Denetimi yapan personelin ad soyad bilgisini Android'e gönder
    inspector_name: str | None = None   

    status: str | None = None
    ai_summary: str | None = None
    inspection_date: datetime | None = None

    latitude: float | None = None
    longitude: float | None = None

    
    model_config = {"from_attributes": True}


    
class PhotoResponse(BaseModel):
    id: int
    photo_path: str
    ai_analysis_result: str | None = None

    model_config = {"from_attributes": True}


# 31.07.2026
# google yorumlarını get etme işlemi uygulamaya
class ReviewResponse(BaseModel):
    id: int
    author_name: str
    rating: float
    text: str | None = None
    publish_date: str | None = None

    class Config:
        from_attributes = True

class InspectionAnswerResponse(BaseModel):
    criterion_id: int
    question_text: str
    is_yes: bool

    model_config = {"from_attributes": True}

#25.08.2026 
#trafik zabıta şemaları
class TrafficInspectionCreate(BaseModel):
    violation_type: str
    plate: str
    vehicle_type: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    action_taken: Optional[str] = None


#25.08.2026
# Trafik işlem kaydı Android tarafına dönerken kullanılacak veri
class TrafficInspectionResponse(BaseModel):
    id: int
    violation_type: str
    plate: str
    vehicle_type: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    action_taken: Optional[str] = None
    status: Optional[str] = None
    inspector_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
