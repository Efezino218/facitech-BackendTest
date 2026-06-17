import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

email = os.getenv('SUPERUSER_EMAIL', 'superadmin@iscooa.com')
password = os.getenv('SUPERUSER_PASSWORD', 'SuperSecurePass123!')
username = os.getenv('SUPERUSER_USERNAME', 'superadmin')

try:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': username,
            'email': email,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True
        }
    )
    
    if not created:
        user.username = username
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
    
    user.set_password(password)
    user.save()
    
    print(f"✅ Superuser {'created' if created else 'updated'}: {email}")
    print(f"✅ Password: {password}")
    print(f"✅ Login with: {email}")
except Exception as e:
    print(f"❌ Error: {e}")