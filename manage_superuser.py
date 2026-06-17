import os
import sys
import django

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=== STARTING SUPERUSER CREATION ===")
print(f"Current directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    print("✅ Django setup complete.")
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    email = "superadmin@iscooa.com"
    password = "SuperSecurePass123!"
    username = "superadmin"
    
    print(f"Creating/updating: {email}")
    
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
    
    print(f"✅ SUCCESS: Superuser {'created' if created else 'updated'}")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("=== SUPERUSER CREATION COMPLETE ===")