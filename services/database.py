from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/adversarial_sandbox_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Model(Base):
    __tablename__ = "models"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)
    version = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="active")
    model_file_url = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)
    input_schema = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Model(id='{self.id}', name='{self.name}', type='{self.type}')>"

class AttackResult(Base):
    __tablename__ = "attack_results"

    id = Column(String, primary_key=True, index=True)
    model_id = Column(String, index=True, nullable=False)
    attack_method_id = Column(String, nullable=False)
    original_input = Column(String, nullable=False)
    original_prediction = Column(String, nullable=False)
    original_confidence = Column(Float, nullable=False)
    adversarial_example = Column(String, nullable=False)
    adversarial_prediction = Column(String, nullable=False)
    adversarial_confidence = Column(Float, nullable=False)
    attack_success = Column(Boolean, nullable=False)
    perturbation_details = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    status = Column(String, default="completed")
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<AttackResult(id='{self.id}', model_id='{self.model_id}', status='{self.status}')>"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
