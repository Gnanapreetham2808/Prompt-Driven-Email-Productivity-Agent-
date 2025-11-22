from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    prompt_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Email(Base):
    __tablename__ = "emails"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    sender = Column(String, nullable=False)
    subject = Column(String)
    body = Column(Text)
    received_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    
    # Relationships
    analysis = relationship("EmailAnalysis", back_populates="email", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="email", cascade="all, delete-orphan")

class EmailAnalysis(Base):
    __tablename__ = "email_analysis"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email_id = Column(String, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    category = Column(String)
    extracted_tasks = Column(JSON)
    analysis_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    email = relationship("Email", back_populates="analysis")

class Draft(Base):
    __tablename__ = "drafts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email_id = Column(String, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    draft_subject = Column(String)
    draft_body = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    email = relationship("Email", back_populates="drafts")
