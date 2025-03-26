from app.database import create_tables
from app import models  # This import is necessary to register the models

if __name__ == "__main__":
    print("Creating database tables...")
    create_tables()
    print("Database tables created successfully!") 