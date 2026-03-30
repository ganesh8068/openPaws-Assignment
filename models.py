import os
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

class Facility(Base):
    __tablename__ = 'facilities'
    id = Column(Integer, primary_key=True)
    customer_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    state = Column(String)
    zip_code = Column(String)
    license_type = Column(String)
    
    inspections = relationship("Inspection", back_populates="facility")

class Inspection(Base):
    __tablename__ = 'inspections'
    id = Column(Integer, primary_key=True)
    facility_id = Column(Integer, ForeignKey('facilities.id'))
    report_id = Column(String, unique=True, nullable=False)
    date = Column(Date)
    
    facility = relationship("Facility", back_populates="inspections")
    violations = relationship("Violation", back_populates="inspection")
    species_affected = relationship("Species", back_populates="inspection")

class Violation(Base):
    __tablename__ = 'violations'
    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey('inspections.id'))
    violation_type = Column(String)  # e.g., "3.1(a)"
    severity = Column(String)        # e.g., "Critical", "Non-Critical", "Direct"
    notes = Column(Text)
    enforcement_action = Column(String) # usually in notes or separate block
    
    inspection = relationship("Inspection", back_populates="violations")

class Species(Base):
    __tablename__ = 'species'
    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey('inspections.id'))
    count = Column(Integer)
    scientific_name = Column(String)
    common_name = Column(String)
    
    inspection = relationship("Inspection", back_populates="species_affected")


DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'aphis.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    engine = create_engine(f'sqlite:///{DB_PATH}')
    Base.metadata.create_all(engine)
    return engine

def get_session():
    engine = create_engine(f'sqlite:///{DB_PATH}')
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == '__main__':
    init_db()
    print(f"Database initialized at {DB_PATH}")
