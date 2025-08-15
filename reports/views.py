from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from sales.models import Sale, SaleItem
from inventory.models import Product, Category
from accounts.models import UserProfile
import json

# For PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

@login_required
def sales_report(request):
    """Enhanced sales report with filtering and financial calculations"""
    
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    payment_method = request.GET.get('payment_method', '')
    category = request.GET.get('category', '')
    customer_search = request.GET.get('customer_search', '')
    invoice_search = request.GET.get('invoice_search', '')
    
    # Set default date range (last 30 days)
    if not start_date:
        start_date = timezone.now().date() - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Build query filters
    filters = Q(sale_date__date__range=[start_date, end_date])
    
    if payment_method:
        filters &= Q(payment_method=payment_method)
    
    if customer_search:
        filters &= Q(customer_name__icontains=customer_search)
    
    if invoice_search:
        filters &= Q(invoice_number__icontains=invoice_search)
    
    if category:
        filters &= Q(items__product__category__name=category)
    
    # Get sales with filters
    sales = Sale.objects.filter(filters).select_related('served_by').prefetch_related('items__product').distinct()
    
    # Financial calculations
    financial_data = sales.aggregate(
        total_sales=Sum('total_amount'),
        total_subtotal=Sum('subtotal'),
        #total_tax=Sum('tax_amount'),
        total_discount=Sum('discount'),
        average_sale=Avg('total_amount'),
        total_transactions=Count('id')
    )
    
    # Calculate total profit
    total_cost = sum(sale.total_cost_price for sale in sales)
    total_profit = (financial_data['total_subtotal'] or 0) - total_cost
    profit_margin = (total_profit / total_cost * 100) if total_cost > 0 else 0
    
    # Top selling products
    top_products = SaleItem.objects.filter(
        sale__sale_date__date__range=[start_date, end_date]
    ).values(
        'product__name', 'product__category__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_quantity')[:10]
    
    # Top selling categories
    top_categories = SaleItem.objects.filter(
        sale__sale_date__date__range=[start_date, end_date]
    ).values(
        'product__category__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price'),
        product_count=Count('product', distinct=True)
    ).order_by('-total_revenue')[:10]
    
    # Payment method breakdown
    payment_breakdown = sales.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('-total')
    
    # Low stock alerts
    low_stock_products = Product.objects.filter(
        quantity_in_stock__lte=F('minimum_stock_level'),
        is_active=True
    )
    
    # Get all categories and payment methods for filters
    all_categories = Category.objects.all()
    payment_methods = Sale.PAYMENT_METHODS
    
    context = {
        'sales': sales,
        'financial_data': financial_data,
        'total_profit': total_profit,
        'profit_margin': profit_margin,
        'top_products': top_products,
        'top_categories': top_categories,
        'payment_breakdown': payment_breakdown,
        'low_stock_products': low_stock_products,
        'start_date': start_date,
        'end_date': end_date,
        'all_categories': all_categories,
        'payment_methods': payment_methods,
        'filters': {
            'payment_method': payment_method,
            'category': category,
            'customer_search': customer_search,
            'invoice_search': invoice_search,
        }
    }
    
    return render(request, 'reports/sales_report.html', context)

@login_required
def generate_pdf_report(request):
    """Generate PDF report"""
    
    # Get same data as sales_report
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = timezone.now().date() - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    sales = Sale.objects.filter(
        sale_date__date__range=[start_date, end_date]
    ).select_related('served_by')
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    # Add title
    title = Paragraph("Eldoret Chemist - Sales Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Add date range
    date_range = Paragraph(f"Period: {start_date} to {end_date}", styles['Normal'])
    elements.append(date_range)
    elements.append(Spacer(1, 12))
    
    # Financial summary
    financial_data = sales.aggregate(
        total_sales=Sum('total_amount'),
        total_subtotal=Sum('subtotal'),
        #total_tax=Sum('tax_amount'),
        total_transactions=Count('id')
    )
    
    summary_data = [
        ['Financial Summary', ''],
        ['Total Sales', f"KES {financial_data['total_sales'] or 0:,.2f}"],
        ['Subtotal', f"KES {financial_data['total_subtotal'] or 0:,.2f}"],
        ['Tax Amount', f"KES {financial_data['total_tax'] or 0:,.2f}"],
        ['Total Transactions', str(financial_data['total_transactions'] or 0)],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 12))
    
    # Sales details table
    if sales.exists():
        sales_data = [['Date', 'Invoice #', 'Customer', 'Payment Method', 'Total']]
        
        for sale in sales[:50]:  # Limit to first 50 for PDF
            sales_data.append([
                sale.sale_date.strftime('%Y-%m-%d'),
                sale.invoice_number or f"#{sale.id}",
                sale.customer_name or 'Walk-in Customer',
                sale.get_payment_method_display(),
                f"KES {sale.total_amount:,.2f}"
            ])
        
        sales_table = Table(sales_data, colWidths=[1.5*inch, 1.5*inch, 2*inch, 1.5*inch, 1.5*inch])
        sales_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(sales_table)
    
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date}_to_{end_date}.pdf"'
    
    return response

@login_required
def dashboard_api(request):
    """API endpoint for dashboard data"""
    today = timezone.now().date()
    
    # Today's sales
    today_sales = Sale.objects.filter(sale_date__date=today).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # This month's sales
    month_start = today.replace(day=1)
    month_sales = Sale.objects.filter(sale_date__date__gte=month_start).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Low stock count
    low_stock_count = Product.objects.filter(
        quantity_in_stock__lte=F('minimum_stock_level'),
        is_active=True
    ).count()
    
    # Recent sales
    recent_sales = Sale.objects.select_related('served_by')[:5]
    recent_sales_data = []
    
    for sale in recent_sales:
        recent_sales_data.append({
            'id': sale.id,
            'invoice_number': sale.invoice_number or f"#{sale.id}",
            'customer_name': sale.customer_name or 'Walk-in Customer',
            'total_amount': str(sale.total_amount),
            'payment_method': sale.get_payment_method_display(),
            'date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
            'served_by': sale.served_by.get_full_name() or sale.served_by.username
        })
    
    data = {
        'today_sales': {
            'total': str(today_sales['total'] or 0),
            'count': today_sales['count'] or 0
        },
        'month_sales': {
            'total': str(month_sales['total'] or 0),
            'count': month_sales['count'] or 0
        },
        'low_stock_count': low_stock_count,
        'recent_sales': recent_sales_data
    }
    
    return JsonResponse(data)

@login_required
def stock_report(request):
    """Enhanced stock report with alerts"""
    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')
    
    # Stock alerts
    low_stock = products.filter(quantity_in_stock__lte=F('minimum_stock_level'))
    expired = products.filter(expiry_date__lt=timezone.now().date())
    expiring_soon = products.filter(
        expiry_date__gte=timezone.now().date(),
        expiry_date__lte=timezone.now().date() + timedelta(days=30)
    )
    
    # Stock value calculation
    total_stock_value = products.aggregate(
        cost_value=Sum(F('quantity_in_stock') * F('cost_price')),
        selling_value=Sum(F('quantity_in_stock') * F('selling_price'))
    )
    
    context = {
        'products': products,
        'low_stock': low_stock,
        'expired': expired,
        'expiring_soon': expiring_soon,
        'total_stock_value': total_stock_value,
        'low_stock_count': low_stock.count(),
        'expired_count': expired.count(),
        'expiring_soon_count': expiring_soon.count(),
    }
    
    return render(request, 'reports/stock_report.html', context)