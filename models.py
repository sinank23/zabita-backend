from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# 1. Kullanıcılar Tablosu
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(10), default="zabita")
    created_at = Column(DateTime, default=datetime.utcnow)

    inspections = relationship("Inspection", back_populates="inspector")

# 2. İşletme Kategorileri Tablosu
class BusinessCategory(Base):
    __tablename__ = "business_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    businesses = relationship("Business", back_populates="category")

# 3. İşletmeler Tablosu
class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("business_categories.id"))
    name = Column(String(150), nullable=False)
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    owner_name = Column(String(100))
    contact_info = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("BusinessCategory", back_populates="businesses")
    inspections = relationship("Inspection", back_populates="business")

    # 20.07.2026 eklendi
    google_place_id = Column(String(255), nullable=True) # google maps id

    google_reviews = relationship("GoogleReview", back_populates="business", cascade="all, delete-orphan" )
# 4. Soru Havuzu Tablosu
class InspectionCriterion(Base):
    __tablename__ = "inspection_criteria"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("business_categories.id"))
    question_text = Column(String(255), nullable=False)

    category = relationship("BusinessCategory")

# 5. Denetim Ana Kayıt (Oturum) Tablosu
class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    inspector_id = Column(Integer, ForeignKey("users.id"))
    notes = Column(Text, nullable=True)     
    ai_summary = Column(Text, nullable=True) # ai'nin değerlendirmesi
    final_score = Column(Float, nullable=True)         
    status = Column(String(20), default="pending")
    inspection_date = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="inspections")
    inspector = relationship("User", back_populates="inspections")
    answers = relationship("InspectionAnswer", back_populates="inspection")
    photos = relationship("InspectionPhoto", back_populates="inspection", cascade="all, delete-orphan")

# 6. Denetim Fotoğrafları Tablosu (BİRLEŞTİRİLMİŞ TEK VERSİYON)
class InspectionPhoto(Base):
    __tablename__ = "inspection_photos"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    photo_path = Column(String(500), nullable=False) 
    ai_analysis_result = Column(Text, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection = relationship("Inspection", back_populates="photos")

# 7. Cevaplar Tablosu
class InspectionAnswer(Base):
    __tablename__ = "inspection_answers"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"))
    criterion_id = Column(Integer, ForeignKey("inspection_criteria.id"))
    is_yes = Column(Boolean, nullable=False)

    inspection = relationship("Inspection", back_populates="answers")
    criterion = relationship("InspectionCriterion")


class GoogleReview(Base):
    __tablename__ = "google_reviews"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id")) # hangi işletmeye ait 
    author_name = Column(String(150)) #yorumu yapan kişi
    rating = Column(Float) # verdiği yıldız
    text = Column(String(1000))
    publish_date = Column(String(50))

    business = relationship("Business", back_populates="google_reviews")



