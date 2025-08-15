from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .models import Sale, SaleItem

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer_name', 'customer_phone', 'payment_method', 'discount']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('customer_name', css_class='form-group col-md-6 mb-0'),
                Column('customer_phone', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('payment_method', css_class='form-group col-md-6 mb-0'),
                Column('discount', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', 'Process Sale', css_class='btn btn-success')
        )

class QuickSaleForm(forms.Form):
    """Form for quick product search and adding to cart"""
    product_search = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search products by name or barcode...',
            'class': 'form-control',
            'autocomplete': 'off'
        })
    )