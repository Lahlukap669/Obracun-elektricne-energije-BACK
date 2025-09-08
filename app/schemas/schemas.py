from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

# Base schemas
class StrankaBase(BaseModel):
    ime: str
    priimek: str
    naslov: Optional[str] = None
    email: Optional[EmailStr] = None
    telefon: Optional[str] = None

class StrankaCreate(StrankaBase):
    pass

class StrankaUpdate(BaseModel):
    ime: Optional[str] = None
    priimek: Optional[str] = None
    naslov: Optional[str] = None
    email: Optional[EmailStr] = None
    telefon: Optional[str] = None

class Stranka(StrankaBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Lokacija schemas
class LokacijaBase(BaseModel):
    stranka_id: int
    naziv: str
    naslov: Optional[str] = None
    merilna_stevilka: Optional[str] = None

class LokacijaCreate(LokacijaBase):
    pass

class LokacijaUpdate(BaseModel):
    naziv: Optional[str] = None
    naslov: Optional[str] = None
    merilna_stevilka: Optional[str] = None

class Lokacija(LokacijaBase):
    id: int
    created_at: datetime
    stranka: Optional[Stranka] = None
    
    class Config:
        from_attributes = True

# Meritev schemas
class MeritevBase(BaseModel):
    lokacija_id: int
    casovni_zig: datetime
    poraba_kwh: Decimal
    dinamicna_cena_eur_kwh: Decimal

class MeritevCreate(MeritevBase):
    pass

class MeritevBulkCreate(BaseModel):
    meritve: List[MeritevCreate]

class Meritev(MeritevBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Racun schemas
class RacunBase(BaseModel):
    lokacija_id: int
    datum_od: date
    datum_do: date
    
class RacunCreate(RacunBase):
    pass

class RacunGenerateRequest(BaseModel):
    lokacija_id: int
    datum_od: date
    datum_do: date
    send_email: bool = False

class Racun(RacunBase):
    id: int
    stevilka_racuna: str
    skupni_znesek: Decimal
    status: str
    datum_izdaje: datetime
    pdf_pot: Optional[str] = None
    lokacija: Optional[Lokacija] = None
    
    class Config:
        from_attributes = True

class RacunDetail(Racun):
    postavke: List['PostavkaRacuna'] = []

# PostavkaRacuna schemas
class PostavkaRacunaBase(BaseModel):
    racun_id: int
    meritev_id: int
    poraba_kwh: Decimal
    cena_eur_kwh: Decimal
    znesek: Decimal

class PostavkaRacuna(PostavkaRacunaBase):
    id: int
    meritev: Optional[Meritev] = None
    
    class Config:
        from_attributes = True

# CSV Import schemas
class CSVImportRequest(BaseModel):
    lokacija_id: int
    replace_existing: bool = False

class CSVImportResponse(BaseModel):
    success: bool
    message: str
    imported_count: int
    errors: List[str] = []

# Email schemas
class EmailRequest(BaseModel):
    racun_id: int
    recipient_email: Optional[EmailStr] = None
    subject: Optional[str] = None
    message: Optional[str] = None

# Statistics schemas
class LokacijaStatistics(BaseModel):
    lokacija_id: int
    naziv: str
    skupna_poraba: Decimal
    skupni_strosek: Decimal
    povprecna_cena: Decimal
    st_meritev: int
    datum_od: date
    datum_do: date

class DashboardStats(BaseModel):
    skupno_strank: int
    skupno_lokacij: int
    skupno_meritev: int
    skupno_racunov: int
    zadnji_racuni: List[Racun]
    mesecna_statistika: List[LokacijaStatistics]

# Update forward references
RacunDetail.model_rebuild()
