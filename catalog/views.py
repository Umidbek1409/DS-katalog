import os
import shutil
import json
from decimal import Decimal
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Count, Case, When, IntegerField, Q
from django.utils import timezone
from datetime import timedelta, datetime
from django.utils.dateparse import parse_datetime
from .models import Category, Product, SiteSettings, DailySchedule
from .decorators import admin_required


def get_telegram_settings():
    settings = SiteSettings.get_settings()
    return {
        'token': settings.telegram_bot_token,
        'group_id': settings.telegram_group_id,
        'owner_id': settings.telegram_owner_id,
    }


def send_telegram_new_product(product):
    tg = get_telegram_settings()
    token = tg['token']
    group_id = tg['group_id']
    
    caption = (
        f"🆕 YANGI MAHSULOT\n\n"
        f"📦 {product.name}\n"
        f"💰 {product.price:,.0f} so'm\n"
        f"🗃 1 qutida: {product.units_per_box} dona"
    )
    
    try:
        if product.image:
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(product.image.path, 'rb') as photo:
                requests.post(url, data={
                    "chat_id": group_id,
                    "caption": caption
                }, files={"photo": photo})
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={
                "chat_id": group_id,
                "text": caption
            })
    except Exception as e:
        print(f"Telegram error: {e}")


def send_telegram_price_change(product, old_price, new_price):
    tg = get_telegram_settings()
    token = tg['token']
    group_id = tg['group_id']
    
    price_diff = new_price - old_price
    if price_diff > 0:
        direction = "📈 NARX OSHDI"
        arrow = "⬆️"
    else:
        direction = "📉 NARX PASAYDI"
        arrow = "⬇️"
    
    caption = (
        f"{direction}\n\n"
        f"📦 {product.name}\n"
        f"❌ Eski narx: {old_price:,.0f} so'm\n"
        f"{arrow} Yangi narx: {new_price:,.0f} so'm\n"
        f"{'+' if price_diff > 0 else ''}{price_diff:,.0f} so'm farq\n"
        f"🗃 1 qutida: {product.units_per_box} dona"
    )
    
    try:
        if product.image:
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(product.image.path, 'rb') as photo:
                requests.post(url, data={
                    "chat_id": group_id,
                    "caption": caption
                }, files={"photo": photo})
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={
                "chat_id": group_id,
                "text": caption
            })
    except Exception as e:
        print(f"Telegram error: {e}")


def send_telegram_product_restored(product, price_changed=False, old_price=None, new_price=None):
    tg = get_telegram_settings()
    token = tg['token']
    group_id = tg['group_id']
    
    if price_changed and old_price is not None and new_price is not None:
        price_diff = new_price - old_price
        if price_diff > 0:
            arrow = "⬆️"
        else:
            arrow = "⬇️"
        caption = (
            f"✅ MAHSULOT MAVJUD (narx o'zgardi)\n\n"
            f"📦 {product.name}\n"
            f"💵 Yangi narx: {new_price:,.0f} so'm {'(+)' if price_diff > 0 else ''}{price_diff:,.0f} so'm {arrow}\n"
            f"🗃 1 qutida: {product.units_per_box} dona"
        )
    else:
        caption = (
            f"✅ MAHSULOT MAVJUD\n\n"
            f"📦 {product.name}\n"
            f"💰 {product.price:,.0f} so'm\n"
            f"🗃 1 qutida: {product.units_per_box} dona"
        )
    
    try:
        if product.image:
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(product.image.path, 'rb') as photo:
                requests.post(url, data={
                    "chat_id": group_id,
                    "caption": caption
                }, files={"photo": photo})
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={
                "chat_id": group_id,
                "text": caption
            })
    except Exception as e:
        print(f"Telegram error: {e}")


def send_telegram_product_unavailable(product):
    tg = get_telegram_settings()
    token = tg['token']
    group_id = tg['group_id']
    
    caption = (
        f"⛔ MAHSULOT QOLMADI\n\n"
        f"📦 {product.name}\n"
        f"💰 {product.price:,.0f} so'm\n"
        f"🗃 1 qutida: {product.units_per_box} dona\n\n"
        f"Bu mahsulot hozirda katalogda ko'rsatilmaydi."
    )
    
    try:
        if product.image:
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(product.image.path, 'rb') as photo:
                requests.post(url, data={
                    "chat_id": group_id,
                    "caption": caption
                }, files={"photo": photo})
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={
                "chat_id": group_id,
                "text": caption
            })
    except Exception as e:
        print(f"Telegram error: {e}")


def index(request):
    categories = Category.objects.filter(products__isnull=False).distinct().order_by('order', 'name')
    products = Product.objects.filter(is_available=True).select_related('category').annotate(
        new_priority=Case(
            When(is_new=True, new_badge_enabled=True, new_until__gt=timezone.now(), then=0),
            default=1,
            output_field=IntegerField()
        )
    ).order_by('new_priority', 'order', 'name')
    site_settings = SiteSettings.get_settings()
    return render(request, 'catalog/index.html', {
        'categories': categories,
        'products': products,
        'site_settings': site_settings,
    })


@csrf_exempt
def send_order_telegram(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '')
        address = data.get('address', '')  # This is the selected region from dropdown
        phone = data.get('phone', '')
        comment = data.get('comment', '')
        cart = data.get('cart', [])
        
        # Check if order can be placed today based on schedule
        today_weekday = datetime.now().weekday()  # 0=Monday, 6=Sunday
        
        try:
            today_schedule = DailySchedule.objects.get(day_of_week=today_weekday)
            today_regions = today_schedule.get_regions()
            
            # Filter out None/empty values
            today_regions = [region for region in today_regions if region]
            
            # If there are regions specified for today, check if address (region) matches any
            if today_regions:
                region_matched = address and address in today_regions
                
                if not region_matched:
                    # Find next available day for the selected region
                    selected_region = address.strip() if address else ''
                    days_ahead = 1
                    next_available_date = None
                    next_available_weekday = None
                    while days_ahead <= 14:  # Check next 14 days
                        check_date = datetime.now() + timedelta(days=days_ahead)
                        check_weekday = check_date.weekday()
                        try:
                            check_schedule = DailySchedule.objects.get(day_of_week=check_weekday)
                            check_regions = check_schedule.get_regions()
                            check_regions = [r for r in check_regions if r]
                            if selected_region and selected_region in check_regions:
                                next_available_date = check_date
                                next_available_weekday = check_weekday
                                break
                        except DailySchedule.DoesNotExist:
                            pass
                        days_ahead += 1
                    
                    # Prepare response data
                    response_data = {
                        'error': 'schedule_restriction',
                        'today_regions': today_regions,
                        'selected_region': selected_region,
                    }
                    
                    if next_available_date:
                        formatted_date = next_available_date.strftime('%d.%m.%Y')
                        response_data['next_available_date'] = formatted_date
                        response_data['next_available_weekday'] = next_available_weekday
                    else:
                        response_data['next_available_date'] = None
                        response_data['next_available_weekday'] = None
                    
                    return JsonResponse(response_data, status=403)
            # If no today_regions or region matched, proceed with order
        except DailySchedule.DoesNotExist:
            # No schedule set for today, allow order
            pass
        
        lines = ["🛒 YANGI BUYURTMA\n"]
        lines.append(f"👤 {name}")
        lines.append(f"📍 {address}")
        lines.append(f"📞 {phone}")
        if comment:
            lines.append(f"💬 {comment}")
        lines.append("")
        
        total = 0
        for index, item in enumerate(cart, start=1):
            subtotal = item['price'] * item['qty']
            total += subtotal
            lines.append(
                f"{index}. <i>{item['name']}</i>: <b>{item['qty']}x</b> = "
                f"{subtotal:,.0f} so'm"
            )
        
        lines.append(f"\n💵 SUMMA: {total:,.0f} so'm")
        
        message = "\n".join(lines)
        
        tg = get_telegram_settings()
        url = f"https://api.telegram.org/bot{tg['token']}/sendMessage"
        requests.post(url, data={
            "chat_id": tg['owner_id'],
            "text": message,
            "parse_mode": "HTML"
        })
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@admin_required
def admin_dashboard(request):
    total_categories = Category.objects.count()
    total_products = Product.objects.count()
    available_products = Product.objects.filter(is_available=True).count()
    return render(request, 'admin_panel/dashboard.html', {
        'total_categories': total_categories,
        'total_products': total_products,
        'available_products': available_products,
    })


def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Login yoki parol noto\'g\'ri')
    return render(request, 'admin_panel/login.html')


@admin_required
def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')


@admin_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count('products')).order_by('order', 'name')
    return render(request, 'admin_panel/category_list.html', {'categories': categories})


@admin_required
def category_add(request):
    errors = {}
    name = ''
    order = '0'
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        order = request.POST.get('order', '0')
        image = request.FILES.get('image')
        if not name:
            errors['name'] = 'Kategoriya nomi majburiy'
        if errors:
            return render(request, 'admin_panel/category_form.html', {
                'category': None, 'errors': errors, 'name': name, 'order': order,
            })
        category = Category(name=name, order=int(order) if order else 0, image=image)
        category.save()
        messages.success(request, f'"{name}" kategoriyasi muvaffaqiyatli qo\'shildi')
        return redirect('admin_category_list')
    return render(request, 'admin_panel/category_form.html', {
        'category': None, 'errors': errors,
    })


@admin_required
def category_edit(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    errors = {}
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        order = request.POST.get('order', '0')
        image = request.FILES.get('image')
        if not name:
            errors['name'] = 'Kategoriya nomi majburiy'
        if errors:
            return render(request, 'admin_panel/category_form.html', {
                'category': category, 'errors': errors, 'name': name, 'order': order,
            })
        category.name = name
        category.order = int(order) if order else 0
        if image:
            category.image = image
        category.save()
        messages.success(request, f'"{name}" kategoriyasi yangilandi')
        return redirect('admin_category_list')
    return render(request, 'admin_panel/category_form.html', {
        'category': category, 'errors': errors,
    })


@require_POST
@admin_required
def category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    name = category.name
    category.delete()
    messages.success(request, f'"{name}" kategoriyasi o\'chirildi')
    return redirect('admin_category_list')


@admin_required
def product_list(request):
    categories = Category.objects.order_by('order', 'name')
    category_filter = request.GET.get('category', '')
    products = Product.objects.select_related('category').order_by('category__order', 'order', 'name')
    if category_filter:
        products = products.filter(category_id=category_filter)
    return render(request, 'admin_panel/product_list.html', {
        'products': products,
        'categories': categories,
        'selected_category': category_filter,
    })


@admin_required
def product_add(request):
    categories = Category.objects.order_by('order', 'name')
    errors = {}
    name = ''
    category_id = ''
    price = ''
    description = ''
    order = '0'
    is_available = False
    is_new = False
    new_badge_enabled = True
    new_until = ''
    units_per_box = '1'
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category', '')
        price = request.POST.get('price', '')
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('image')
        is_available = request.POST.get('is_available') == 'on'
        is_new = request.POST.get('is_new') == 'on'
        new_badge_enabled = request.POST.get('new_badge_enabled') == 'on'
        new_until = request.POST.get('new_until', '')
        order = request.POST.get('order', '0')
        units_per_box = request.POST.get('units_per_box', '1')
        if not name:
            errors['name'] = 'Mahsulot nomi majburiy'
        if not category_id:
            errors['category'] = 'Kategoriya tanlang'
        if not price:
            errors['price'] = 'Narx majburiy'
        if not image:
            errors['image'] = 'Rasm yuklash majburiy'
        if errors:
            return render(request, 'admin_panel/product_form.html', {
                'product': None, 'categories': categories, 'errors': errors,
                'name': name, 'category_id': category_id, 'price': price,
                'description': description, 'order': order, 'is_available': is_available,
                'is_new': is_new, 'new_badge_enabled': new_badge_enabled,
                'new_until': new_until, 'units_per_box': units_per_box,
            })
        product = Product(
            name=name, category_id=int(category_id), price=Decimal(price),
            description=description, image=image, is_available=is_available,
            order=int(order) if order else 0,
            is_new=is_new, new_badge_enabled=new_badge_enabled,
            units_per_box=int(units_per_box) if units_per_box else 1,
        )
        if is_new:
            if new_until:
                product.new_until = parse_datetime(new_until)
            else:
                product.new_until = timezone.now() + timedelta(days=7)
        else:
            product.new_until = None
        product.save()
        send_telegram_new_product(product)
        messages.success(request, f'"{name}" mahsuloti muvaffaqiyatli qo\'shildi')
        return redirect('admin_product_list')
    return render(request, 'admin_panel/product_form.html', {
        'product': None, 'categories': categories, 'errors': errors,
        'is_new': is_new, 'new_badge_enabled': new_badge_enabled,
        'new_until': new_until, 'units_per_box': units_per_box,
    })


@admin_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.order_by('order', 'name')
    errors = {}
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category', '')
        price = request.POST.get('price', '')
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('image')
        is_available = request.POST.get('is_available') == 'on'
        is_new = request.POST.get('is_new') == 'on'
        new_badge_enabled = request.POST.get('new_badge_enabled') == 'on'
        new_until = request.POST.get('new_until', '')
        order = request.POST.get('order', '0')
        units_per_box = request.POST.get('units_per_box', '1')
        if not name:
            errors['name'] = 'Mahsulot nomi majburiy'
        if not category_id:
            errors['category'] = 'Kategoriya tanlang'
        if not price:
            errors['price'] = 'Narx majburiy'
        if errors:
            return render(request, 'admin_panel/product_form.html', {
                'errors': errors, 'categories': categories, 'product': product,
                'name': name, 'category_id': category_id, 'price': price,
                'description': description, 'order': order, 'is_available': is_available,
                'is_new': is_new, 'new_badge_enabled': new_badge_enabled,
                'new_until': new_until, 'units_per_box': units_per_box,
            })
        old_price = product.price
        new_price = Decimal(price)
        price_changed = (old_price != new_price)
        product.name = name
        product.category_id = int(category_id)
        if price_changed:
            product.previous_price = old_price
            product.price_changed_at = timezone.now()
        product.price = new_price
        product.description = description
        product.is_available = is_available
        product.order = int(order) if order else 0
        product.is_new = is_new
        product.new_badge_enabled = new_badge_enabled
        product.units_per_box = int(units_per_box) if units_per_box else 1
        if is_new:
            if new_until:
                product.new_until = parse_datetime(new_until)
            else:
                product.new_until = timezone.now() + timedelta(days=7)
        else:
            product.new_until = None
        if image:
            product.image = image
        product.save()
        if price_changed:
            send_telegram_price_change(product, old_price, new_price)
        messages.success(request, f'"{name}" mahsuloti yangilandi')
        return redirect('admin_product_list')
    return render(request, 'admin_panel/product_form.html', {
        'product': product, 'categories': categories, 'errors': errors,
        'is_new': product.is_new, 'new_badge_enabled': product.new_badge_enabled,
        'new_until': product.new_until, 'units_per_box': product.units_per_box,
    })


@require_POST
@admin_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    name = product.name
    product.delete()
    messages.success(request, f'"{name}" mahsuloti o\'chirildi')
    return redirect('admin_product_list')


@require_POST
@admin_required
def product_move_image(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    target_category_id = request.POST.get('target_category')
    if not target_category_id:
        return JsonResponse({'success': False, 'error': 'Kategoriya tanlanmagan'})
    target_category = get_object_or_404(Category, id=target_category_id)
    if not product.image:
        return JsonResponse({'success': False, 'error': 'Mahsulotda rasm yo\'q'})
    source_path = product.image.path
    if not os.path.exists(source_path):
        return JsonResponse({'success': False, 'error': 'Rasm fayli topilmadi'})
    ext = os.path.splitext(source_path)[1]
    filename = f'category_{target_category.slug}{ext}'
    target_path = os.path.join(settings.MEDIA_ROOT, 'categories', filename)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.copy2(source_path, target_path)
    relative_path = os.path.join('categories', filename)
    target_category.image = relative_path
    target_category.save()
    return JsonResponse({'success': True, 'message': f'Rasm "{target_category.name}" kategoriyasiga ko\'chirildi'})


@admin_required
def update_product_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        for item in data.get('orders', []):
            Product.objects.filter(pk=item['id']).update(order=item['order'])
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@admin_required
def admin_settings(request):
    site_settings = SiteSettings.get_settings()
    errors = {}
    if request.method == 'POST':
        site_name = request.POST.get('site_name', '').strip()
        contact_info = request.POST.get('contact_info', '').strip()
        telegram_bot_token = request.POST.get('telegram_bot_token', '').strip()
        telegram_group_id = request.POST.get('telegram_group_id', '').strip()
        telegram_owner_id = request.POST.get('telegram_owner_id', '').strip()
        if not site_name:
            errors['site_name'] = 'Sayt nomi majburiy'
        if not contact_info:
            errors['contact_info'] = "Bog'lanish ma'lumoti majburiy"
        if not telegram_bot_token:
            errors['telegram_bot_token'] = 'Telegram bot token majburiy'
        if not telegram_group_id:
            errors['telegram_group_id'] = 'Telegram guruh ID majburiy'
        if not telegram_owner_id:
            errors['telegram_owner_id'] = 'Telegram shaxsiy chat ID majburiy'
        if errors:
            return render(request, 'admin_panel/settings.html', {
                'site_settings': site_settings,
                'errors': errors,
                'site_name': site_name,
                'contact_info': contact_info,
                'telegram_bot_token': telegram_bot_token,
                'telegram_group_id': telegram_group_id,
                'telegram_owner_id': telegram_owner_id,
            })
        site_settings.site_name = site_name
        site_settings.contact_info = contact_info
        site_settings.telegram_bot_token = telegram_bot_token
        site_settings.telegram_group_id = telegram_group_id
        site_settings.telegram_owner_id = telegram_owner_id
        site_settings.save()
        messages.success(request, 'Sozlamalar muvaffaqiyatli yangilandi')
        return redirect('admin_settings')
    return render(request, 'admin_panel/settings.html', {
        'site_settings': site_settings,
        'errors': {},
    })


@admin_required
def admin_jadval(request):
    # Get or create schedule entries for all days of the week
    days_of_week = [0, 1, 2, 3, 4, 5, 6]  # Monday to Sunday
    day_names = {
        0: 'Dushanba',
        1: 'Seshanba',
        2: 'Chorshanba',
        3: 'Payshanba',
        4: 'Juma',
        5: 'Shanba',
        6: 'Yakshanba'
    }

    # Prepare list of day data for the template
    days_data = []
    for day in days_of_week:
        obj, created = DailySchedule.objects.get_or_create(
            day_of_week=day,
            defaults={'region1': '', 'region2': '', 'region3': ''}
        )
        days_data.append({
            'day_num': day,
            'day_name': day_names[day],
            'region1': obj.region1 or '',
            'region2': obj.region2 or '',
            'region3': obj.region3 or '',
        })

    if request.method == 'POST':
        for day in days_of_week:
            schedule_obj = DailySchedule.objects.get(day_of_week=day)
            schedule_obj.region1 = request.POST.get(f'region1_{day}', '').strip() or None
            schedule_obj.region2 = request.POST.get(f'region2_{day}', '').strip() or None
            schedule_obj.region3 = request.POST.get(f'region3_{day}', '').strip() or None
            schedule_obj.save()

        messages.success(request, 'Jadval muvaffaqiyatli saqlandi')
        return redirect('admin_jadval')

    return render(request, 'admin_panel/jadval.html', {
        'days_data': days_data,
    })


def get_today_regions(request):
    """API endpoint to get today's regions for validation"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        today_weekday = datetime.now().weekday()  # 0=Monday, 6=Sunday
        
        try:
            today_schedule = DailySchedule.objects.get(day_of_week=today_weekday)
            today_regions = today_schedule.get_regions()
            
            # Filter out None/empty values
            today_regions = [region for region in today_regions if region]
            
            return JsonResponse({
                'success': True,
                'regions': today_regions,
                'today': today_weekday,
                'day_name': dict(DailySchedule.DAYS_OF_WEEK)[today_weekday]
            })
        except DailySchedule.DoesNotExist:
            # No schedule set for today
            return JsonResponse({
                'success': True,
                'regions': [],
                'today': today_weekday,
                'day_name': dict(DailySchedule.DAYS_OF_WEEK)[today_weekday]
            })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_all_regions(request):
    """API endpoint to get all unique regions from the entire week's schedule"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get all schedule entries
        all_schedules = DailySchedule.objects.all()
        all_regions = set()
        
        for schedule in all_schedules:
            regions = schedule.get_regions()
            for region in regions:
                if region:  # Skip None/empty values
                    all_regions.add(region.strip())
        
        # Convert to sorted list
        sorted_regions = sorted(list(all_regions))
        
        return JsonResponse({
            'success': True,
            'regions': sorted_regions
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@admin_required
def toggle_product_availability(request):
    product_id = request.POST.get('product_id')
    is_available = request.POST.get('is_available') == 'true'
    product = get_object_or_404(Product, id=product_id)
    was_available = product.is_available
    product.is_available = is_available
    product.save()
    if was_available and not is_available:
        send_telegram_product_unavailable(product)
    return JsonResponse({'success': True})


@admin_required
def archived_products(request):
    categories = Category.objects.order_by('order', 'name').annotate(
        total_products_count=Count('products'),
        available_count=Count('products', filter=Q(products__is_available=True)),
    )
    category_filter = request.GET.get('category', '')

    if category_filter:
        filtered_products = Product.objects.filter(category_id=category_filter, is_available=False).select_related('category').order_by('category__order', 'order', 'name')
        stats = Product.objects.filter(category_id=category_filter).aggregate(
            total=Count('id'),
            available=Count('id', filter=Q(is_available=True)),
        )
        catalog_name = categories.get(id=category_filter).name if categories.filter(id=category_filter).exists() else 'Noma\'lum'
    else:
        filtered_products = Product.objects.filter(is_available=False).select_related('category').order_by('category__order', 'order', 'name')
        stats = Product.objects.aggregate(
            total=Count('id'),
            available=Count('id', filter=Q(is_available=True)),
        )
        catalog_name = 'Barchasi'

    total_products = stats['total'] or 0
    available_products = stats['available'] or 0
    out_of_stock_count = total_products - available_products
    out_of_stock_percent = round((out_of_stock_count / total_products * 100) if total_products > 0 else 0, 1)

    return render(request, 'admin_panel/archived_products.html', {
        'products': filtered_products,
        'categories': categories,
        'selected_category': category_filter,
        'catalog_name': catalog_name,
        'total_products': total_products,
        'available_products': available_products,
        'out_of_stock_count': out_of_stock_count,
        'out_of_stock_percent': out_of_stock_percent,
    })


@admin_required
def archived_stats_api(request):
    category_filter = request.GET.get('category', '')

    if category_filter:
        stats = Product.objects.filter(category_id=category_filter).aggregate(
            total=Count('id'),
            available=Count('id', filter=Q(is_available=True)),
        )
        try:
            catalog_name = Category.objects.get(id=category_filter).name
        except Category.DoesNotExist:
            catalog_name = 'Noma\'lum'
    else:
        stats = Product.objects.aggregate(
            total=Count('id'),
            available=Count('id', filter=Q(is_available=True)),
        )
        catalog_name = 'Barchasi'

    total = stats['total'] or 0
    available = stats['available'] or 0
    out_of_stock = total - available
    out_of_stock_percent = round((out_of_stock / total * 100) if total > 0 else 0, 1)

    return JsonResponse({
        'catalog_name': catalog_name,
        'total_products': total,
        'available_products': available,
        'out_of_stock_count': out_of_stock,
        'out_of_stock_percent': out_of_stock_percent,
    })


@require_POST
@admin_required
def restore_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    price_changed = False
    old_price = None
    new_price = None
    if product.show_price_change and product.previous_price:
        price_changed = True
        old_price = product.previous_price
        new_price = product.price
    product.is_available = True
    product.save()
    send_telegram_product_restored(product, price_changed, old_price, new_price)
    messages.success(request, f'"{product.name}" mahsuloti qayta tiklandi')
    return redirect('admin_archived_products')
