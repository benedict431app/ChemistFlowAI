import bcrypt
import secrets
from datetime import datetime, timedelta
from database import User, UserRole, SessionLocal

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def authenticate_user(username: str, password: str):
    """Authenticate a user and return user object if valid"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and verify_password(password, user.password_hash):
            if user.is_approved:
                return user
            else:
                return None  # Not approved
        return None
    finally:
        db.close()

def create_user(username: str, email: str, password: str, role: UserRole, display_name: str = None):
    """Create a new user"""
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            return None, "Username or email already exists"
        
        # Create user
        password_hash = hash_password(password)
        is_approved = (role == UserRole.ADMIN)  # Auto-approve admin
        
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_approved=is_approved,
            display_name=display_name
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, None
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()

def generate_reset_token():
    """Generate a secure reset token"""
    return secrets.token_urlsafe(32)

def create_reset_token(email: str):
    """Create a password reset token for user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None, "Email not found"
        
        token = generate_reset_token()
        expiry = datetime.utcnow() + timedelta(hours=1)
        
        user.reset_token = token
        user.reset_token_expiry = expiry
        db.commit()
        
        return token, None
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()

def reset_password_with_token(token: str, new_password: str):
    """Reset password using a valid token"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.reset_token == token).first()
        if not user:
            return False, "Invalid token"
        
        if user.reset_token_expiry < datetime.utcnow():
            return False, "Token expired"
        
        user.password_hash = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.commit()
        
        return True, None
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def get_user_by_id(user_id: int):
    """Get user by ID"""
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()

def get_admin_display_name():
    """Get the admin's display name (pharmacy name)"""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if admin and admin.display_name:
            return admin.display_name
        return "ChemistFlow Pharmacy"
    finally:
        db.close()

def update_admin_display_name(user_id: int, display_name: str):
    """Update admin display name"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.role == UserRole.ADMIN).first()
        if user:
            user.display_name = display_name
            db.commit()
            return True
        return False
    finally:
        db.close()

def approve_user(admin_id: int, user_id: int):
    """Approve a user (employee registration)"""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.id == admin_id, User.role == UserRole.ADMIN).first()
        if not admin:
            return False, "Not authorized"
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"
        
        user.is_approved = True
        db.commit()
        return True, None
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def get_pending_users():
    """Get all users pending approval"""
    db = SessionLocal()
    try:
        return db.query(User).filter(User.is_approved == False).all()
    finally:
        db.close()
