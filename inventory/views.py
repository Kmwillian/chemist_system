from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Product, Category, Supplier, Purchase
from sales.models import Sale, SaleItem
from .forms import ProductForm, CategoryForm, SupplierForm  # Removed ProductEditForm from here
from django.db.models import Count, Q
from .models import Category
from django import forms  # Added this import

@login_required
def dashboard(request):
    # Get key statistics
    total_products = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(
        quantity_in_stock__lte=F('minimum_stock_level'),
        is_active=True
    ).count()
    
    today_sales = Sale.objects.filter(sale_date__date=timezone.now().date())
    today_revenue = today_sales.aggregate(Sum('final_amount'))['final_amount__sum'] or 0
    
    expired_products = Product.objects.filter(
        expiry_date__lt=timezone.now().date(),
        is_active=True
    ).count()
    
    recent_sales = Sale.objects.select_related('served_by')[:5]
    low_stock_items = Product.objects.filter(
        quantity_in_stock__lte=F('minimum_stock_level'),
        is_active=True
    )[:10]
    
    context = {
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'today_revenue': today_revenue,
        'expired_products': expired_products,
        'recent_sales': recent_sales,
        'low_stock_items': low_stock_items,
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
def product_list(request):
    query = request.GET.get('q')
    category = request.GET.get('category')
    
    products = Product.objects.filter(is_active=True)
    
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(generic_name__icontains=query) |
            Q(barcode__icontains=query)
        )
    
    if category:
        products = products.filter(category_id=category)
    
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category,
    }
    return render(request, 'inventory/product_list.html', context)

@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('inventory:product_list')
    else:
        form = ProductForm()
    
    return render(request, 'inventory/add_product.html', {'form': form})

@login_required
def category_list(request):
    categories = Category.objects.annotate(
        active_products_count=Count('products', filter=Q(products__is_active=True))
    )
    return render(request, 'inventory/category_list.html', {'categories': categories})

@login_required
def supplier_list(request):
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    location = request.GET.get('location', '')
    
    suppliers = Supplier.objects.all()
    
    # Apply filters
    if search:
        suppliers = suppliers.filter(
            Q(name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    if status == 'active':
        suppliers = suppliers.filter(is_active=True)
    elif status == 'inactive':
        suppliers = suppliers.filter(is_active=False)
    
    if location:
        suppliers = suppliers.filter(address__icontains=location)
    
    # Get statistics
    active_suppliers = Supplier.objects.filter(is_active=True).count()
    recent_orders = 0  # You can implement this based on your Purchase model
    pending_payments = 0  # You can implement this based on your business logic
    
    # Get unique locations for filter dropdown
    locations = Supplier.objects.exclude(
        address__isnull=True
    ).exclude(
        address__exact=''
    ).values_list('address', flat=True).distinct()
    
    # Pagination
    paginator = Paginator(suppliers, 10)  # Show 10 suppliers per page
    page_number = request.GET.get('page')
    suppliers = paginator.get_page(page_number)
    
    context = {
        'suppliers': suppliers,
        'active_suppliers': active_suppliers,
        'recent_orders': recent_orders,
        'pending_payments': pending_payments,
        'locations': locations,
    }
    return render(request, 'inventory/supplier_list.html', context)

@login_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier added successfully!')
            return redirect('inventory:supplier_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SupplierForm()
    
    return render(request, 'inventory/supplier_form.html', {
        'form': form,
        'title': 'Add New Supplier',
        'action': 'Add'
    })

@login_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    # Get supplier statistics
    # total_orders = Purchase.objects.filter(supplier=supplier).count()
    # total_amount = Purchase.objects.filter(supplier=supplier).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    # recent_purchases = Purchase.objects.filter(supplier=supplier).order_by('-created_at')[:5]
    
    context = {
        'supplier': supplier,
        # 'total_orders': total_orders,
        # 'total_amount': total_amount,
        # 'recent_purchases': recent_purchases,
    }
    return render(request, 'inventory/supplier_detail.html', context)

@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f'Supplier "{supplier.name}" updated successfully!')
            return redirect('inventory:supplier_detail', pk=supplier.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SupplierForm(instance=supplier)
    
    return render(request, 'inventory/supplier_form.html', {
        'form': form,
        'supplier': supplier,
        'title': f'Edit {supplier.name}',
        'action': 'Update'
    })

@login_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier_name = supplier.name
        
        # Check if supplier has related purchases
        # if Purchase.objects.filter(supplier=supplier).exists():
        #     messages.error(request, f'Cannot delete supplier "{supplier_name}" because it has related purchase orders.')
        #     return redirect('inventory:supplier_detail', pk=supplier.pk)
        
        try:
            supplier.delete()
            messages.success(request, f'Supplier "{supplier_name}" deleted successfully!')
            return redirect('inventory:supplier_list')
        except Exception as e:
            messages.error(request, f'Error deleting supplier: {str(e)}')
            return redirect('inventory:supplier_detail', pk=supplier.pk)
    
    return render(request, 'inventory/supplier_confirm_delete.html', {
        'supplier': supplier
    })

@login_required
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if name:
            try:
                Category.objects.create(
                    name=name,
                    description=description
                )
                messages.success(request, f'Category "{name}" added successfully!')
            except Exception as e:
                messages.error(request, f'Error adding category: {str(e)}')
        else:
            messages.error(request, 'Category name is required.')
    
    return redirect('inventory:category_list')

@login_required
def edit_category(request):
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if category_id and name:
            try:
                category = Category.objects.get(id=category_id)
                category.name = name
                category.description = description
                category.save()
                messages.success(request, f'Category "{name}" updated successfully!')
            except Category.DoesNotExist:
                messages.error(request, 'Category not found.')
            except Exception as e:
                messages.error(request, f'Error updating category: {str(e)}')
        else:
            messages.error(request, 'Category ID and name are required.')
    
    return redirect('inventory:category_list')

#@login_required
#def delete_category(request):
 #   if request.method == 'POST':
  #      category_id = request.POST.get('category_id')
   #     
    #    if category_id:
     #       try:
      #          category = Category.objects.get(id=category_id)
       #         category_name = category.name
                
        #        # Check if category has products
         #       if category.products.exists():
          #          messages.error(request, f'Cannot delete category "{category_name}" because it has products assigned to it.')
           #     else:
            #        category.delete()
             #       messages.success(request, f'Category "{category_name}" deleted successfully!')
            #except Category.DoesNotExist:
             #   messages.error(request, 'Category not found.')
            #except Exception as e:
             #   messages.error(request, f'Error deleting category: {str(e)}')
        #else:
         #   messages.error(request, 'Category ID is required.')
    
    #return redirect('inventory:category_list')
@login_required
def delete_category(request):
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                category_name = category.name
                
                # Check if category has products
                if category.products.exists():
                    messages.error(request, f'Cannot delete category "{category_name}" because it has products assigned to it.')
                else:
                    category.delete()
                    messages.success(request, f'Category "{category_name}" deleted successfully!')
            except Category.DoesNotExist:
                messages.error(request, 'Category not found.')
            except Exception as e:
                messages.error(request, f'Error deleting category: {str(e)}')
        else:
            messages.error(request, 'Category ID is required.')
    else:
        messages.error(request, 'Invalid request method.')
    
    return redirect('inventory:category_list')

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    context = {
        'product': product,
    }
    return render(request, 'inventory/product_detail.html', context)

# Product Edit Form - Defined here in views.py
class ProductEditForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'generic_name', 'category', 'barcode', 'description',
            'cost_price', 'selling_price', 'quantity_in_stock', 
            'minimum_stock_level', 'batch_number', 'manufacture_date', 
            'expiry_date', 'supplier', 'image', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'required': True}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'required': True}),
            'quantity_in_stock': forms.NumberInput(attrs={'class': 'form-control', 'required': True}),
            'minimum_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'required': True}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacture_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'supplier': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default values
        if not self.instance.pk:  # Only for new products
            self.fields['is_active'].initial = True

@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductEditForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            updated_product = form.save()
            messages.success(request, f'Product "{updated_product.name}" has been updated successfully!')
            return redirect('inventory:product_detail', pk=updated_product.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductEditForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'inventory/product_edit.html', context)