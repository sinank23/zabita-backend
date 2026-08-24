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
from schemas import ReviewResponse
from services.ai_vision import synthesize_inspection_data
from services.google_service import fetch_google_reviews

#13.08.2026
#pdf oluşturma endpointi için eklendi
import io

from fastapi.responses import StreamingResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


router = APIRouter(
    prefix="/inspections", tags=["Denetim ve Kriter İşlemleri"]
)


# Fotoğrafların kaydedileceği klasör
UPLOAD_DIR = "uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 13.08.2026
# PDF raporlarında Türkçe karakterlerin doğru görünmesi için font ayarı
PDF_FONT_NAME = "Helvetica"
PDF_FONT_BOLD_NAME = "Helvetica-Bold"

try:
    arial_path = r"C:\Windows\Fonts\arial.ttf"
    arial_bold_path = r"C:\Windows\Fonts\arialbd.ttf"

    if os.path.exists(arial_path) and os.path.exists(arial_bold_path):
        pdfmetrics.registerFont(
            TTFont("ArialPdf", arial_path)
        )

        pdfmetrics.registerFont(
            TTFont("ArialPdfBold", arial_bold_path)
        )

        pdfmetrics.registerFontFamily(
            "ArialPdf",
            normal="ArialPdf",
            bold="ArialPdfBold",
            italic="ArialPdf",
            boldItalic="ArialPdfBold",
        )

        PDF_FONT_NAME = "ArialPdf"
        PDF_FONT_BOLD_NAME = "ArialPdfBold"

except Exception as error:
    print(f"PDF font yükleme uyarısı: {str(error)}")

# ---------------------------------------------------------
# DENETİM KRİTERLERİ
# ---------------------------------------------------------


@router.post("/criteria/", response_model=schemas.CriterionResponse)
def create_criteria(
    criteria: schemas.CriterionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    #19.08.2026
    # Kriter belirli bir kategoriye bağlıysa kategorinin gerçekten var olduğunu kontrol et
    # category_id boşsa kriter tüm işletmeler için ortak kriter olarak kaydedilebilir
    if criteria.category_id is not None:

        category = (
            db.query(models.BusinessCategory)
            .filter(models.BusinessCategory.id == criteria.category_id)
            .first()
        )

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Belirtilen kategori bulunamadı."
            )

    new_criteria = models.InspectionCriterion(**criteria.model_dump())

    db.add(new_criteria)
    db.commit()
    db.refresh(new_criteria)

    return new_criteria


@router.get(
    "/criteria/{category_id}", response_model=List[schemas.CriterionResponse]
)
def get_criteria_by_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    criteria = (
        db.query(models.InspectionCriterion)
        .filter(models.InspectionCriterion.category_id == category_id)
        .all()
    )

    return criteria


#10.08.2026
#denetim sorularını veritabanından dinamik olarak çekmek için endpoint
@router.get(
    "/criteria/common/all",
    response_model=List[schemas.CriterionResponse],
)
def get_common_inspection_criteria(
    db: Session = Depends(get_db),
):
    criteria = (
        db.query(models.InspectionCriterion)
        .filter(models.InspectionCriterion.category_id.is_(None))
        .all()
    )

    return criteria

#19.08.2026
# süper admin panelinde tüm denetim kriterleri gelsin
@router.get(
    "/criteria/admin/all",
    response_model=List[schemas.CriterionResponse],
)
def get_all_inspection_criteria(
    db: Session = Depends(get_db),
):
    # tüm kriterleri tek listede getir
    criteria = (
        db.query(models.InspectionCriterion)
        .order_by(models.InspectionCriterion.id.asc())
        .all()

    )

    return criteria

#19.08.2026
# Süper Admin tarafından mevcut denetim kriterini güncellemek için
@router.put(
    "/criteria/admin/{criterion_id}",
    response_model=schemas.CriterionResponse
)
def update_inspection_criterion(
    criterion_id: int,
    criterion: schemas.CriterionCreate,
    db: Session = Depends(get_db),
):
    # Güncellenecek kriteri ID üzerinden bul
    existing_criterion = (
        db.query(models.InspectionCriterion)
        .filter(models.InspectionCriterion.id == criterion_id)
        .first()
    )

    if not existing_criterion:
        raise HTTPException(
            status_code=404,
            detail="Denetim kriteri bulunamadı."
        )

    # Kriter belirli bir kategoriye bağlanacaksa kategoriyi kontrol et
    if criterion.category_id is not None:
        category = (
            db.query(models.BusinessCategory)
            .filter(models.BusinessCategory.id == criterion.category_id)
            .first()
        )

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Belirtilen kategori bulunamadı."
            )

    # Kriter metnini ve kategori bağlantısını güncelle
    existing_criterion.question_text = criterion.question_text
    existing_criterion.category_id = criterion.category_id

    db.commit()
    db.refresh(existing_criterion)

    return existing_criterion




# ---------------------------------------------------------
# DENETİM KAYDETME
# ---------------------------------------------------------

#24.08.2026
#denetim kriteri silmek için(süper admin)

#24.08.2026
# Süper Admin tarafından denetim kriterini silmek için
@router.delete("/criteria/admin/{criterion_id}")
def delete_inspection_criterion(
    criterion_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):

    # silinecek kriteri ID üzerinden bul
    criterion = (
        db.query(models.InspectionCriterion)
        .filter(models.InspectionCriterion.id == criterion_id)
        .first()
    )

    if not criterion:
        raise HTTPException(
            status_code=404,
            detail="Denetim kriteri bulunamadı."
        )

    try:

        # kriter geçmiş denetimlerde kullanılmışsa
        # ona bağlı cevap kayıtlarını da sil
        db.query(models.InspectionAnswer).filter(
            models.InspectionAnswer.criterion_id == criterion_id
        ).delete(synchronize_session=False)

        # kriter kaydını sil
        db.delete(criterion)

        db.commit()

        return {
            "message": f"{criterion_id} ID'li denetim kriteri başarıyla silindi."
        }

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Denetim kriteri silinirken hata oluştu: {str(error)}"
        )


@router.post("/", response_model=schemas.InspectionResponse)
def create_inspection(
    inspection: schemas.InspectionCreate,
    db: Session = Depends(get_db),

    # Giriş yapan kullanıcıyı JWT token üzerinden al
    current_user: models.User = Depends(get_current_user),
):
    print("------- İSTEK BAŞARIYLA BACKEND'E ULAŞTI -------")
    print(f"Gelen İşletme: {inspection.businessName}")
    print(f"Gelen Adres: {inspection.address}")
    print(f"Gelen Cevaplar: {inspection.answers}")

    new_inspection = models.Inspection(
        businessName=inspection.businessName,
        address=inspection.address,
        answers=inspection.answers,
        # bu satırı da 30.07.2026 tarihinde not kısmı için ekliyorum
        inspector_notes=inspection.inspector_notes,
        # Şimdilik kullanıcı doğrulaması olmadığı için boş bırakıyoruz.
        # inspector_id=1 kullanmak, veritabanında 1 ID'li kullanıcı
        # yoksa Foreign Key hatası çıkarabilir.
        inspector_id=current_user.id,
        business_id=inspection.business_id,
        latitude=inspection.latitude,
        longitude=inspection.longitude,
    )

    try:
        db.add(new_inspection)
        db.commit()
        db.refresh(new_inspection)

        # Bu for döngüsünün içindeki işlemler girintili olmalıydı
        for answer_record in inspection.answer_records:
            new_answer = models.InspectionAnswer(
                inspection_id=new_inspection.id,
                criterion_id=answer_record.criterion_id,
                is_yes=answer_record.is_yes,
            )
            db.add(new_answer)

        # For döngüsü bittikten sonra hepsini veritabanına kaydetmek için döngüyle aynı hizada olmalı
        db.commit()

        print(f"Denetim başarıyla kaydedildi. Denetim ID: {new_inspection.id}")

        return new_inspection

    except Exception as error:
        db.rollback()

        print("DENETİM KAYDETME HATASI:")
        print(str(error))

        raise HTTPException(
            status_code=500, detail=f"Denetim kaydedilemedi: {str(error)}"
        )


@router.get("/", response_model=List[schemas.InspectionResponse])
def get_inspections(db: Session = Depends(get_db)):
    inspections = (
        db.query(models.Inspection).order_by(models.Inspection.id.desc()).all()
    )

    return inspections


#13.08.2026 eklendi
#13.08.2026
#denetime ait bilgileri PDF raporu olarak oluşturmak için endpoint
@router.get("/{inspection_id}/report/pdf")
def generate_inspection_pdf(
    inspection_id: int,
    db: Session = Depends(get_db),
):
    inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id)
        .first()
    )

    if not inspection:
        raise HTTPException(
            status_code=404,
            detail="PDF raporu oluşturulacak denetim bulunamadı."
        )

    answer_records = (
        db.query(models.InspectionAnswer)
        .filter(models.InspectionAnswer.inspection_id == inspection_id)
        .all()
    )

    photos = (
        db.query(models.InspectionPhoto)
        .filter(models.InspectionPhoto.inspection_id == inspection_id)
        .all()
    )

    buffer = io.BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Denetim Raporu #{inspection.id}",
    )

    styles = getSampleStyleSheet()

    PRIMARY_COLOR = colors.HexColor("#1F4E79")
    SECONDARY_COLOR = colors.HexColor("#DCEAF7")
    LIGHT_ROW_COLOR = colors.HexColor("#F7FAFD")
    TEXT_COLOR = colors.HexColor("#222222")
    BORDER_COLOR = colors.HexColor("#9AA7B3")

    title_style = ParagraphStyle(
        "PdfTitle",
        parent=styles["Title"],
        fontName=PDF_FONT_BOLD_NAME,
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=PRIMARY_COLOR,
        spaceAfter=16,
    )

    normal_style = ParagraphStyle(
        "PdfNormal",
        parent=styles["BodyText"],
        fontName=PDF_FONT_NAME,
        fontSize=10,
        leading=15,
        textColor=TEXT_COLOR,
        spaceAfter=5,
    )

    ai_report_style = ParagraphStyle(
        "PdfAiReport",
        parent=styles["BodyText"],
        fontName=PDF_FONT_NAME,
        fontSize=10,
        leading=15,
        textColor=TEXT_COLOR,
        backColor=LIGHT_ROW_COLOR,
        borderColor=BORDER_COLOR,
        borderWidth=0.5,
        borderPadding=8,
        spaceAfter=8,
    )

    label_style = ParagraphStyle(
        "PdfLabel",
        parent=styles["BodyText"],
        fontName=PDF_FONT_BOLD_NAME,
        fontSize=10,
        leading=15,
        textColor=PRIMARY_COLOR,
        spaceAfter=5,
    )

    table_header_style = ParagraphStyle(
        "PdfTableHeader",
        parent=styles["BodyText"],
        fontName=PDF_FONT_BOLD_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    section_title_style = ParagraphStyle(
        "PdfSectionTitle",
        parent=styles["BodyText"],
        fontName=PDF_FONT_BOLD_NAME,
        fontSize=11,
        leading=14,
        textColor=colors.white,
    )

    def build_section_header(title_text: str):
        section_table = Table(
            [[Paragraph(title_text, section_title_style)]],
            colWidths=[18 * cm],
        )

        section_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_COLOR),
                    ("BOX", (0, 0), (-1, -1), 0.6, PRIMARY_COLOR),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        return section_table

    story = []

    story.append(
        Paragraph(
            "YAPAY ZEKA DESTEKLİ ZABITA DENETİM RAPORU",
            title_style
        )
    )

    business = getattr(inspection, "business", None)

    category_name = (
        getattr(inspection, "category_name", None)
        or "Belirtilmemiş"
    )

    owner_name = (
        getattr(inspection, "owner_name", None)
        or "Belirtilmemiş"
    )

    contact_info = (
        getattr(inspection, "contact_info", None)
        or "Belirtilmemiş"
    )

    inspection_date = (
        str(inspection.inspection_date)
        if getattr(inspection, "inspection_date", None)
        else "Belirtilmemiş"
    )

    info_data = [
        [
            Paragraph("Denetim No", label_style),
            Paragraph(str(inspection.id), normal_style),
        ],
        [
            Paragraph("Denetim Tarihi", label_style),
            Paragraph(inspection_date, normal_style),
        ],
        [
            Paragraph("Durum", label_style),
            Paragraph(
                inspection.status or "Belirtilmemiş",
                normal_style
            ),
        ],
        [
            Paragraph("İşletme", label_style),
            Paragraph(
                inspection.businessName or "Belirtilmemiş",
                normal_style
            ),
        ],
        [
            Paragraph("Adres", label_style),
            Paragraph(
                inspection.address or "Belirtilmemiş",
                normal_style
            ),
        ],
        [
            Paragraph("Faaliyet Konusu", label_style),
            Paragraph(category_name, normal_style),
        ],
        [
            Paragraph("İşletme Sahibi", label_style),
            Paragraph(owner_name, normal_style),
        ],
        [
            Paragraph("İletişim", label_style),
            Paragraph(contact_info, normal_style),
        ],
    ]

    info_table = Table(
        info_data,
        colWidths=[4.5 * cm, 12 * cm],
        repeatRows=0,
    )

    info_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), SECONDARY_COLOR),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(info_table)

    story.append(Spacer(1, 12))

    story.append(build_section_header("Zabıta Personeli Notu"))
    story.append(Spacer(1, 6))

    inspector_notes = (
        inspection.inspector_notes
        if getattr(inspection, "inspector_notes", None)
        else "Bu denetim için zabıta personeli notu girilmemiş."
    )

    story.append(
        Paragraph(
            inspector_notes,
            normal_style
        )
    )

    story.append(build_section_header("Denetim Kriterleri ve Cevapları"))
    story.append(Spacer(1, 6))

    if answer_records:
        answer_data = [
            [
                Paragraph("Kriter", table_header_style),
                Paragraph("Cevap", table_header_style),
            ]
        ]

        for answer in answer_records:
            question_text = (
                answer.criterion.question_text
                if answer.criterion
                else f"Kriter #{answer.criterion_id}"
            )

            answer_data.append(
                [
                    Paragraph(question_text, normal_style),
                    Paragraph(
                        "Evet" if answer.is_yes else "Hayır",
                        normal_style
                    ),
                ]
            )

        answer_table = Table(
            answer_data,
            colWidths=[14 * cm, 2.5 * cm],
            repeatRows=1,
        )

        answer_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, LIGHT_ROW_COLOR],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        story.append(answer_table)

    else:
        story.append(
            Paragraph(
                "Bu denetime ait ilişkisel soru-cevap kaydı bulunamadı.",
                normal_style
            )
        )

    story.append(Spacer(1, 12))

    story.append(build_section_header("Denetim Fotoğrafları"))
    story.append(Spacer(1, 8))

    if photos:
        for index, photo in enumerate(photos, start=1):

            if photo.photo_path and os.path.exists(photo.photo_path):
                try:
                    report_image = Image(photo.photo_path)

                    max_width = 16 * cm
                    max_height = 10 * cm

                    width_ratio = max_width / report_image.imageWidth
                    height_ratio = max_height / report_image.imageHeight

                    scale_ratio = min(
                        width_ratio,
                        height_ratio,
                        1
                    )

                    report_image.drawWidth = (
                        report_image.imageWidth * scale_ratio
                    )

                    report_image.drawHeight = (
                        report_image.imageHeight * scale_ratio
                    )

                    story.append(
                        Paragraph(
                            f"Fotoğraf {index}",
                            label_style
                        )
                    )

                    story.append(report_image)
                    story.append(Spacer(1, 12))

                except Exception as error:
                    story.append(
                        Paragraph(
                            f"Fotoğraf {index} PDF'e eklenemedi: {str(error)}",
                            normal_style
                        )
                    )

                    story.append(Spacer(1, 8))

            else:
                story.append(
                    Paragraph(
                        f"Fotoğraf {index} dosyası bulunamadı.",
                        normal_style
                    )
                )

                story.append(Spacer(1, 8))

    else:
        story.append(
            Paragraph(
                "Bu denetime ait fotoğraf bulunamadı.",
                normal_style
            )
        )

    story.append(Spacer(1, 12))

    story.append(build_section_header("Yapay Zeka Çapraz Analiz Raporu"))
    story.append(Spacer(1, 6))

    ai_summary = (
        inspection.ai_summary
        if getattr(inspection, "ai_summary", None)
        else "Bu denetim için yapay zeka raporu oluşturulmamış."
    )

    ai_blocks = [
        block.strip()
        for block in ai_summary.split("\n\n")
        if block.strip()
    ]

    for block in ai_blocks:
        story.append(
            Paragraph(
                block.replace("\n", "<br/>"),
                ai_report_style
            )
        )

        story.append(Spacer(1, 4))

    try:
        pdf.build(story)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"PDF raporu oluşturulamadı: {str(error)}"
        )

    buffer.seek(0)

    filename = f"denetim_raporu_{inspection.id}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{filename}"'
            )
        },
    )


#10.08.2026 eklendi
@router.get(
    "/{inspection_id}/answers",
    response_model=List[schemas.InspectionAnswerResponse],
)
def get_inspection_answers(
    inspection_id: int,
    db: Session = Depends(get_db),
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
        .filter(models.InspectionAnswer.inspection_id == inspection_id)
        .all()
    )

    return [
        schemas.InspectionAnswerResponse(
            criterion_id=answer.criterion_id,
            question_text=answer.criterion.question_text,
            is_yes=answer.is_yes,
        )
        for answer in answer_records
    ]


@router.delete("/{inspection_id}")
async def delete_inspection(inspection_id: int, db: Session = Depends(get_db)):

    # öncelikle silinecek denetimi bulalım
    inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id)
        .first()
    )

    if not inspection:
        raise HTTPException(
            status_code=404, detail="Silinmek istenen denetim bulunamadı."
        )

    try:
        # denetime ait fotoğrafları veritabanından sil
        db.query(models.InspectionPhoto).filter(
            models.InspectionPhoto.inspection_id == inspection_id
        ).delete()

        db.delete(inspection)
        db.commit()  # kalıcılaştırma fonksiyonu

        return {
            "message": f"{inspection_id} ID'li denetim ve verileri başarıyla silindi."
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Silme işlemi sırasında hata oluştu: {str(error)}"
        )


# ---------------------------------------------------------
# DENETİM FOTOĞRAFLARI VE YAPAY ZEKA
# ---------------------------------------------------------


@router.post("/{inspection_id}/photos/", status_code=201)
async def upload_inspection_photo(
    inspection_id: int,
    file: UploadFile = File(None),
    photo: UploadFile = File(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    file = file or photo or image

    # denetim var mı kontrolünü yaptık
    inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id)
        .first()
    )

    if not inspection:
        raise HTTPException(status_code=404, detail="Denetim bulunamadı.")

    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="Fotoğraf seçilmedi.")

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
            status_code=500, detail=f"Fotoğraf kaydedilemedi: {str(error)}"
        )

    # yapay zeka analizini yapma işlemi
    try:
        ai_result = await analyze_inspection_photo(file_path)

    except Exception as error:
        ai_result = f"Yapay zeka analizi başarısız oldu: {str(error)}"

    # veritabanı modeli için kayıt
    new_photo = models.InspectionPhoto(
        inspection_id=inspection_id,
        photo_path=file_path,
        ai_analysis_result=ai_result,
    )

    try:
        db.add(new_photo)
        db.commit()
        db.refresh(new_photo)

    except Exception as error:
        db.rollback()

        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=500,
            detail=(
                "Fotoğraf bilgileri veritabanına kaydedilemedi: " f"{str(error)}"
            ),
        )

    return {
        "message": ("Fotoğraf başarıyla yüklendi ve analiz edildi."),
        "photo": {
            "photo_id": new_photo.id,
            "photo_path": new_photo.photo_path,
            "ai_result": new_photo.ai_analysis_result,
        },
    }


@router.get("/{inspection_id}/photos/", response_model=List[schemas.PhotoResponse])
def get_inspection_photos(inspection_id: int, db: Session = Depends(get_db)):
    inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id)
        .first()
    )

    if not inspection:
        raise HTTPException(status_code=404, detail="Denetim bulunamadı.")

    photos = (
        db.query(models.InspectionPhoto)
        .filter(models.InspectionPhoto.inspection_id == inspection_id)
        .all()
    )

    return photos


# ---------------------------------------------------------
# DENETİM tamamlama ve çapraz yapay zeka modeli güncelleme: 30.07.2026
# ---------------------------------------------------------


@router.post("/{inspection_id}/complete/")
async def complete_inspection(inspection_id: int, db: Session = Depends(get_db)):

    # denetimi bul getir
    inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id)
        .first()
    )

    if not inspection:
        raise HTTPException(status_code=404, detail="Denetim bulunamadı")

    answer_records = (
        db.query(models.InspectionAnswer)
        .filter(models.InspectionAnswer.inspection_id == inspection_id)
        .all()
    )

    if answer_records:
        answers_text = "\n".join(
            [
                f"- {answer.criterion.question_text}:"
                f"{'Evet' if answer.is_yes else 'Hayır'}"
                for answer in answer_records
            ]
        )

    else:
        answers_text = (
            str(inspection.answers)
            if inspection.answers
            else "Cevap yok."
        )

    # denetim fotoğraflarının analizlerini alma işlemi
    photos = (
        db.query(models.InspectionPhoto)
        .filter(models.InspectionPhoto.inspection_id == inspection_id)
        .all()
    )

    photo_analyses_list = [
        p.ai_analysis_result for p in photos if p.ai_analysis_result
    ]

    photo_analyses_text = (
        "\n".join(photo_analyses_list)
        if photo_analyses_list
        else "Fotoğraf yüklenmemiş"
    )

    # google yorumlarını alalım ve toplayalım
    reviews_text = "Yorum bulunamadı."

    if inspection.business_id:
        reviews = (
            db.query(models.GoogleReview)
            .filter(models.GoogleReview.business_id == inspection.business_id)
            .all()
        )

        reviews_list = [f"- {r.text}" for r in reviews if r.text]

        if reviews_list:
            reviews_text = "\n".join(reviews_list)

        # google geminiyle fotoğraf analizi
        # Google Gemini ile nihai denetim raporu oluşturma
    try:
        ai_report = await synthesize_inspection_data(
            answers_text=answers_text,
            inspector_notes=(
                inspection.inspector_notes
                if getattr(inspection, "inspector_notes", None)
                else "Zabıta personeli ek bir not girmedi"
            ),
            photo_analyses=photo_analyses_text,
            google_reviews=reviews_text,
        )

    except Exception as error:
        inspection.status = "AI Analizi Bekliyor"
        db.commit()

        raise HTTPException(
            status_code=503,
            detail=f"Yapay zeka servisine şu anda ulaşılamıyor: {str(error)}"
        )

    # AI raporu başarıyla üretildiyse veritabanına kaydet
    try:
        inspection.ai_summary = ai_report
        inspection.status = "Tamamlandı"

        db.commit()
        db.refresh(inspection)

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Yapay zeka raporu veritabanına kaydedilemedi: {str(error)}"
        )

    return {
        "message": "Denetim başarıyla tamamlandı ve AI raporu oluşturuldu.",
        "inspection_id": inspection_id,
        "ai_report": ai_report,
    }


# ---------------------------------------------------------
# GOOGLE YORUMLARI
# ---------------------------------------------------------


@router.post("/{business_id}/sync-reviews", status_code=201)
async def sync_business_reviews(business_id: int, db: Session = Depends(get_db)):
    business = (
        db.query(models.Business)
        .filter(models.Business.id == business_id)
        .first()
    )

    if not business:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı.")

    if not business.google_place_id:
        raise HTTPException(
            status_code=400,
            detail=("İşletmenin Google Place ID bilgisi tanımlı değil."),
        )

    reviews = await fetch_google_reviews(business.google_place_id)

    try:
        for review in reviews:
            new_review = models.GoogleReview(
                business_id=business_id,
                author_name=review.get("author_name"),
                rating=review.get("rating"),
                text=review.get("text"),
                publish_date=review.get("publish_date"),
            )

            db.add(new_review)

        db.commit()

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=("Google yorumları kaydedilemedi: " f"{str(error)}"),
        )

    return {
        "message": (f"{len(reviews)} adet yorum başarıyla senkronize edildi.")
    }


@router.get(
    "/businesses/{business_id}/reviews", response_model=List[ReviewResponse]
)
def get_business_reviews(business_id: int, db: Session = Depends(get_db)):
    # Veritabanından o dükkana (business_id) ait yorumları liste halinde çekiyoruz
    reviews = (
        db.query(models.GoogleReview)
        .filter(models.GoogleReview.business_id == business_id)
        .all()
    )

    return reviews