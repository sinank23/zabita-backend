from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import SessionLocal
from routers.auth import get_current_user

router = APIRouter(
    prefix="/inspections",
    tags=["Denetim ve Kriter İşlemleri"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- DENETİM KRİTERLERİ (SORULAR) ---

@router.post("/criteria/", response_model=schemas.CriterionResponse)
def create_criteria(criteria: schemas.CriterionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    category = db.query(models.BusinessCategory).filter(models.BusinessCategory.id == criteria.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Belirtilen kategori bulunamadı.")
    
    new_criteria = models.InspectionCriterion(**criteria.model_dump())
    db.add(new_criteria)
    db.commit()
    db.refresh(new_criteria)
    return new_criteria

@router.get("/criteria/{category_id}", response_model=List[schemas.CriterionResponse])
def get_criteria_by_category(category_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.InspectionCriterion).filter(models.InspectionCriterion.category_id == category_id).all()

# --- DENETİM VE CEVAPLARI TEK SEFERDE KAYDETME (TRANSACTION) ---

@router.post("/", response_model=schemas.InspectionResponse)
def create_inspection(inspection: schemas.InspectionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.id == inspection.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı.")

    new_inspection = models.Inspection(
        business_id=inspection.business_id,
        inspector_id=current_user.id,
        notes=inspection.notes
    )
    db.add(new_inspection)
    db.flush() 

    for answer in inspection.answers:
        new_answer = models.InspectionAnswer(
            inspection_id=new_inspection.id,
            criterion_id=answer.criterion_id,  
            is_yes=answer.is_yes
        )
        db.add(new_answer)

    db.commit()
    db.refresh(new_inspection)
    
    return new_inspection

@router.get("/", response_model=List[schemas.InspectionResponse])
def get_inspections(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Inspection).all()