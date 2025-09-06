import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT now()"))
        current_time = result.scalar()
        print(f"Successfully connected to the database. Current time: {current_time}")
except SQLAlchemyError as e:
    print(f"Error connecting to the database: {e}")