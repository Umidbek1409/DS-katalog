#!/usr/bin/env bash
set -e

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating media directories..."
mkdir -p media/categories
mkdir -p media/products

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating/updating admin user..."
python create_admin.py

echo "Build complete."
