#!/bin/bash

set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

# Clear any lockouts from failed attempts
echo "Clearing failed login attempts..."
python manage.py shell <<EOF
from axes.models import AccessAttempt
AccessAttempt.objects.all().delete()
print("✅ Lockouts cleared")
EOF

# Create fresh superuser
echo "Creating superuser..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()

# Use NEW credentials
email = "superadmin@iscooa.com"
password = "SuperSecurePass123!"
username = "superadmin"

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f"✅ Superuser created: {email}")
    print(f"✅ Username: {username}")
    print(f"✅ Password: {password}")
else:
    print(f"✅ Superuser already exists: {email}")
    
    # Reset password in case you forgot
    user = User.objects.get(email=email)
    user.set_password(password)
    user.save()
    print(f"✅ Password reset to: {password}")
EOF

echo "Build completed!"