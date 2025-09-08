from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime, date

from ..core.database import get_db
from ..core.logging import app_logger
from ..models.models import Meritev, Lokacija
from ..schemas.schemas import (
    Meritev as MeritevSchema,
    MeritevCreate,
    MeritevBulkCreate
)

router = APIRouter(prefix="/meritve", tags=["Meritve"])

@router.get("/", response_model=List[MeritevSchema])
async def get_meritve(
    skip: int = 0,
    limit: int = 1000,
    lokacija_id: Optional[int] = None,
    datum_od: Optional[str] = None,
    datum_do: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Pridobi seznam meritev"""
    query = db.query(Meritev)
    
    if lokacija_id:
        query = query.filter(Meritev.lokacija_id == lokacija_id)
    
    if datum_od:
        try:
            datum_od_parsed = datetime.strptime(datum_od, '%Y-%m-%d')
            query = query.filter(Meritev.casovni_zig >= datum_od_parsed)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Napačen format datuma od. Uporabite YYYY-MM-DD"
            )
    
    if datum_do:
        try:
            datum_do_parsed = datetime.strptime(datum_do, '%Y-%m-%d')
            query = query.filter(Meritev.casovni_zig <= datum_do_parsed)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Napačen format datuma do. Uporabite YYYY-MM-DD"
            )
    
    meritve = query.order_by(desc(Meritev.casovni_zig)).offset(skip).limit(limit).all()
    
    app_logger.info(f"Retrieved {len(meritve)} measurements")
    return meritve

@router.get("/{meritev_id}", response_model=MeritevSchema)
async def get_meritev(meritev_id: int, db: Session = Depends(get_db)):
    """Pridobi podrobnosti meritve"""
    meritev = db.query(Meritev).filter(Meritev.id == meritev_id).first()
    if not meritev:
        raise HTTPException(status_code=404, detail="Meritev ne obstaja")
    
    return meritev

@router.post("/", response_model=MeritevSchema)
async def create_meritev(meritev: MeritevCreate, db: Session = Depends(get_db)):
    """Ustvari novo meritev"""
    
    # Check if location exists
    lokacija = db.query(Lokacija).filter(Lokacija.id == meritev.lokacija_id).first()
    if not lokacija:
        raise HTTPException(status_code=404, detail="Lokacija ne obstaja")
    
    # Check if measurement already exists for this location and time
    existing = db.query(Meritev).filter(
        and_(
            Meritev.lokacija_id == meritev.lokacija_id,
            Meritev.casovni_zig == meritev.casovni_zig
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Meritev za ta čas in lokacijo že obstaja"
        )
    
    # Validate values
    if meritev.poraba_kwh < 0:
        raise HTTPException(status_code=400, detail="Poraba ne sme biti negativna")
    
    if meritev.dinamicna_cena_eur_kwh <= 0:
        raise HTTPException(status_code=400, detail="Cena mora biti pozitivna")
    
    try:
        db_meritev = Meritev(**meritev.dict())
        db.add(db_meritev)
        db.commit()
        db.refresh(db_meritev)
        
        app_logger.info(f"Created measurement for location {lokacija.naziv}")
        return db_meritev
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error creating measurement: {str(e)}")
        raise HTTPException(status_code=400, detail="Napaka pri ustvarjanju meritve")

@router.post("/bulk", response_model=dict)
async def create_bulk_meritve(
    bulk_data: MeritevBulkCreate, 
    db: Session = Depends(get_db)
):
    """Ustvari več meritev naenkrat"""
    
    if not bulk_data.meritve:
        raise HTTPException(status_code=400, detail="Seznam meritev je prazen")
    
    if len(bulk_data.meritve) > 10000:
        raise HTTPException(
            status_code=400, 
            detail="Preveč meritev naenkrat. Maksimalno 10.000"
        )
    
    # Validate all locations exist
    lokacija_ids = list(set([m.lokacija_id for m in bulk_data.meritve]))
    lokacije = db.query(Lokacija).filter(Lokacija.id.in_(lokacija_ids)).all()
    existing_ids = [l.id for l in lokacije]
    
    for meritev in bulk_data.meritve:
        if meritev.lokacija_id not in existing_ids:
            raise HTTPException(
                status_code=400, 
                detail=f"Lokacija {meritev.lokacija_id} ne obstaja"
            )
    
    try:
        success_count = 0
        error_count = 0
        errors = []
        
        for meritev_data in bulk_data.meritve:
            try:
                # Check if measurement already exists
                existing = db.query(Meritev).filter(
                    and_(
                        Meritev.lokacija_id == meritev_data.lokacija_id,
                        Meritev.casovni_zig == meritev_data.casovni_zig
                    )
                ).first()
                
                if existing:
                    error_count += 1
                    errors.append(f"Meritev za {meritev_data.casovni_zig} že obstaja")
                    continue
                
                # Validate values
                if meritev_data.poraba_kwh < 0 or meritev_data.dinamicna_cena_eur_kwh <= 0:
                    error_count += 1
                    errors.append(f"Neveljavne vrednosti za {meritev_data.casovni_zig}")
                    continue
                
                db_meritev = Meritev(**meritev_data.dict())
                db.add(db_meritev)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"Napaka pri {meritev_data.casovni_zig}: {str(e)}")
        
        if success_count > 0:
            db.commit()
        else:
            db.rollback()
        
        app_logger.info(f"Bulk create: {success_count} success, {error_count} errors")
        
        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors[:10]  # Limit errors shown
        }
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error in bulk create: {str(e)}")
        raise HTTPException(status_code=500, detail="Napaka pri množičnem uvozu")

@router.delete("/{meritev_id}")
async def delete_meritev(meritev_id: int, db: Session = Depends(get_db)):
    """Izbriši meritev"""
    meritev = db.query(Meritev).filter(Meritev.id == meritev_id).first()
    if not meritev:
        raise HTTPException(status_code=404, detail="Meritev ne obstaja")
    
    # Check if measurement is used in any invoice
    if meritev.postavke_racuna:
        raise HTTPException(
            status_code=400,
            detail="Meritve, ki se uporabljajo v računih, ni mogoče izbrisati"
        )
    
    try:
        db.delete(meritev)
        db.commit()
        
        app_logger.info(f"Deleted measurement {meritev_id}")
        return {"message": "Meritev je bila uspešno izbrisana"}
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error deleting measurement: {str(e)}")
        raise HTTPException(status_code=400, detail="Napaka pri brisanju meritve")

@router.get("/statistics/summary")
async def get_meritve_summary(
    lokacija_id: Optional[int] = None,
    datum_od: Optional[str] = None,
    datum_do: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Pridobi povzetek meritev"""
    from sqlalchemy import func
    
    query = db.query(
        func.count(Meritev.id).label('count'),
        func.sum(Meritev.poraba_kwh).label('total_consumption'),
        func.avg(Meritev.dinamicna_cena_eur_kwh).label('avg_price'),
        func.min(Meritev.dinamicna_cena_eur_kwh).label('min_price'),
        func.max(Meritev.dinamicna_cena_eur_kwh).label('max_price')
    )
    
    if lokacija_id:
        query = query.filter(Meritev.lokacija_id == lokacija_id)
    
    if datum_od:
        try:
            datum_od_parsed = datetime.strptime(datum_od, '%Y-%m-%d')
            query = query.filter(Meritev.casovni_zig >= datum_od_parsed)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Napačen format datuma od. Uporabite YYYY-MM-DD"
            )
    
    if datum_do:
        try:
            datum_do_parsed = datetime.strptime(datum_do, '%Y-%m-%d')
            query = query.filter(Meritev.casovni_zig <= datum_do_parsed)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Napačen format datuma do. Uporabite YYYY-MM-DD"
            )
    
    result = query.first()
    
    return {
        "count": result.count or 0,
        "total_consumption": float(result.total_consumption or 0),
        "avg_price": float(result.avg_price or 0),
        "min_price": float(result.min_price or 0),
        "max_price": float(result.max_price or 0)
    }

@router.delete("/bulk/location/{lokacija_id}")
async def delete_all_meritve_for_location(
    lokacija_id: int,
    confirm: bool = Query(False, description="Potrditev brisanja"),
    db: Session = Depends(get_db)
):
    """Izbriši vse meritve za lokacijo"""
    
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Za brisanje vseh meritev morate potrditi z ?confirm=true"
        )
    
    lokacija = db.query(Lokacija).filter(Lokacija.id == lokacija_id).first()
    if not lokacija:
        raise HTTPException(status_code=404, detail="Lokacija ne obstaja")
    
    try:
        # Check if any measurements are used in invoices
        from ..models.models import PostavkaRacuna
        used_measurements = db.query(Meritev).join(PostavkaRacuna).filter(
            Meritev.lokacija_id == lokacija_id
        ).first()
        
        if used_measurements:
            raise HTTPException(
                status_code=400,
                detail="Lokacija ima meritve, ki se uporabljajo v računih"
            )
        
        # Delete all measurements
        deleted_count = db.query(Meritev).filter(
            Meritev.lokacija_id == lokacija_id
        ).delete()
        
        db.commit()
        
        app_logger.info(f"Deleted {deleted_count} measurements for location {lokacija_id}")
        
        return {
            "message": f"Izbrisanih {deleted_count} meritev za lokacijo {lokacija.naziv}",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error deleting measurements: {str(e)}")
        raise HTTPException(status_code=500, detail="Napaka pri brisanju meritev")
