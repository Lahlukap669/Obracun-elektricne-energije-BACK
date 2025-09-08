import pandas as pd
import io
from typing import List, Tuple
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from ..models.models import Meritev, Lokacija
from ..schemas.schemas import CSVImportResponse
from ..core.logging import app_logger
from fastapi import HTTPException

class CSVService:
    
    @staticmethod
    def parse_csv_content(content: bytes) -> pd.DataFrame:
        """Parse CSV content and return DataFrame"""
        try:
            # Try different encodings
            for encoding in ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252']:
                try:
                    csv_string = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise HTTPException(status_code=400, detail="Nepodprta kodna tabela datoteke")
            
            # Parse CSV
            df = pd.read_csv(
                io.StringIO(csv_string),
                sep=';',
                decimal=',',
                parse_dates=['Časovna Značka (CEST/CET)']
            )
            
            # Rename columns for easier handling
            df.columns = ['casovni_zig', 'poraba_kwh', 'dinamicna_cena_eur_kwh']
            
            app_logger.info(f"Successfully parsed CSV with {len(df)} rows")
            return df
            
        except Exception as e:
            app_logger.error(f"Error parsing CSV: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Napaka pri branju CSV datoteke: {str(e)}")
    
    @staticmethod
    def validate_csv_data(df: pd.DataFrame) -> List[str]:
        """Validate CSV data and return list of errors"""
        errors = []
        
        # Check required columns
        required_columns = ['casovni_zig', 'poraba_kwh', 'dinamicna_cena_eur_kwh']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Manjkajo stolpci: {', '.join(missing_columns)}")
            return errors
        
        # Check for empty data
        if df.empty:
            errors.append("CSV datoteka je prazna")
            return errors
        
        # Check data types and values
        for idx, row in df.iterrows():
            row_errors = []
            
            # Check timestamp
            if pd.isna(row['casovni_zig']):
                row_errors.append("manjka časovna značka")
            
            # Check poraba_kwh
            try:
                poraba = float(str(row['poraba_kwh']).replace(',', '.'))
                if poraba < 0:
                    row_errors.append("poraba ne more biti negativna")
            except (ValueError, TypeError):
                row_errors.append("neveljavna vrednost porabe")
            
            # Check dinamicna_cena_eur_kwh
            try:
                cena = float(str(row['dinamicna_cena_eur_kwh']).replace(',', '.'))
                if cena <= 0:
                    row_errors.append("cena mora biti pozitivna")
            except (ValueError, TypeError):
                row_errors.append("neveljavna vrednost cene")
            
            if row_errors:
                errors.append(f"Vrstica {idx + 2}: {', '.join(row_errors)}")
        
        return errors
    
    @staticmethod
    def import_csv_to_database(
        db: Session, 
        df: pd.DataFrame, 
        lokacija_id: int, 
        replace_existing: bool = False
    ) -> CSVImportResponse:
        """Import CSV data to database"""
        
        try:
            # Check if location exists
            lokacija = db.query(Lokacija).filter(Lokacija.id == lokacija_id).first()
            if not lokacija:
                return CSVImportResponse(
                    success=False,
                    message="Lokacija ne obstaja",
                    imported_count=0,
                    errors=["Lokacija ne obstaja"]
                )
            
            # Validate data
            errors = CSVService.validate_csv_data(df)
            if errors:
                return CSVImportResponse(
                    success=False,
                    message="Napake v podatkih",
                    imported_count=0,
                    errors=errors[:10]  # Limit errors
                )
            
            # Delete existing data if replace_existing is True
            if replace_existing:
                deleted_count = db.query(Meritev).filter(
                    Meritev.lokacija_id == lokacija_id
                ).delete()
                app_logger.info(f"Deleted {deleted_count} existing measurements for location {lokacija_id}")
            
            # Prepare data for bulk insert
            meritve_data = []
            imported_count = 0
            
            for _, row in df.iterrows():
                try:
                    # Convert values
                    poraba = Decimal(str(row['poraba_kwh']).replace(',', '.'))
                    cena = Decimal(str(row['dinamicna_cena_eur_kwh']).replace(',', '.'))
                    
                    meritev_data = {
                        'lokacija_id': lokacija_id,
                        'casovni_zig': row['casovni_zig'],
                        'poraba_kwh': poraba,
                        'dinamicna_cena_eur_kwh': cena
                    }
                    
                    meritve_data.append(meritev_data)
                    imported_count += 1
                    
                except Exception as e:
                    app_logger.error(f"Error processing row: {str(e)}")
                    continue
            
            # Bulk insert
            if meritve_data:
                db.bulk_insert_mappings(Meritev, meritve_data)
                db.commit()
                
                app_logger.info(f"Successfully imported {imported_count} measurements for location {lokacija_id}")
                
                return CSVImportResponse(
                    success=True,
                    message=f"Uspešno uvoženih {imported_count} meritev",
                    imported_count=imported_count,
                    errors=[]
                )
            else:
                return CSVImportResponse(
                    success=False,
                    message="Ni veljavnih podatkov za uvoz",
                    imported_count=0,
                    errors=["Ni veljavnih podatkov za uvoz"]
                )
                
        except Exception as e:
            db.rollback()
            app_logger.error(f"Error importing CSV data: {str(e)}")
            return CSVImportResponse(
                success=False,
                message=f"Napaka pri uvozu: {str(e)}",
                imported_count=0,
                errors=[str(e)]
            )
