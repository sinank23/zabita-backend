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



#24.08.2026
#süper admin panelinde tüm kullanıcıları listelemek için
@router.get(
    "/admin/all",
    response_model=list[schemas.UserResponse]
)
def get_all_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Süper Admin yetkisi gereklidir."
        )

    users = (
        db.query(models.User)
        .order_by(models.User.id.asc())
        .all()
    )

    return users

#24.08.2026
# Süper Admin tarafından mevcut kullanıcı bilgilerini güncellemek için
@router.put(
    "/admin/{user_id}",
    response_model=schemas.UserResponse
)
def update_user(
    user_id: int,
    user: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # sadece süper admin kullanıcı güncelleyebilsin
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Süper Admin yetkisi gereklidir."
        )

    # güncellenecek kullanıcıyı bul
    existing_user = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı."
        )

    # aynı e-posta başka bir kullanıcı tarafından kullanılıyor mu kontrol et
    duplicate_email = (
        db.query(models.User)
        .filter(
            models.User.email == user.email,
            models.User.id != user_id
        )
        .first()
    )

    if duplicate_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresi başka bir kullanıcı tarafından kullanılıyor."
        )

    try:

        existing_user.full_name = user.full_name
        existing_user.email = user.email
        existing_user.role = user.role

        # yeni şifre girildiyse hashleyerek güncelle
        if user.password:
            existing_user.password_hash = get_password_hash(user.password)

        db.commit()
        db.refresh(existing_user)

        return existing_user

    except HTTPException:
        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kullanıcı güncellenirken sistem hatası oluştu: {str(e)}"
        )


#24.08.2026
#süper admin tarafından kullanıcı silmek için
@router.delete(
    "/admin/{user_id}"
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # sadece admin hesap silebilsin
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Admin yetkisi gereklidir."

        )

    # sileceğimiz kullanıcıyı bulalım.
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı."
        )

    #süper admin kendi hesabını silemesin
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Süper Admin kendi hesabını silemez."
        )

    try:

        db.delete(user)
        db.commit()

        return {
            "message": f"{user_id} ID'li kullanıcı başarıyla silindi."
        }

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kullanıcı silinirken sistem hatası oluştu: {str(e)}"
        )
    