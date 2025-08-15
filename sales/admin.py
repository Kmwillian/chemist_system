from django.contrib import admin
from django.utils.html import format_html
from .models import Sale, SaleItem

from django.contrib import admin
from django.utils.html import format_html
from .models import Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['unit_price', 'total_price']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'customer_name', 'final_amount', 'payment_method', 
        'sale_date', 'served_by'
    ]
    list_filter = ['payment_method', 'sale_date', 'served_by']
    search_fields = ['customer_name', 'customer_phone', 'id']
    readonly_fields = ['sale_date', 'total_amount', 'final_amount']
    inlines = [SaleItemInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('served_by')

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'product', 'quantity', 'unit_price', 'total_price']
    list_filter = ['sale__sale_date', 'product__category']
    search_fields = ['product__name', 'sale__customer_name']