import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal, Product, Customer, Sale, SaleItem, PaymentMode
from utils import format_currency, generate_receipt, save_offline_sale
import json

def show():
    """Sales module"""
    st.title("💰 Point of Sale")
    
    tab1, tab2 = st.tabs(["New Sale", "Sales History"])
    
    with tab1:
        show_new_sale()
    
    with tab2:
        show_sales_history()

def show_new_sale():
    """Create new sale"""
    st.subheader("New Sale")
    
    db = SessionLocal()
    
    # Check if offline mode
    if 'offline_mode' not in st.session_state:
        st.session_state.offline_mode = False
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("💡 Scan barcodes in the Inventory > Barcode Scanner to add items quickly")
    with col2:
        offline_toggle = st.checkbox("Offline Mode", value=st.session_state.offline_mode)
        if offline_toggle != st.session_state.offline_mode:
            st.session_state.offline_mode = offline_toggle
    
    if st.session_state.offline_mode:
        st.warning("⚠️ Offline Mode: Sales will be synced when you go online")
    
    # Customer selection
    st.subheader("Select Customer")
    
    customer_search = st.text_input("🔍 Search customer by name or phone", key="customer_search")
    
    customers = []
    if customer_search:
        customers = db.query(Customer).filter(
            (Customer.name.ilike(f'%{customer_search}%')) |
            (Customer.phone.ilike(f'%{customer_search}%'))
        ).limit(10).all()
        
        if customers:
            customer_options = {f"{c.name} - {c.phone}": c.id for c in customers}
            selected_customer_key = st.selectbox("Select Customer", list(customer_options.keys()))
            selected_customer_id = customer_options[selected_customer_key]
        else:
            st.warning("No customers found")
            selected_customer_id = None
    else:
        selected_customer_id = None
    
    # Option to add new customer
    with st.expander("➕ Add New Customer"):
        new_customer_name = st.text_input("Customer Name")
        new_customer_phone = st.text_input("Phone Number")
        new_customer_email = st.text_input("Email (optional)")
        new_customer_credit_limit = st.number_input("Credit Limit (KES)", min_value=0.0, step=100.0, value=0.0)
        
        if st.button("Add Customer"):
            if new_customer_name and new_customer_phone:
                customer = Customer(
                    name=new_customer_name,
                    phone=new_customer_phone,
                    email=new_customer_email if new_customer_email else None,
                    credit_limit=new_customer_credit_limit
                )
                db.add(customer)
                db.commit()
                st.success(f"Customer '{new_customer_name}' added successfully!")
                st.rerun()
            else:
                st.error("Name and phone are required")
    
    # Product selection
    st.subheader("Add Products")
    
    product_search = st.text_input("🔍 Search product", key="product_search", placeholder="Type product name or barcode...")
    
    if product_search:
        products = db.query(Product).filter(
            (Product.name.ilike(f'%{product_search}%')) |
            (Product.barcode.ilike(f'%{product_search}%'))
        ).limit(10).all()
        
        if products:
            for product in products:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(f"**{product.name}**")
                    st.caption(f"Stock: {product.quantity_in_stock} | {format_currency(product.unit_price)}")
                
                with col2:
                    quantity = st.number_input(
                        "Qty",
                        min_value=1,
                        max_value=product.quantity_in_stock,
                        value=1,
                        step=1,
                        key=f"qty_{product.id}"
                    )
                
                with col3:
                    if st.button("Add", key=f"add_{product.id}"):
                        if 'cart' not in st.session_state:
                            st.session_state.cart = []
                        
                        # Check if already in cart
                        existing = next((item for item in st.session_state.cart if item['product_id'] == product.id), None)
                        if existing:
                            existing['quantity'] += quantity
                            existing['subtotal'] = existing['quantity'] * existing['unit_price']
                        else:
                            st.session_state.cart.append({
                                'product_id': product.id,
                                'product_name': product.name,
                                'unit_price': product.unit_price,
                                'quantity': quantity,
                                'subtotal': product.unit_price * quantity
                            })
                        
                        st.success(f"Added {product.name}")
                        st.rerun()
    
    # Shopping cart
    st.subheader("Shopping Cart")
    
    if 'cart' not in st.session_state or not st.session_state.cart:
        st.info("Cart is empty. Add products to continue.")
    else:
        cart_data = []
        for idx, item in enumerate(st.session_state.cart):
            cart_data.append({
                'Product': item['product_name'],
                'Price': format_currency(item['unit_price']),
                'Qty': item['quantity'],
                'Subtotal': format_currency(item['subtotal'])
            })
        
        df = pd.DataFrame(cart_data)
        st.dataframe(df, use_container_width=True)
        
        # Remove item
        remove_idx = st.number_input("Remove item # (row index)", min_value=0, max_value=len(st.session_state.cart)-1, step=1)
        if st.button("Remove Item"):
            st.session_state.cart.pop(remove_idx)
            st.rerun()
        
        # Total
        total = sum(item['subtotal'] for item in st.session_state.cart)
        st.markdown(f"### Total: {format_currency(total)}")
        
        # Payment
        st.subheader("Payment")
        
        payment_mode = st.selectbox("Payment Mode", ["Cash", "Credit", "M-Pesa", "Card"])
        
        amount_paid = st.number_input("Amount Paid (KES)", min_value=0.0, value=float(total), step=1.0)
        
        mpesa_ref = None
        if payment_mode == "M-Pesa":
            mpesa_ref = st.text_input("M-Pesa Transaction ID")
        
        # Validate credit payment
        can_proceed = True
        if payment_mode == "Credit":
            if not selected_customer_id:
                st.error("Please select a customer for credit payment")
                can_proceed = False
            else:
                customer = db.query(Customer).filter(Customer.id == selected_customer_id).first()
                if customer:
                    new_credit = customer.current_credit + (total - amount_paid)
                    if new_credit > customer.credit_limit:
                        st.error(f"Credit limit exceeded! Limit: {format_currency(customer.credit_limit)}, Current: {format_currency(customer.current_credit)}")
                        can_proceed = False
                    else:
                        st.info(f"New credit balance: {format_currency(new_credit)} / {format_currency(customer.credit_limit)}")
        
        if st.button("Complete Sale", disabled=not can_proceed or not selected_customer_id):
            if not selected_customer_id:
                st.error("Please select a customer")
            else:
                # Create sale
                sale_data = {
                    'customer_id': selected_customer_id,
                    'employee_id': st.session_state.user['id'],
                    'payment_mode': payment_mode.lower(),
                    'total_amount': total,
                    'amount_paid': amount_paid,
                    'mpesa_transaction_id': mpesa_ref,
                    'items': st.session_state.cart,
                    'created_at': datetime.now().isoformat()
                }
                
                if st.session_state.offline_mode:
                    # Save for offline sync
                    save_offline_sale(sale_data)
                    st.success("Sale saved offline! Will sync when online.")
                else:
                    # Save to database
                    try:
                        sale = Sale(
                            customer_id=selected_customer_id,
                            employee_id=st.session_state.user['id'],
                            payment_mode=PaymentMode[payment_mode.upper()],
                            total_amount=total,
                            amount_paid=amount_paid,
                            mpesa_transaction_id=mpesa_ref,
                            is_synced=True
                        )
                        db.add(sale)
                        db.flush()
                        
                        # Add sale items and update inventory
                        for item in st.session_state.cart:
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
                        
                        # Update customer credit if applicable
                        if payment_mode == "Credit":
                            customer = db.query(Customer).filter(Customer.id == selected_customer_id).first()
                            if customer:
                                customer.current_credit += (total - amount_paid)
                        
                        db.commit()
                        
                        # Generate receipt
                        customer = db.query(Customer).filter(Customer.id == selected_customer_id).first()
                        from auth import get_admin_display_name
                        
                        receipt_data = {
                            'id': sale.id,
                            'payment_mode': payment_mode,
                            'mpesa_transaction_id': mpesa_ref,
                            'total_amount': total,
                            'amount_paid': amount_paid,
                            'items': st.session_state.cart
                        }
                        
                        receipt_pdf = generate_receipt(
                            receipt_data,
                            customer.name,
                            st.session_state.user['username'],
                            get_admin_display_name()
                        )
                        
                        st.success(f"✅ Sale completed! Receipt #{sale.id}")
                        
                        # Download receipt
                        st.download_button(
                            "📄 Download Receipt",
                            receipt_pdf,
                            file_name=f"receipt_{sale.id}.pdf",
                            mime="application/pdf"
                        )
                        
                        # Clear cart
                        st.session_state.cart = []
                        st.rerun()
                        
                    except Exception as e:
                        db.rollback()
                        st.error(f"Error completing sale: {e}")
    
    db.close()

def show_sales_history():
    """Show sales history"""
    st.subheader("Sales History")
    
    db = SessionLocal()
    
    # Filter
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("From Date", datetime.now().date())
    
    with col2:
        end_date = st.date_input("To Date", datetime.now().date())
    
    sales = db.query(Sale).filter(
        Sale.created_at >= start_date,
        Sale.created_at <= end_date
    ).order_by(Sale.created_at.desc()).all()
    
    if sales:
        sales_data = []
        for sale in sales:
            sales_data.append({
                'ID': sale.id,
                'Date': sale.created_at.strftime('%Y-%m-%d %H:%M'),
                'Customer': sale.customer.name,
                'Amount': format_currency(sale.total_amount),
                'Paid': format_currency(sale.amount_paid),
                'Payment': sale.payment_mode.value.upper(),
                'Employee': sale.employee.username
            })
        
        df = pd.DataFrame(sales_data)
        st.dataframe(df, use_container_width=True)
        
        # View details
        sale_id = st.number_input("View Sale Details (ID)", min_value=1, step=1)
        
        if st.button("View Details"):
            sale = db.query(Sale).filter(Sale.id == sale_id).first()
            if sale:
                st.subheader(f"Sale #{sale.id}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Customer:** {sale.customer.name}")
                    st.write(f"**Date:** {sale.created_at.strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**Payment Mode:** {sale.payment_mode.value.upper()}")
                
                with col2:
                    st.write(f"**Total:** {format_currency(sale.total_amount)}")
                    st.write(f"**Paid:** {format_currency(sale.amount_paid)}")
                    st.write(f"**Employee:** {sale.employee.username}")
                
                # Items
                st.subheader("Items")
                items_data = []
                for item in sale.sale_items:
                    items_data.append({
                        'Product': item.product.name,
                        'Quantity': item.quantity,
                        'Price': format_currency(item.unit_price),
                        'Subtotal': format_currency(item.subtotal)
                    })
                
                df_items = pd.DataFrame(items_data)
                st.dataframe(df_items, use_container_width=True)
            else:
                st.error("Sale not found")
    else:
        st.info("No sales found for the selected date range")
    
    db.close()
