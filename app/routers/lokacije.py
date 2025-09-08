from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..core.database import get_db
from ..core.logging import app_logger
from ..models.models import Lokacija, Stranka
from ..schemas.schemas import (
    Lokacija as LokacijaSchema,
    LokacijaCreate,
    LokacijaUpdate
)

router = APIRouter(prefix="/lokacije", tags=["Lokacije"])

@router.get("/", response_model=List[LokacijaSchema])
async def get_lokacije(
    skip: int = 0,
    limit: int = 100,
    stranka_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Pridobi seznam lokacij"""
    query = db.query(Lokacija)
    
    if stranka_id:
        query = query.filter(Lokacija.stranka_id == stranka_id)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Lokacija.naziv.ilike(search_filter)) |
            (Lokacija.naslov.ilike(search_filter)) |
            (Lokacija.merilna_stevilka.ilike(search_filter))
        )
    
    lokacije = query.offset(skip).limit(limit).all()
    
    app_logger.info(f"Retrieved {len(lokacije)} locations")
    return lokacije

@router.get("/{lokacija_id}", response_model=LokacijaSchema)
async def get_lokacija(lokacija_id: int, db: Session = Depends(get_db)):
    """Pridobi podrobnosti lokacije"""
    lokacija = db.query(Lokacija).filter(Lokacija.id == lokacija_id).first()
    if not lokacija:
        raise HTTPException(status_code=404, detail="Lokacija ne obstaja")
    
    return lokacija

@router.post("/", response_model=LokacijaSchema)
async def create_lokacija(lokacija: LokacijaCreate, db: Session = Depends(get_db)):
    """Ustvari novo lokacijo"""
    
    # Check if customer exists
    stranka = db.query(Stranka).filter(Stranka.id == lokacija.stranka_id).first()
    if not stranka:
        raise HTTPException(status_code=404, detail="Stranka ne obstaja")
    
    # Check if merilna_stevilka already exists
    if lokacija.merilna_stevilka:
        existing = db.query(Lokacija).filter(
            Lokacija.merilna_stevilka == lokacija.merilna_stevilka
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Merilna številka že obstaja")
    
    try:
        db_lokacija = Lokacija(**lokacija.dict())
        db.add(db_lokacija)
        db.commit()
        db.refresh(db_lokacija)
        
        app_logger.info(f"Created location: {db_lokacija.naziv} for customer {stranka.ime} {stranka.priimek}")
        return db_lokacija
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error creating location: {str(e)}")
        raise HTTPException(status_code=400, detail="Napaka pri ustvarjanju lokacije")

@router.put("/{lokacija_id}", response_model=LokacijaSchema)
async def update_lokacija(
    lokacija_id: int, 
    lokacija_update: LokacijaUpdate, 
    db: Session = Depends(get_db)
):
    """Posodobi lokacijo"""
    lokacija = db.query(Lokacija).filter(Lokacija.id == lokacija_id).first()
    if not lokacija:
        raise HTTPException(status_code=404, detail="Lokacija ne obstaja")
    
    # Check merilna_stevilka uniqueness if being updated
    if (lokacija_update.merilna_stevilka and 
        lokacija_update.merilna_stevilka != lokacija.merilna_stevilka):
        existing = db.query(Lokacija).filter(
            Lokacija.merilna_stevilka == lokacija_update.merilna_stevilka,
            Lokacija.id != lokacija_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Merilna številka že obstaja")
    
    try:
        # Update only provided fields
        update_data = lokacija_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lokacija, field, value)
        
        db.commit()
        db.refresh(lokacija)
        
        app_logger.info(f"Updated location: {lokacija.naziv}")
        return lokacija
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error updating location: {str(e)}")
        raise HTTPException(status_code=400, detail="Napaka pri posodabljanju lokacije")

@router.delete("/{lokacija_id}")
async def delete_lokacija(lokacija_id: int, db: Session = Depends(get_db)):
    """Izbriši lokacijo"""
    lokacija = db.query(Lokacija).filter(Lokacija.id == lokacija_id).first()
    if not lokacija:
        raise HTTPException(status_code=404, detail="Lokacija ne obstaja")
    
    # Check if location has measurements
    if lokacija.meritve:
        raise HTTPException(
            status_code=400, 
            detail="Lokacije z obstoječimi meritvami ni mogoče izbrisati"
        )
    
    # Check if location has invoices
    if lokacija.racuni:
        raise HTTPException(
            status_code=400, 
            detail="Lokacije z obstoječimi računi ni mogoče izbrisati"
        )
    
    try:
        db.delete(lokacija)
        db.commit()
        
        app_logger.info(f"Deleted location: {lokacija.naziv}")
        return {"message": "Lokacija je bila uspešno izbrisana"}
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error deleting location: {str(e)}")
        raise HTTPException(status_code=400, detail="Napaka pri brisanju lokacije")

@router.get("/{lokacija_id}/meritve")
async def get_lokacija_meritve(
    lokacija_id: int,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Pridobi meritve za lokacijo"""
    from ..models.models import Meritev
    
    lokacija = db.query(Lokacija).filter(Lokacija.id == lokacija_id).first()
    if not lokacija:
        raise HTTPException(status_code=404, detail="Lokacija ne obstaja")
    
    meritve = db.query(Meritev).filter(
        Meritev.lokacija_id == lokacija_id
    ).order_by(Meritev.casovni_zig.desc()).offset(skip).limit(limit).all()
    
    return meritve

@router.get("/{lokacija_id}/racuni")
async def get_lokacija_racuni(lokacija_id: int, db: Session = Depends(get_db)):
    """Pridobi račune za lokacijo"""
    lokacija = db.query(Lokacija).filter(Lokacija.id == lokacija_id).first()
    if not lokacija:
        raise HTTPException(status_code=404, detail="Lokacija ne obstaja")
    
    return lokacija.racuni

@router.get("/{lokacija_id}/statistics")
async def get_lokacija_statistics(
    lokacija_id: int,
    datum_od: Optional[str] = None,
    datum_do: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Pridobi statistike za lokacijo"""
    from datetime import datetime, date
    from ..services.calculation_service import CalculationService
    
    lokacija = db.query(Lokacija).filter(Lokacija.id == lokacija_id).first()
    if not lokacija:
        raise HTTPException(status_code=404, detail="Lokacija ne obstaja")
    
    # Default to current month if no dates provided
    if not datum_od or not datum_do:
        today = date.today()
        datum_od = today.replace(day=1)
        if today.month == 12:
            datum_do = today.replace(year=today.year + 1, month=1, day=1)
        else:
            datum_do = today.replace(month=today.month + 1, day=1)
    else:
        try:
            datum_od = datetime.strptime(datum_od, '%Y-%m-%d').date()
            datum_do = datetime.strptime(datum_do, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Napačen format datuma. Uporabite YYYY-MM-DD"
            )
    
    try:
        stats = CalculationService.calculate_statistics(
            db, lokacija_id, datum_od, datum_do
        )
        
        return {
            "lokacija": lokacija,
            "obdobje": {
                "datum_od": datum_od,
                "datum_do": datum_do
            },
            "statistike": stats
        }
        
    except Exception as e:
        app_logger.error(f"Error calculating statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Napaka pri izračunu statistik")
