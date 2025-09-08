import os
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader
import weasyprint
from ..models.models import Racun, PostavkaRacuna, Lokacija, Stranka
from ..services.calculation_service import CalculationService
from ..core.config import settings
from ..core.logging import app_logger

class InvoiceService:
    
    def __init__(self):
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
    
    def generate_invoice_number(self, db: Session) -> str:
        """Generate unique invoice number"""
        current_year = datetime.now().year
        
        # Count invoices for current year
        count = db.query(Racun).filter(
            Racun.stevilka_racuna.like(f"{current_year}-%")
        ).count()
        
        invoice_number = f"{current_year}-{count + 1:06d}"
        return invoice_number
    
    def create_invoice(
        self,
        db: Session,
        lokacija_id: int,
        datum_od: date,
        datum_do: date
    ) -> Racun:
        """Create a new invoice"""
        
        try:
            app_logger.info(f"Creating invoice for location {lokacija_id} from {datum_od} to {datum_do}")
            
            # Calculate invoice amount and get line items
            total_amount, line_items = CalculationService.calculate_invoice_amount(
                db, lokacija_id, datum_od, datum_do
            )
            
            if not line_items:
                raise ValueError("Ni podatkov za izbrano obdobje")
            
            # Generate invoice number
            invoice_number = self.generate_invoice_number(db)
            
            # Create invoice record
            racun = Racun(
                lokacija_id=lokacija_id,
                stevilka_racuna=invoice_number,
                datum_od=datum_od,
                datum_do=datum_do,
                skupni_znesek=total_amount,
                status="USTVARJEN"
            )
            
            db.add(racun)
            db.flush()  # Get the ID
            
            # Create invoice line items
            postavke = []
            for item in line_items:
                postavka = PostavkaRacuna(
                    racun_id=racun.id,
                    meritev_id=item['meritev_id'],
                    poraba_kwh=item['poraba_kwh'],
                    cena_eur_kwh=item['cena_eur_kwh'],
                    znesek=item['znesek']
                )
                postavke.append(postavka)
            
            db.add_all(postavke)
            db.commit()
            
            app_logger.info(f"Created invoice {invoice_number} with total amount {total_amount} EUR")
            
            # Refresh to get relationships
            db.refresh(racun)
            return racun
            
        except Exception as e:
            db.rollback()
            app_logger.error(f"Error creating invoice: {str(e)}")
            raise e
    
    def generate_pdf(self, db: Session, racun_id: int) -> str:
        """Generate PDF for invoice"""
        
        try:
            # Get invoice with all related data
            racun = db.query(Racun).filter(Racun.id == racun_id).first()
            if not racun:
                raise ValueError("Račun ne obstaja")
            
            # Get location and customer data
            lokacija = db.query(Lokacija).filter(Lokacija.id == racun.lokacija_id).first()
            stranka = db.query(Stranka).filter(Stranka.id == lokacija.stranka_id).first()
            
            # Get invoice line items
            postavke = db.query(PostavkaRacuna).filter(
                PostavkaRacuna.racun_id == racun_id
            ).all()
            
            # Calculate statistics
            stats = CalculationService.calculate_statistics(
                db, racun.lokacija_id, racun.datum_od, racun.datum_do
            )
            
            # Prepare template data
            template_data = {
                'racun': racun,
                'lokacija': lokacija,
                'stranka': stranka,
                'postavke': postavke,
                'stats': stats,
                'company': {
                    'name': settings.COMPANY_NAME,
                    'address': settings.COMPANY_ADDRESS,
                    'tax_number': settings.COMPANY_TAX_NUMBER,
                    'phone': settings.COMPANY_PHONE,
                    'email': settings.COMPANY_EMAIL
                },
                'generated_at': datetime.now()
            }
            
            # Render HTML template
            template = self.jinja_env.get_template('invoice_template.html')
            html_content = template.render(**template_data)
            
            # Generate PDF
            pdf_filename = f"racun_{racun.stevilka_racuna}.pdf"
            pdf_path = os.path.join(settings.INVOICE_DIR, pdf_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            # Generate PDF using WeasyPrint
            weasyprint.HTML(string=html_content).write_pdf(pdf_path)
            
            # Update invoice with PDF path
            racun.pdf_pot = pdf_path
            racun.status = "GENERIRAN"
            db.commit()
            
            app_logger.info(f"Generated PDF for invoice {racun.stevilka_racuna}: {pdf_path}")
            
            return pdf_path
            
        except Exception as e:
            app_logger.error(f"Error generating PDF: {str(e)}")
            raise e
