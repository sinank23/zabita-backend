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
    

async def synthesize_inspection_data(answers_text: str, inspector_notes: str, photo_analyses: str) -> str:

    """
Denetim verilerini analiz edip genel durumu özetler.
"""

    try:
        prompt = f"""
        Sen uzman bir belediye denetim asistanısın. Görevin, sahadaki zabıta memurunun girdiği verileri ve görsel analizleri inceleyerek kısa, net ve resmi bir özet rapor oluşturmaktır.
        
        Aşağıda bir işletmenin denetim verileri bulunmaktadır:
        
        1. FORM CEVAPLARI:
        {answers_text}
        
        2. ZABITA MEMURUNUN NOTLARI:
        {inspector_notes or "Not girilmemiş."}
        
        3. FOTOĞRAF ANALİZ SONUÇLARI:
        {photo_analyses or "Fotoğraf yüklenmemiş."}
        
        Lütfen bu üç veri kaynağını karşılaştır. 
        - Gözle görülür bir tutarsızlık var mı? (Örn: Zabıta temizliğe "Evet" demiş ama fotoğrafta çöp tespit edilmiş mi?)
        - İşletmenin genel durumu nasıl?
        - Acil düzeltilmesi gereken kritik ihlaller (ruhsat, yangın tüpü, hijyen) var mı?
        
        Cevabını madde imleri kullanarak, resmi bir rapor formatında ve anlaşılır bir Türkçe ile yaz. Puan verme, sadece durumu özetle.
        """

        resonse = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=[prompt]
        )

        return response.text
    
    except Exception as e:
        return f"Rapor oluşturulurken hata meydana geldi"