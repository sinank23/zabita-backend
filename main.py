from fastapi import FastAPI
import models
from database import engine
from routers import users, businesses, inspections, photos # photos eklendi

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Zabıta AI API", description="Zabıta Mobil Uygulaması Backend Servisi")

app.include_router(users.router)
app.include_router(businesses.router)
app.include_router(inspections.router)
app.include_router(photos.router) # Yeni departman eklendi

@app.get("/")
def read_root():
    return {"mesaj": "Zabıta Mobil Uygulaması API'si Başarıyla Çalışıyor!"}