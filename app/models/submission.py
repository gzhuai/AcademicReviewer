from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_name = Column(String(128), nullable=False, default="")
    competition = Column(String(128), nullable=False)
    competition_type = Column(String(64), nullable=False, default="")
    filename = Column(String(256), nullable=False)
    word_count = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="pending")
    submitted_at = Column(DateTime, default=datetime.utcnow)

    reviews = relationship("Review", back_populates="submission", cascade="all, delete-orphan")
    document_text = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Submission(id={self.id}, student={self.student_name}, competition={self.competition})>"


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    model_provider = Column(String(32), nullable=False)
    total_score = Column(Float, nullable=True)
    score_rubric = Column(Float, nullable=True)
    score_structure = Column(Float, nullable=True)
    score_argument = Column(Float, nullable=True)
    score_language = Column(Float, nullable=True)
    score_integrity = Column(Float, nullable=True)
    feedback_json = Column(Text, nullable=True)
    token_usage = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0)
    duration_seconds = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="reviews")

    def __repr__(self):
        return f"<Review(id={self.id}, submission_id={self.submission_id}, provider={self.model_provider})>"


class CalibrationRecord(Base):
    __tablename__ = "calibrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_name = Column(String(128), nullable=False, default="")
    competition = Column(String(128), nullable=False)
    competition_type = Column(String(64), nullable=False, default="")
    n_winners = Column(Integer, nullable=False, default=0)
    n_losers = Column(Integer, nullable=False, default=0)
    n_external = Column(Integer, nullable=False, default=0)
    report_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CalibrationRecord(id={self.id}, instance={self.instance_name}, competition={self.competition})>"
