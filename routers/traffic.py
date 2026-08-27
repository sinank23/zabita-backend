import os
import shutil
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

import models
import schemas

from database import get_db
from routers.auth import get_current_user
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

router = APIRouter(
    prefix="/traffic",
    tags=["Trafik Zabıta İşlemleri"]
)

#27.08.2026
#trafik zabıta fotoğraflarının kaydedileceği klasör
TRAFFIC_UPLOAD_DIR = os.path.join("uploads", "traffic")

if not os.path.exists(TRAFFIC_UPLOAD_DIR):
    os.makedirs(TRAFFIC_UPLOAD_DIR)

    #27.08.2026
# trafik zabıta PDF raporlarının kaydedileceği klasör
TRAFFIC_REPORT_DIR = os.path.join("reports", "traffic")

if not os.path.exists(TRAFFIC_REPORT_DIR):
    os.makedirs(TRAFFIC_REPORT_DIR)

#25.08.2026
#yeni trafik işlem kaydı oluştrumak için

@router.post(
    "/",
    response_model=schemas.TrafficInspectionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_traffic_inspection(
    traffic_data: schemas.TrafficInspectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # sadece trafik zabıta işlem yapabilsin
    if current_user.role != "trafik_zabita":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Trafik Zabıta yetkisi gereklidir."
        )
    try:
        new_traffic_inspection = models.TrafficInspection(
            violation_type=traffic_data.violation_type,
            plate=traffic_data.plate,
            vehicle_type=traffic_data.vehicle_type,
            address=traffic_data.address,
            latitude=traffic_data.latitude,
            longitude=traffic_data.longitude,
            description=traffic_data.description,
            action_taken=traffic_data.action_taken,
            inspector_id=current_user.id
        )

        db.add(new_traffic_inspection)
        db.commit()
        db.refresh(new_traffic_inspection)

        return new_traffic_inspection

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trafik işlemi oluşturulurken hata oluştu: {str(e)}"
        )

    
#26.08.2026
# trafik zabıta kayıtlarının getirilmesi iiçin
@router.get(
    "/",
    response_model=list[schemas.TrafficInspectionResponse]
)
def get_traffic_inspections(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    
    # sadece trafik zabıta görebilsin
    if current_user.role != "trafik_zabita":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için trafik zabıtası yetkilidir."
        )

    traffic_records = (
        db.query(models.TrafficInspection)
        .order_by(models.TrafficInspection.id.desc())
        .all()
    )

    return traffic_records

#27.08.2026
# trafik zabıta işlem kaydına fotoğraf yüklemek için
@router.post(
    "/{traffic_inspection_id}/photos/",
    status_code=status.HTTP_201_CREATED
)
async def upload_traffic_inspection_photo(
    traffic_inspection_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # sadece trafik zabıta personeli fotoğraf yükleyebilsin
    if current_user.role != "trafik_zabita":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Trafik Zabıta yetkisi gereklidir."
        )

    # fotoğrafın bağlanacağı trafik kaydı var mı kontrol et
    traffic_inspection = (
        db.query(models.TrafficInspection)
        .filter(
            models.TrafficInspection.id == traffic_inspection_id
        )
        .first()
    )

    if not traffic_inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trafik işlem kaydı bulunamadı."
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fotoğraf seçilmedi."
        )

    # dosyanın uzantısını al ve benzersiz bir dosya adı oluştur
    file_extension = file.filename.split(".")[-1]

    unique_id = uuid.uuid4().hex[:8]

    new_filename = (
        f"traffic_{traffic_inspection_id}_{unique_id}.{file_extension}"
    )

    file_path = os.path.join(
        TRAFFIC_UPLOAD_DIR,
        new_filename
    )

    # fotoğrafı sunucuya kaydet
    try:

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as error:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fotoğraf kaydedilemedi: {str(error)}"
        )

    # fotoğrafın veritabanı kaydını oluştur
    new_photo = models.TrafficInspectionPhoto(
        traffic_inspection_id=traffic_inspection_id,
        photo_path=file_path
    )

    try:

        db.add(new_photo)
        db.commit()
        db.refresh(new_photo)

    except Exception as error:

        db.rollback()

        # veritabanı kaydı başarısızsa diske yazılan dosyayı da sil
        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Trafik fotoğraf bilgisi veritabanına "
                f"kaydedilemedi: {str(error)}"
            )
        )

    return {
        "message": "Trafik işlem fotoğrafı başarıyla yüklendi.",
        "photo": {
            "photo_id": new_photo.id,
            "traffic_inspection_id": new_photo.traffic_inspection_id,
            "photo_path": new_photo.photo_path
        }
    }


#27.08.2026
# trafik zabıta işlem kaydı için PDF raporu oluşturmak için
@router.get("/{traffic_inspection_id}/report/pdf")
def get_traffic_inspection_pdf(
    traffic_inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    if current_user.role != "trafik_zabita":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yetkiniz yok."
        )

    traffic_inspection = (
        db.query(models.TrafficInspection)
        .filter(
            models.TrafficInspection.id == traffic_inspection_id
        )
        .first()
    )

    if not traffic_inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trafik kaydı bulunamadı."
        )

    file_name = f"traffic_report_{traffic_inspection_id}.pdf"

    file_path = os.path.join(
        TRAFFIC_REPORT_DIR,
        file_name
    )

    pdf = canvas.Canvas(
        file_path,
        pagesize=A4
    )

    page_width, page_height = A4

    y = page_height - 60

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(
        50,
        y,
        "TRAFIK ZABITA ISLEM RAPORU"
    )

    y -= 40

    pdf.setFont("Helvetica", 11)

    report_lines = [
        f"Kayit No: {traffic_inspection.id}",
        f"Ihlal Turu: {traffic_inspection.violation_type}",
        f"Plaka: {traffic_inspection.plate}",
        f"Arac Turu: {traffic_inspection.vehicle_type or 'Belirtilmemis'}",
        f"Adres: {traffic_inspection.address or 'Belirtilmemis'}",
        f"Aciklama: {traffic_inspection.description or 'Belirtilmemis'}",
        f"Yapilan Islem: {traffic_inspection.action_taken or 'Belirtilmemis'}",
        f"Durum: {traffic_inspection.status or 'Belirtilmemis'}",
        f"Enlem: {traffic_inspection.latitude if traffic_inspection.latitude is not None else 'Belirtilmemis'}",
        f"Boylam: {traffic_inspection.longitude if traffic_inspection.longitude is not None else 'Belirtilmemis'}",
        f"Personel ID: {traffic_inspection.inspector_id}",
        f"Tarih: {traffic_inspection.created_at}"
    ]

    for line in report_lines:

        pdf.drawString(
            50,
            y,
            line
        )

        y -= 22

        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = page_height - 60

    pdf.save()

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=file_name
    )