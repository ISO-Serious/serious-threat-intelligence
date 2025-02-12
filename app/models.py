from .extensions import db
from datetime import datetime

class Feed(db.Model):
    __tablename__ = 'feeds'
    
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String, unique=True)
    name = db.Column(db.String)
    category = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)
    articles = db.relationship('Article', backref='feed', lazy=True)

class Article(db.Model):
    __tablename__ = 'articles'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('feeds.id'))
    title = db.Column(db.String)
    url = db.Column(db.String, unique=True)
    published = db.Column(db.DateTime)
    summary = db.Column(db.Text)
    content = db.Column(db.Text)
    author = db.Column(db.String)
    
class DailySummary(db.Model):
    __tablename__ = 'daily_summaries'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.String, nullable=False)
    summary = db.Column(db.JSON, nullable=False)
    generated_at = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)
    commentary = db.Column(db.Text)
    summary_type = db.Column(db.String, nullable=False, default='daily')  # Options: 'daily' or 'weekly'