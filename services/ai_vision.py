import os
from google import genai
from PIL import Image
from dotenv import load_dotenv

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
    

async def synthesize_inspection_data(answers_text: str, inspector_notes: str, photo_analyses: str, google_reviews: str) -> str:
    """
    Denetim verilerini analiz edip genel durumu özetler.
    """
    try:
        # GÜNCELLENDİ: Puanlama kaldırıldı, başmüfettiş rolüyle çapraz analiz (cross-check) promptu eklendi.
        prompt = f"""
        Sen uzman bir denetim başmüfettişisin. Görevin, bir işletme hakkında farklı kaynaklardan gelen verileri analiz etmek ve çapraz doğrulama (cross-check) yapmaktır.
        
        KESİN KURAL: Hiçbir şekilde 100 üzerinden veya başka bir ölçekte sayısal puanlama YAPMA. Sadece niteliksel bir durum raporu yaz.

        Eldeki Veriler:
        1. Zabıtanın Anket Cevapları: {answers_text}
        2. Zabıtanın Sahadaki Gözlem Notları: {inspector_notes}
        3. Denetim Fotoğraflarının Yapay Zeka Analizi: {photo_analyses}
        4. İşletmenin Google Haritalar Yorumları: {google_reviews}

        Lütfen şu adımları izleyerek profesyonel bir rapor oluştur:
        - Tutarlılık Kontrolü: Zabıtanın cevapları, gözlemleri ve fotoğraflar birbiriyle uyuşuyor mu? (Örneğin; zabıta hijyen 'Evet' demiş ama fotoğraflarda kirlilik varsa veya yorumlarda sürekli şikayet varsa bu çelişkiyi yakala).
        - Müşteri Gözü: Google yorumlarındaki kronik şikayetler, denetim bulgularıyla örtüşüyor mu?
        - Sonuç ve Öneri: Mevcut tabloya göre işletmenin genel durumunu özetle ve tespit edilen tutarsızlıkları/eksikleri net bir şekilde belirt.
        
        Raporu kurumsal, resmi bir dille ve doğrudan konuya girerek yaz.
        """

        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=[prompt]
        )

        return response.text
    
    except Exception as e:
        raise RuntimeError(f"Yapay zeka raporu oluşturulamadı: {str(e)}") from e