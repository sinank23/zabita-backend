import os
from google import genai
from PIL import Image
from dotenv import load_dotenv

# 1. Ortam değişkenlerini yüklüyoruz
load_dotenv()

# 2. Yeni kütüphane ile Client oluşturuyoruz (GEMINI_API_KEY'i otomatik bulur)
client = genai.Client()

async def analyze_inspection_photo(image_path: str) -> str:
    try:
        # Fotoğrafı açıyoruz
        img = Image.open(image_path)
        
        # Prompt metnimiz
        prompt = """
        Sen uzman bir belediye zabıta denetim asistanısın. 
        Bu fotoğraftaki işletmenin genel hijyen durumunu, düzenini ve göze çarpan herhangi bir kural ihlali (örneğin; yerlerde çöp, dağınıklık, bozuk gıda vb.) olup olmadığını kısaca analiz et. 
        Cevabını resmi bir rapor diliyle ve kısa paragraflar halinde ver.
        """
        
        # 3. Listeden seçtiğimiz en yeni ve hızlı model ile analizi başlatıyoruz
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=[img, prompt]
        )
        
        return response.text
        
    except Exception as e:
        return f"Yapay zeka analizi sırasında bir hata oluştu: {str(e)}"