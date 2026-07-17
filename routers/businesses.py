from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
# get_db yerine doğrudan SessionLocal'ı çağırıyoruz
from database import SessionLocal 
from routers.auth import get_current_user

router = APIRouter(
    prefix="/businesses",
    tags=["Businesses"]
)

# Senin mimarine uygun olan veritabanı bağlantı fonksiyonu
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.BusinessResponse, status_code=status.HTTP_201_CREATED)
def create_business(
    business: schemas.BusinessCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    # İşletme adında çakışma var mı kontrolü
    existing_business = db.query(models.Business).filter(models.Business.name == business.name).first()
    if existing_business:
        raise HTTPException(status_code=400, detail="Bu isimde bir işletme zaten kayıtlı.")

    new_business = models.Business(**business.model_dump())
    db.add(new_business)
    db.commit()
    db.refresh(new_business)
    
    return new_business

@router.get("/", response_model=List[schemas.BusinessResponse])
def get_businesses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    businesses = db.query(models.Business).all()
    return businesses



@router.get("/{business_id}", response_model=schemas.BusinessResponse)
def get_business_by_id(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    business = db.query(models.Business).filter(
        models.Business.id == business_id
    ).first()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="İşletme bulunamadı."
        )

    return business