from django.urls import path
from . import views
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.views.generic import RedirectView
from django.http import HttpResponse
urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', lambda request: HttpResponse(status=204)),  
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico')),
    path('', include('billing_app.urls')),

]
urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/edit/', views.customer_update, name='customer_update'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    # Stock Management
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/create/', views.stock_create, name='stock_create'),
    path('stock/<int:pk>/edit/', views.stock_update, name='stock_update'),
    path('stock/<int:pk>/delete/', views.stock_delete, name='stock_delete'),
    
    # Bills
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/create/', views.bill_create, name='bill_create'),
    path('bills/<int:pk>/items/', views.bill_items, name='bill_items'),
    path('bills/<int:pk>/finalize/', views.bill_finalize, name='bill_finalize'),
    path('bills/<int:pk>/', views.bill_detail, name='bill_detail'),
    path('bills/<int:pk>/pdf/', views.generate_bill_pdf, name='bill_pdf'),
    path('bill/delete/<int:pk>/', views.delete_bill, name='delete_bill'),
    path('get-product-price/<int:product_id>/',views.get_product_price,name='get_product_price'),
]