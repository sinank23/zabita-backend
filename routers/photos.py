import os
import shutil
import uuid
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

import models
from database import get_db
from services.ai_vision import analyze_image_with_ai


router = APIRouter(
    prefix="/photos",
    tags=["Fotoğraf ve AI İşlemleri"]
)


# Fotoğrafların fiziksel olarak kaydedileceği klasör
UPLOAD_DIR = "uploaded_images"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


# ---------------------------------------------------------
# FOTOĞRAFLARI DENETİME KAYDETME
# ---------------------------------------------------------

@router.post("/upload/{inspection_id}")
def upload_photos(
    inspection_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id)
        .first()
    )

    if not inspection:
        raise HTTPException(
            status_code=404,
            detail="Denetim bulunamadı."
        )

    uploaded_photos = []
    saved_file_paths = []

    try:
        for file in files:
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="Fotoğraf dosyasının adı bulunamadı."
                )

            file_extension = file.filename.rsplit(".", 1)[-1]

            unique_filename = (
                f"{uuid4()}.{file_extension}"
            )

            file_path = os.path.join(
                UPLOAD_DIR,
                unique_filename
            )

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(
                    file.file,
                    buffer
                )

            saved_file_paths.append(file_path)

            new_photo = models.InspectionPhoto(
                inspection_id=inspection_id,

                # Modelde photo_url değil photo_path var
                photo_path=file_path,

                ai_analysis_result=None
            )

            db.add(new_photo)
            db.flush()

            uploaded_photos.append({
                "photo_id": new_photo.id,
                "photo_path": new_photo.photo_path
            })

        db.commit()

    except HTTPException:
        db.rollback()

        for file_path in saved_file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)

        raise

    except Exception as error:
        db.rollback()

        # Veritabanına yazılamadıysa fiziksel dosyaları da silelim
        for file_path in saved_file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)

        raise HTTPException(
            status_code=500,
            detail=(
                "Fotoğraflar kaydedilemedi: "
                f"{str(error)}"
            )
        )

    return {
        "message": (
            "Fotoğraflar başarıyla yüklendi "
            "ve veritabanına kaydedildi."
        ),
        "photos": uploaded_photos
    }


# ---------------------------------------------------------
# FOTOĞRAFI YAPAY ZEKÂ İLE ANALİZ ETME
# ---------------------------------------------------------

@router.post("/analyze/")
async def upload_and_analyze_photo(
    criteria_text: str = Form(
        ...,
        description=(
            "Yapay zekânın kontrol edeceği denetim kuralı."
        )
    ),
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Fotoğraf dosyasının adı bulunamadı."
        )

    file_extension = file.filename.rsplit(".", 1)[-1]

    unique_filename = (
        f"{uuid.uuid4()}.{file_extension}"
    )

    file_location = os.path.join(
        UPLOAD_DIR,
        unique_filename
    )

    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

        ai_result = analyze_image_with_ai(
            image_path=file_location,
            criteria_text=criteria_text
        )

        return {
            "status": "success",
            "filename": unique_filename,
            "file_path": file_location,
            "ai_analysis": ai_result
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "İşlem sırasında hata oluştu: "
                f"{str(error)}"
            )
        )