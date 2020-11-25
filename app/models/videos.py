import datetime
from typing import Optional

from sqlalchemy import func, UniqueConstraint

from app import db
from app.models.base import BaseModel
from app.util import to_tmdb_id


class Video(BaseModel):
    __tablename__ = "videos"
    # format of id is zdone:video:service:service_id
    id: str = db.Column(db.Text, primary_key=True)
    name: str = db.Column(db.Text, nullable=False)
    original_name: str = db.Column(db.Text)
    description: str = db.Column(db.Text)
    release_date: datetime.date = db.Column(db.Date)
    last_air_date: datetime.date = db.Column(db.Date)
    in_production: bool = db.Column(db.Boolean)
    youtube_trailer_key: str = db.Column(db.Text, db.ForeignKey("youtube_videos.key"))
    poster_image_url: str = db.Column(db.Text)
    film_or_tv: str = db.Column(db.Text, nullable=False, server_default="film")
    budget: int = db.Column(db.BigInteger)
    revenue: int = db.Column(db.BigInteger)
    seasons: int = db.Column(db.Integer)

    def is_film(self) -> bool:
        return self.film_or_tv == "film"

    def is_tv(self) -> bool:
        return self.film_or_tv == "TV show"

    def get_url(self) -> str:
        if self.is_tv():
            return f"https://www.themoviedb.org/tv/{self.get_tmdb_id()}"
        elif self.is_film():
            return f"https://www.themoviedb.org/movie/{self.get_tmdb_id()}"
        else:
            return ""

    def get_tmdb_id(self) -> int:
        return to_tmdb_id(self.id)


class ManagedVideo(BaseModel):
    __tablename__ = "managed_videos"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    video_id: str = db.Column(db.Text, db.ForeignKey("videos.id"), nullable=False)
    date_added: datetime.date = db.Column(db.Date, nullable=False, server_default=func.current_date())
    watched: bool = db.Column(db.Boolean, server_default="false", nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "video_id", name="_user_id_and_video_id"),)


class YouTubeVideo(BaseModel):
    __tablename__ = "youtube_videos"
    key: str = db.Column(db.Text, primary_key=True)
    duration_seconds: int = db.Column(db.Integer, nullable=False)


# For situations where we don't like the API-provided YouTube video and want to override it with an alternative.
class YouTubeVideoOverride(BaseModel):
    __tablename__ = "youtube_video_overrides"
    video_id: int = db.Column(db.Text, db.ForeignKey("videos.id"), primary_key=True)
    youtube_trailer_key: Optional[str] = db.Column(db.Text, db.ForeignKey("youtube_videos.key"), nullable=True)


class VideoPerson(BaseModel):
    __tablename__ = "video_persons"
    # format of id is zdone:person:service:service_id
    id: str = db.Column(db.Text, primary_key=True)
    name: str = db.Column(db.Text)
    birthday: datetime.date = db.Column(db.Date)
    deathday: datetime.date = db.Column(db.Date)
    known_for: str = db.Column(db.Text)
    image_url: str = db.Column(db.Text)


class VideoCredit(BaseModel):
    __tablename__ = "video_credits"
    # format of id is zdone:credit:service:service_id
    id: str = db.Column(db.Text, primary_key=True)
    video_id: int = db.Column(db.Text, db.ForeignKey("videos.id"), nullable=False)
    person_id: int = db.Column(db.Text, db.ForeignKey("video_persons.id"), nullable=False)
    character: Optional[str] = db.Column(db.Text, nullable=True)
    job: Optional[str] = db.Column(db.Text, nullable=True)
    order: Optional[int] = db.Column(db.Integer, nullable=True)
