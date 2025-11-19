import json
import io
import os
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import cohere

# Use environment variable for API key, fallback to provided key for demo
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "FEWr21565ZTPK3lR2obCwUmqq3g08Grnu9YeLoYb")

def format_currency(amount: float) -> str:
    """Format amount as Kenyan Shilling"""
    return f"KES {amount:,.2f}"

def get_cohere_client():
    """Get Cohere client"""
    return cohere.Client(COHERE_API_KEY)

def get_ai_response(message: str, chat_history: list = None):
    """Get AI response from Cohere"""
    try:
        co = get_cohere_client()
        
        # Prepare chat history
        history = []
        if chat_history:
            for msg in chat_history[-10:]:  # Last 10 messages for context
                history.append({
                    "role": "USER" if msg["role"] == "user" else "CHATBOT",
                    "message": msg["message"]
                })
        
        # Add system context about pharmacy
        preamble = """You are a helpful AI assistant for a pharmacy management system in Kenya. 
        You can help customers with:
        - General pharmacy questions
        - Medicine information and usage
        - Store policies and services
        - Account inquiries
        
        Always be professional, helpful, and accurate. If you're unsure about medical advice, 
        recommend consulting with a pharmacist or doctor."""
        
        response = co.chat(
            message=message,
            chat_history=history,
            preamble=preamble
        )
        
        return response.text
    except Exception as e:
        return f"I apologize, but I'm having trouble processing your request right now. Error: {str(e)}"

def generate_receipt(sale_data: dict, customer_name: str, employee_name: str, pharmacy_name: str):
    """Generate a printable receipt as PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f77b4'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    # Header
    story.append(Paragraph(pharmacy_name, title_style))
    story.append(Paragraph("SALES RECEIPT", header_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Receipt info
    receipt_info = [
        ['Receipt #:', str(sale_data.get('id', 'N/A'))],
        ['Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['Customer:', customer_name],
        ['Served by:', employee_name],
        ['Payment Mode:', sale_data.get('payment_mode', 'N/A').upper()],
    ]
    
    if sale_data.get('mpesa_transaction_id'):
        receipt_info.append(['M-Pesa Ref:', sale_data['mpesa_transaction_id']])
    
    info_table = Table(receipt_info, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Items table
    items_data = [['Item', 'Qty', 'Price', 'Total']]
    for item in sale_data.get('items', []):
        items_data.append([
            item['product_name'],
            str(item['quantity']),
            format_currency(item['unit_price']),
            format_currency(item['subtotal'])
        ])
    
    items_table = Table(items_data, colWidths=[3*inch, 0.7*inch, 1.2*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Total
    total_data = [
        ['TOTAL:', format_currency(sale_data.get('total_amount', 0))],
        ['Amount Paid:', format_currency(sale_data.get('amount_paid', 0))],
    ]
    
    if sale_data.get('payment_mode') == 'credit':
        balance = sale_data.get('total_amount', 0) - sale_data.get('amount_paid', 0)
        total_data.append(['Credit Balance:', format_currency(balance)])
    
    total_table = Table(total_data, colWidths=[4.9*inch, 1.2*inch])
    total_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer = Paragraph("Thank you for your business!", header_style)
    story.append(footer)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def save_offline_sale(sale_data: dict):
    """Save sale data for offline sync"""
    try:
        from database import OfflineSale, SessionLocal
        db = SessionLocal()
        offline_sale = OfflineSale(sale_data=json.dumps(sale_data))
        db.add(offline_sale)
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"Error saving offline sale: {e}")
        return False

def sync_offline_sales():
    """Sync offline sales to main database"""
    try:
        from database import OfflineSale, Sale, SaleItem, Product, SessionLocal, PaymentMode
        db = SessionLocal()
        
        offline_sales = db.query(OfflineSale).all()
        synced_count = 0
        
        for offline_sale in offline_sales:
            try:
                sale_data = json.loads(offline_sale.sale_data)
                
                # Create sale
                sale = Sale(
                    customer_id=sale_data['customer_id'],
                    employee_id=sale_data['employee_id'],
                    payment_mode=PaymentMode[sale_data['payment_mode'].upper()],
                    total_amount=sale_data['total_amount'],
                    amount_paid=sale_data['amount_paid'],
                    mpesa_transaction_id=sale_data.get('mpesa_transaction_id'),
                    is_synced=True,
                    created_at=datetime.fromisoformat(sale_data['created_at'])
                )
                db.add(sale)
                db.flush()
                
                # Create sale items
                for item in sale_data['items']:
                    sale_item = SaleItem(
                        sale_id=sale.id,
                        product_id=item['product_id'],
                        quantity=item['quantity'],
                        unit_price=item['unit_price'],
                        subtotal=item['subtotal']
                    )
                    db.add(sale_item)
                    
                    # Update inventory
                    product = db.query(Product).filter(Product.id == item['product_id']).first()
                    if product:
                        product.quantity_in_stock -= item['quantity']
                
                # Delete offline sale record
                db.delete(offline_sale)
                synced_count += 1
                
            except Exception as e:
                print(f"Error syncing sale: {e}")
                continue
        
        db.commit()
        db.close()
        return synced_count
    except Exception as e:
        print(f"Error in sync_offline_sales: {e}")
        return 0

def search_products(query: str, limit: int = 10):
    """Search products by name or barcode"""
    from database import Product, SessionLocal
    db = SessionLocal()
    try:
        products = db.query(Product).filter(
            (Product.name.ilike(f'%{query}%')) | 
            (Product.barcode.ilike(f'%{query}%'))
        ).limit(limit).all()
        return products
    finally:
        db.close()

def search_customers(query: str, limit: int = 10):
    """Search customers by name or phone"""
    from database import Customer, SessionLocal
    db = SessionLocal()
    try:
        customers = db.query(Customer).filter(
            (Customer.name.ilike(f'%{query}%')) | 
            (Customer.phone.ilike(f'%{query}%'))
        ).limit(limit).all()
        return customers
    finally:
        db.close()

def decode_barcode(image):
    """Decode barcode from image using pyzbar"""
    try:
        from pyzbar.pyzbar import decode
        import cv2
        import numpy as np
        from PIL import Image
        
        # Convert to numpy array
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # Decode barcodes
        barcodes = decode(image)
        if barcodes:
            return barcodes[0].data.decode('utf-8')
        return None
    except Exception as e:
        print(f"Barcode decode error: {e}")
        return None
