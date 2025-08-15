from django.contrib import admin
from django.utils.html import format_html
from django.db.models import F
from .models import Category, Supplier, Product, Purchase, PurchaseItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'product_count', 'created_at']
    search_fields = ['name']
    list_filter = ['created_at']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'product_count']
    search_fields = ['name', 'contact_person', 'phone', 'email']
    list_filter = ['created_at']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'supplier', 'selling_price', 
        'quantity_in_stock', 'stock_status', 'expiry_status', 'is_active'
    ]
    list_filter = [
        'category', 'supplier', 'is_active', 'created_at', 
        'expiry_date', 'quantity_in_stock'
    ]
    search_fields = ['name', 'generic_name', 'barcode']
    list_editable = ['selling_price', 'quantity_in_stock', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'generic_name', 'category', 'supplier', 'description')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'selling_price')
        }),
        ('Inventory', {
            'fields': ('quantity_in_stock', 'minimum_stock_level')
        }),
        ('Product Details', {
            'fields': ('batch_number', 'manufacture_date', 'expiry_date', 'barcode', 'image')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        })
    )
    
    def stock_status(self, obj):
        if obj.is_low_stock:
            return format_html('<span style="color: red;">Low Stock</span>')
        return format_html('<span style="color: green;">In Stock</span>')
    stock_status.short_description = 'Stock Status'
    
    def expiry_status(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.expiry_date:
            return format_html('<span style="color: orange;">Expires: {}</span>', obj.expiry_date)
        return 'No expiry date'
    expiry_status.short_description = 'Expiry Status'

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    readonly_fields = ['total_cost']

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'supplier', 'total_amount', 'purchase_date', 'created_by']
    list_filter = ['supplier', 'purchase_date', 'created_by']
    search_fields = ['invoice_number', 'supplier__name']
    readonly_fields = ['purchase_date', 'total_amount']
    inlines = [PurchaseItemInline]
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new
            obj.created_by = request.user
        super().save_model(request, obj, form, change)