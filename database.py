from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Bağlantı Bilgileri
SERVER_NAME = "localhost" 
DATABASE_NAME = "zabita_ai_db"
DRIVER = "ODBC Driver 17 for SQL Server" 

# Windows Kimlik Doğrulaması (Trusted_Connection=yes) kullanan bağlantı dizesi
SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc://@{SERVER_NAME}/{DATABASE_NAME}?driver={DRIVER}&Trusted_Connection=yes"

# 2. Motor (Engine) Oluşturma
# SQLAlchemy'nin veritabanı ile kurduğu fiziksel bağlantının merkezidir.
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 3. Oturum (Session) Yapılandırması
# Her bir API isteği geldiğinde veritabanı ile işlem yapmak için geçici bir oturum açacağız.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Temel Sınıf (Base)
# Tablolarımızı (users, businesses vb.) Python sınıfları olarak tanımlarken bu Base sınıfını miras alacağız.
Base = declarative_base()