from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from ..core.database import get_db
from ..core.logging import app_logger
from ..models.models import Racun, Lokacija, Stranka
from ..schemas.schemas import (
    Racun as RacunSchema,
    RacunDetail,
    RacunCreate,
    RacunGenerateRequest,
    EmailRequest
)
from ..services.invoice_service import InvoiceService
from ..services.email_service import EmailService

router = APIRouter(prefix="/racuni", tags=["Računi"])

@router.get("/", response_model=List[RacunSchema])
async def get_racuni(
    skip: int = 0,
    limit: int = 100,
    lokacija_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Pridobi seznam računov"""
    query = db.query(Racun)
    
    if lokacija_id:
        query = query.filter(Racun.lokacija_id == lokacija_id)
    
    if status:
        query = query.filter(Racun.status == status)
    
    racuni = query.offset(skip).limit(limit).all()
    
    app_logger.info(f"Retrieved {len(racuni)} invoices")
    return racuni

@router.get("/{racun_id}", response_model=RacunDetail)
async def get_racun(racun_id: int, db: Session = Depends(get_db)):
    """Pridobi podrobnosti računa"""
    racun = db.query(Racun).filter(Racun.id == racun_id).first()
    if not racun:
        raise HTTPException(status_code=404, detail="Račun ne obstaja")
    
    return racun

@router.post("/generate", response_model=RacunSchema)
async def generate_racun(
    request: RacunGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generiraj nov račun"""
    
    # Check if location exists
    lokacija = db.query(Lokacija).filter(Lokacija.id == request.lokacija_id).first()
    if not lokacija:
        raise HTTPException(status_code=404, detail="Lokacija ne obstaja")
    
    try:
        # Create invoice
        invoice_service = InvoiceService()
        racun = invoice_service.create_invoice(
            db, request.lokacija_id, request.datum_od, request.datum_do
        )
        
        # Generate PDF in background
        background_tasks.add_task(
            generate_pdf_background, 
            db, 
            racun.id, 
            request.send_email
        )
        
        app_logger.info(f"Generated invoice {racun.stevilka_racuna}")
        return racun
        
    except Exception as e:
        app_logger.error(f"Error generating invoice: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{racun_id}/pdf")
async def get_racun_pdf(racun_id: int, db: Session = Depends(get_db)):
    """Prenesi PDF računa"""
    racun = db.query(Racun).filter(Racun.id == racun_id).first()
    if not racun:
        raise HTTPException(status_code=404, detail="Račun ne obstaja")
    
    if not racun.pdf_pot:
        # Generate PDF if it doesn't exist
        invoice_service = InvoiceService()
        pdf_path = invoice_service.generate_pdf(db, racun_id)
    else:
        pdf_path = racun.pdf_pot
    
    return FileResponse(
        pdf_path,
        media_type='application/pdf',
        filename=f"racun_{racun.stevilka_racuna}.pdf"
    )

@router.post("/{racun_id}/send-email")
async def send_racun_email(
    racun_id: int,
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Pošlji račun po e-pošti"""
    racun = db.query(Racun).filter(Racun.id == racun_id).first()
    if not racun:
        raise HTTPException(status_code=404, detail="Račun ne obstaja")
    
    # Send email in background
    background_tasks.add_task(
        send_email_background,
        db,
        racun_id,
        request.recipient_email,
        request.subject,
        request.message
    )
    
    return {"message": "E-mail se pošilja v ozadju"}

@router.delete("/{racun_id}")
async def delete_racun(racun_id: int, db: Session = Depends(get_db)):
    """Izbriši račun"""
    racun = db.query(Racun).filter(Racun.id == racun_id).first()
    if not racun:
        raise HTTPException(status_code=404, detail="Račun ne obstaja")
    
    db.delete(racun)
    db.commit()
    
    app_logger.info(f"Deleted invoice {racun.stevilka_racuna}")
    return {"message": "Račun je bil izbrisan"}

# Background tasks
async def generate_pdf_background(db: Session, racun_id: int, send_email: bool):
    """Generate PDF in background"""
    try:
        invoice_service = InvoiceService()
        pdf_path = invoice_service.generate_pdf(db, racun_id)
        
        if send_email:
            await EmailService.send_invoice_email(db, racun_id)
            
    except Exception as e:
        app_logger.error(f"Error in background PDF generation: {str(e)}")

async def send_email_background(
    db: Session, 
    racun_id: int, 
    recipient_email: Optional[str],
    subject: Optional[str],
    message: Optional[str]
):
    """Send email in background"""
    try:
        await EmailService.send_invoice_email(
            db, racun_id, recipient_email, subject, message
        )
    except Exception as e:
        app_logger.error(f"Error sending email: {str(e)}")
