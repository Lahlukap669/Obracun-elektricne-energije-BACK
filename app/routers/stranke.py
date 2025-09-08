from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..core.database import get_db
from ..core.logging import app_logger
from ..models.models import Stranka
from ..schemas.schemas import (
    Stranka as StrankaSchema,
    StrankaCreate,
    StrankaUpdate
)

router = APIRouter(prefix="/stranke", tags=["Stranke"])

@router.get("/", response_model=List[StrankaSchema])
async def get_stranke(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Pridobi seznam strank"""
    query = db.query(Stranka)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Stranka.ime.ilike(search_filter)) |
            (Stranka.priimek.ilike(search_filter)) |
            (Stranka.email.ilike(search_filter))
        )
    
    stranke = query.offset(skip).limit(limit).all()
    
    app_logger.info(f"Retrieved {len(stranke)} customers")
    return stranke

@router.get("/{stranka_id}", response_model=StrankaSchema)
async def get_stranka(stranka_id: int, db: Session = Depends(get_db)):
    """Pridobi podrobnosti stranke"""
    stranka = db.query(Stranka).filter(Stranka.id == stranka_id).first()
    if not stranka:
        raise HTTPException(status_code=404, detail="Stranka ne obstaja")
    
    return stranka

@router.post("/", response_model=StrankaSchema)
async def create_stranka(stranka: StrankaCreate, db: Session = Depends(get_db)):
    """Ustvari novo stranko"""
    
    # Check if email already exists
    if stranka.email:
        existing = db.query(Stranka).filter(Stranka.email == stranka.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="E-mail naslov že obstaja")
    
    try:
        db_stranka = Stranka(**stranka.dict())
        db.add(db_stranka)
        db.commit()
        db.refresh(db_stranka)
        
        app_logger.info(f"Created customer: {db_stranka.ime} {db_stranka.priimek}")
        return db_stranka
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error creating customer: {str(e)}")
        raise HTTPException(status_code=400, detail="Napaka pri ustvarjanju stranke")

@router.put("/{stranka_id}", response_model=StrankaSchema)
async def update_stranka(
    stranka_id: int, 
    stranka_update: StrankaUpdate, 
    db: Session = Depends(get_db)
):
    """Posodobi stranko"""
    stranka = db.query(Stranka).filter(Stranka.id == stranka_id).first()
    if not stranka:
        raise HTTPException(status_code=404, detail="Stranka ne obstaja")
    
    # Check email uniqueness if being updated
    if stranka_update.email and stranka_update.email != stranka.email:
        existing = db.query(Stranka).filter(
            Stranka.email == stranka_update.email,
            Stranka.id != stranka_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="E-mail naslov že obstaja")
    
    try:
        # Update only provided fields
        update_data = stranka_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(stranka, field, value)
        
        db.commit()
        db.refresh(stranka)
        
        app_logger.info(f"Updated customer: {stranka.ime} {stranka.priimek}")
        return stranka
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error updating customer: {str(e)}")
        raise HTTPException(status_code=400, detail="Napaka pri posodabljanju stranke")

@router.delete("/{stranka_id}")
async def delete_stranka(stranka_id: int, db: Session = Depends(get_db)):
    """Izbriši stranko"""
    stranka = db.query(Stranka).filter(Stranka.id == stranka_id).first()
    if not stranka:
        raise HTTPException(status_code=404, detail="Stranka ne obstaja")
    
    # Check if customer has locations
    if stranka.lokacije:
        raise HTTPException(
            status_code=400, 
            detail="Stranke z obstoječimi lokacijami ni mogoče izbrisati"
        )
    
    try:
        db.delete(stranka)
        db.commit()
        
        app_logger.info(f"Deleted customer: {stranka.ime} {stranka.priimek}")
        return {"message": "Stranka je bila uspešno izbrisana"}
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error deleting customer: {str(e)}")
        raise HTTPException(status_code=400, detail="Napaka pri brisanju stranke")

@router.get("/{stranka_id}/lokacije")
async def get_stranka_lokacije(stranka_id: int, db: Session = Depends(get_db)):
    """Pridobi vse lokacije stranke"""
    stranka = db.query(Stranka).filter(Stranka.id == stranka_id).first()
    if not stranka:
        raise HTTPException(status_code=404, detail="Stranka ne obstaja")
    
    return stranka.lokacije

@router.get("/{stranka_id}/racuni")
async def get_stranka_racuni(stranka_id: int, db: Session = Depends(get_db)):
    """Pridobi vse račune stranke"""
    from ..models.models import Racun, Lokacija
    
    stranka = db.query(Stranka).filter(Stranka.id == stranka_id).first()
    if not stranka:
        raise HTTPException(status_code=404, detail="Stranka ne obstaja")
    
    # Get all invoices for customer's locations
    racuni = db.query(Racun).join(Lokacija).filter(
        Lokacija.stranka_id == stranka_id
    ).order_by(Racun.datum_izdaje.desc()).all()
    
    return racuni
