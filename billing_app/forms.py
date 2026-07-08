from django import forms
from .models import Product, Customer, Bill, BillItem, Stock, Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }



class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'unit', 'price', 'quantity', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Price per unit'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Current stock'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Product description'}),
        }
        labels = {
            'unit': 'Unit of Measurement',
        }


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address', 'city']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
        }

class BillForm(forms.ModelForm):
    customer = forms.ModelChoiceField(
    queryset=Customer.objects.all(),
    empty_label="Search Customer...",
    widget=forms.Select(attrs={
        'class': 'form-control',
        'id': 'customer_select'
    })
)
    class Meta:
        model = Bill
        fields = ['customer', 'discount_percent', 'payment_method', 'payment_received']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'payment_received': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class BillItemForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        empty_label="-- Select Product --",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'product_select'
        })
    )
    class Meta:
        model = BillItem
        fields = ['product', 'quantity', 'item_discount']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control', 'id': 'product_select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'id': 'quantity_input'}),
            'item_discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'discount_input'}),
        }
        labels = {
            'product': 'Select Product',
            'quantity': 'Quantity',
            'item_discount': 'Discount (%)',
        }

class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['product', 'movement_type', 'quantity', 'unit', 'reason']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'movement_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Supplier delivery, Sale, Damage'}),
        }
        labels = {
            'unit': 'Unit',
        }