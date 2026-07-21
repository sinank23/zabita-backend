import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from ai_service import analyze_inspection_photo
from database import get_db
import models
import schemas
from routers.auth import get_current_user

router = APIRouter(
    prefix="/inspections",
    tags=["Denetim ve Kriter İşlemleri"]
)

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
    # Tüm denetimleri getir (İlişkili tablolarla birlikte)
    return db.query(models.Inspection).all()

# --- DENETİM FOTOĞRAFLARI VE YAPAY ZEKA ---

@router.post("/{inspection_id}/photos/", status_code=201)
async def upload_inspection_photo(
    inspection_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Fotoğrafın ekleneceği denetim gerçekten var mı kontrol et
    inspection = db.query(models.Inspection).filter(models.Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Denetim bulunamadı")

    # 2. Dosya yolunu ayarla
    file_extension = file.filename.split(".")[-1]
    new_filename = f"inspection_{inspection_id}_{file.filename}"
    file_path = f"uploads/{new_filename}"

    # 3. Dosyayı fiziksel olarak uploads klasörüne kaydet
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fotoğraf kaydedilemedi: {str(e)}")

    # 4. Yapay Zeka Analizini Başlat
    ai_result = await analyze_inspection_photo(file_path)

    # 5. Veritabanına dosya yolunu ve yapay zeka sonucunu kaydet
    new_photo = models.InspectionPhoto(
        inspection_id=inspection_id,
        photo_path=file_path,
        ai_analysis_result=ai_result 
    )
    
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)

    return {
        "message": "Fotoğraf başarıyla yüklendi ve analiz edildi", 
        "photo_id": new_photo.id, 
        "photo_path": new_photo.photo_path,
        "ai_result": new_photo.ai_analysis_result 
    }

@router.get("/{inspection_id}/photos/", response_model=List[schemas.PhotoResponse])
def get_inspection_photos(inspection_id: int, db: Session = Depends(get_db)):
    # İlgili denetime ait tüm fotoğrafları veritabanından çek
    photos = db.query(models.InspectionPhoto).filter(models.InspectionPhoto.inspection_id == inspection_id).all()
    return photos


@router.post("/{inspection_id}/complete", response_model=schemas.InspectionResponse)
def complete_inspection(
    inspection_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # 1. Denetimi bul
    inspection = db.query(models.Inspection).filter(models.Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Denetim bulunamadı.")
        
    # 2. Denetime ait cevapları getir
    answers = db.query(models.InspectionAnswer).filter(models.InspectionAnswer.inspection_id == inspection_id).all()
    if not answers:
        raise HTTPException(status_code=400, detail="Bu denetime ait hiç cevap girilmemiş, puan hesaplanamaz.")
        
    # 3. Puan Hesaplama Mantığı (Basit Orantı: (Evet Sayısı / Toplam Soru) * 100)
    total_questions = len(answers)
    yes_answers = sum(1 for a in answers if a.is_yes)
    
    calculated_score = (yes_answers / total_questions) * 100
    
    # 4. Veritabanını Güncelle
    inspection.final_score = calculated_score
    inspection.status = "completed"
    
    db.commit()
    db.refresh(inspection)
    
    return inspection


from services.google_service import fetch_google_reviews

@router.post("/{business_id}/sync-reviews", status_code=201)
async def sync_business_reviews(business_id: int, db: Session = Depends(get_db)):
    # 1. İşletmeyi bul
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if not business or not business.google_place_id:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı veya Google Place ID'si tanımlı değil.")

    # 2. Google'dan yorumları çek (Az önce yazdığımız simülasyon servisi)
    reviews = await fetch_google_reviews(business.google_place_id)

    # 3. Yorumları veritabanına kaydet
    for review in reviews:
        new_review = models.GoogleReview(
            business_id=business_id,
            author_name=review["author_name"],
            rating=review["rating"],
            text=review["text"],
            publish_date=review["publish_date"]
        )
        db.add(new_review)
    
    db.commit()
    
    return {"message": f"{len(reviews)} adet yorum başarıyla senkronize edildi."}