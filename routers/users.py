from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas

from database import get_db
from services.security import get_password_hash
from routers.auth import get_current_user


router = APIRouter(
    prefix="/users",
    tags=["Kullanıcı İşlemleri"]
)


@router.post(
    "/",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    try:
        # Aynı e-posta adresine sahip kullanıcı var mı?
        existing_user = (
            db.query(models.User)
            .filter(models.User.email == user.email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu e-posta adresi zaten kayıtlı."
            )

        # Kullanıcının düz şifresini hashle
        hashed_password = get_password_hash(user.password)

        # Veritabanına kaydedilecek User modelini oluştur
        new_user = models.User(
            full_name=user.full_name,
            email=user.email,
            password_hash=hashed_password,
            role=user.role
        )

        # Kullanıcıyı veritabanına ekle
        db.add(new_user)
        db.commit()

        # Veritabanının oluşturduğu id ve created_at gibi alanları yenile
        db.refresh(new_user)

        return new_user

    except HTTPException:
        # Bilerek oluşturduğumuz 400 gibi HTTP hatalarını aynen gönder
        raise

    except Exception as e:
        # Yarım kalan veritabanı işlemini geri al
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kullanıcı oluşturulurken sistem hatası oluştu: {str(e)}"
        )


@router.get(
    "/me",
    response_model=schemas.UserResponse
)
def get_my_profile(
    current_user: models.User = Depends(get_current_user)
):
    return current_user