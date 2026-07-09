from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import datetime
from decimal import Decimal, InvalidOperation
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import tempfile
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from .models import Product, Customer, Bill, BillItem, Stock, Category
from .forms import ProductForm, ProductImportForm, CustomerForm, BillForm, BillItemForm, StockForm, CategoryForm


XLSX_NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'office_rel': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}

HEADER_ALIASES = {
    'name': 'name',
    'product': 'name',
    'product name': 'name',
    'item': 'name',
    'item name': 'name',
    'description': 'description',
    'details': 'description',
    'category': 'category',
    'type': 'category',
    'unit': 'unit',
    'uom': 'unit',
    'price': 'price',
    'rate': 'price',
    'mrp': 'price',
    'amount': 'price',
    'selling price': 'price',
    'quantity': 'quantity',
    'qty': 'quantity',
    'stock': 'quantity',
    'opening stock': 'quantity',
}


def column_index_from_ref(cell_ref):
    letters = ''.join(char for char in cell_ref if char.isalpha())
    index = 0
    for letter in letters:
        index = index * 26 + (ord(letter.upper()) - ord('A') + 1)
    return index - 1


def column_letter(index):
    result = ''
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def normalize_header(value):
    header = ' '.join(str(value).strip().lower().replace('_', ' ').split())
    return HEADER_ALIASES.get(header, header)


def first_sheet_path(workbook_zip):
    workbook_root = ET.fromstring(workbook_zip.read('xl/workbook.xml'))
    first_sheet = workbook_root.find('main:sheets/main:sheet', XLSX_NS)
    if first_sheet is None:
        return 'xl/worksheets/sheet1.xml'

    relationship_id = first_sheet.attrib.get(f'{{{XLSX_NS["office_rel"]}}}id')
    if not relationship_id:
        return 'xl/worksheets/sheet1.xml'

    rels_root = ET.fromstring(workbook_zip.read('xl/_rels/workbook.xml.rels'))
    for relationship in rels_root.findall('rel:Relationship', XLSX_NS):
        if relationship.attrib.get('Id') == relationship_id:
            target = relationship.attrib.get('Target', 'worksheets/sheet1.xml')
            return 'xl/' + target.lstrip('/')

    return 'xl/worksheets/sheet1.xml'


def read_product_xlsx(upload):
    with zipfile.ZipFile(upload) as workbook_zip:
        shared_strings = []
        if 'xl/sharedStrings.xml' in workbook_zip.namelist():
            shared_root = ET.fromstring(workbook_zip.read('xl/sharedStrings.xml'))
            for item in shared_root.findall('main:si', XLSX_NS):
                text_parts = [node.text or '' for node in item.findall('.//main:t', XLSX_NS)]
                shared_strings.append(''.join(text_parts))

        sheet_root = ET.fromstring(workbook_zip.read(first_sheet_path(workbook_zip)))
        rows = []
        for row_node in sheet_root.findall('.//main:sheetData/main:row', XLSX_NS):
            row_values = []
            for cell in row_node.findall('main:c', XLSX_NS):
                cell_ref = cell.attrib.get('r', '')
                cell_index = column_index_from_ref(cell_ref)
                while len(row_values) <= cell_index:
                    row_values.append('')

                cell_type = cell.attrib.get('t')
                value_node = cell.find('main:v', XLSX_NS)
                inline_node = cell.find('main:is/main:t', XLSX_NS)

                if cell_type == 's' and value_node is not None:
                    value_index = int(value_node.text or 0)
                    value = shared_strings[value_index] if value_index < len(shared_strings) else ''
                elif cell_type == 'inlineStr' and inline_node is not None:
                    value = inline_node.text or ''
                elif value_node is not None:
                    value = value_node.text or ''
                else:
                    value = ''

                row_values[cell_index] = value
            rows.append(row_values)

    if not rows:
        return []

    header_index = None
    headers = []
    for index, row in enumerate(rows[:10]):
        normalized_headers = [normalize_header(value) for value in row]
        if 'name' in normalized_headers and 'price' in normalized_headers:
            header_index = index
            headers = normalized_headers
            break

    if header_index is None:
        return []

    products = []
    for row in rows[header_index + 1:]:
        if not any(str(value).strip() for value in row):
            continue
        products.append({
            headers[index]: str(value).strip()
            for index, value in enumerate(row)
            if index < len(headers) and headers[index]
        })
    return products


def build_xlsx(rows):
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row):
            ref = f'{column_letter(col_index)}{row_index}'
            if isinstance(value, (int, float, Decimal)):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                cells.append(
                    f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
                )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheetData>
    {''.join(sheet_rows)}
  </sheetData>
</worksheet>'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
    workbook_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Products" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>'''

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as workbook_zip:
        workbook_zip.writestr('[Content_Types].xml', content_types)
        workbook_zip.writestr('_rels/.rels', root_rels)
        workbook_zip.writestr('xl/workbook.xml', workbook_xml)
        workbook_zip.writestr('xl/_rels/workbook.xml.rels', workbook_rels)
        workbook_zip.writestr('xl/worksheets/sheet1.xml', sheet_xml)
    buffer.seek(0)
    return buffer


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
    search_query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    stock_filter = request.GET.get('stock', '').strip()

    if search_query:
        products = products.filter(
            models.Q(name__icontains=search_query) |
            models.Q(description__icontains=search_query)
        )

    if category_filter:
        products = products.filter(category=category_filter)

    if stock_filter == 'in_stock':
        products = products.filter(quantity__gt=10)
    elif stock_filter == 'low_stock':
        products = products.filter(quantity__gt=0, quantity__lte=10)
    elif stock_filter == 'out_of_stock':
        products = products.filter(quantity__lte=0)
    elif stock_filter == 'attention':
        products = products.filter(quantity__lte=10)

    product_count = products.count()
    total_quantity = products.aggregate(total=models.Sum('quantity'))['total'] or 0
    stock_value = sum(product.price * product.quantity for product in products)
    low_stock_count = products.filter(quantity__gt=0, quantity__lte=10).count()
    out_of_stock_count = products.filter(quantity__lte=0).count()

    context = {
        'products': products,
        'category_choices': Product.CATEGORY_CHOICES,
        'search_query': search_query,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
        'product_count': product_count,
        'total_quantity': total_quantity,
        'stock_value': stock_value,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
    }
    return render(request, 'billing/product_list.html', context)

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

def product_import(request):
    if request.method == 'POST':
        form = ProductImportForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.cleaned_data['file']
            update_existing = form.cleaned_data['update_existing']

            if not upload.name.lower().endswith('.xlsx'):
                messages.error(request, 'Please upload an Excel .xlsx file.')
                return redirect('product_import')

            try:
                imported_rows = read_product_xlsx(upload)
                required_columns = {'name', 'price'}
                headers = set(imported_rows[0].keys()) if imported_rows else set()

                if not required_columns.issubset(headers):
                    messages.error(
                        request,
                        'Excel file must include product name and price columns. '
                        'Accepted headers include Product Name/Name and Price/Rate/MRP.'
                    )
                    return redirect('product_import')

                category_values = {value for value, _label in Product.CATEGORY_CHOICES}
                unit_values = {value for value, _label in Product.UNIT_CHOICES}
                created_count = 0
                updated_count = 0
                skipped_rows = []

                for row_number, row in enumerate(imported_rows, start=2):
                    normalized = {
                        (key or '').strip().lower(): (value or '').strip()
                        for key, value in row.items()
                    }

                    name = normalized.get('name', '')
                    if not name:
                        skipped_rows.append(f'Row {row_number}: missing product name')
                        continue

                    try:
                        price = Decimal(normalized.get('price', ''))
                    except (InvalidOperation, TypeError):
                        skipped_rows.append(f'Row {row_number}: invalid price')
                        continue

                    try:
                        quantity = int(normalized.get('quantity') or 0)
                    except ValueError:
                        skipped_rows.append(f'Row {row_number}: invalid quantity')
                        continue

                    category = (normalized.get('category') or 'other').lower()
                    unit = (normalized.get('unit') or 'piece').lower()

                    if category not in category_values:
                        category = 'other'
                    if unit not in unit_values:
                        unit = 'piece'

                    defaults = {
                        'category': category,
                        'unit': unit,
                        'price': price,
                        'quantity': quantity,
                        'description': normalized.get('description', ''),
                    }

                    product = Product.objects.filter(name__iexact=name).first()
                    if product and update_existing:
                        for field, value in defaults.items():
                            setattr(product, field, value)
                        product.name = name
                        product.save()
                        updated_count += 1
                    elif product:
                        skipped_rows.append(f'Row {row_number}: product already exists')
                    else:
                        Product.objects.create(name=name, **defaults)
                        created_count += 1

                messages.success(
                    request,
                    f'Import complete: {created_count} added, {updated_count} updated.'
                )
                if skipped_rows:
                    messages.warning(request, 'Skipped rows: ' + '; '.join(skipped_rows[:6]))
                return redirect('product_list')
            except (KeyError, ET.ParseError, zipfile.BadZipFile):
                messages.error(request, 'Could not read the Excel file. Please use the sample format and try again.')
    else:
        form = ProductImportForm()

    return render(request, 'billing/product_import.html', {'form': form})

def product_sample_excel(request):
    rows = [
        ['name', 'category', 'unit', 'price', 'quantity', 'description'],
        ['Flower Pot Small', 'fountain', 'box', 120.00, 25, 'Small flower pot crackers'],
        ['7cm Sparklers', 'sparklers', 'packet', 45.00, 50, 'Standard sparkler packet'],
        ['Atom Bomb', 'bomb', 'packet', 85.00, 30, 'Classic atom bomb packet'],
    ]
    workbook = build_xlsx(rows)
    response = HttpResponse(
        workbook,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="product_import_sample.xlsx"'
    return response

def product_export_excel(request):
    rows = [['name', 'category', 'unit', 'price', 'quantity', 'description']]
    for product in Product.objects.all().order_by('name'):
        rows.append([
            product.name,
            product.category,
            product.unit,
            product.price,
            product.quantity,
            product.description or '',
        ])
    workbook = build_xlsx(rows)
    response = HttpResponse(
        workbook,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="products.xlsx"'
    return response

def product_export_pdf(request):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [
        Paragraph('GOMU CRACKERS - Product List', styles['Title']),
        Spacer(1, 0.2 * inch),
    ]

    data = [['S.No', 'Product', 'Category', 'Unit', 'Price', 'Stock']]
    for index, product in enumerate(Product.objects.all().order_by('name'), start=1):
        data.append([
            str(index),
            product.name,
            product.get_category_display(),
            product.get_unit_display(),
            f'{product.price:.2f}',
            str(product.quantity),
        ])

    table = Table(data, colWidths=[0.45 * inch, 2.35 * inch, 1.15 * inch, 0.85 * inch, 0.9 * inch, 0.75 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    doc.build(story)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="products.pdf"'
    return response

# ========== CUSTOMER MANAGEMENT ==========
def customer_list(request):
    customers = Customer.objects.all()
    search_query = request.GET.get('q', '').strip()
    if search_query:
        customers = customers.filter(
            models.Q(name__icontains=search_query) |
            models.Q(phone__icontains=search_query) |
            models.Q(city__icontains=search_query)
        )

    context = {
        'customers': customers,
        'search_query': search_query,
        'customer_count': customers.count(),
    }
    return render(request, 'billing/customer_list.html', context)

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
    products = Product.objects.annotate(
        stock_total=models.ExpressionWrapper(
            models.F('price') * models.F('quantity'),
            output_field=models.DecimalField(max_digits=12, decimal_places=2),
        )
    )
    low_stock = products.filter(quantity__gt=0, quantity__lt=10)
    out_of_stock = products.filter(quantity__lte=0)
    total_quantity = products.aggregate(total=models.Sum('quantity'))['total'] or 0
    stock_value = sum(product.price * product.quantity for product in products)

    context = {
        'stocks': stocks,
        'products': products,
        'product_count': products.count(),
        'total_quantity': total_quantity,
        'stock_value': stock_value,
        'low_stock_count': low_stock.count(),
        'out_of_stock_count': out_of_stock.count(),
        'stock_in_count': stocks.filter(movement_type='in').count(),
        'stock_out_count': stocks.filter(movement_type='out').count(),
        'adjustment_count': stocks.filter(movement_type='adjustment').count(),
        'low_stock_products': low_stock[:8],
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
        movement_type = request.GET.get('type', 'in')
        valid_types = {value for value, _label in Stock.MOVEMENT_CHOICES}
        initial = {'movement_type': movement_type} if movement_type in valid_types else {'movement_type': 'in'}
        form = StockForm(initial=initial)

    title_map = {
        'in': 'Stock In',
        'out': 'Stock Out',
        'adjustment': 'Stock Adjustment',
    }
    title = title_map.get(request.GET.get('type'), 'Add Stock')
    return render(request, 'billing/stock_form.html', {'form': form, 'title': title})

def stock_update(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Stock updated!')
                return redirect('stock_list')
            except ValueError as e:
                messages.error(request, str(e))
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
            quick_name = request.POST.get('quick_customer_name', '').strip()
            quick_phone = request.POST.get('quick_customer_phone', '').strip()
            if not bill.customer and quick_name:
                bill.customer = Customer.objects.create(
                    name=quick_name,
                    phone=quick_phone or 'Walk-in',
                )
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
    logo_path = settings.BASE_DIR / 'static' / 'images' / 'gomu_crackers_logo.jpeg'

    try:
        logo = Image(str(logo_path), width=1.15 * inch, height=1.15 * inch)
    except Exception:
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
