from decimal import Decimal
from typing import List, Tuple
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models.models import Meritev, PostavkaRacuna
from ..core.logging import app_logger

class CalculationService:
    
    @staticmethod
    def calculate_invoice_amount(
        db: Session, 
        lokacija_id: int, 
        datum_od: date, 
        datum_do: date
    ) -> Tuple[Decimal, List[dict]]:
        """
        Calculate invoice amount and return total cost and line items
        """
        try:
            # Get measurements for the period
            meritve = db.query(Meritev).filter(
                and_(
                    Meritev.lokacija_id == lokacija_id,
                    Meritev.casovni_zig >= datum_od,
                    Meritev.casovni_zig <= datum_do
                )
            ).order_by(Meritev.casovni_zig).all()
            
            if not meritve:
                app_logger.warning(f"No measurements found for location {lokacija_id} between {datum_od} and {datum_do}")
                return Decimal('0.0'), []
            
            line_items = []
            total_amount = Decimal('0.0')
            
            for meritev in meritve:
                # Calculate cost for this measurement
                znesek = meritev.poraba_kwh * meritev.dinamicna_cena_eur_kwh
                znesek = znesek.quantize(Decimal('0.01'))  # Round to 2 decimal places
                
                line_item = {
                    'meritev_id': meritev.id,
                    'casovni_zig': meritev.casovni_zig,
                    'poraba_kwh': meritev.poraba_kwh,
                    'cena_eur_kwh': meritev.dinamicna_cena_eur_kwh,
                    'znesek': znesek
                }
                
                line_items.append(line_item)
                total_amount += znesek
            
            total_amount = total_amount.quantize(Decimal('0.01'))
            
            app_logger.info(f"Calculated invoice for location {lokacija_id}: {total_amount} EUR ({len(line_items)} items)")
            
            return total_amount, line_items
            
        except Exception as e:
            app_logger.error(f"Error calculating invoice amount: {str(e)}")
            raise e
    
    @staticmethod
    def calculate_statistics(
        db: Session,
        lokacija_id: int,
        datum_od: date,
        datum_do: date
    ) -> dict:
        """Calculate statistics for a location and period"""
        
        try:
            meritve = db.query(Meritev).filter(
                and_(
                    Meritev.lokacija_id == lokacija_id,
                    Meritev.casovni_zig >= datum_od,
                    Meritev.casovni_zig <= datum_do
                )
            ).all()
            
            if not meritve:
                return {
                    'skupna_poraba': Decimal('0.0'),
                    'skupni_strosek': Decimal('0.0'),
                    'povprecna_cena': Decimal('0.0'),
                    'minimalna_cena': Decimal('0.0'),
                    'maksimalna_cena': Decimal('0.0'),
                    'st_meritev': 0
                }
            
            skupna_poraba = sum(m.poraba_kwh for m in meritve)
            skupni_strosek = sum(m.poraba_kwh * m.dinamicna_cena_eur_kwh for m in meritve)
            cene = [m.dinamicna_cena_eur_kwh for m in meritve]
            
            povprecna_cena = sum(cene) / len(cene) if cene else Decimal('0.0')
            
            stats = {
                'skupna_poraba': skupna_poraba.quantize(Decimal('0.0001')),
                'skupni_strosek': skupni_strosek.quantize(Decimal('0.01')),
                'povprecna_cena': povprecna_cena.quantize(Decimal('0.00001')),
                'minimalna_cena': min(cene).quantize(Decimal('0.00001')) if cene else Decimal('0.0'),
                'maksimalna_cena': max(cene).quantize(Decimal('0.00001')) if cene else Decimal('0.0'),
                'st_meritev': len(meritve)
            }
            
            app_logger.info(f"Calculated statistics for location {lokacija_id}: {stats}")
            return stats
            
        except Exception as e:
            app_logger.error(f"Error calculating statistics: {str(e)}")
            raise e
