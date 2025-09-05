from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(Text)
    email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    energy_data = relationship("EnergyData", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")

class EnergyData(Base):
    __tablename__ = "energy_data"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    timestamp = Column(DateTime, nullable=False)
    consumption_kwh = Column(Float, nullable=False)
    dynamic_price_eur_kwh = Column(Float, nullable=False)
    cost_eur = Column(Float)  # Izračunano
    
    # Relationships
    customer = relationship("Customer", back_populates="energy_data")

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    invoice_number = Column(String, unique=True, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_consumption_kwh = Column(Float, nullable=False)
    total_cost_eur = Column(Float, nullable=False)
    pdf_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="invoices")
