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

from io import BytesIO
from fastapi.responses import StreamingResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as ReportLabImage
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

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



#28.08.2026
#pdf türkçe karakterler için yardımcı fonksiyon
def register_turkish_fonts():
    regular_font_path = "C:/Windows/Fonts/arial.ttf"
    bold_font_path = "C:/Windows/Fonts/arialbd.ttf"

    pdfmetrics.registerFont(TTFont("ArialTR", regular_font_path))
    pdfmetrics.registerFont(TTFont("ArialTR-Bold", bold_font_path))



def build_traffic_pdf(traffic_record):
    register_turkish_fonts()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="TrafficTitle",
        parent=styles["Title"],
        fontName="ArialTR-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1F3C88"),
        alignment=TA_CENTER,
        spaceAfter=12
    )

    section_style = ParagraphStyle(
        name="TrafficSection",
        parent=styles["Heading2"],
        fontName="ArialTR-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.white,
        backColor=colors.HexColor("#3F5AA9"),
        spaceBefore=8,
        spaceAfter=8,
        leftIndent=6,
        borderPadding=6
    )

    normal_style = ParagraphStyle(
        name="TrafficNormal",
        parent=styles["BodyText"],
        fontName="ArialTR",
        fontSize=10,
        leading=14,
        textColor=colors.black
    )

    small_style = ParagraphStyle(
        name="TrafficSmall",
        parent=styles["BodyText"],
        fontName="ArialTR",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#444444")
    )

    elements = []

    elements.append(
        Paragraph(
            "TRAFİK ZABITA İŞLEM RAPORU",
            title_style
        )
    )

    elements.append(
        Spacer(1, 6)
    )

    info_data = [
        ["Kayıt No", str(traffic_record.id)],
        ["İhlal Türü", traffic_record.violation_type or "-"],
        ["Plaka", traffic_record.plate or "-"],
        ["Araç Türü", traffic_record.vehicle_type or "-"],
        ["Adres", traffic_record.address or "-"],
        ["Durum", traffic_record.status or "-"],
        [
            "Personel ID",
            str(traffic_record.inspector_id)
            if traffic_record.inspector_id
            else "-"
        ],
        [
            "Tarih",
            str(traffic_record.created_at)
            if traffic_record.created_at
            else "-"
        ],
        [
            "Enlem",
            str(traffic_record.latitude)
            if traffic_record.latitude is not None
            else "-"
        ],
        [
            "Boylam",
            str(traffic_record.longitude)
            if traffic_record.longitude is not None
            else "-"
        ],
    ]

    info_table = Table(
        info_data,
        colWidths=[
            45 * mm,
            120 * mm
        ]
    )

    info_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#EAF0FF")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, -1),
                    colors.black
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "ArialTR-Bold"
                ),
                (
                    "FONTNAME",
                    (1, 0),
                    (1, -1),
                    "ArialTR"
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9.5
                ),
                (
                    "LEADING",
                    (0, 0),
                    (-1, -1),
                    12
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#B8C4E3")
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
            ]
        )
    )

    elements.append(
        Paragraph(
            "Genel Bilgiler",
            section_style
        )
    )

    elements.append(
        info_table
    )

    elements.append(
        Spacer(1, 12)
    )

    elements.append(
        Paragraph(
            "Açıklama",
            section_style
        )
    )

    elements.append(
        Paragraph(
            traffic_record.description
            or "Açıklama girilmemiştir.",
            normal_style
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(
        Paragraph(
            "Yapılan İşlem",
            section_style
        )
    )

    elements.append(
        Paragraph(
            traffic_record.action_taken
            or "Yapılan işlem bilgisi girilmemiştir.",
            normal_style
        )
    )

    elements.append(
        Spacer(1, 14)
    )

    #28.08.2026
    # trafik işlemine eklenen fotoğrafları PDF raporunda göstermek için
    traffic_photos = traffic_record.photos or []

    if traffic_photos:

        elements.append(
            Paragraph(
                "İşlem Fotoğrafları",
                section_style
            )
        )

        elements.append(
            Spacer(1, 6)
        )

        for index, photo in enumerate(
            traffic_photos,
            start=1
        ):

            photo_path = photo.photo_path

            if (
                photo_path
                and os.path.exists(photo_path)
            ):

                try:

                    image_reader = ImageReader(
                        photo_path
                    )

                    image_width, image_height = (
                        image_reader.getSize()
                    )

                    max_width = 150 * mm
                    max_height = 90 * mm

                    scale = min(
                        max_width / image_width,
                        max_height / image_height
                    )

                    displayed_width = (
                        image_width * scale
                    )

                    displayed_height = (
                        image_height * scale
                    )

                    elements.append(
                        Paragraph(
                            f"Fotoğraf {index}",
                            normal_style
                        )
                    )

                    elements.append(
                        Spacer(1, 5)
                    )

                    elements.append(
                        ReportLabImage(
                            photo_path,
                            width=displayed_width,
                            height=displayed_height
                        )
                    )

                    elements.append(
                        Spacer(1, 12)
                    )

                except Exception as e:

                    print(
                        f"Trafik fotoğrafı PDF'e eklenemedi: {e}"
                    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(
        Paragraph(
            "Bu rapor Trafik Zabıta Sistemi üzerinden elektronik olarak oluşturulmuştur.",
            small_style
        )
    )

    doc.build(elements)

    buffer.seek(0)

    return buffer


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
    
    #31.08.2026
# trafik kayıtlarını trafik zabıta ve süper admin görebilsin
    if current_user.role not in ["trafik_zabita", "superadmin"]:
        raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Bu işlem için Trafik Zabıta veya Süper Admin yetkisi gereklidir."
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
    if current_user.role not in ["trafik_zabita", "superadmin"]:
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




#31.08.2026
# seçilen trafik işlem kaydına ait fotoğrafları listelemek için
@router.get("/{traffic_inspection_id}/photos/")
def get_traffic_inspection_photos(
    traffic_inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # sadece trafik zabıta personeli fotoğrafları görebilsin
    if current_user.role != "trafik_zabita":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Trafik Zabıta yetkisi gereklidir."
        )

    # ilgili trafik kaydının varlığını kontrol et
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

    traffic_photos = (
        db.query(models.TrafficInspectionPhoto)
        .filter(
            models.TrafficInspectionPhoto.traffic_inspection_id
            == traffic_inspection_id
        )
        .order_by(
            models.TrafficInspectionPhoto.id.asc()
        )
        .all()
    )

    return [
    {
        "photo_id": photo.id,
        "traffic_inspection_id": photo.traffic_inspection_id,
        "photo_path": photo.photo_path,

        #31.08.2026
        # Android tarafının fotoğrafı görüntüleyebilmesi için erişilebilir URL
        "photo_url": (
            "/uploads/"
            + photo.photo_path
                .replace("\\", "/")
                .replace("uploads/", "")
        ),

        "created_at": photo.created_at
    }
    for photo in traffic_photos
]

#27.08.2026
# trafik zabıta işlem kaydı için PDF raporu oluşturmak için
@router.get("/{traffic_inspection_id}/report/pdf")
def get_traffic_inspection_pdf(
    traffic_inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    traffic_record = (
        db.query(models.TrafficInspection)
        .filter(models.TrafficInspection.id == traffic_inspection_id)
        .first()
    )

    if not traffic_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trafik kaydı bulunamadı."
        )

    pdf_buffer = build_traffic_pdf(traffic_record)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="traffic_report_{traffic_inspection_id}.pdf"'
        }
    )

#31.08.2026
# süper admin trafik işlem kaydının durumunu güncelleyebilsin
@router.patch("/{traffic_inspection_id}/status")
def update_traffic_inspection_status(
    traffic_inspection_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # sadece süper admin durum değiştirebilsin
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Süper Admin yetkisi gereklidir."
        )

    allowed_statuses = [
        "Kaydedildi",
        "İnceleniyor",
        "Tamamlandı",
        "İptal Edildi"
    ]

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Geçersiz durum. Kullanılabilecek durumlar: "
                + ", ".join(allowed_statuses)
            )
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
            detail="Trafik işlem kaydı bulunamadı."
        )

    try:

        traffic_inspection.status = new_status

        db.commit()
        db.refresh(traffic_inspection)

        return {
            "message": "Trafik işlem durumu başarıyla güncellendi.",
            "traffic_inspection_id": traffic_inspection.id,
            "status": traffic_inspection.status
        }

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Durum güncellenirken hata oluştu: {str(error)}"
        )

#31.08.2026
# süper admin trafik işlem kaydını silebilsin
@router.delete("/{traffic_inspection_id}")
def delete_traffic_inspection(
    traffic_inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # sadece süper admin trafik kaydı silebilsin
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Süper Admin yetkisi gereklidir."
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
            detail="Trafik işlem kaydı bulunamadı."
        )

    try:

        # trafik kaydına bağlı fotoğraf dosyalarını diskten sil
        for photo in traffic_inspection.photos:

            if (
                photo.photo_path
                and os.path.exists(photo.photo_path)
            ):
                os.remove(photo.photo_path)

        db.delete(traffic_inspection)
        db.commit()

        return {
            "message": "Trafik işlem kaydı başarıyla silindi.",
            "traffic_inspection_id": traffic_inspection_id
        }

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trafik kaydı silinirken hata oluştu: {str(error)}"
        )