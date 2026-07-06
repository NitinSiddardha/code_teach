"""
app/memory/session_memory.py
─────────────────────────────
Persistent session storage backed by SQLAlchemy.
The public functions still accept and return SessionSummary objects, but
storage is now compatible with a hosted Postgres database.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config import SESSIONS_DIR, CONCEPT_WEAK_THRESHOLD
from app.prompts.parsers import SessionSummary


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'code_teach.db'}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sessions = relationship("Session", back_populates="student")


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    topic = Column(String(255), nullable=False)
    level = Column(String(50), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    student = relationship("Student", back_populates="sessions")


class TaskRecord(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    difficulty = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    code = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    passed = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StudentProfileRecord(Base):
    __tablename__ = "student_profiles"
    student_id = Column(Integer, primary_key=True)
    mastery_json = Column(JSON, nullable=True)
    weak_concepts_json = Column(JSON, nullable=True)
    last_active = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def save_session(summary: SessionSummary, topic: str) -> str:
    """Persist a session summary in the database and fall back to a local JSON file if needed."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.name == "default").first()
        if not student:
            student = Student(name="default")
            db.add(student)
            db.flush()

        session = Session(student_id=student.id, topic=topic, level=summary.level)
        db.add(session)
        db.flush()

        task = TaskRecord(session_id=session.id, prompt=summary.next_focus or topic, difficulty=summary.level)
        db.add(task)
        db.flush()

        submission = Submission(
            task_id=task.id,
            code="",
            result=json.dumps(summary.model_dump()),
            passed=1,
            feedback=summary.next_focus,
        )
        db.add(submission)
        db.commit()
    except Exception:
        db.rollback()
        filename = f"{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        filepath = os.path.join(SESSIONS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(summary.model_dump(), fh, indent=2)
        return filepath
    finally:
        db.close()

    return f"session:{topic}"


def load_last_session(topic: str) -> Optional[SessionSummary]:
    """Load the most recent session summary for a topic from the database or local JSON fallback."""
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.topic == topic).order_by(Session.started_at.desc()).first()
        if session:
            latest_submission = db.query(Submission).join(TaskRecord).filter(TaskRecord.session_id == session.id).order_by(Submission.created_at.desc()).first()
            if latest_submission and latest_submission.result:
                payload = json.loads(latest_submission.result)
                return SessionSummary(**payload)
    finally:
        db.close()

    if not os.path.exists(SESSIONS_DIR):
        return None

    topic_slug = topic.replace(" ", "_")
    files = [f for f in os.listdir(SESSIONS_DIR) if f.startswith(topic_slug) and f.endswith(".json")]
    if not files:
        return None

    files.sort()
    with open(os.path.join(SESSIONS_DIR, files[-1]), "r", encoding="utf-8") as fh:
        data = json.load(fh)
        return SessionSummary(**data)


def load_all_sessions(topic: str = None) -> list:
    """Load all session summaries, optionally filtered by topic."""
    if not os.path.exists(SESSIONS_DIR):
        return []

    files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]
    if topic:
        topic_slug = topic.replace(" ", "_")
        files = [f for f in files if f.startswith(topic_slug)]

    summaries = []
    for filename in files:
        with open(os.path.join(SESSIONS_DIR, filename), "r", encoding="utf-8") as fh:
            data = json.load(fh)
            summaries.append(SessionSummary(**data))
    return summaries


def get_weak_concepts_across_sessions(topic: str) -> list:
    """Aggregate weak concepts across stored sessions."""
    sessions = load_all_sessions(topic)
    if not sessions:
        return []

    concept_aggregate = {}
    for session in sessions:
        for concept, score in session.concept_scores.items():
            concept_aggregate.setdefault(concept, []).append(score)

    return [concept for concept, scores in concept_aggregate.items() if sum(scores) / len(scores) <= CONCEPT_WEAK_THRESHOLD]

