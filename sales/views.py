import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, F
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import Sale, SaleItem
from inventory.models import Product, Category
from .forms import SaleForm
# Add these imports to your existing views.py
from .models import MpesaTransaction
#from .mpesa_service import MpesaService
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

@login_required
def create_sale(request):
    """Traditional form-based sale creation"""
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    sale = form.save(commit=False)
                    sale.served_by = request.user
                    sale.save()
                    
                    # Handle sale items from form data
                    # This assumes your form handles items in a specific way
                    # You might need to adjust this based on your form structure
                    
                    messages.success(request, f'Sale #{sale.id} created successfully!')
                    return redirect('sales:sale_detail', sale_id=sale.id)
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SaleForm()
    
    products = Product.objects.filter(
        is_active=True, 
        quantity_in_stock__gt=0
    ).select_related('category')
    
    context = {
        'form': form,
        'products': products,
        'payment_methods': Sale.PAYMENT_METHODS,
    }
    
    return render(request, 'sales/create_sale.html', context)




@login_required
def pos_system(request):
    """Enhanced Point of Sale System"""
    products = Product.objects.filter(
        is_active=True, 
        quantity_in_stock__gt=0
    ).select_related('category', 'supplier')
    
    categories = Category.objects.all()
    
    # Low stock alerts for POS
    low_stock_products = Product.objects.filter(
        quantity_in_stock__lte=F('minimum_stock_level'),
        is_active=True
    )
    
    context = {
        'products': products,
        'categories': categories,
        'low_stock_products': low_stock_products,
        'payment_methods': Sale.PAYMENT_METHODS,
    }
    
    return render(request, 'sales/pos.html', context)

@login_required
def search_products_api(request):
    """Enhanced API endpoint for product search in POS"""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    
    products_query = Product.objects.filter(
        is_active=True,
        quantity_in_stock__gt=0
    )
    
    if query:
        products_query = products_query.filter(
            Q(name__icontains=query) | 
            Q(barcode__icontains=query) |
            Q(generic_name__icontains=query)
        )
    
    if category_id:
        products_query = products_query.filter(category_id=category_id)
    
    products = products_query.select_related('category')[:20]
    
    data = [{
        'id': p.id,
        'name': p.name,
        'generic_name': p.generic_name or '',
        'price': str(p.selling_price),
        'cost_price': str(p.cost_price),
        'stock': p.quantity_in_stock,
        'barcode': p.barcode or '',
        'category': p.category.name,
        'is_low_stock': p.is_low_stock,
        'profit_margin': str(p.profit_margin),
    } for p in products]
    
    return JsonResponse({'products': data})

@login_required
@require_http_methods(["POST"])
def process_sale(request):
    """Enhanced sale processing with better financial calculations"""
    try:
        # Parse JSON data from request
        data = json.loads(request.body)
        
        # Extract data
        items = data.get('items', [])
        customer_name = data.get('customer_name', 'Walk-in Customer')
        customer_phone = data.get('customer_phone', '')
        payment_method = data.get('payment_method', 'cash')
        discount = Decimal(str(data.get('discount', 0)))
        notes = data.get('notes', '')
        
        if not items:
            return JsonResponse({
                'success': False,
                'message': 'No items in cart'
            })
        
        # Calculate totals and validate items
        subtotal = Decimal('0')
        sale_items_data = []
        
        for item in items:
            try:
                product = Product.objects.get(id=item['id'], is_active=True)
                quantity = int(item['quantity'])
                
                # Check stock availability
                if quantity > product.quantity_in_stock:
                    return JsonResponse({
                        'success': False,
                        'message': f'Insufficient stock for {product.name}. Available: {product.quantity_in_stock}'
                    })
                
                item_total = product.selling_price * quantity
                subtotal += item_total
                
                sale_items_data.append({
                    'product': product,
                    'quantity': quantity,
                    'unit_price': product.selling_price,
                    'unit_cost': product.cost_price,
                    'total_price': item_total
                })
                
            except Product.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f'Product not found: {item.get("name", "Unknown")}'
                })
        
        # Create sale with transaction to ensure data consistency
        with transaction.atomic():
            # Create the sale record
            sale = Sale.objects.create(
                customer_name=customer_name,
                customer_phone=customer_phone,
                payment_method=payment_method,
                total_amount=subtotal,
                discount=discount,
                served_by=request.user,
                status='paid'
            )
            
            # Create sale items and update stock
            for item_data in sale_items_data:
                SaleItem.objects.create(
                    sale=sale,
                    product=item_data['product'],
                    quantity=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    unit_cost=item_data['unit_cost'],
                )
        
        # Prepare response data for receipt
        response_data = {
            'success': True,
            'message': 'Sale processed successfully',
            'sale': {
                'id': sale.id,
                'date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
                'customer_name': sale.customer_name,
                'customer_phone': sale.customer_phone,
                'payment_method': sale.get_payment_method_display(),
                'total_amount': str(sale.total_amount),
                'discount': str(sale.discount),
                'final_amount': str(sale.final_amount),
                'served_by': sale.served_by.get_full_name() or sale.served_by.username,
                'items': [
                    {
                        'name': item_data['product'].name,
                        'quantity': item_data['quantity'],
                        'unit_price': str(item_data['unit_price']),
                        'total_price': str(item_data['total_price'])
                    }
                    for item_data in sale_items_data
                ]
            }
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing sale: {str(e)}'
        })

@login_required
def sales_history(request):
    """Enhanced sales history with filtering"""
    
    # Get filter parameters
    search = request.GET.get('search', '')
    payment_method = request.GET.get('payment_method', '')
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build query
    sales_query = Sale.objects.select_related('served_by').prefetch_related('items__product')
    
    # Apply filters
    if search:
        sales_query = sales_query.filter(
            Q(customer_name__icontains=search) |
            Q(customer_phone__icontains=search) |
            Q(id__icontains=search)
        )
    
    if payment_method:
        sales_query = sales_query.filter(payment_method=payment_method)
    
    if status:
        sales_query = sales_query.filter(status=status)
    
    if date_from:
        sales_query = sales_query.filter(sale_date__date__gte=date_from)
    
    if date_to:
        sales_query = sales_query.filter(sale_date__date__lte=date_to)
    
    sales = sales_query.order_by('-sale_date')
    
    # Calculate totals for filtered results
    totals = sales.aggregate(
        total_amount=Sum('final_amount'),
        total_discount=Sum('discount'),
        count=Sum('id')
    )
    
    context = {
        'sales': sales,
        'totals': totals,
        'payment_methods': Sale.PAYMENT_METHODS,
        'status_choices': Sale.STATUS_CHOICES,
        'filters': {
            'search': search,
            'payment_method': payment_method,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'sales/sales_history.html', context)

@login_required
def sale_detail(request, sale_id):
    """View individual sale details"""
    sale = get_object_or_404(
        Sale.objects.select_related('served_by').prefetch_related('items__product'),
        id=sale_id
    )
    
    context = {
        'sale': sale,
        'items': sale.items.all(),
        'can_refund': sale.status == 'paid' and request.user.has_perm('sales.change_sale')
    }
    
    return render(request, 'sales/sale_detail.html', context)

@login_required
@require_http_methods(["POST"])
def refund_sale(request, sale_id):
    """Process sale refund"""
    if not request.user.has_perm('sales.change_sale'):
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to process refunds'
        })
    
    sale = get_object_or_404(Sale, id=sale_id)
    
    if sale.status != 'paid':
        return JsonResponse({
            'success': False,
            'message': 'Only paid sales can be refunded'
        })
    
    try:
        with transaction.atomic():
            # Restore stock for all items
            for item in sale.items.all():
                item.product.quantity_in_stock += item.quantity
                item.product.save()
            
            # Update sale status
            sale.status = 'refunded'
            sale.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Sale #{sale.id} has been refunded successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing refund: {str(e)}'
        })

@login_required
def get_sale_receipt_data(request, sale_id):
    """Get sale data for receipt printing"""
    sale = get_object_or_404(
        Sale.objects.select_related('served_by').prefetch_related('items__product'),
        id=sale_id
    )
    
    items_data = []
    for item in sale.items.all():
        items_data.append({
            'name': item.product.name,
            'quantity': item.quantity,
            'unit_price': str(item.unit_price),
            'total_price': str(item.total_price)
        })
    
    receipt_data = {
        'sale': {
            'id': sale.id,
            'date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
            'customer_name': sale.customer_name or 'Walk-in Customer',
            'customer_phone': sale.customer_phone or '',
            'payment_method': sale.get_payment_method_display(),
            'total_amount': str(sale.total_amount),
            'discount': str(sale.discount),
            'final_amount': str(sale.final_amount),
            'served_by': sale.served_by.get_full_name() or sale.served_by.username,
            'status': sale.get_status_display(),
        },
        'items': items_data
    }
    
    return JsonResponse(receipt_data)

@login_required
def categories_api(request):
    """API endpoint to get categories for filtering"""
    categories = Category.objects.all().values('id', 'name')
    return JsonResponse({'categories': list(categories)})

@login_required 
def daily_sales_summary(request):
    """Get daily sales summary for dashboard"""
    today = timezone.now().date()
    
    # Today's sales by hour
    from django.db.models import Count
    from django.db.models.functions import TruncHour
    
    hourly_sales = Sale.objects.filter(
        sale_date__date=today
    ).annotate(
        hour=TruncHour('sale_date')
    ).values('hour').annotate(
        total_sales=Sum('final_amount'),
        transaction_count=Count('id')
    ).order_by('hour')
    
    # Payment method breakdown for today
    payment_breakdown = Sale.objects.filter(
        sale_date__date=today
    ).values('payment_method').annotate(
        count=Count('id'),
        total=Sum('final_amount')
    )
    
    # Top selling products today
    top_products_today = SaleItem.objects.filter(
        sale__sale_date__date=today
    ).values(
        'product__name'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum('total_price')
    ).order_by('-quantity_sold')[:5]
    
    data = {
        'hourly_sales': list(hourly_sales),
        'payment_breakdown': list(payment_breakdown),
        'top_products_today': list(top_products_today)
    }
    
    return JsonResponse(data)




# Add these 3 new views to your views.py

# Add these imports at the top of your views.py
import requests
import base64
from datetime import datetime
import json
from decimal import Decimal
from django.db import transaction
from django.http import HttpResponse

def check_payment_status(request, sale_id):
    # Implement your logic here
    return HttpResponse(f"Checking payment status for sale ID: {sale_id}")

# Add MpesaService class
class MpesaService:
    def get_access_token(self):
        url = f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
        credentials = f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {'Authorization': f'Basic {encoded_credentials}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json().get('access_token')
            return None
        except:
            return None
    
    def initiate_stk_push(self, phone, amount, account_reference):
        token = self.get_access_token()
        if not token:
            return {'success': False, 'message': 'Failed to get token'}
        
        # Format phone
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('7'):
            phone = '254' + phone
        
        # Generate password
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{settings.MPESA_BUSINESS_SHORT_CODE}{settings.MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        
        url = f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest"
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        
        payload = {
            "BusinessShortCode": settings.MPESA_BUSINESS_SHORT_CODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone,
            "PartyB": settings.MPESA_BUSINESS_SHORT_CODE,
            "PhoneNumber": phone,
            "CallBackURL": "https://httpbin.org/post",  # Temporary
            "AccountReference": account_reference,
            "TransactionDesc": "POS Payment"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            if response.status_code == 200 and data.get('ResponseCode') == '0':
                return {'success': True, 'checkout_request_id': data.get('CheckoutRequestID')}
            else:
                return {'success': False, 'message': data.get('errorMessage', 'STK push failed')}
        except Exception as e:
            return {'success': False, 'message': f'Error: {str(e)}'}

# Add M-Pesa views
@login_required
@require_http_methods(["POST"])
def initiate_mpesa_payment(request):
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        amount = Decimal(str(data.get('amount')))
        
        if not phone_number or amount <= 0:
            return JsonResponse({'success': False, 'message': 'Invalid phone or amount'})
        
        mpesa_service = MpesaService()
        result = mpesa_service.initiate_stk_push(phone_number, amount, f"TEST{int(amount)}")
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})