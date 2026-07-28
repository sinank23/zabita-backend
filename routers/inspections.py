import os
import shutil
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

import models
import schemas
from ai_service import analyze_inspection_photo
from database import get_db
from routers.auth import get_current_user
from services.google_service import fetch_google_reviews


router = APIRouter(
    prefix="/inspections",
    tags=["Denetim ve Kriter İşlemleri"]
)


# Fotoğrafların kaydedileceği klasör
UPLOAD_DIR = "uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


# ---------------------------------------------------------
# DENETİM KRİTERLERİ
# ---------------------------------------------------------

@router.post(
    "/criteria/",
    response_model=schemas.CriterionResponse
)
def create_criteria(
    criteria: schemas.CriterionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    category = (
        db.query(models.BusinessCategory)
        .filter(
            models.BusinessCategory.id == criteria.category_id
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Belirtilen kategori bulunamadı."
        )

    new_criteria = models.InspectionCriterion(
        **criteria.model_dump()
    )

    db.add(new_criteria)
    db.commit()
    db.refresh(new_criteria)

    return new_criteria


@router.get(
    "/criteria/{category_id}",
    response_model=List[schemas.CriterionResponse]
)
def get_criteria_by_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    criteria = (
        db.query(models.InspectionCriterion)
        .filter(
            models.InspectionCriterion.category_id == category_id
        )
        .all()
    )

    return criteria


# ---------------------------------------------------------
# DENETİM KAYDETME
# ---------------------------------------------------------

@router.post(
    "/",
    response_model=schemas.InspectionResponse
)
def create_inspection(
    inspection: schemas.InspectionCreate,
    db: Session = Depends(get_db)
):
    print("------- İSTEK BAŞARIYLA BACKEND'E ULAŞTI -------")
    print(f"Gelen İşletme: {inspection.businessName}")
    print(f"Gelen Adres: {inspection.address}")
    print(f"Gelen Cevaplar: {inspection.answers}")

    new_inspection = models.Inspection(
        businessName=inspection.businessName,
        address=inspection.address,
        answers=inspection.answers,

        # Şimdilik kullanıcı doğrulaması olmadığı için boş bırakıyoruz.
        # inspector_id=1 kullanmak, veritabanında 1 ID'li kullanıcı
        # yoksa Foreign Key hatası çıkarabilir.
        inspector_id=None,
        business_id=None
    )

    try:
        db.add(new_inspection)
        db.commit()
        db.refresh(new_inspection)

        print(
            f"Denetim başarıyla kaydedildi. "
            f"Denetim ID: {new_inspection.id}"
        )

        return new_inspection

    except Exception as error:
        db.rollback()

        print("DENETİM KAYDETME HATASI:")
        print(str(error))

        raise HTTPException(
            status_code=500,
            detail=f"Denetim kaydedilemedi: {str(error)}"
        )


@router.get(
    "/",
    response_model=List[schemas.InspectionResponse]
)
def get_inspections(
    db: Session = Depends(get_db)
):
    inspections = (
        db.query(models.Inspection)
        .order_by(models.Inspection.id.desc())
        .all()
    )

    return inspections


# ---------------------------------------------------------
# DENETİM FOTOĞRAFLARI VE YAPAY ZEKA
# ---------------------------------------------------------

@router.post(
    "/{inspection_id}/photos/",
    status_code=201
)
async def upload_inspection_photo(
    inspection_id: int,
    files: List[UploadFile] = File(...),  # artık çoklu fotoğraflar için liste bekleniyor.
    db: Session = Depends(get_db)
):
    # denetim var mı kontrolünü yaptık
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



    # gelen her foto için döngğ açıyoruz
    for file in files:
        if not file.filename:
            continue

        file_extension = file.filename.split(".")[-1]

        unique_id = uuid.uuid4().hex[:8]
        new_filename = f"inspection_{inspection_id}_{unique_id}.{file_extension}"

        file_path = os.path.join(UPLOAD_DIR, new_filename)



    # fotoyu sunucuya kaydetme işlemi
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Fotoğraf kaudedilemedi: {str(error)}"
        )

    # yapay zeka analizini yapma işlemi
    try:
        ai_result = await analyze_inspection_photo(file_path)
    except Exception as error:
        ai_result = f"Yapay zeka analizi başarısız oldu: {str(error)}"

    # veritabanı modeli için kayıt
    new_photo = models.InspectionPhoto(
        inspection_id = inspection_id,
        photo_path=file_path,
        ai_analysis_result=ai_result
    )
    db.add(new_photo)
    uploaded_photos.append(new_photo)

    # tüm fotoğrafları topluca vt kaydet
    try:
        db.commit()
        for photo in uploaded_photos:
            db.refresh(photo)
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Fotoğraf bilgileri veritabanına kaydedilmedi: {str(error)}"


        )

    return {
        "message": f"{len(uploaded_photos)} fotoğraf başarıyla yüklendi ve analiz edildi.",
        "photos": [
            {
                "photo_id": p.id,
                "photo_path": p.photo_path,
                "ai_result": p.ai_analysis_result

            } for p in uploaded_photos
        ]
    }

@router.get(
    "/{inspection_id}/photos/",
    response_model=List[schemas.PhotoResponse]
)
def get_inspection_photos(
    inspection_id: int,
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

    photos = (
        db.query(models.InspectionPhoto)
        .filter(
            models.InspectionPhoto.inspection_id
            == inspection_id
        )
        .all()
    )

    return photos


# ---------------------------------------------------------
# DENETİM PUANI HESAPLAMA
# ---------------------------------------------------------

@router.post("/{inspection_id}/complete")
def complete_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
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

    answer_records = (
        db.query(models.InspectionAnswer)
        .filter(
            models.InspectionAnswer.inspection_id
            == inspection_id
        )
        .all()
    )

    # Ayrı inspection_answers tablosunda cevap varsa
    if answer_records:
        total_questions = len(answer_records)

        yes_answers = sum(
            1
            for answer in answer_records
            if answer.is_yes
        )

        calculated_score = (
            yes_answers / total_questions
        ) * 100

        return {
            "message": "Denetim puanı hesaplandı.",
            "inspection_id": inspection.id,
            "score": calculated_score,
            "total_questions": total_questions,
            "yes_answers": yes_answers
        }

    # Cevaplar JSON olarak kaydedilmişse
    if inspection.answers:
        if isinstance(inspection.answers, list):
            total_questions = len(
                inspection.answers
            )

            if total_questions == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cevap listesi boş."
                )

            yes_answers = sum(
                1
                for answer in inspection.answers
                if answer is True
            )

            calculated_score = (
                yes_answers / total_questions
            ) * 100

            return {
                "message": (
                    "Denetim puanı JSON cevaplarından "
                    "hesaplandı."
                ),
                "inspection_id": inspection.id,
                "score": calculated_score,
                "total_questions": total_questions,
                "yes_answers": yes_answers
            }

    raise HTTPException(
        status_code=400,
        detail=(
            "Bu denetime ait cevap bulunamadı. "
            "Puan hesaplanamaz."
        )
    )


# ---------------------------------------------------------
# GOOGLE YORUMLARI
# ---------------------------------------------------------

@router.post(
    "/{business_id}/sync-reviews",
    status_code=201
)
async def sync_business_reviews(
    business_id: int,
    db: Session = Depends(get_db)
):
    business = (
        db.query(models.Business)
        .filter(models.Business.id == business_id)
        .first()
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="İşletme bulunamadı."
        )

    if not business.google_place_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "İşletmenin Google Place ID bilgisi "
                "tanımlı değil."
            )
        )

    reviews = await fetch_google_reviews(
        business.google_place_id
    )

    try:
        for review in reviews:
            new_review = models.GoogleReview(
                business_id=business_id,
                author_name=review.get("author_name"),
                rating=review.get("rating"),
                text=review.get("text"),
                publish_date=review.get("publish_date")
            )

            db.add(new_review)

        db.commit()

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Google yorumları kaydedilemedi: "
                f"{str(error)}"
            )
        )

    return {
        "message": (
            f"{len(reviews)} adet yorum "
            "başarıyla senkronize edildi."
        )
    }