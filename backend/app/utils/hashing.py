from passlib.context import CryptContext

# CryptContext manages hashing schemes.
# "bcrypt" = the algorithm we use.
# deprecated="auto" = if we ever add a new scheme,
#   old hashes are automatically flagged for re-hashing on next login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    
    bcrypt automatically generates a unique random salt for each hash.
    Two calls with the same password produce DIFFERENT hashes —
    this prevents rainbow table attacks.
    
    >>> hash_password("hunter2")
    "$2b$12$Kx9..."  ← different every time
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored hash.
    
    bcrypt extracts the salt from the stored hash, re-hashes the
    plaintext with that salt, then compares. You never see the salt
    directly — it's embedded in the hash string.
    
    Uses constant-time comparison to prevent timing attacks.
    (A timing attack measures how long verification takes to
    guess which characters are correct.)
    """
    return pwd_context.verify(plain_password, hashed_password)