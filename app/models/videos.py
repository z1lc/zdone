import datetime

from app import db
from app.models.base import BaseModel


class Video(BaseModel):
    __tablename__ = "videos"
    # format of id is zdone:video:service:service_id
    id: str = db.Column(db.Text, primary_key=True)
    name: str = db.Column(db.Text, nullable=False)
    description: str = db.Column(db.Text)
    release_date: datetime.date = db.Column(db.Date)
    last_air_date: datetime.date = db.Column(db.Date)
    in_production: bool = db.Column(db.Boolean)
    youtube_trailer_key: str = db.Column(db.Text, db.ForeignKey('youtube_videos.key'))
    poster_image_url: str = db.Column(db.Text)
    film_or_tv: str = db.Column(db.Text, nullable=False, server_default='film')


class YouTubeVideo(BaseModel):
    __tablename__ = "youtube_videos"
    key: str = db.Column(db.Text, primary_key=True)
    duration_seconds: int = db.Column(db.Integer, nullable=False)


# For situations where we don't like the API-provided YouTube video and want to override it with an alternative.
class YouTubeVideoOverride(BaseModel):
    __tablename__ = "youtube_video_overrides"
    video_id: int = db.Column(db.Text, db.ForeignKey('videos.id'), primary_key=True)
    youtube_trailer_key: str = db.Column(db.Text, db.ForeignKey('youtube_videos.key'), nullable=True)


class VideoPerson(BaseModel):
    __tablename__ = "video_persons"
    # format of id is zdone:person:service:service_id
    id: str = db.Column(db.Text, primary_key=True)
    name: str = db.Column(db.Text)
    birthday: datetime.date = db.Column(db.Date)
    known_for: str = db.Column(db.Text)
    image_url: str = db.Column(db.Text)


class VideoCredit(BaseModel):
    __tablename__ = "video_credits"
    # format of id is zdone:credit:service:service_id
    id: str = db.Column(db.Text, primary_key=True)
    video_id: int = db.Column(db.Text, db.ForeignKey('videos.id'), nullable=False)
    person_id: int = db.Column(db.Text, db.ForeignKey('video_persons.id'), nullable=False)
    character: str = db.Column(db.Text)
    order: int = db.Column(db.Integer)
