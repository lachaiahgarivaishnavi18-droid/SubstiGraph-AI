import os
from sqlalchemy import create_engine, JSON, String, Float, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column, sessionmaker
from datetime import datetime, timezone

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./substigraph.db')
if DATABASE_URL.startswith(('postgres://','postgresql://')):
    DATABASE_URL = 'postgresql+psycopg://' + DATABASE_URL.split('://',1)[1]
if os.getenv('VERCEL') and not DATABASE_URL.startswith('postgresql+psycopg://'):
    raise RuntimeError('Set DATABASE_URL to a persistent PostgreSQL database before deploying to Vercel. Local SQLite is not cloud storage.')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = 'products'
    product_id = mapped_column(Integer, primary_key=True)
    product_name = mapped_column(String(200))
    sku = mapped_column(String(80), unique=True, index=True)
    brand = mapped_column(String(100), index=True)
    category = mapped_column(String(100), index=True)
    subcategory = mapped_column(String(100))
    description = mapped_column(String(2000), default='')
    price = mapped_column(Float)
    cost = mapped_column(Float)
    attributes = mapped_column(JSON, default=dict)
    specifications = mapped_column(JSON, default=dict)
    color = mapped_column(String(80), default='')
    size = mapped_column(String(80), default='')
    material = mapped_column(String(80), default='')
    product_rating = mapped_column(Float, default=0)
    stock_quantity = mapped_column(Integer, default=0)
    supplier_id = mapped_column(String(80))
    sales_quantity = mapped_column(Integer, default=0)
    status = mapped_column(String(30), default='active')
    created_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Setting(Base):
    __tablename__ = 'settings'
    key = mapped_column(String(80), primary_key=True)
    value = mapped_column(JSON)

def serialize(p):
    result = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    result['profit_margin'] = round((p.price-p.cost)/p.price*100, 2) if p.price else 0
    return result
