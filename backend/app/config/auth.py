import os

# Google OAuth2 - Client ID for token audience validation
# No client secret needed - we only verify ID tokens using Google's public keys
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# JWT Session Configuration
# Reuse SECRET_KEY from the existing environment for signing platform JWTs
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "test_secret"))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

# Cookie configuration for session JWT
SESSION_COOKIE_NAME = "nbd_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = os.getenv("APP_ENV", "development") == "production"
SESSION_COOKIE_SAMESITE = "lax"
