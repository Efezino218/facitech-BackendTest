"""
Environment variable validator.
Checks all required environment variables are present
before the application starts.
Called from settings.py.
"""
import os
import sys


def validate_environment():
    """
    Validates all required environment variables are set.
    Exits with a clear error message if any are missing.
    Only runs critical validation — optional vars are noted.
    """

    # Always required
    required = [
        'SECRET_KEY',
        'DB_NAME',
        'DB_USER',
        'DB_PASSWORD',
        'DB_HOST',
        'DB_PORT',
    ]

    # Required in production only
    production_required = [
        'ALLOWED_HOSTS',
        'CORS_ALLOWED_ORIGINS',
    ]

    missing = []
    for var in required:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print('\n' + '='*60)
        print('ISCOOA FACITECH — MISSING ENVIRONMENT VARIABLES')
        print('='*60)
        for var in missing:
            print(f'  ✗  {var} is not set')
        print('\nPlease check your .env file.')
        print('Reference: backend/.env.example')
        print('='*60 + '\n')
        sys.exit(1)

    debug = os.getenv('DEBUG', 'True') == 'True'
    if not debug:
        prod_missing = []
        for var in production_required:
            if not os.getenv(var):
                prod_missing.append(var)
        if prod_missing:
            print('\nPRODUCTION MODE — Missing required variables:')
            for var in prod_missing:
                print(f'  ✗  {var}')
            sys.exit(1)