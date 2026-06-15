#!/bin/bash

set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

# Create superuser - works with email-based User models
echo "Checking for existing superuser..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()

email = "$DJANGO_SUPERUSER_EMAIL"
password = "$DJANGO_SUPERUSER_PASSWORD"
username = "$DJANGO_SUPERUSER_USERNAME"

if email and password:
    if not User.objects.filter(email=email).exists():
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        print(f"✅ Superuser created: {email}")
    else:
        print(f"✅ Superuser already exists: {email}")
else:
    print("⚠️  Superuser environment variables not set")
EOF

echo "Build completed!"