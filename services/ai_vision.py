import os
from google import genai
from PIL import Image
from dotenv import load_dotenv
import asyncio

# 1. Ortam değişkenlerini yüklüyoruz
load_dotenv()

# 2. Yeni kütüphane ile Client oluşturuyoruz
client = genai.Client()

async def analyze_image_with_ai(image_path: str) -> str:
    try:
        # Fotoğrafı açıyoruz
        img = Image.open(image_path)
        
        # Prompt metnimiz
        prompt = """
        Sen uzman bir belediye zabıta denetim asistanısın. 
        Bu fotoğraftaki işletmenin genel hijyen durumunu, düzenini ve göze çarpan herhangi bir kural ihlali (örneğin; yerlerde çöp, dağınıklık, bozuk gıda vb.) olup olmadığını kısaca analiz et. 
        Cevabını resmi bir rapor diliyle ve kısa paragraflar halinde ver.
        """
        
        # 3. En yeni ve hızlı model ile analizi başlatıyoruz
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=[img, prompt]
        )
        
        return response.text
        
    except Exception as e:
        return f"Yapay zeka analizi sırasında bir hata oluştu: {str(e)}"
    

async def synthesize_inspection_data(
    answers_text: str,
    inspector_notes: str,
    photo_analyses: str,
    google_reviews: str
) -> str:
    """
    Denetim verilerini analiz edip genel durumu özetler.
    """

    # GÜNCELLENDİ: Puanlama kaldırıldı, başmüfettiş rolüyle çapraz analiz (cross-check) promptu eklendi.
    prompt = f"""
    Sen uzman bir belediye denetim başmüfettişisin.
    Görevin, bir işletme hakkında farklı kaynaklardan gelen denetim verilerini
    birlikte incelemek, kaynaklar arasında çapraz doğrulama yapmak ve
    anlaşılır, kurumsal bir denetim raporu oluşturmaktır.

    KESİN KURALLAR:
    - Hiçbir şekilde 100 üzerinden veya başka bir ölçekte sayısal puanlama YAPMA.
    - Markdown kullanma.
    - **, *, #, ### gibi biçimlendirme karakterleri kullanma.
    - Aşağıda verilen bölüm başlıklarını aynen kullan.
    - Bölüm başlıklarının dışına yeni bir başlık ekleme.
    - Bir veri kaynağında görünmeyen bir durumu kesin olarak yok kabul etme.
    - Fotoğrafların yalnızca görüntüde bulunan alanları temsil ettiğini dikkate al.
    - Google yorumlarını resmi zabıta tespiti gibi değerlendirme; bunları destekleyici kullanıcı geri bildirimi olarak kullan.
    - Zabıta personelinin notlarını, kriter cevaplarını, fotoğraf bulgularını ve Google yorumlarını birbirinin yerine kullanma.
    - Veriler arasında çelişki varsa bunu açıkça belirt.
    - Yeterli veri olmayan konuda kesin hüküm verme.
    - Aynı bulguyu farklı bölümlerde gereksiz yere tekrar etme.
    - Raporu resmi, sade ve anlaşılır Türkçe ile yaz.

    DENETİM VERİLERİ:

    Zabıtanın Denetim Kriteri Cevapları:
    {answers_text}

    Zabıta Personelinin Sahadaki Gözlem Notu:
    {inspector_notes}

    Denetim Fotoğraflarının Yapay Zeka Analizleri:
    {photo_analyses}

    İşletmenin Google Haritalar Yorumları:
    {google_reviews}

    Aşağıdaki yapıyı KESİNLİKLE bozma:

    [GENEL_DEGERLENDIRME]
    İşletmenin genel denetim durumunu birkaç açık cümleyle özetle.
    En önemli olumlu ve olumsuz bulguları belirt.
    Ayrıntıları diğer bölümlere bırak.

    [DENETIM_KRITERLERI]
    Zabıta tarafından cevaplanan denetim kriterlerindeki önemli olumlu ve olumsuz bulguları değerlendir.
    Özellikle "Hayır" cevabı verilen ve risk veya eksiklik ifade edebilecek kriterleri açıkla.
    Kriter cevaplarını başka veri kaynaklarıyla henüz karıştırmadan önce kendi içinde değerlendir.

    [FOTOGRAF_BULGULARI]
    Fotoğraf analizlerinden elde edilen önemli görsel bulguları özetle.
    Fotoğrafta görünmeyen alanlar hakkında kesin çıkarım yapma.
    Fotoğrafların kapsamının sınırlı olduğu durumlarda bunu açıkça belirt.

    [GOOGLE_YORUMLARI]
    Google yorumlarında tekrar eden olumlu veya olumsuz kullanıcı geri bildirimlerini değerlendir.
    Özellikle hijyen, hizmet kalitesi, düzen ve tekrar eden şikayetleri belirt.
    Yorumları resmi denetim bulgusu olarak sunma.

    [ZABITA_NOTU_KARSILASTIRMASI]
    Zabıta personelinin gözlem notunu;
    denetim kriterleri, fotoğraf bulguları ve Google yorumlarıyla karşılaştır.
    Desteklenen, desteklenmeyen veya diğer verilerle çelişen noktaları açıkça belirt.
    Eğer zabıta notu boş veya yetersizse bunu kısa şekilde belirt.

    [TUTARLILIK_VE_RISKLER]
    Tüm veri kaynaklarını birlikte çapraz değerlendir.
    Birbirini destekleyen bulguları ve varsa çelişkileri açıkça yaz.
    Tespit edilen önemli hijyen, düzen, hizmet, güvenlik veya mevzuat risklerini niteliksel olarak belirt.
    Sayısal risk puanı üretme.

    [ONERILER]
    Tespit edilen bulgulara göre uygulanabilir ve kısa öneriler sun.
    Hangi konuların tekrar kontrol edilmesi veya yerinde doğrulanması gerektiğini belirt.
    Verinin yeterli olmadığı konularda kesin yaptırım önerme.

    Her bölümde yalnızca o bölüme ait içeriği yaz.
    Başlıkları aynen köşeli parantez içinde bırak.
    """

    # İlk istek başarısız olursa toplam 3 kez deneme yapılacak.
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=[prompt]
            )

            return response.text

        except Exception as e:
            error_text = str(e)

            # Yalnızca geçici yoğunluk veya servis kullanılamıyor
            # hatalarında yeniden deneme yapıyoruz.
            is_temporary_error = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "high demand" in error_text.lower()
                or "overloaded" in error_text.lower()
            )

            # Geçici olmayan bir hataysa boşuna tekrar denemiyoruz.
            if not is_temporary_error:
                raise RuntimeError(
                    f"Yapay zeka raporu oluşturulamadı: {error_text}"
                ) from e

            # Son deneme de başarısız olduysa hatayı üst katmana iletiyoruz.
            if attempt == max_attempts:
                raise RuntimeError(
                    f"Yapay zeka servisi {max_attempts} denemeden sonra hâlâ kullanılamıyor: {error_text}"
                ) from e

            # İlk hatada 2 saniye, ikinci hatada 4 saniye beklenir.
            wait_seconds = 2 ** attempt

            print(
                f"Gemini servisi geçici olarak kullanılamıyor. "
                f"{wait_seconds} saniye sonra yeniden denenecek. "
                f"Deneme: {attempt}/{max_attempts}"
            )

            # Asenkron bekleme sayesinde backend tamamen kilitlenmez.
            await asyncio.sleep(wait_seconds)

    # Normal şartlarda buraya ulaşılmaz.
    raise RuntimeError("Yapay zeka raporu bilinmeyen bir nedenle oluşturulamadı.")