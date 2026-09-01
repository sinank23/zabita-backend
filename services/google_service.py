import httpx
import os
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yüklüyoruz
load_dotenv()

# API anahtarını değişkene alıyoruz
# .env dosyasındaki değişkenin adını yazıyoruz
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# asenkron yapmamızın sebebi google den cevap beklerken sunucu kitlenmez.

async def fetch_google_reviews(place_id: str) -> list:        #Bu kimlik Google Maps’teki işletmeyi benzersiz şekilde tanımlar.
    """
    Verilen Google Place ID'sine ait yorumları Google Places API'den çeker.
    """
    if not GOOGLE_API_KEY:
        print("HATA: Google API Key bulunamadı!") 
        return []

    

    # Google Places API uç noktası
    url = f"https://maps.googleapis.com/maps/api/place/details/json"
    
    # API'ye göndereceğimiz parametreler (sadece yorumları istiyoruz ki kota az gitsin)
    params = {
        "place_id": place_id,
        "fields": "reviews",  # sadece yorum alanını istiyoruz.
        "language": "tr", # Yorumların Türkçe çevirisi varsa onu getirir
        "key": GOOGLE_API_KEY
    }


    #async with kullanmamızın sebebi işimiz bittiğinde bağlanıtıyı düzgünce kapatabilmek için.
    async with httpx.AsyncClient() as client:
        try:
            # Google'a GET isteği atıyoruz
            response = await client.get(url, params=params)
            response.raise_for_status() # Hata varsa fırlatır
            
            data = response.json()
            print("GOOGLE'DAN GELEN CEVAP:", data)
            
            # Gelen veriyi (ayrıştırıyoruz)
            if "result" in data and "reviews" in data["result"]:
                raw_reviews = data["result"]["reviews"]
                processed_reviews = []     # sadeleşen ayrışan yorumlar bu listeye eklenecek
                
                # Google'ın verdiği karmaşık veriyi kendi sistemimize uygun hale getiriyoruz
                for rev in raw_reviews:
                    processed_reviews.append({
                        "author_name": rev.get("author_name", "Gizli Kullanıcı"),
                        "rating": rev.get("rating", 0),
                        "text": rev.get("text", ""),
                        "publish_date": rev.get("time", 0) 
                    })
                return processed_reviews
            else:
                return [] # Yorum yoksa boş liste dön

        except Exception as e:
            print(f"Google API'den veri çekerken hata oluştu: {e}")
            return []


#google arama butonu 04.08.2026 ekliyoruz.
async def search_google_places(
     query: str,
     latitude: float,
     longitude: float  
) -> list:

    """
    Kullanıcının yazdığı işletme adını Google Places üzerinde arar.

    Arama sonuçlarını, zabıtanın mevcut konumuna yakın işletmelerden
    başlayacak şekilde önceliklendirir.
    """

    #.env dosyasındaki api keyi okuma işlemi
    if not GOOGLE_API_KEY:
        print("HATA: Google API Key bulunamadı.")
        return []

    #metin girerek işletme arama
    url = "https://places.googleapis.com/v1/places:searchText"


    headers = {
        "Content-Type": "application/json",

        "X-Goog-Api-Key": GOOGLE_API_KEY,

    # googledean ihtiyacımız olan alanları alalım gereksiz veriler gelmesin
    "X-Goog-FieldMask": (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.primaryTypeDisplayName"
)
}

  # Google'a gönderilecek arama verileri.
    body = {
        # Kullanıcının yazdığı işletme adı.
        # Örnek: "Yesemek Gaziantep Mutfağı"
        "textQuery": query,

        # İşletme adı ve adreslerin mümkün olduğunca Türkçe dönmesini ister.
        "languageCode": "tr",

        # Google'ın en fazla kaç işletme sonucu döndüreceği.
        "maxResultCount": 10,

        # Arama sonuçlarını belirtilen konuma yakın yerlerden
        # başlayacak şekilde önceliklendiriyoruz.
        "locationBias": {
            "circle": {
                # Zabıtanın mevcut GPS konumu.
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },

                # Konumun çevresindeki 5000 metrelik alanı önceliklendirir.
                # Bu kesin bir sınır değildir, yakın sonuçlara öncelik verir.
                "radius": 5000.0
            }
        }
    }

    # Asenkron istemci kullanıyoruz.
    # Google'dan cevap beklerken backend tamamen kilitlenmez.
    async with httpx.AsyncClient() as client:
        try:
            # Google Places API'ye POST isteği gönderiyoruz.
            response = await client.post(
                url,
                headers=headers,
                json=body
            )

            # Google 400, 403 veya 500 gibi bir hata döndürürse
            # bu satır hata oluşturup except bölümüne geçer.
            response.raise_for_status()

            # Google'dan gelen JSON cevabını Python sözlüğüne çeviriyoruz.
            data = response.json()

            # Cevabın içindeki "places" listesini alıyoruz.
            # Hiç sonuç yoksa boş liste kullanıyoruz.
            places = data.get("places", [])

            # Android'e göndereceğimiz sadeleştirilmiş işletme listesi.
            processed_places = []

            # Google'ın gönderdiği işletmeleri teker teker dolaşıyoruz.
            for place in places:

                # İşletme adı iç içe bir JSON nesnesi olarak geliyor.
                display_name = place.get("displayName", {})

                # Enlem ve boylam da location nesnesinin içinde geliyor.
                location = place.get("location", {})

                #01.09.2026
# Google Places üzerinden işletmenin ana faaliyet türünü almak için
                primary_type_display_name = place.get(
                    "primaryTypeDisplayName",
                    {}
)

                # Yalnızca uygulamamızın ihtiyaç duyduğu alanları alıyoruz.
                processed_places.append({
                    # Google Maps üzerindeki benzersiz işletme kimliği.
                    # Yorumları daha sonra bu kimlikle çekeceğiz.
                    "place_id": place.get("id"),

                    # İşletmenin Google Maps üzerindeki görünen adı.
                    "name": display_name.get(
                        "text",
                        "İsimsiz işletme"
                    ),

                    # İşletmenin Google Maps üzerindeki açık adresi.
                    "address": place.get("formattedAddress"),

                    # İşletmenin konumu.
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),

                    #işletmenin google mapste görünen faaliyet konusu
                    "activity_type": primary_type_display_name.get("text")
                })

            # Düzenlediğimiz işletme listesini endpoint'e geri gönderiyoruz.
            return processed_places

        except Exception as e:
            # İnternet, API anahtarı veya Google servisinden kaynaklanan
            # bir hata olursa backend terminaline hata mesajını yazdırıyoruz.
            print(f"Google işletme araması sırasında hata oluştu: {e}")

            # Uygulamanın tamamen çökmesini önlemek için boş liste döndürüyoruz.
            return []

    
