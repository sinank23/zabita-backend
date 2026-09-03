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
# Google'a gidip yorumları ve işletme arama sonuçlarını getirecek dış servis fonksiyonları.
from services.google_service import fetch_google_reviews, search_google_places

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
    #current_user: models.User = Depends(get_current_user) # Sadece giriş yapan zabıtalar burayı kullanabilir.
):
    # 1. Aynı isimde dükkan daha önce sisteme eklenmiş mi diye deftere bakıyoruz.
    # Google Place ID gönderilmişse önce bu benzersiz kimliğe göre işletmeyi arıyoruz.
    existing_business = None

    if business.google_place_id:
        existing_business = db.query(models.Business).filter(
            models.Business.google_place_id == business.google_place_id
        ).first()

    # Place ID ile bulunamazsa aynı isimde kayıt olup olmadığını kontrol ediyoruz.
    if not existing_business:
        existing_business = db.query(models.Business).filter(
            models.Business.name == business.name
        ).first()

    # İşletme zaten kayıtlıysa hata vermek yerine mevcut kaydı geri döndürüyoruz.
    # Böylece aynı işletmede daha sonra tekrar denetim yapılabilir.
    #02.09.2026
# işletme daha önce kayıtlıysa yeni gelen bilgileri mevcut kayda işle
    if existing_business:

        if business.address is not None:
            existing_business.address = business.address

        if business.latitude is not None:
            existing_business.latitude = business.latitude

        if business.longitude is not None:
            existing_business.longitude = business.longitude

        if business.owner_name is not None:
            existing_business.owner_name = business.owner_name

        if business.contact_info is not None:
            existing_business.contact_info = business.contact_info

        if business.activity_type is not None:
            existing_business.activity_type = business.activity_type

        if business.category_id is not None:
            existing_business.category_id = business.category_id

        db.commit()
        db.refresh(existing_business)

        return existing_business

        
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
):
    # Veritabanına gidip "Bana sistemdeki tüm işletmeleri getir" diyoruz.
    businesses = db.query(models.Business).all()
    return businesses


# GOOGLE MAPS ÜZERİNDE İŞLETME ARAMA EKRANI
@router.get("/search")
async def search_businesses_from_google(
    query: str,
    latitude: float,
    longitude: float
):
    """
    Zabıtanın yazdığı işletme adına ve mevcut GPS konumuna göre
    Google Maps üzerinde yakın işletmeleri arar.
    """

    # Kullanıcı arama alanını boş gönderdiyse
    # Google'a gereksiz istek atmadan hata döndürüyoruz.
    if not query.strip():
        raise HTTPException(
            status_code=400,
            detail="İşletme adı boş bırakılamaz."
        )

    # google_service.py dosyasına yazdığımız fonksiyonu çağırıyoruz.
    # İşletme adı ile zabıtanın enlem ve boylam bilgisini gönderiyoruz.
    places = await search_google_places(
        query=query,
        latitude=latitude,
        longitude=longitude
    )

    # Google'dan sonuç gelmezse Android'e boş liste gönderiyoruz.
    # Böylece uygulama çökmek yerine 'işletme bulunamadı' yazabilir.
    if not places:
        return []

    # Google'dan gelen sadeleştirilmiş işletme listesini Android'e gönderiyoruz.
    return places


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

#14.08.2026 eklendi
#amaç işleetmenin geçmiş denetimlerini de göstermek
@router.get(
        "/{business_id}/inspections",
        response_model=List[schemas.InspectionResponse]
)
def get_business_inspections(
    business_id: int,
    db: Session = Depends(get_db),
):
    business = db.query(models.Business).filter(
        models.Business.id == business_id
    ).first()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="İşletme Bulunamadı"
        )

    inspections = (
        db.query(models.Inspection)
        .filter(models.Inspection.business_id == business_id)
        .order_by(models.Inspection.inspection_date.desc())
        .all()
    )

    return inspections


# GOOGLE'DAN YORUMLARI ÇEKİP SİSTEME KAYDETME EKRANI
@router.post("/{business_id}/sync-reviews")
async def sync_business_reviews(
    business_id: int, 
    db: Session = Depends(get_db),
    #current_user: models.User = Depends(get_current_user) 
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
        #aynı yorum daha önce var mı diye bakalım
        existing_review = db.query(models.GoogleReview).filter(
            models.GoogleReview.business_id == business_id,
            models.GoogleReview.author_name == rev_data["author_name"],
            models.GoogleReview.rating == rev_data["rating"],
            models.GoogleReview.text == rev_data["text"],
            models.GoogleReview.publish_date == str(rev_data["publish_date"])
        ).first()

        # yorum zaten varsa eklemeden sonraki yoruma geçiyoruz.
        if existing_review:
            continue

        new_review = models.GoogleReview(
            business_id=business_id,
            author_name=rev_data["author_name"],
            rating=rev_data["rating"],
            text=rev_data["text"],
            publish_date=str(rev_data["publish_date"])
        )

        # Yorumu şimdilik alışveriş sepetine atıyoruz, henüz kasadan geçirmedik.
        db.add(new_review)
        added_count += 1

    # 4. Adım: Sepetteki her şeyi tek seferde kasadan geçirip deftere işliyoruz.
    # Tek tek uğraşmak yerine hepsini bir kerede kaydedip sistemi yormuyoruz.
    db.commit()

    # İşlem bitince ekrana "Şu kadar yorum başarıyla kaydedildi" yazdırıyoruz.
    return {"message": f"{added_count} adet yorum başarıyla eşitlendi."}


#07.08.2026
#Kategorileri listeleme endpointi ekleyelim
@router.get("/categories/all", response_model=List[schemas.CategoryResponse])
def get_business_categories(
    db: Session = Depends(get_db),
): 
    categories = db.query(models.BusinessCategory).all()
    return categories

#18.08.2026
#süper adminin yeni işletme kategorisi eklemesi için
@router.post(
    "/categories",
    response_model=schemas.CategoryResponse,
    status_code=status.HTTP_201_CREATED
)
def create_business_category(
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
):
    #aynı isimde kategori var mı
    existing_category = db.query(models.BusinessCategory).filter(
        models.BusinessCategory.name == category.name
    ).first()

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu kategori zaten mevcut."
        )

    # yeni jkategori ekle
    new_category = models.BusinessCategory(
        name=category.name
    )

    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    return new_category


#18.08.2026
#mevcut işletme kategorilerini güncellemek için
@router.put(
    "/categories/{category_id}",
    response_model=schemas.CategoryResponse
)
def update_business_category(
    category_id: int,
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
):
    #güncellenecek kategoriyi bul
    existing_category = db.query(models.BusinessCategory).filter(
        models.BusinessCategory.id == category_id
    ).first()

    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kategori bulunamadı."
        )

    duplicate_category = db.query(models.BusinessCategory).filter(
        models.BusinessCategory.name == category.name,
        models.BusinessCategory.id != category_id

    ).first()

    if duplicate_category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Bu kategori adı zaten kullanılıyor.")

    #güncelle
    existing_category.name = category.name

    db.commit()
    db.refresh(existing_category)

    return existing_category



#kategori silme işlemi
#18.08.2026
@router.delete("/categories/{category_id}")
def delete_business_category(
    category_id: int,
    db: Session = Depends(get_db),
): 
    # silinecek kategoriyi bul
    existing_category = db.query(models.BusinessCategory).filter(
        models.BusinessCategory.id == category_id
    ).first()

    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kategori bulunamadı."
        )

    db.delete(existing_category)
    db.commit()

    return {
        "message": "Kategori başarıyla silindi.",
        "category_id": category_id
    }