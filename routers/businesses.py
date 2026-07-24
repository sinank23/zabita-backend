from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Kendi yazdığımız dosyaları (tabloları ve kuralları) buraya çağırıyoruz.
import models
import schemas
from database import SessionLocal 

# İşlem yapan kişi gerçekten zabıta mı, sisteme giriş yapmış mı diye kontrol edeceğimiz kilit sistemimiz.
from routers.auth import get_current_user

# Google'a gidip yorumları alıp getirecek olan kuryemiz (dış servis fonksiyonu).
from services.google_service import fetch_google_reviews

# Buradaki tüm adreslerin başına otomatik "/businesses" ekliyoruz. 
# Böylece her defasında uzun uzun yazmamıza gerek kalmıyor, hepsi aynı klasörde toplanıyor.
router = APIRouter(
    prefix="/businesses",
    tags=["Businesses"]
)

# Veritabanıyla konuşmak için telefon hattı açıyoruz. 
# İşimiz bitince telefonu kapatıyoruz ki fatura (sunucu) şişmesin.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# YENİ İŞLETME KAYDETME EKRANI
@router.post("/", response_model=schemas.BusinessResponse, status_code=status.HTTP_201_CREATED)
def create_business(
    business: schemas.BusinessCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # Sadece giriş yapan zabıtalar burayı kullanabilir.
):
    # 1. Aynı isimde dükkan daha önce sisteme eklenmiş mi diye deftere bakıyoruz.
    existing_business = db.query(models.Business).filter(models.Business.name == business.name).first()
    if existing_business:
        # Varsa hata verip "Bu dükkan zaten var" diyoruz, işlemi durduruyoruz.
        raise HTTPException(status_code=400, detail="Bu isimde bir işletme zaten kayıtlı.")

    # 2. Dışarıdan gelen temiz bilgileri alıp, bizim veritabanının anlayacağı şekle sokuyoruz.
    new_business = models.Business(**business.model_dump())
    
    # 3. Bilgileri deftere yazıp kalemi bırakıyoruz (kaydediyoruz).
    db.add(new_business)
    db.commit()
    
    # 4. Veritabanının bu yeni dükkana otomatik verdiği numarayı (ID'yi) görebilmek için sayfayı yeniliyoruz.
    db.refresh(new_business)
    
    return new_business


# TÜM İŞLETMELERİ LİSTELEME EKRANI
@router.get("/", response_model=List[schemas.BusinessResponse])
def get_businesses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    # Veritabanına gidip "Bana sistemdeki tüm işletmeleri getir" diyoruz.
    businesses = db.query(models.Business).all()
    return businesses


# TEK BİR İŞLETMENİN BİLGİLERİNİ GETİRME EKRANI
@router.get("/{business_id}", response_model=schemas.BusinessResponse)
def get_business_by_id(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Tıklanan dükkanın numarasını (ID) alıp defterde o numaraya sahip işletmeyi arıyoruz.
    business = db.query(models.Business).filter(
        models.Business.id == business_id
    ).first()

    # Eğer o numaraya ait bir işletme yoksa "Bulamadım" diye hata dönüyoruz.
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="İşletme bulunamadı."
        )

    return business


# GOOGLE'DAN YORUMLARI ÇEKİP SİSTEME KAYDETME EKRANI
@router.post("/{business_id}/sync-reviews")
async def sync_business_reviews(
    business_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    """
    Bu kısım bizim Google operasyonumuz. Dışarıdan veriyi alıp içeri kaydediyoruz.
    """
    # 1. Adım: Önce "Böyle bir dükkan gerçekten var mı?" diye sisteme bakıyoruz.
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı")
        
    # Dükkan var ama Google Haritalar linkini (ID'sini) kaydederken girmemişler. 
    # O zaman Google'da neyi arayacağız? Hata verip durduruyoruz.
    if not business.google_place_id:
        raise HTTPException(status_code=400, detail="Bu işletmenin Google Place ID'si kayıtlı değil!")

    # 2. Adım: Yazdığımız Google kuryesini çağırıp git şu dükkanın yorumlarını al gel" diyoruz.
    fetched_reviews = await fetch_google_reviews(business.google_place_id)
    
    # Eğer dükkanın hiç yorumu yoksa boşuna uğraşmayıp "Yorum yok" deyip geri dönüyoruz.
    if not fetched_reviews:
        return {"message": "Yeni yorum bulunamadı veya çekilemedi."}

    added_count = 0
    # 3. Adım: Google'dan gelen yorum paketini açıp, teker teker kendi tablomuza diziyoruz.
    for rev_data in fetched_reviews:
        new_review = models.GoogleReview(
            business_id=business.id, # Bu yorum hangi dükkana ait? Fişini buraya kesiyoruz.
            author_name=rev_data["author_name"],
            rating=rev_data["rating"],
            text=rev_data["text"],
            publish_date=str(rev_data["publish_date"]) # Tarih formatını bizim tabloya uysun diye metne çeviriyoruz.
        )
        # Yorumu şimdilik alışveriş sepetine atıyoruz, henüz kasadan geçirmedik.
        db.add(new_review)
        added_count += 1

    # 4. Adım: Sepetteki her şeyi tek seferde kasadan geçirip deftere işliyoruz.
    # Tek tek uğraşmak yerine hepsini bir kerede kaydedip sistemi yormuyoruz.
    db.commit()

    # İşlem bitince ekrana "Şu kadar yorum başarıyla kaydedildi" yazdırıyoruz.
    return {"message": f"{added_count} adet yorum başarıyla eşitlendi."}