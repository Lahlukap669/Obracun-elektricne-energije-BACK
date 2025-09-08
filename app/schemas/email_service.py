import aiosmtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional
from sqlalchemy.orm import Session
from ..models.models import Racun, Lokacija, Stranka
from ..core.config import settings
from ..core.logging import app_logger

class EmailService:
    
    @staticmethod
    async def send_invoice_email(
        db: Session,
        racun_id: int,
        recipient_email: Optional[str] = None,
        subject: Optional[str] = None,
        message: Optional[str] = None
    ) -> bool:
        """Send invoice via email"""
        
        try:
            # Get invoice data
            racun = db.query(Racun).filter(Racun.id == racun_id).first()
            if not racun:
                raise ValueError("Račun ne obstaja")
            
            if not racun.pdf_pot or not os.path.exists(racun.pdf_pot):
                raise ValueError("PDF računa ne obstaja")
            
            # Get customer data
            lokacija = db.query(Lokacija).filter(Lokacija.id == racun.lokacija_id).first()
            stranka = db.query(Stranka).filter(Stranka.id == lokacija.stranka_id).first()
            
            # Determine recipient email
            to_email = recipient_email or stranka.email
            if not to_email:
                raise ValueError("E-mail naslov prejemnika ni naveden")
            
            # Email configuration
            if not all([settings.SMTP_USERNAME, settings.SMTP_PASSWORD, settings.EMAIL_FROM]):
                raise ValueError("E-mail ni konfiguriran")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = subject or f"Račun za električno energijo - {racun.stevilka_racuna}"
            
            # Email body
            if not message:
                message = f"""
Spoštovani/a {stranka.ime} {stranka.priimek},

v prilogi vam pošiljamo račun za dobavljeno električno energijo.

Podatki o računu:
- Številka računa: {racun.stevilka_racuna}
- Obdobje: {racun.datum_od} - {racun.datum_do}
- Znesek: {racun.skupni_znesek} EUR
- Lokacija: {lokacija.naziv}

Prosimo za pravočasno plačilo računa.

Lep pozdrav,
{settings.COMPANY_NAME}
                """.strip()
            
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            # Attach PDF
            with open(racun.pdf_pot, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= "racun_{racun.stevilka_racuna}.pdf"'
                )
                msg.attach(part)
            
            # Send email
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_SERVER,
                port=settings.SMTP_PORT,
                start_tls=True,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
            )
            
            # Update invoice status
            racun.status = "POSLAN"
            db.commit()
            
            app_logger.info(f"Sent invoice {racun.stevilka_racuna} to {to_email}")
            
            return True
            
        except Exception as e:
            app_logger.error(f"Error sending email: {str(e)}")
            raise e
