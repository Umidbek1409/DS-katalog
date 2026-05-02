"""
Script to create or update the admin user.
Run: python create_admin.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalogue_web.settings')
django.setup()

from django.contrib.auth.models import User

username = os.environ.get('ADMIN_USERNAME', 'gulom5001')
password = os.environ.get('ADMIN_PASSWORD', 'umidbek1409')
email = os.environ.get('ADMIN_EMAIL', '')

print(f"Creating admin user: username='{username}'")

try:
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.save()
    print(f"SUCCESS: Admin user '{username}' password updated.")
except User.DoesNotExist:
    User.objects.create_superuser(username, email, password)
    print(f"SUCCESS: Admin user '{username}' created.")
except Exception as e:
    print(f"ERROR: {e}")
