import datetime

from app import db
from app.models.base import BaseModel


class Video(BaseModel):
    __tablename__ = "videos"
    # format of id is zdone:video:service:service_id
    id: str = db.Column(db.Text, primary_key=True)
    name: str = db.Column(db.Text, nullable=False)
    description: str = db.Column(db.Text)
    release_date: datetime.datetime = db.Column(db.DateTime)
    youtube_trailer_key: str = db.Column(db.Text)
    poster_image_url: str = db.Column(db.Text)
    film_or_tv: str = db.Column(db.Text, nullable=False, server_default='film')
