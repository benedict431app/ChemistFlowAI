import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal, Product
from utils import decode_barcode, format_currency
from streamlit_camera_input_live import camera_input_live
import qrcode
from io import BytesIO

def show():
    """Inventory management module"""
    st.title("📦 Inventory Management")
    
    tab1, tab2, tab3 = st.tabs(["Products List", "Add Product", "Barcode Scanner"])
    
    with tab1:
        show_products_list()
    
    with tab2:
        show_add_product()
    
    with tab3:
        show_barcode_scanner()

def show_products_list():
    """Display products list"""
    st.subheader("Products Inventory")
    
    db = SessionLocal()
    
    # Search
    search_query = st.text_input("🔍 Search products", placeholder="Type to search...")
    
    if search_query:
        products = db.query(Product).filter(
            (Product.name.ilike(f'%{search_query}%')) |
            (Product.barcode.ilike(f'%{search_query}%')) |
            (Product.category.ilike(f'%{search_query}%'))
        ).all()
    else:
        products = db.query(Product).all()
    
    if products:
        products_data = []
        for product in products:
            products_data.append({
                'ID': product.id,
                'Barcode': product.barcode or 'N/A',
                'Name': product.name,
                'Category': product.category or 'N/A',
                'Price': format_currency(product.unit_price),
                'Stock': product.quantity_in_stock,
                'Reorder Level': product.reorder_level
            })
        
        df = pd.DataFrame(products_data)
        st.dataframe(df, use_container_width=True)
        
        # Edit/Delete product
        st.subheader("Manage Product")
        product_id = st.number_input("Product ID to Edit/Delete", min_value=1, step=1)
        
        if st.button("Load Product"):
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                st.session_state.edit_product = product
                st.rerun()
            else:
                st.error("Product not found")
        
        if 'edit_product' in st.session_state:
            product = st.session_state.edit_product
            
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Product Name", value=product.name)
                new_category = st.text_input("Category", value=product.category or '')
                new_price = st.number_input("Price (KES)", value=float(product.unit_price), min_value=0.0, step=1.0)
                new_stock = st.number_input("Stock Quantity", value=product.quantity_in_stock, min_value=0, step=1)
            
            with col2:
                new_barcode = st.text_input("Barcode", value=product.barcode or '')
                new_reorder = st.number_input("Reorder Level", value=product.reorder_level, min_value=0, step=1)
                new_supplier = st.text_input("Supplier", value=product.supplier or '')
                new_description = st.text_area("Description", value=product.description or '')
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Update Product", use_container_width=True):
                    product.name = new_name
                    product.category = new_category
                    product.unit_price = new_price
                    product.quantity_in_stock = new_stock
                    product.barcode = new_barcode if new_barcode else None
                    product.reorder_level = new_reorder
                    product.supplier = new_supplier if new_supplier else None
                    product.description = new_description if new_description else None
                    
                    db.commit()
                    st.success("Product updated successfully!")
                    del st.session_state.edit_product
                    st.rerun()
            
            with col2:
                if st.button("Delete Product", use_container_width=True):
                    db.delete(product)
                    db.commit()
                    st.success("Product deleted successfully!")
                    del st.session_state.edit_product
                    st.rerun()
    else:
        st.info("No products found")
    
    db.close()

def show_add_product():
    """Add new product"""
    st.subheader("Add New Product")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("Product Name*")
        category = st.text_input("Category")
        price = st.number_input("Unit Price (KES)*", min_value=0.0, step=1.0)
        stock = st.number_input("Initial Stock*", min_value=0, step=1, value=0)
    
    with col2:
        barcode = st.text_input("Barcode (optional)")
        reorder_level = st.number_input("Reorder Level", min_value=0, step=1, value=10)
        supplier = st.text_input("Supplier")
        description = st.text_area("Description")
    
    # Generate barcode option
    if st.checkbox("Generate Barcode"):
        if name:
            # Generate a simple barcode based on product name
            import hashlib
            barcode_value = hashlib.md5(name.encode()).hexdigest()[:12]
            st.info(f"Generated Barcode: {barcode_value}")
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(barcode_value)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img.save(buf, format='PNG')
            st.image(buf.getvalue(), width=200)
            
            if st.button("Use This Barcode"):
                st.session_state.generated_barcode = barcode_value
                st.rerun()
        else:
            st.warning("Enter product name first")
    
    if 'generated_barcode' in st.session_state:
        barcode = st.session_state.generated_barcode
        st.success(f"Using barcode: {barcode}")
    
    if st.button("Add Product", use_container_width=True):
        if not name or price <= 0:
            st.error("Please fill in all required fields")
        else:
            db = SessionLocal()
            
            # Check if barcode exists
            if barcode:
                existing = db.query(Product).filter(Product.barcode == barcode).first()
                if existing:
                    st.error("Barcode already exists")
                    db.close()
                    return
            
            product = Product(
                name=name,
                category=category if category else None,
                unit_price=price,
                quantity_in_stock=stock,
                barcode=barcode if barcode else None,
                reorder_level=reorder_level,
                supplier=supplier if supplier else None,
                description=description if description else None
            )
            
            db.add(product)
            db.commit()
            st.success(f"Product '{name}' added successfully!")
            
            if 'generated_barcode' in st.session_state:
                del st.session_state.generated_barcode
            
            db.close()
            st.rerun()

def show_barcode_scanner():
    """Barcode scanner using camera"""
    st.subheader("📸 Barcode Scanner")
    
    st.info("Use your camera to scan product barcodes for quick lookup or sales")
    
    # Camera input
    image = camera_input_live()
    
    if image is not None:
        from PIL import Image
        import io
        
        # Convert to PIL Image
        pil_image = Image.open(io.BytesIO(image))
        
        # Decode barcode
        barcode_value = decode_barcode(pil_image)
        
        if barcode_value:
            st.success(f"Barcode detected: {barcode_value}")
            
            # Look up product
            db = SessionLocal()
            product = db.query(Product).filter(Product.barcode == barcode_value).first()
            
            if product:
                st.subheader("Product Found!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Name:** {product.name}")
                    st.write(f"**Category:** {product.category or 'N/A'}")
                    st.write(f"**Price:** {format_currency(product.unit_price)}")
                
                with col2:
                    st.write(f"**Stock:** {product.quantity_in_stock}")
                    st.write(f"**Barcode:** {product.barcode}")
                
                if st.button("Add to Sale Cart"):
                    if 'cart' not in st.session_state:
                        st.session_state.cart = []
                    
                    # Check if already in cart
                    existing = next((item for item in st.session_state.cart if item['product_id'] == product.id), None)
                    if existing:
                        existing['quantity'] += 1
                    else:
                        st.session_state.cart.append({
                            'product_id': product.id,
                            'product_name': product.name,
                            'unit_price': product.unit_price,
                            'quantity': 1,
                            'subtotal': product.unit_price
                        })
                    
                    st.success(f"Added {product.name} to cart!")
            else:
                st.warning("Product not found in inventory")
            
            db.close()
        else:
            st.info("No barcode detected. Make sure the barcode is clear and well-lit.")
