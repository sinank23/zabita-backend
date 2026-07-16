import os
from dotenv import load_dotenv
import google.generativeai as genai

# .env dosyasını yükle
load_dotenv()

# API anahtarını al
api_key = os.getenv("GEMINI_API_KEY")

# API anahtarı varsa Gemini'yi yapılandır
if api_key:
    genai.configure(api_key=api_key)


def analyze_image_with_ai(image_path: str, criteria_text: str) -> str:
    """
    Belirtilen yoldaki fotoğrafı yapay zekaya gönderir ve
    denetim kriterine göre analiz eder.
    """

    try:
        # API anahtarı kontrolü
        if not api_key or api_key == "BURAYA_GELECEK":
            return "Sistem uyarısı: Geçerli bir API anahtarı bulunamadı."

        # Fotoğrafı Gemini'nin anlayacağı formata yükle
        sample_file = genai.upload_file(path=image_path)

        # Modeli oluştur
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")

        # Prompt
        prompt = f"""
Sen uzman ve tarafsız bir zabıta denetim asistanısın.

Sana verilen şu denetim kriterine göre bu fotoğrafı incele:
'{criteria_text}'.

Değerlendirmeni yaparken ilk kelimen kesinlikle 'Uygun' veya 'Uygun Değil' olmalı.
Ardından tek ve kısa bir cümleyle nedenini açıkla.
"""

        # Gemini'den cevap al
        response = model.generate_content([prompt, sample_file])

        return response.text

    except Exception as e:
        return f"Yapay zeka analizinde hata oluştu: {e}"