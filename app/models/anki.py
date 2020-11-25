import datetime

from app import db
from app.models.base import BaseModel


class ApkgGeneration(BaseModel):
    __tablename__ = "apkg_generations"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # always UTC
    at: datetime.datetime = db.Column(db.DateTime, nullable=False)
    b2_file_id: str = db.Column(db.Text, nullable=False)
    b2_file_name: str = db.Column(db.Text, nullable=False)
    # in bytes
    file_size: int = db.Column(db.BigInteger, nullable=False)
    # the number of notes in this package, used to notify users when their newly generated deck has new notes
    notes: int = db.Column(db.Integer, nullable=False)


class AnkiReviewLog(BaseModel):
    __tablename__ = "anki_review_logs"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    zdone_id: str = db.Column(db.Text, nullable=False)
    template_name: str = db.Column(db.Text, nullable=False)
    # always in UTC
    at: datetime.datetime = db.Column(db.DateTime, nullable=False)
