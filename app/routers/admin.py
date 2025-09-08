from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime

from ..core.database import get_db
from ..core.logging import app_logger
from ..models.models import Stranka, Lokacija, Meritev, Racun
from ..schemas.schemas import (
    CSVImportRequest,
    CSVImportResponse,
    DashboardStats,
    LokacijaStatistics
)
from ..services.csv_service import CSVService
from ..services.calculation_service import CalculationService

router = APIRouter(prefix="/admin", tags=["Administracija"])

@router.post("/import-csv", response_model=CSVImportResponse)
async def import_csv(
    background_tasks: BackgroundTasks,
    lokacija_id: int = Form(...),
    replace_existing: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uvozi CSV datoteko z meritvami"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Samo CSV datoteke so dovoljene")
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse CSV
        df = CSVService.parse_csv_content(content)
        
        # Import to database
        result = CSVService.import_csv_to_database(
            db, df, lokacija_id, replace_existing
        )
        
        app_logger.info(f"CSV import completed for location {lokacija_id}: {result.imported_count} records")
        
        return result
        
    except Exception as e:
        app_logger.error(f"Error importing CSV: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Pridobi statistike za nadzorno ploščo"""
    
    try:
        # Count totals
        skupno_strank = db.query(Stranka).count()
        skupno_lokacij = db.query(Lokacija).count()
        skupno_meritev = db.query(Meritev).count()
        skupno_racunov = db.query(Racun).count()
        
        # Get recent invoices
        zadnji_racuni = db.query(Racun).order_by(
            Racun.datum_izdaje.desc()
        ).limit(5).all()
        
        # Get monthly statistics for all locations
        current_month_start = date.today().replace(day=1)
        if current_month_start.month == 1:
            previous_month_start = current_month_start.replace(year=current_month_start.year-1, month=12)
        else:
            previous_month_start = current_month_start.replace(month=current_month_start.month-1)
        
        lokacije = db.query(Lokacija).all()
        mesecna_statistika = []
        
        for lokacija in lokacije:
            try:
                stats = CalculationService.calculate_statistics(
                    db, lokacija.id, previous_month_start, current_month_start
                )
                
                if stats['st_meritev'] > 0:  # Only include locations with data
                    lokacija_stats = LokacijaStatistics(
                        lokacija_id=lokacija.id,
                        naziv=lokacija.naziv,
                        skupna_poraba=stats['skupna_poraba'],
                        skupni_strosek=stats['skupni_strosek'],
                        povprecna_cena=stats['povprecna_cena'],
                        st_meritev=stats['st_meritev'],
                        datum_od=previous_month_start,
                        datum_do=current_month_start
                    )
                    mesecna_statistika.append(lokacija_stats)
            except Exception as e:
                app_logger.warning(f"Error calculating stats for location {lokacija.id}: {str(e)}")
                continue
        
        dashboard_stats = DashboardStats(
            skupno_strank=skupno_strank,
            skupno_lokacij=skupno_lokacij,
            skupno_meritev=skupno_meritev,
            skupno_racunov=skupno_racunov,
            zadnji_racuni=zadnji_racuni,
            mesecna_statistika=mesecna_statistika
        )
        
        return dashboard_stats
        
    except Exception as e:
        app_logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Napaka pri pridobivanju statistik")

@router.get("/statistics/{lokacija_id}")
async def get_location_statistics(
    lokacija_id: int,
    datum_od: date,
    datum_do: date,
    db: Session = Depends(get_db)
):
    """Pridobi statistike za lokacijo"""
    
    lokacija = db.query(Lokacija).filter(Lokacija.id == lokacija_id).first()
    if not lokacija:
        raise HTTPException(status_code=404, detail="Lokacija ne obstaja")
    
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

@router.post("/cleanup-old-data")
async def cleanup_old_data(
    days_old: int = 365,
    dry_run: bool = True,
    db: Session = Depends(get_db)
):
    """Počisti stare podatke"""
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    # Count records to be deleted
    old_meritve_count = db.query(Meritev).filter(
        Meritev.created_at < cutoff_date
    ).count()
    
    old_racuni_count = db.query(Racun).filter(
        Racun.datum_izdaje < cutoff_date
    ).count()
    
    if dry_run:
        return {
            "dry_run": True,
            "cutoff_date": cutoff_date,
            "meritve_to_delete": old_meritve_count,
            "racuni_to_delete": old_racuni_count
        }
    
    # Actually delete the records
    try:
        deleted_meritve = db.query(Meritev).filter(
            Meritev.created_at < cutoff_date
        ).delete()
        
        deleted_racuni = db.query(Racun).filter(
            Racun.datum_izdaje < cutoff_date
        ).delete()
        
        db.commit()
        
        app_logger.info(f"Cleanup completed: deleted {deleted_meritve} measurements and {deleted_racuni} invoices")
        
        return {
            "dry_run": False,
            "cutoff_date": cutoff_date,
            "deleted_meritve": deleted_meritve,
            "deleted_racuni": deleted_racuni
        }
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail="Napaka pri čiščenju podatkov")
