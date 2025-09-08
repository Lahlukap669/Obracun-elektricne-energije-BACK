from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/electricity_billing"
    
    # App
    APP_NAME: str = "Sistem za obračun električne energije"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Email
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    
    # File paths
    LOG_DIR: str = "logs"
    INVOICE_DIR: str = "generated_invoices"
    UPLOAD_DIR: str = "uploads"
    
    # Company info
    COMPANY_NAME: str = "BISOL Energija d.o.o."
    COMPANY_ADDRESS: str = "Limbuška cesta 2a, 2341 Limbuš"
    COMPANY_TAX_NUMBER: str = "SI12345678"
    COMPANY_PHONE: str = "+386 1 234 5678"
    COMPANY_EMAIL: str = "info@bisol-energija.si"
    
    class Config:
        env_file = ".env"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.LOG_DIR, exist_ok=True)
os.makedirs(settings.INVOICE_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
