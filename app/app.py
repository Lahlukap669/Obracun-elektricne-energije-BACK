from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# Konfiguracija logginga
def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/app_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler()  # Console output
        ]
    )
    return logging.getLogger(__name__)

load_dotenv()
logger = setup_logging()

app = FastAPI(
    title="Electricity Billing System",
    description="Mini-sistem za obračun električne energije",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    # Inicializacija baze podatkov
    from .database import engine, Base
    Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Electricity Billing System API"}

# Importaj route-je
from .routes import router
app.include_router(router)
