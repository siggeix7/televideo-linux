from __future__ import annotations

import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [value.strip() for value in os.environ.get(name, default).split(",") if value.strip()]

_SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not _SECRET_KEY:
    raise SystemExit("DJANGO_SECRET_KEY is required. Generate one with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'")
SECRET_KEY = _SECRET_KEY
DEBUG = env_bool("DJANGO_DEBUG")
RUNNING_TESTS = "test" in sys.argv
ADMIN_ENABLED = env_bool("DJANGO_ADMIN_ENABLED")
PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "").rstrip("/")
APP_VERSION = os.environ.get("APP_VERSION", "dev")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "*")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
USE_X_FORWARDED_HOST = env_bool("DJANGO_USE_X_FORWARDED_HOST", True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if env_bool("DJANGO_SECURE_PROXY_SSL_HEADER", True) else None
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD")
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = env_bool("DJANGO_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env_bool("DJANGO_COOKIE_SECURE")
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "news",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "chronica.csp_middleware.ContentSecurityPolicyMiddleware",
    "chronica.rate_limit_middleware.RateLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "chronica.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "news.site_urls.seo_context",
            ],
        },
    },
]

WSGI_APPLICATION = "chronica.wsgi.application"

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost").strip()
_USE_POSTGRES = POSTGRES_HOST != ""

_SQLITE_PATH = os.environ.get("SQLITE_PATH") or str(BASE_DIR / "db.sqlite3")

SQLITE_LEGACY = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": _SQLITE_PATH,
    "OPTIONS": {
        "timeout": int(os.environ.get("SQLITE_TIMEOUT", "60")),
        "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
    },
}

if _USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "televideo"),
            "USER": os.environ.get("POSTGRES_USER", "televideo"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": POSTGRES_HOST,
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "OPTIONS": {
                "connect_timeout": int(os.environ.get("POSTGRES_CONNECT_TIMEOUT", "10")),
            },
        },
        "sqlite": SQLITE_LEGACY,
    }
    DATABASE_ROUTERS = ["chronica.routers.DefaultOnlyRouter"]
else:
    DATABASES = {
        "default": SQLITE_LEGACY,
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHE_DIR = os.environ.get("DJANGO_CACHE_DIR") or str(Path("/data/django_cache"))
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": CACHE_DIR,
        "OPTIONS": {"MAX_ENTRIES": 5000},
    }
}

LOG_DIR = os.environ.get("DJANGO_LOG_DIR", "")
LOG_FILE = os.path.join(LOG_DIR, "televideo.log") if LOG_DIR else ""
LOG_MAX_BYTES = int(os.environ.get("DJANGO_LOG_MAX_BYTES", str(5 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.environ.get("DJANGO_LOG_BACKUP_COUNT", "3"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
        "handlers": ["console"],
    },
    "loggers": {
        "news": {
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

if LOG_FILE:
    LOGGING["handlers"]["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "formatter": "simple",
        "filename": LOG_FILE,
        "maxBytes": LOG_MAX_BYTES,
        "backupCount": LOG_BACKUP_COUNT,
    }
    LOGGING["root"]["handlers"].append("file")
    LOGGING["loggers"]["news"]["handlers"].append("file")

NEWS_REFRESH_SECONDS = int(os.environ.get("NEWS_REFRESH_SECONDS", "1200"))
NEWS_FETCH_LIMIT = int(os.environ.get("NEWS_FETCH_LIMIT", "30"))
CATEGORY_FETCH_LIMIT = int(os.environ.get("CATEGORY_FETCH_LIMIT", "2"))
TELETEXT_SECTION_REFRESH_SECONDS = int(os.environ.get("TELETEXT_SECTION_REFRESH_SECONDS", "21600"))
METEO_SECTION_REFRESH_SECONDS = int(os.environ.get("METEO_SECTION_REFRESH_SECONDS", "3600"))
TRANSLATION_TIMEOUT = float(os.environ.get("TRANSLATION_TIMEOUT", "8"))
TRANSLATION_RETRIES = int(os.environ.get("TRANSLATION_RETRIES", "1"))
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "").strip()
OPENWEATHER_REFRESH_CHECK_SECONDS = int(os.environ.get("OPENWEATHER_REFRESH_CHECK_SECONDS", "3600"))
OPENWEATHER_STALE_SECONDS = int(os.environ.get("OPENWEATHER_STALE_SECONDS", "3600"))
OPENWEATHER_MAX_CALLS_PER_MINUTE = int(os.environ.get("OPENWEATHER_MAX_CALLS_PER_MINUTE", "40"))
OPENWEATHER_BATCH_SIZE = int(os.environ.get("OPENWEATHER_BATCH_SIZE", "200"))
OPENWEATHER_TIMEOUT = float(os.environ.get("OPENWEATHER_TIMEOUT", "8"))
