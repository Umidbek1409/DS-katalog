#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create admin user if environment variables are set
if [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
    python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='$ADMIN_USERNAME').exists():
    User.objects.create_superuser('$ADMIN_USERNAME', '', '$ADMIN_PASSWORD')
    print(f"Admin user '$ADMIN_USERNAME' created successfully.")
else:
    user = User.objects.get(username='$ADMIN_USERNAME')
    user.set_password('$ADMIN_PASSWORD')
    user.save()
    print(f"Admin user '$ADMIN_USERNAME' password updated.")
EOF
fi
