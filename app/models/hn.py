import datetime

from app import db
from app.models.base import BaseModel


class HnStory(BaseModel):
    __tablename__ = "hn_stories"
    id: int = db.Column(db.Integer, primary_key=True)
    comments: int = db.Column(db.Integer, nullable=False)
    score: int = db.Column(db.Integer, nullable=False)
    title: str = db.Column(db.Text, nullable=False)
    url: str = db.Column(db.Text, nullable=False)
    posted_at: datetime.datetime = db.Column(db.DateTime, nullable=False)
    last_refreshed_at: datetime.datetime = db.Column(db.DateTime, nullable=False)


class HnReadLog(BaseModel):
    __tablename__ = "hn_read_logs"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hn_story_id: int = db.Column(db.Integer, db.ForeignKey('hn_stories.id'), nullable=False)
    at: datetime.datetime = db.Column(db.DateTime, nullable=False)
