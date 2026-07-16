from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import models
from database import SessionLocal
import shutil
import os
from uuid import uuid4

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