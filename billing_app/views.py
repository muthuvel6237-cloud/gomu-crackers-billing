from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db import models
from django.utils import timezone
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import tempfile
import urllib.request
from .models import Product, Customer, Bill, BillItem, Stock, Category
from .forms import ProductForm, CustomerForm, BillForm, BillItemForm, StockForm, CategoryForm


# ========== DASHBOARD ==========
def dashboard(request):
    total_bills = Bill.objects.count()
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()
    total_stock_movements = Stock.objects.count()
    
    today_revenue = Bill.objects.filter(bill_date__date=timezone.now().date()).aggregate(
        total=models.Sum('total_amount'))['total'] or 0
    
    recent_bills = Bill.objects.all()[:5]
    low_stock_products = Product.objects.filter(quantity__lt=10)
    
    context = {
        'total_bills': total_bills,
        'total_customers': total_customers,
        'total_products': total_products,
        'total_stock_movements': total_stock_movements,
        'today_revenue': today_revenue,
        'recent_bills': recent_bills,
        'low_stock_count': low_stock_products.count(),
    }
    return render(request, 'billing/dashboard.html', context)

# ========== PRODUCT MANAGEMENT ==========
def product_list(request):
    products = Product.objects.all()
    return render(request, 'billing/product_list.html', {'products': products})

def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'billing/product_form.html', {'form': form, 'title': 'Add Product'})

def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'billing/product_form.html', {'form': form, 'title': 'Edit Product'})

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('product_list')
    return render(request, 'billing/confirm_delete.html', {'object': product})

# ========== CUSTOMER MANAGEMENT ==========
def customer_list(request):
    customers = Customer.objects.all()
    return render(request, 'billing/customer_list.html', {'customers': customers})

def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer added successfully!')
            return redirect('customer_list')
    else:
        form = CustomerForm()
    return render(request, 'billing/customer_form.html', {'form': form, 'title': 'Add Customer'})

def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated successfully!')
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'billing/customer_form.html', {'form': form, 'title': 'Edit Customer'})

def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Customer deleted successfully!')
        return redirect('customer_list')
    return render(request, 'billing/confirm_delete.html', {'object': customer})

# ========== STOCK MANAGEMENT ==========
def stock_list(request):
    stocks = Stock.objects.all()
    low_stock = Product.objects.filter(quantity__lt=10)
    context = {
        'stocks': stocks,
        'low_stock_count': low_stock.count(),
    }
    return render(request, 'billing/stock_list.html', context)

def stock_create(request):
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Stock added successfully!')
                return redirect('stock_list')
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = StockForm()
    return render(request, 'billing/stock_form.html', {'form': form, 'title': 'Add Stock'})

def stock_update(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stock updated!')
            return redirect('stock_list')
    else:
        form = StockForm(instance=stock)
    return render(request, 'billing/stock_form.html', {'form': form, 'title': 'Edit Stock'})

def stock_delete(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == 'POST':
        stock.delete()
        messages.success(request, 'Stock deleted!')
        return redirect('stock_list')
    return render(request, 'billing/confirm_delete.html', {'object': stock})

# ========== BILL MANAGEMENT ==========
def bill_list(request):
    bills = Bill.objects.all()
    return render(request, 'billing/bill_list.html', {'bills': bills})

def bill_create(request):
    if request.method == 'POST':
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.save()
            return redirect('bill_items', pk=bill.pk)
    else:
        form = BillForm()
    return render(request, 'billing/bill_form.html', {'form': form})

def bill_items(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    if request.method == 'POST':
        form = BillItemForm(request.POST)
        if form.is_valid():
            try:
                item = form.save(commit=False)
                item.bill = bill
                item.save()
                bill.calculate_total()
                messages.success(request, f'{item.product.name} added to bill!')
                return redirect('bill_items', pk=pk)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = BillItemForm()
    
    items = bill.billitem_set.all()
    products = Product.objects.all()
    
    context = {
        'bill': bill, 
        'form': form, 
        'items': items,
        'products': products
    }
    return render(request, 'billing/bill_items.html', context)
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

def delete_bill(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    bill.delete()
    messages.success(request, "Bill deleted successfully!")
    return redirect('bill_list')

def bill_finalize(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    bill.calculate_total()
    bill.is_completed = True
    bill.save()
    messages.success(request, 'Bill completed!')
    return redirect('bill_detail', pk=pk)

def bill_detail(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    bill.calculate_total()
    context = {'bill': bill}
    return render(request, 'billing/bill_detail.html', context)

# ========== PDF GENERATION ==========
def add_page_border(canvas, doc):
    """Add border to PDF pages"""
    canvas.setLineWidth(1)
    canvas.rect(20, 20, doc.pagesize[0] - 40, doc.pagesize[1] - 40)

def fixed_footer(canvas, doc):
    """Add fixed footer at bottom of each page"""
    canvas.saveState()

    width, height = A4

    # FULL PAGE MARGIN BORDER
    canvas.rect(
        30,          # left margin
        30,          # bottom margin
        width - 60,  # page width
        height - 60, # page height
        stroke=1,
        fill=0
    )  
     # HORIZONTAL LINE ABOVE FOOTER
    canvas.line(
        35,   # start x
        125,  # y position
        width - 35,  # end x
        125
    )


    # FOOTER AT BOTTOM
    canvas.setFont("Helvetica", 9)

    # Left side - Terms
    canvas.drawString(40, 110, "Terms & Conditions:")
    canvas.drawString(40, 95, "Goods once sold will not be taken back.")
    canvas.drawString(40, 80, "Payment must be made within due date.")

    # Right side - Company info
    canvas.drawRightString(width - 40, 110, "For GOMU CRACKERS")
    canvas.drawRightString(width - 40, 70, "Authorised Signature")

    # Center - Thank you (moved up slightly)
    canvas.drawCentredString(width / 2, 50, "Thank You! Visit Again")

    canvas.restoreState()

def generate_bill_pdf(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    bill.calculate_total()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=100,  # INCREASED to accommodate footer
    )
    
    page_width, page_height = A4
    usable_width = page_width - 80   # 40 left + 40 right

    story = []
    styles = getSampleStyleSheet()
    
    # ===== STYLES =====
    shop_style = ParagraphStyle(
        'ShopStyle',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        textColor=colors.black,
    )

    small_style = ParagraphStyle(
        'SmallStyle',
        parent=styles['Normal'],     
        fontSize=10,
        leading=14,
    )

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=11,
    )

    # ===== LOGO =====
    logo_url = "https://i.ibb.co/TMwkDcp6/gomu1.jpg"

    try:
        temp_logo = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        urllib.request.urlretrieve(logo_url, temp_logo.name)
        logo = Image(temp_logo.name, width=1.2 * inch, height=1.2 * inch)
    except:
        logo = Paragraph("GOMU CRACKERS", small_style)

    # ===== HEADER SECTION =====
    shop_details = [
        Paragraph("<b>GOMU CRACKERS</b>", shop_style),
        Paragraph("Sivakasi - 626189", small_style),
        Paragraph("Phone : +91 7550038974", small_style),
        Paragraph("Email : gomucrackers@gmail.com", small_style),
    ]

    invoice_details = Paragraph(f"""
        <b>ESTIMATE</b><br/><br/>
        <b>Bill No:</b> {bill.bill_number}<br/>
        <b>Date:</b> {bill.bill_date.strftime('%d-%m-%Y')}
    """, small_style)

    header_table = Table(
        [[logo, shop_details, "", invoice_details]],
        colWidths=[
            1.4 * inch,
            3.5 * inch,
            0.25 * inch,
            2.0 * inch
        ]
    )

    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBEFORE', (3, 0), (3, 0), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))

    story.append(header_table)

    # Horizontal line
    story.append(Table([[""]], colWidths=[7.2 * inch], rowHeights=[1]))
    story[-1].setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 1, colors.black),
    ]))

    story.append(Spacer(1, 0.2 * inch))

    # ===== CUSTOMER DETAILS =====
    customer_name = bill.customer.name if bill.customer else "Walk-in Customer"
    customer_phone = bill.customer.phone if bill.customer else "N/A"

    customer_text = f"""
        <b>BILL TO:</b><br/>
        <b>{customer_name}</b><br/>
        Phone: {customer_phone}
    """

    story.append(Paragraph(customer_text, small_style))
    story.append(Spacer(1, 0.25 * inch))

    # ===== PRODUCT TABLE =====
    data = [['S.No', 'Product', 'Unit', 'Qty', 'Rate', 'Amount']]

    items = bill.billitem_set.all()

    for i, item in enumerate(items, start=1):
        # CALCULATE AMOUNT FIRST
        item_total_before_discount = item.quantity * item.unit_price
        discount = item.item_discount or 0
        discount_amount = item_total_before_discount * discount / 100
        final_amount = item_total_before_discount - discount_amount

        # THEN APPEND WITH CORRECT AMOUNT
        data.append([
            str(i),
            item.product.name,
            item.unit,
            str(item.quantity),
            f"{item.unit_price:.2f}",
            f"{final_amount:.2f}"  # NOW CORRECT
        ])

    product_table = Table(data, colWidths=[
        0.6 * inch,
        3.0 * inch,
        0.7 * inch,
        0.9 * inch,
        0.9 * inch,
        1 * inch
    ])

    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.7, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    product_table.hAlign = 'LEFT'
    story.append(product_table)
    story.append(Spacer(1, 0.15 * inch))

    # ===== TOTAL TABLE =====
    subtotal = 0
    total_discount_amount = 0

    for item in bill.billitem_set.all():
        item_total = item.quantity * item.unit_price
        item_discount = item_total * (item.item_discount or 0) / 100

        subtotal += item_total
        total_discount_amount += item_discount

    bill_discount = bill.discount_amount if bill.discount_percent > 0 else 0
    grand_total = subtotal - total_discount_amount - bill_discount

    totals = [['Goods Value', f"{subtotal:.2f}"]]
    
    if total_discount_amount > 0:
        totals.append(['Item Discounts', f"-{total_discount_amount:.2f}"])
    
    if bill.discount_percent > 0:
        discount_label = f"Bill Discount ({bill.discount_percent:.0f}%)"
        totals.append([discount_label, f"-{bill_discount:.2f}"])
    
    totals.append(['Grand Total', f"{grand_total:.2f}"])

    total_table = Table(totals, colWidths=[1.5 * inch, 1.0 * inch])

    total_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.7, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFD700')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    total_table.hAlign = 'RIGHT'
    story.append(total_table)
    story.append(Spacer(1, 0.3 * inch))

    # ===== FOOTER TABLE =====


    # ===== BUILD PDF (ONLY ONCE) =====
    doc.build(
        story,
        onFirstPage=fixed_footer,
        onLaterPages=fixed_footer
    )

    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Bill_{bill.bill_number}.pdf"'

    return response
# ========== API ENDPOINTS ==========
def get_product_price(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        return JsonResponse({
            'price': float(product.price),
            'unit': product.get_unit_display(),
            'quantity': product.quantity
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
