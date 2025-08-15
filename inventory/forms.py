from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, HTML, Div
from .models import Product, Category, Supplier, Purchase, PurchaseItem

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'generic_name', 'category', 'supplier', 'description',
            'cost_price', 'selling_price', 'quantity_in_stock', 
            'minimum_stock_level', 'batch_number', 'manufacture_date',
            'expiry_date', 'barcode', 'image'
        ]
        widgets = {
            'manufacture_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('generic_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('category', css_class='form-group col-md-4 mb-0'),
                Column('supplier', css_class='form-group col-md-4 mb-0'),
                Column('barcode', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'description',
            Row(
                Column('cost_price', css_class='form-group col-md-4 mb-0'),
                Column('selling_price', css_class='form-group col-md-4 mb-0'),
                Column('quantity_in_stock', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('minimum_stock_level', css_class='form-group col-md-6 mb-0'),
                Column('batch_number', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('manufacture_date', css_class='form-group col-md-6 mb-0'),
                Column('expiry_date', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'image',
            Submit('submit', 'Save Product', css_class='btn btn-primary')
        )

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            'description',
            Submit('submit', 'Save Category', css_class='btn btn-primary')
        )

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('contact_person', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('phone', css_class='form-group col-md-6 mb-0'),
                Column('email', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'address',
            Submit('submit', 'Save Supplier', css_class='btn btn-primary')
        )

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'invoice_number', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('supplier', css_class='form-group col-md-6 mb-0'),
                Column('invoice_number', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'notes',
            Submit('submit', 'Create Purchase', css_class='btn btn-primary')
        )

# Add this to your inventory/forms.py file

