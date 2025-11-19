import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import SessionLocal, Sale, Product, Customer, Complaint, ComplaintMessage, Notification
from auth import get_admin_display_name
from utils import format_currency, sync_offline_sales

def show():
    """Employee dashboard"""
    pharmacy_name = get_admin_display_name()
    
    st.sidebar.title(f"💊 {pharmacy_name}")
    st.sidebar.write(f"Welcome, {st.session_state.user['username']}!")
    st.sidebar.caption("Employee Portal")
    
    menu = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Sales", "Inventory", "Customers", "Support", "AI Assistant"]
    )
    
    if st.sidebar.button("Logout", use_container_width=True):
        from app import logout
        logout()
    
    # Sync offline sales on load
    synced = sync_offline_sales()
    if synced > 0:
        st.sidebar.success(f"Synced {synced} offline sales")
    
    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Sales":
        show_sales()
    elif menu == "Inventory":
        show_inventory()
    elif menu == "Customers":
        show_customers()
    elif menu == "Support":
        show_support()
    elif menu == "AI Assistant":
        show_ai_assistant()

def show_dashboard():
    """Employee dashboard overview"""
    st.title("📊 Dashboard")
    
    db = SessionLocal()
    
    # Today's metrics
    today = datetime.now().date()
    
    my_sales_today = db.query(Sale).filter(
        Sale.employee_id == st.session_state.user['id'],
        Sale.created_at >= today
    ).all()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("My Sales Today", len(my_sales_today))
    
    with col2:
        total_revenue = sum(s.total_amount for s in my_sales_today)
        st.metric("My Revenue Today", format_currency(total_revenue))
    
    with col3:
        all_sales_today = db.query(Sale).filter(Sale.created_at >= today).count()
        st.metric("Total Sales Today", all_sales_today)
    
    # Recent sales
    st.subheader("My Recent Sales")
    
    recent_sales = db.query(Sale).filter(
        Sale.employee_id == st.session_state.user['id']
    ).order_by(Sale.created_at.desc()).limit(10).all()
    
    if recent_sales:
        sales_data = []
        for sale in recent_sales:
            sales_data.append({
                'ID': sale.id,
                'Date': sale.created_at.strftime('%Y-%m-%d %H:%M'),
                'Customer': sale.customer.name,
                'Amount': format_currency(sale.total_amount),
                'Payment': sale.payment_mode.value.upper()
            })
        
        df = pd.DataFrame(sales_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No sales yet")
    
    # Low stock alerts
    st.subheader("⚠️ Low Stock Alerts")
    
    low_stock = db.query(Product).filter(
        Product.quantity_in_stock <= Product.reorder_level
    ).all()
    
    if low_stock:
        for product in low_stock:
            st.warning(f"**{product.name}** - Only {product.quantity_in_stock} left")
    else:
        st.success("All products well stocked!")
    
    db.close()

def show_sales():
    """Sales module for employees"""
    from pages import sales_module
    sales_module.show()

def show_inventory():
    """Inventory view for employees"""
    from pages import inventory_module
    st.title("📦 Inventory")
    
    tab1, tab2 = st.tabs(["View Products", "Barcode Scanner"])
    
    with tab1:
        inventory_module.show_products_list()
    
    with tab2:
        inventory_module.show_barcode_scanner()

def show_customers():
    """Customer management for employees"""
    from pages import customer_module
    st.title("👥 Customers")
    
    tab1, tab2 = st.tabs(["Customers List", "Add Customer"])
    
    with tab1:
        customer_module.show_customers_list()
    
    with tab2:
        customer_module.show_add_customer()

def show_support():
    """Support/complaints for employees"""
    st.title("💬 Support & Complaints")
    
    st.subheader("Submit a Complaint")
    
    subject = st.text_input("Subject")
    description = st.text_area("Description")
    
    if st.button("Submit Complaint"):
        if subject and description:
            from database import Complaint
            db = SessionLocal()
            
            complaint = Complaint(
                customer_id=None,
                submitted_by_role="employee",
                subject=subject,
                description=description,
                status="pending"
            )
            
            db.add(complaint)
            db.commit()
            
            # Notify admin
            from database import Notification, NotificationType, User, UserRole
            admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
            if admin:
                notification = Notification(
                    user_id=admin.id,
                    notification_type=NotificationType.COMPLAINT,
                    title="New Employee Complaint",
                    message=f"Employee {st.session_state.user['username']} submitted: {subject}",
                    is_read=False
                )
                db.add(notification)
                db.commit()
            
            st.success("Complaint submitted successfully!")
            db.close()
        else:
            st.error("Please fill in all fields")

def show_ai_assistant():
    """AI Assistant"""
    from pages import ai_assistant_module
    ai_assistant_module.show()
