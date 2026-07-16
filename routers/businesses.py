from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import SessionLocal

# İşte main.py'nin arayıp da bulamadığı o meşhur 'router' değişkeni burası:
router = APIRouter(
    prefix="/businesses",
    tags=["İşletme ve Kategori İşlemleri"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- KATEGORİ İŞLEMLERİ ---

@router.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    new_category = models.BusinessCategory(name=category.name)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@router.get("/categories/", response_model=List[schemas.CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.BusinessCategory).all()

# --- İŞLETME İŞLEMLERİ ---

@router.post("/", response_model=schemas.BusinessResponse)
def create_business(business: schemas.BusinessCreate, db: Session = Depends(get_db)):
    category = db.query(models.BusinessCategory).filter(models.BusinessCategory.id == business.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Belirtilen kategori bulunamadı.")
        
    new_business = models.Business(**business.model_dump())
    db.add(new_business)
    db.commit()
    db.refresh(new_business)
    return new_business

@router.get("/", response_model=List[schemas.BusinessResponse])
def get_businesses(db: Session = Depends(get_db)):
    return db.query(models.Business).all()