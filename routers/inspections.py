from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import SessionLocal

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

@router.post("/criteria/", response_model=schemas.CriteriaResponse)
def create_criteria(criteria: schemas.CriteriaCreate, db: Session = Depends(get_db)):
    # Soru eklenmek istenen kategori (Fırın, Kasap vb.) gerçekten var mı kontrol edelim
    category = db.query(models.BusinessCategory).filter(models.BusinessCategory.id == criteria.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Belirtilen kategori bulunamadı.")
    
    new_criteria = models.InspectionCriteria(**criteria.model_dump())
    db.add(new_criteria)
    db.commit()
    db.refresh(new_criteria)
    return new_criteria

# Mobil uygulama "Fırın" türündeki işletmeye girince sadece Fırın sorularını çekmek için kullanılacak endpoint
@router.get("/criteria/{category_id}", response_model=List[schemas.CriteriaResponse])
def get_criteria_by_category(category_id: int, db: Session = Depends(get_db)):
    return db.query(models.InspectionCriteria).filter(models.InspectionCriteria.category_id == category_id).all()

# --- DENETİM (INSPECTION) İŞLEMLERİ ---

@router.post("/", response_model=schemas.InspectionResponse)
def create_inspection(inspection: schemas.InspectionCreate, db: Session = Depends(get_db)):
    # Yeni bir denetim başlatma
    new_inspection = models.Inspection(**inspection.model_dump())
    db.add(new_inspection)
    db.commit()
    db.refresh(new_inspection)
    return new_inspection

@router.get("/", response_model=List[schemas.InspectionResponse])
def get_inspections(db: Session = Depends(get_db)):
    return db.query(models.Inspection).all()



# --- DENETİM CEVAPLARI (ANSWERS) İŞLEMLERİ ---

@router.post("/answers/", response_model=schemas.AnswerResponse)
def create_answer(answer: schemas.AnswerCreate, db: Session = Depends(get_db)):
    # Cevabın ait olduğu denetim (inspection) gerçekten var mı?
    inspection = db.query(models.Inspection).filter(models.Inspection.id == answer.inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Denetim kaydı bulunamadı.")
        
    # Cevaplanan soru (criteria) gerçekten var mı?
    criteria = db.query(models.InspectionCriteria).filter(models.InspectionCriteria.id == answer.criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Değerlendirilen kriter bulunamadı.")
        
    # Her iki kontrol de geçildiyse cevabı veritabanına yaz
    new_answer = models.InspectionAnswers(**answer.model_dump())
    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)
    return new_answer