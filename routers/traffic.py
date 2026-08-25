from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas

from database import get_db
from routers.auth import get_current_user

router = APIRouter(
    prefix="/traffic",
    tags=["Trafik Zabıta İşlemleri"]
)

#25.08.2026
#yeni trafik işlem kaydı oluştrumak için

@router.post(
    "/",
    response_model=schemas.TrafficInspectionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_traffic_inspection(
    traffic_data: schemas.TrafficInspectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # sadece trafik zabıta işlem yapabilsin
    if current_user.role != "trafik_zabita":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Trafik Zabıta yetkisi gereklidir."
        )
    try:
        new_traffic_inspection = models.TrafficInspection(
            violation_type=traffic_data.violation_type,
            plate=traffic_data.plate,
            vehicle_type=traffic_data.vehicle_type,
            address=traffic_data.address,
            latitude=traffic_data.latitude,
            longitude=traffic_data.longitude,
            description=traffic_data.description,
            action_taken=traffic_data.action_taken,
            inspector_id=current_user.id
        )

        db.add(new_traffic_inspection)
        db.commit()
        db.refresh(new_traffic_inspection)

        return new_traffic_inspection

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trafik işlemi oluşturulurken hata oluştu: {str(e)}"
        )