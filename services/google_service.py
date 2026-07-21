import httpx
import os
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yüklüyoruz
load_dotenv()

# API anahtarını değişkene alıyoruz
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