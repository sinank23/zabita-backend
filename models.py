from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

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

    inspections = relationship(
        "Inspection",
        back_populates="inspector"
    )


# 2. İşletme Kategorileri Tablosu
class BusinessCategory(Base):
    __tablename__ = "business_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    businesses = relationship(
        "Business",
        back_populates="category"
    )


# 3. İşletmeler Tablosu
class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)

    category_id = Column(
        Integer,
        ForeignKey("business_categories.id"),
        nullable=True
    )

    name = Column(String(150), nullable=False)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    owner_name = Column(String(100), nullable=True)
    contact_info = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Google Maps işletme kimliği
    google_place_id = Column(String(255), nullable=True)

    category = relationship(
        "BusinessCategory",
        back_populates="businesses"
    )

    inspections = relationship(
        "Inspection",
        back_populates="business"
    )

    google_reviews = relationship(
        "GoogleReview",
        back_populates="business",
        cascade="all, delete-orphan"
    )


# 4. Soru Havuzu Tablosu
class InspectionCriterion(Base):
    __tablename__ = "inspection_criteria"

    id = Column(Integer, primary_key=True, index=True)

    category_id = Column(
        Integer,
        ForeignKey("business_categories.id"),
        nullable=True
    )

    question_text = Column(String(255), nullable=False)

    category = relationship("BusinessCategory")

    answer_records = relationship(
        "InspectionAnswer",
        back_populates="criterion"
    )


# 5. Denetim Ana Kayıt Tablosu
class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)

    # Android uygulamasından gelen temel denetim bilgileri
    businessName = Column(String(150), index=True, nullable=False)
    address = Column(String(500), nullable=True)

    # Checkbox cevaplarını JSON olarak tutuyoruz
    answers = Column(JSON, nullable=True)

    # memurun not yazmaası için (30.07.2026)
    inspector_notes = Column(String, nullable=True)

    inspector_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    business_id = Column(
        Integer,
        ForeignKey("businesses.id"),
        nullable=True
    )

    status = Column(String(50), default="Bekliyor", nullable=True)
    ai_summary = Column(Text, nullable=True)
    inspection_date = Column(DateTime, default=datetime.utcnow, nullable=True)

    # 31.07.2026 eklendi.
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    inspector = relationship(
        "User",
        back_populates="inspections"
    )

    business = relationship(
        "Business",
        back_populates="inspections"
    )

    # Bir denetimin birden fazla fotoğrafı olabilir
    photos = relationship(
        "InspectionPhoto",
        back_populates="inspection",
        cascade="all, delete-orphan"
    )

    # Ayrı inspection_answers tablosundaki cevap kayıtları
    # JSON olan "answers" alanıyla çakışmaması için adı answer_records
    answer_records = relationship(
        "InspectionAnswer",
        back_populates="inspection",
        cascade="all, delete-orphan"
    )


    



# 6. Denetim Fotoğrafları Tablosu
class InspectionPhoto(Base):
    __tablename__ = "inspection_photos"

    id = Column(Integer, primary_key=True, index=True)

    inspection_id = Column(
        Integer,
        ForeignKey("inspections.id"),
        nullable=False
    )

    photo_path = Column(String(500), nullable=False)
    ai_analysis_result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection = relationship(
        "Inspection",
        back_populates="photos"
    )


# 7. Denetim Cevapları Tablosu
class InspectionAnswer(Base):
    __tablename__ = "inspection_answers"

    id = Column(Integer, primary_key=True, index=True)

    inspection_id = Column(
        Integer,
        ForeignKey("inspections.id"),
        nullable=False
    )

    criterion_id = Column(
        Integer,
        ForeignKey("inspection_criteria.id"),
        nullable=False
    )

    is_yes = Column(Boolean, nullable=False)

    inspection = relationship(
        "Inspection",
        back_populates="answer_records"
    )

    criterion = relationship(
        "InspectionCriterion",
        back_populates="answer_records"
    )


# 8. Google Yorumları Tablosu
class GoogleReview(Base):
    __tablename__ = "google_reviews"

    id = Column(Integer, primary_key=True, index=True)

    business_id = Column(
        Integer,
        ForeignKey("businesses.id"),
        nullable=False
    )

    author_name = Column(String(150), nullable=True)
    rating = Column(Float, nullable=True)
    text = Column(Text, nullable=True)
    publish_date = Column(String(50), nullable=True)

    business = relationship(
        "Business",
        back_populates="google_reviews"
    )