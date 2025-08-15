from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from inventory.models import Product
from decimal import Decimal


class Sale(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('card', 'Card'),
        ('credit', 'Credit'),
    ]

    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    sale_date = models.DateTimeField(auto_now_add=True)
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    customer_phone = models.CharField(max_length=15, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='cash')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    served_by = models.ForeignKey(User, on_delete=models.CASCADE)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    class Meta:
        ordering = ['-sale_date']
    
    def __str__(self):
        return f"Sale #{self.id} - KES {self.final_amount}"
    
    @property
    def total_cost_price(self):
        """Calculate total cost price for all items in this sale"""
        return sum(item.total_cost_price for item in self.items.all())
    
    @property
    def total_profit(self):
        """Calculate total profit for this sale"""
        return self.total_amount - self.total_cost_price
    
    def save(self, *args, **kwargs):
        self.final_amount = self.total_amount - self.discount
        super().save(*args, **kwargs)


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        self.unit_price = self.product.selling_price
        self.unit_cost = self.product.cost_price
        self.total_price = self.quantity * self.unit_price
        
        # Only reduce stock on create, not on update
        if not self.pk:  # Only on create
            if self.product.quantity_in_stock >= self.quantity:
                self.product.quantity_in_stock -= self.quantity
                self.product.save()
            else:
                raise ValueError(f"Insufficient stock for {self.product.name}")
        
        super().save(*args, **kwargs)
        
        # Update sale total amount
        self._update_sale_total()
    
    def _update_sale_total(self):
        """Update the sale's total amount when items change"""
        total = self.sale.items.aggregate(
            total=models.Sum('total_price')
        )['total'] or 0
        
        self.sale.total_amount = total
        self.sale.save()
    
    @property
    def total_cost_price(self):
        """Total cost price for this item"""
        return self.quantity * self.unit_cost
    
    @property
    def item_profit(self):
        """Profit for this item"""
        return self.total_price - self.total_cost_price
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} units"