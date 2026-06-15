#!/bin/bash

# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser automatically if environment variables are set
if [[ -n "$DJANGO_SUPERUSER_USERNAME" ]] && [[ -n "$DJANGO_SUPERUSER_PASSWORD" ]]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --no-input \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "$DJANGO_SUPERUSER_EMAIL" 2>/dev/null || echo "Superuser already exists or creation failed"
fi

echo "Build completed successfully!"