from passlib.context import CryptContext

# bcrypt password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """
    Convert a plain password into a hashed password.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify whether the entered password matches the stored hash.
    """
    return pwd_context.verify(plain_password, hashed_password)