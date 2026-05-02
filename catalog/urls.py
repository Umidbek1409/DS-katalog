from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/login/', views.admin_login_view, name='admin_login'),
    path('admin-panel/logout/', views.admin_logout_view, name='admin_logout'),

    path('admin-panel/categories/', views.category_list, name='admin_category_list'),
    path('admin-panel/categories/add/', views.category_add, name='admin_category_add'),
    path('admin-panel/categories/<int:category_id>/edit/', views.category_edit, name='admin_category_edit'),
    path('admin-panel/categories/<int:category_id>/delete/', views.category_delete, name='admin_category_delete'),

    path('admin-panel/products/', views.product_list, name='admin_product_list'),
    path('admin-panel/products/add/', views.product_add, name='admin_product_add'),
    path('admin-panel/products/<int:product_id>/edit/', views.product_edit, name='admin_product_edit'),
    path('admin-panel/products/<int:product_id>/delete/', views.product_delete, name='admin_product_delete'),
    path('admin-panel/products/<int:product_id>/move-image/', views.product_move_image, name='admin_product_move_image'),
    path('admin-panel/products/update-order/', views.update_product_order, name='admin_product_update_order'),
    path('admin-panel/products/toggle-availability/', views.toggle_product_availability, name='admin_toggle_product_availability'),
    path('admin-panel/archived/', views.archived_products, name='admin_archived_products'),
    path('admin-panel/archived/<int:product_id>/restore/', views.restore_product, name='admin_restore_product'),
    path('admin-panel/settings/', views.admin_settings, name='admin_settings'),
    path('send-order/', views.send_order_telegram, name='send_order_telegram'),
]
