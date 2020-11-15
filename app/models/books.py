from sqlalchemy import UniqueConstraint

from app import db
from app.models.base import BaseModel


class ReadwiseBook(BaseModel):
    __tablename__ = "readwise_books"
    # format of id is zdone:book:readwise:readwise_id
    id: str = db.Column(db.Text, primary_key=True)
    title: str = db.Column(db.Text, nullable=False)
    author: str = db.Column(db.Text)
    cover_image_url: str = db.Column(db.Text)

    def get_bare_id(self):
        return self.id.split("zdone:book:readwise:")[1]


class ManagedReadwiseBook(BaseModel):
    __tablename__ = "managed_readwise_books"
    id: int = db.Column(db.Integer, primary_key=True)
    readwise_book_id: str = db.Column(db.Text, db.ForeignKey('readwise_books.id'), nullable=False)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category: str = db.Column(db.Text)
    __table_args__ = (
        UniqueConstraint('user_id', 'readwise_book_id', 'category', name='_user_id_readwise_book_id_and_category'),
    )


class ReadwiseHighlight(BaseModel):
    __tablename__ = "readwise_highlights"
    # format of id is zdone:highlight:readwise:readwise_id
    id: str = db.Column(db.Text, primary_key=True)
    managed_readwise_book_id: int = db.Column(db.Integer, db.ForeignKey('managed_readwise_books.id'), nullable=False)
    text: str = db.Column(db.Text, nullable=False)
    __table_args__ = (
        UniqueConstraint('managed_readwise_book_id', 'text', name='_managed_readwise_book_id_and_text'),
    )

    def get_bare_id(self):
        return self.id.split("zdone:highlight:readwise:")[1]
