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
    category_id: int
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

# --- DENETİM (INSPECTION) ŞEMALARI ---
class InspectionCreate(BaseModel):
    business_id: int
    notes: Optional[str] = None
    answers: List[AnswerCreate]

class InspectionResponse(BaseModel):
    id: int
    business_id: int
    inspector_id: int
    notes: Optional[str] = None
    status: str
    ai_summary: Optional[str] = None
    inspection_date: datetime
    answers: List[AnswerResponse]
    
    model_config = {"from_attributes": True}

class PhotoResponse(BaseModel):
    id: int
    photo_path: str
    ai_analysis_result: str | None = None

    model_config = {"from_attributes": True}