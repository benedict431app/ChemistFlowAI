import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///pharmacy.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserRole(enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"
    CUSTOMER = "customer"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    display_name = Column(String(100), nullable=True)  # For admin's pharmacy name
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reset_token = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    
    # Relationships
    sales = relationship("Sale", back_populates="employee")
    notifications = relationship("Notification", back_populates="user")

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional link to user account
    name = Column(String(200), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    credit_limit = Column(Float, default=0.0)
    current_credit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sales = relationship("Sale", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")
    crm_interactions = relationship("CRMInteraction", back_populates="customer")
    complaints = relationship("Complaint", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String(100), unique=True, nullable=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    unit_price = Column(Float, nullable=False)
    quantity_in_stock = Column(Integer, default=0)
    reorder_level = Column(Integer, default=10)
    supplier = Column(String(200), nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sale_items = relationship("SaleItem", back_populates="product")

class PaymentMode(enum.Enum):
    CASH = "cash"
    CREDIT = "credit"
    MPESA = "mpesa"
    CARD = "card"

class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_mode = Column(Enum(PaymentMode), nullable=False)
    total_amount = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    mpesa_transaction_id = Column(String(100), nullable=True)
    is_synced = Column(Boolean, default=False)  # For offline sales
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="sales")
    employee = relationship("User", back_populates="sales")
    sale_items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")

class SaleItem(Base):
    __tablename__ = "sale_items"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    # Relationships
    sale = relationship("Sale", back_populates="sale_items")
    product = relationship("Product", back_populates="sale_items")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_mode = Column(Enum(PaymentMode), nullable=False)
    mpesa_transaction_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="payments")

class CRMInteraction(Base):
    __tablename__ = "crm_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    interaction_type = Column(String(50), nullable=False)  # call, visit, email, etc.
    notes = Column(Text, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="crm_interactions")

class Complaint(Base):
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    submitted_by_role = Column(String(50), nullable=False)  # customer, employee, user
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, in_progress, resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="complaints")
    messages = relationship("ComplaintMessage", back_populates="complaint", cascade="all, delete-orphan")

class ComplaintMessage(Base):
    __tablename__ = "complaint_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    sender_role = Column(String(50), nullable=False)  # admin, customer, employee
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    complaint = relationship("Complaint", back_populates="messages")

class NotificationType(enum.Enum):
    EMPLOYEE_APPROVAL = "employee_approval"
    SYSTEM_CHANGE = "system_change"
    COMPLAINT = "complaint"
    LOW_STOCK = "low_stock"
    FOLLOW_UP = "follow_up"

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=False)
    approval_data = Column(Text, nullable=True)  # JSON string for approval details
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="notifications")

class OfflineSale(Base):
    __tablename__ = "offline_sales"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_data = Column(Text, nullable=False)  # JSON string of sale details
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # Null for anonymous
    role = Column(String(20), nullable=False)  # user, assistant
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass

def init_db():
    """Initialize database and create tables"""
    Base.metadata.create_all(bind=engine)

def create_admin_if_not_exists():
    """Create default admin user if none exists"""
    import bcrypt
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin_exists:
            password = "admin123"
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            admin = User(
                username="admin",
                email="admin@pharmacy.com",
                password_hash=hashed.decode('utf-8'),
                role=UserRole.ADMIN,
                is_approved=True,
                display_name="ChemistFlow Pharmacy"
            )
            db.add(admin)
            db.commit()
            print("Default admin created: username=admin, password=admin123")
    finally:
        db.close()
