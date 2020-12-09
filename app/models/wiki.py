from sqlalchemy import UniqueConstraint

from app import db
from app.models.base import BaseModel


class WikipediaPage(BaseModel):
    __tablename__ = "wikipedia_pages"
    # simply the raw page name in the URL on Wikipedia
    id: str = db.Column(db.Text, primary_key=True)


class WikipediaFollow(BaseModel):
    __tablename__ = "wikipedia_follows"
    id: int = db.Column(db.Integer, primary_key=True)
    wikipedia_page_id: str = db.Column(db.Text, db.ForeignKey("wikipedia_pages.id"), nullable=False)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "wikipedia_page_id", name="_user_id_wikipedia_page_id"),)
