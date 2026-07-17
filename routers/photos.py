from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
import models
from database import SessionLocal
import shutil
import os
from uuid import uuid4
from services.ai_vision import analyze_image_with_ai
import uuid


router = APIRouter(
    prefix="/photos",
    tags=["Fotoğraf ve AI İşlemleri"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Fotoğrafların fiziksel olarak kaydedileceği klasör
UPLOAD_DIR = "uploaded_images"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/upload/")
def upload_photo(inspection_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    # 1. Denetim kaydı sistemde var mı kontrol et
    inspection = db.query(models.Inspection).filter(models.Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Denetim bulunamadı.")
    
    # 2. Dosya ismini benzersiz yap (aynı isimli fotoğraflar birbirini ezmesin)
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # 3. Dosyayı sunucuya (bilgisayara) kaydet
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 4. Veritabanına dosya yolunu kaydet
    new_photo = models.InspectionPhoto(
        inspection_id=inspection_id,
        photo_url=file_path
    )
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)
    
    return {
        "mesaj": "Fotoğraf başarıyla yüklendi ve veritabanına işlendi.", 
        "photo_id": new_photo.id,
        "photo_url": file_path
    }

@router.post("/analyze/")
async def upload_and_analyze_photo(
    criteria_text: str = Form(..., description="Yapay zekanın denetleyeceği kural (Örn: Çalışanların örneği temiz mi.)"),
    file: UploadFile = File(...)
):
    try:
        # İlk olarak fotoğrafı güvenli bir isimle sunucuya kaydedelim
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_location = f"uploaded_images/{unique_filename}"

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # daha sonra kaydedilen fotoyu ve zabıta kriterine yapay zekaya gönderelim.
        ai_result = analyze_image_with_ai(image_path=file_location, criteria_text=criteria_text)

        return {
            "status": "success",
            "filename": unique_filename,
            "ai_analysis": ai_result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İşlem sırasında hata oluştu: {str(e)}")
    
        
