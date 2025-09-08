from sqlalchemy import Column, Integer, String, Text, DECIMAL, TIMESTAMP, DATE, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base

class Stranka(Base):
    __tablename__ = "stranke"
    
    id = Column(Integer, primary_key=True, index=True)
    ime = Column(String(100), nullable=False)
    priimek = Column(String(100), nullable=False)
    naslov = Column(Text)
    email = Column(String(100))
    telefon = Column(String(20))
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    lokacije = relationship("Lokacija", back_populates="stranka")

class Lokacija(Base):
    __tablename__ = "lokacije"
    
    id = Column(Integer, primary_key=True, index=True)
    stranka_id = Column(Integer, ForeignKey("stranke.id"), nullable=False)
    naziv = Column(String(100), nullable=False)
    naslov = Column(Text)
    merilna_stevilka = Column(String(50), unique=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    stranka = relationship("Stranka", back_populates="lokacije")
    meritve = relationship("Meritev", back_populates="lokacija")
    racuni = relationship("Racun", back_populates="lokacija")

class Meritev(Base):
    __tablename__ = "meritve"
    
    id = Column(Integer, primary_key=True, index=True)
    lokacija_id = Column(Integer, ForeignKey("lokacije.id"), nullable=False)
    casovni_zig = Column(TIMESTAMP, nullable=False)
    poraba_kwh = Column(DECIMAL(10, 4), nullable=False)
    dinamicna_cena_eur_kwh = Column(DECIMAL(8, 5), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    lokacija = relationship("Lokacija", back_populates="meritve")
    postavke_racuna = relationship("PostavkaRacuna", back_populates="meritev")
    
    __table_args__ = (
        {"extend_existing": True}
    )

class Racun(Base):
    __tablename__ = "racuni"
    
    id = Column(Integer, primary_key=True, index=True)
    lokacija_id = Column(Integer, ForeignKey("lokacije.id"), nullable=False)
    stevilka_racuna = Column(String(50), unique=True, nullable=False)
    datum_od = Column(DATE, nullable=False)
    datum_do = Column(DATE, nullable=False)
    skupni_znesek = Column(DECIMAL(10, 2), nullable=False)
    status = Column(String(20), default="USTVARJEN")
    datum_izdaje = Column(TIMESTAMP, server_default=func.now())
    pdf_pot = Column(Text)
    
    # Relationships
    lokacija = relationship("Lokacija", back_populates="racuni")
    postavke = relationship("PostavkaRacuna", back_populates="racun")

class PostavkaRacuna(Base):
    __tablename__ = "postavke_racuna"
    
    id = Column(Integer, primary_key=True, index=True)
    racun_id = Column(Integer, ForeignKey("racuni.id"), nullable=False)
    meritev_id = Column(Integer, ForeignKey("meritve.id"), nullable=False)
    poraba_kwh = Column(DECIMAL(10, 4), nullable=False)
    cena_eur_kwh = Column(DECIMAL(8, 5), nullable=False)
    znesek = Column(DECIMAL(10, 2), nullable=False)
    
    # Relationships
    racun = relationship("Racun", back_populates="postavke")
    meritev = relationship("Meritev", back_populates="postavke_racuna")
