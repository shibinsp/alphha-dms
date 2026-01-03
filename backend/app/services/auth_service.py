from datetime import datetime, timedelta
from typing import Optional, Tuple
import hashlib

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token,
    generate_mfa_secret, verify_mfa_code, generate_mfa_qr_code,
    validate_password_strength
)
from app.models.user import User, Role, Session as UserSession
from app.models.tenant import Tenant
from app.schemas.user import UserCreate, UserUpdate, Token

settings = get_settings()


class AuthService:
    """Authentication service handling login, tokens, and MFA."""

    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(
        self,
        email: str,
        password: str,
        mfa_code: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user with email/password and optional MFA.
        Returns (user, error_message) tuple.
        """
        user = self.db.query(User).filter(User.email == email).first()

        if not user:
            return None, "Invalid email or password"

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            return None, "Account is temporarily locked"

        # Verify password
        if not verify_password(password, user.password_hash):
            user.failed_attempts += 1
            if user.failed_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=settings.LOCKOUT_DURATION_MINUTES
                )
            self.db.commit()
            return None, "Invalid email or password"

        # Check if user is active
        if not user.is_active:
            return None, "Account is deactivated"

        # Check MFA if enabled
        if user.mfa_enabled:
            if not mfa_code:
                return None, "MFA code required"
            if not verify_mfa_code(user.mfa_secret, mfa_code):
                return None, "Invalid MFA code"

        # Reset failed attempts on successful login
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        self.db.commit()

        return user, None

    def create_tokens(self, user: User, ip_address: str = None, user_agent: str = None) -> Token:
        """Create access and refresh tokens for user."""
        token_data = {
            "sub": user.id,
            "email": user.email,
            "tenant_id": user.tenant_id
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Store session
        session = UserSession(
            user_id=user.id,
            token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        self.db.add(session)
        self.db.commit()

        return Token(
            access_token=access_token,
            refresh_token=refresh_token
        )

    def refresh_tokens(self, refresh_token: str) -> Optional[Token]:
        """Refresh access token using refresh token."""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        # Verify session exists
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        session = self.db.query(UserSession).filter(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > datetime.utcnow()
        ).first()

        if not session:
            return None

        user = self.db.query(User).filter(User.id == payload.get("sub")).first()
        if not user or not user.is_active:
            return None

        # Invalidate old session
        self.db.delete(session)
        self.db.commit()

        # Create new tokens
        return self.create_tokens(user)

    def logout(self, refresh_token: str) -> bool:
        """Logout user by invalidating refresh token."""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        session = self.db.query(UserSession).filter(
            UserSession.token_hash == token_hash
        ).first()

        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False

    def logout_all_sessions(self, user_id: str) -> int:
        """Logout user from all devices."""
        count = self.db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).delete()
        self.db.commit()
        return count

    def setup_mfa(self, user: User) -> Tuple[str, str]:
        """Setup MFA for user. Returns (secret, qr_code_base64)."""
        secret = generate_mfa_secret()
        qr_code = generate_mfa_qr_code(secret, user.email)
        return secret, qr_code

    def enable_mfa(self, user: User, secret: str, code: str) -> bool:
        """Verify MFA code and enable MFA for user."""
        if not verify_mfa_code(secret, code):
            return False

        user.mfa_secret = secret
        user.mfa_enabled = True
        self.db.commit()
        return True

    def disable_mfa(self, user: User) -> None:
        """Disable MFA for user."""
        user.mfa_secret = None
        user.mfa_enabled = False
        self.db.commit()

    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """Change user password. Returns (success, message)."""
        if not verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect"

        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            return False, message

        user.password_hash = get_password_hash(new_password)
        self.db.commit()

        # Invalidate all sessions
        self.logout_all_sessions(user.id)

        return True, "Password changed successfully"

    def create_user(
        self,
        user_data: UserCreate,
        tenant_id: str,
        created_by_id: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """Create a new user. Returns (user, error_message)."""
        # Check if email already exists
        existing = self.db.query(User).filter(User.email == user_data.email).first()
        if existing:
            return None, "Email already registered"

        # Validate password
        is_valid, message = validate_password_strength(user_data.password)
        if not is_valid:
            return None, message

        # Create user
        user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            department=user_data.department,
            region=user_data.region,
            clearance_level=user_data.clearance_level,
            phone=user_data.phone,
            tenant_id=tenant_id
        )

        # Assign roles
        if user_data.role_ids:
            roles = self.db.query(Role).filter(Role.id.in_(user_data.role_ids)).all()
            user.roles = roles

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user, None

    def update_user(self, user: User, user_data: UserUpdate) -> User:
        """Update user information."""
        update_data = user_data.model_dump(exclude_unset=True)

        # Handle role updates separately
        role_ids = update_data.pop("role_ids", None)
        if role_ids is not None:
            roles = self.db.query(Role).filter(Role.id.in_(role_ids)).all()
            user.roles = roles

        # Update other fields
        for field, value in update_data.items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate_user(self, user: User) -> None:
        """Deactivate user account."""
        user.is_active = False
        self.db.commit()
        self.logout_all_sessions(user.id)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
