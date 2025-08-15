from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('pos/', views.pos_system, name='pos'),
    path('create/', views.create_sale, name='create_sale'),
    path('api/search-products/', views.search_products_api, name='search_products_api'),
    path('api/categories/', views.categories_api, name='categories_api'),
    path('process/', views.process_sale, name='process_sale'),
    path('history/', views.sales_history, name='sales_history'),
    path('detail/<int:sale_id>/', views.sale_detail, name='sale_detail'),
    path('refund/<int:sale_id>/', views.refund_sale, name='refund_sale'),
    path('receipt/<int:sale_id>/', views.get_sale_receipt_data, name='receipt_data'),
    path('daily-summary/', views.daily_sales_summary, name='daily_summary'),
]