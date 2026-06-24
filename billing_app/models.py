from django.db import models
from django.utils import timezone
from datetime import datetime

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Product(models.Model):
    CATEGORY_CHOICES = [
        ('cracker', 'Cracker'),
        ('sparklers', 'Sparklers'),
        ('fancy', 'Fancy'),
        ('bomb', 'Bomb'),
        ('fountain', 'Fountain'),
        ('other', 'Other'),
    ]
    
    UNIT_CHOICES = [
        ('packet', 'Packet'),
        ('piece', 'Piece'),
        ('box', 'Box'),
        ('case', 'Case'),
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece', help_text='Unit of measurement')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=0)  # Current stock
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_unit_display()}) - Stock: {self.quantity}"
    
    def is_low_stock(self):
        return self.quantity < 10

class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class Bill(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
    ]
    
    bill_number = models.CharField(max_length=30, unique=True, blank=True, null=True, editable=False)
    bill_sequence = models.PositiveIntegerField(default=1)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    bill_date = models.DateTimeField(auto_now_add=True)
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cash')
    payment_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    is_completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-bill_date']
    
    def __str__(self):
        return f"Bill {self.bill_number}"
    
    def save(self, *args, **kwargs):
        """Auto-generate bill number in format: 202605-01, 202605-02, etc."""
        
        if not self.bill_number:
            year_month = datetime.now().strftime("%Y%m")
            
            last_bill = Bill.objects.filter(
                bill_number__startswith=year_month
            ).order_by('-bill_sequence').first()
            
            if last_bill:
                next_sequence = last_bill.bill_sequence + 1
            else:
                next_sequence = 1
            
            self.bill_sequence = next_sequence
            self.bill_number = f"{year_month}-{next_sequence:02d}"
        
        super().save(*args, **kwargs)
    
    def calculate_total(self):
        """Calculate subtotal, discount, and total (without GST)"""
        self.subtotal = sum(item.item_total for item in self.billitem_set.all())
        self.discount_amount = (self.subtotal * self.discount_percent) / 100
        self.total_amount = self.subtotal - self.discount_amount
        self.change_amount = self.payment_received - self.total_amount
        self.save()
        return self.total_amount

class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=20, blank=True, null=True, help_text='Unit of this item')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    item_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    item_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        # Automatically get product price and unit
        self.unit_price = self.product.price
        self.unit = self.product.get_unit_display()

        # Calculate total
        subtotal = self.quantity * self.unit_price
        discount_amount = (subtotal * self.item_discount / 100)
        self.item_total = subtotal - discount_amount

        # Check if this is a new item (not being edited)
        if self.pk is None:
            # Check if enough stock available
            if self.product.quantity < self.quantity:
                raise ValueError(f'Insufficient stock! Available: {self.product.quantity} {self.unit}')
            
            # Decrease product stock
            self.product.quantity -= self.quantity
            self.product.save()
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Restore stock when item is deleted
        self.product.quantity += self.quantity
        self.product.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} ({self.unit})"

class Stock(models.Model):
    """Track stock movements"""
    MOVEMENT_CHOICES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
    ]
    
    UNIT_CHOICES = [
        ('packet', 'Packet'),
        ('piece', 'Piece'),
        ('box', 'Box'),
        ('case', 'Case'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_CHOICES)
    quantity = models.IntegerField()
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece', help_text='Unit of measurement')
    reason = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} ({self.get_unit_display()}) - {self.movement_type}: {self.quantity}"
    

    