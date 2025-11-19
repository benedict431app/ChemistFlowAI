import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import SessionLocal, User, Customer, Product, Sale, SaleItem, Payment, CRMInteraction, Complaint, ComplaintMessage, Notification, NotificationType, UserRole, PaymentMode
from auth import get_pending_users, approve_user, update_admin_display_name
from utils import format_currency, sync_offline_sales, search_products, search_customers
import plotly.express as px
import plotly.graph_objects as go

def show():
    """Admin dashboard"""
    st.sidebar.title(f"👨‍💼 Admin Panel")
    st.sidebar.write(f"Welcome, {st.session_state.user['username']}!")
    
    # Check for notifications
    db = SessionLocal()
    unread_notifications = db.query(Notification).filter(
        Notification.user_id == st.session_state.user['id'],
        Notification.is_read == False
    ).count()
    db.close()
    
    if unread_notifications > 0:
        st.sidebar.markdown(f'<span class="notification-badge">{unread_notifications}</span> New Notifications', unsafe_allow_html=True)
    
    menu = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Settings", "Employee Approvals", "Inventory", "Sales", "Customers", "CRM", "Complaints", "Reports", "Notifications", "AI Assistant"]
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
    elif menu == "Settings":
        show_settings()
    elif menu == "Employee Approvals":
        show_employee_approvals()
    elif menu == "Inventory":
        show_inventory()
    elif menu == "Sales":
        show_sales()
    elif menu == "Customers":
        show_customers()
    elif menu == "CRM":
        show_crm()
    elif menu == "Complaints":
        show_complaints()
    elif menu == "Reports":
        show_reports()
    elif menu == "Notifications":
        show_notifications()
    elif menu == "AI Assistant":
        show_ai_assistant()

def show_dashboard():
    """Main dashboard"""
    st.title("📊 Dashboard Overview")
    
    db = SessionLocal()
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sales = db.query(Sale).count()
        st.metric("Total Sales", total_sales)
    
    with col2:
        total_customers = db.query(Customer).count()
        st.metric("Customers", total_customers)
    
    with col3:
        total_products = db.query(Product).count()
        st.metric("Products", total_products)
    
    with col4:
        today_sales = db.query(Sale).filter(
            Sale.created_at >= datetime.now().date()
        ).count()
        st.metric("Today's Sales", today_sales)
    
    # Revenue metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_revenue = db.query(Sale).with_entities(
            db.func.sum(Sale.total_amount)
        ).scalar() or 0
        st.metric("Total Revenue", format_currency(total_revenue))
    
    with col2:
        today_revenue = db.query(Sale).filter(
            Sale.created_at >= datetime.now().date()
        ).with_entities(
            db.func.sum(Sale.total_amount)
        ).scalar() or 0
        st.metric("Today's Revenue", format_currency(today_revenue))
    
    with col3:
        pending_credit = db.query(Customer).with_entities(
            db.func.sum(Customer.current_credit)
        ).scalar() or 0
        st.metric("Pending Credit", format_currency(pending_credit))
    
    # Low stock alerts
    st.subheader("⚠️ Low Stock Alerts")
    low_stock = db.query(Product).filter(
        Product.quantity_in_stock <= Product.reorder_level
    ).all()
    
    if low_stock:
        for product in low_stock:
            st.warning(f"**{product.name}** - Only {product.quantity_in_stock} left (Reorder at {product.reorder_level})")
    else:
        st.success("All products are well stocked!")
    
    # Recent sales chart
    st.subheader("📈 Sales Trend (Last 7 Days)")
    
    seven_days_ago = datetime.now() - timedelta(days=7)
    sales_data = db.query(
        db.func.date(Sale.created_at).label('date'),
        db.func.count(Sale.id).label('count'),
        db.func.sum(Sale.total_amount).label('revenue')
    ).filter(
        Sale.created_at >= seven_days_ago
    ).group_by(
        db.func.date(Sale.created_at)
    ).all()
    
    if sales_data:
        df = pd.DataFrame(sales_data, columns=['Date', 'Sales Count', 'Revenue'])
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df['Date'],
            y=df['Revenue'],
            name='Revenue (KES)',
            marker_color='#1f77b4'
        ))
        
        st.plotly_chart(fig, use_container_width=True)
    
    db.close()

def show_settings():
    """Settings page"""
    st.title("⚙️ Settings")
    
    st.subheader("Pharmacy Information")
    
    current_name = st.session_state.user.get('display_name', 'ChemistFlow Pharmacy')
    new_name = st.text_input("Pharmacy Display Name", value=current_name)
    
    if st.button("Update Display Name"):
        if new_name:
            if update_admin_display_name(st.session_state.user['id'], new_name):
                st.session_state.user['display_name'] = new_name
                st.success("Display name updated successfully!")
                st.info("This name will appear to all employees across the system.")
                st.rerun()
            else:
                st.error("Failed to update display name")
    
    st.divider()
    st.subheader("System Information")
    st.info(f"**Admin:** {st.session_state.user['username']}")
    st.info(f"**Email:** {st.session_state.user['email']}")

def show_employee_approvals():
    """Employee approval page"""
    st.title("👥 Employee Approvals")
    
    # Password protection for approvals
    if 'approval_verified' not in st.session_state:
        st.session_state.approval_verified = False
    
    if not st.session_state.approval_verified:
        st.warning("Enter your password to manage employee approvals")
        password = st.text_input("Admin Password", type="password")
        
        if st.button("Verify"):
            from auth import authenticate_user
            user = authenticate_user(st.session_state.user['username'], password)
            if user:
                st.session_state.approval_verified = True
                st.rerun()
            else:
                st.error("Invalid password")
        return
    
    pending_users = get_pending_users()
    
    if not pending_users:
        st.success("No pending employee approvals")
        return
    
    for user in pending_users:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"**{user.username}** - {user.email}")
                st.caption(f"Role: {user.role.value.title()} | Registered: {user.created_at.strftime('%Y-%m-%d %H:%M')}")
            
            with col2:
                if st.button("✅ Approve", key=f"approve_{user.id}"):
                    success, error = approve_user(st.session_state.user['id'], user.id)
                    if success:
                        st.success(f"Approved {user.username}")
                        st.rerun()
                    else:
                        st.error(error)
            
            with col3:
                if st.button("❌ Reject", key=f"reject_{user.id}"):
                    db = SessionLocal()
                    db.query(User).filter(User.id == user.id).delete()
                    db.commit()
                    db.close()
                    st.success(f"Rejected {user.username}")
                    st.rerun()
            
            st.divider()

def show_inventory():
    """Inventory management"""
    from pages import inventory_module
    inventory_module.show()

def show_sales():
    """Sales module"""
    from pages import sales_module
    sales_module.show()

def show_customers():
    """Customer management"""
    from pages import customer_module
    customer_module.show()

def show_crm():
    """CRM module"""
    from pages import crm_module
    crm_module.show()

def show_complaints():
    """Complaints management"""
    from pages import complaints_module
    complaints_module.show()

def show_reports():
    """Reports"""
    st.title("📊 Reports")
    
    db = SessionLocal()
    
    report_type = st.selectbox(
        "Select Report",
        ["Sales Summary", "Revenue by Payment Mode", "Top Products", "Customer Credit Report"]
    )
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From Date", datetime.now().date() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To Date", datetime.now().date())
    
    if report_type == "Sales Summary":
        sales = db.query(Sale).filter(
            Sale.created_at >= start_date,
            Sale.created_at <= end_date
        ).all()
        
        total_sales = len(sales)
        total_revenue = sum(s.total_amount for s in sales)
        
        st.metric("Total Sales", total_sales)
        st.metric("Total Revenue", format_currency(total_revenue))
        
        # Sales table
        sales_data = []
        for sale in sales:
            sales_data.append({
                'ID': sale.id,
                'Date': sale.created_at.strftime('%Y-%m-%d %H:%M'),
                'Customer': sale.customer.name,
                'Amount': format_currency(sale.total_amount),
                'Payment': sale.payment_mode.value.upper(),
                'Employee': sale.employee.username
            })
        
        if sales_data:
            df = pd.DataFrame(sales_data)
            st.dataframe(df, use_container_width=True)
    
    elif report_type == "Revenue by Payment Mode":
        revenue_data = db.query(
            Sale.payment_mode,
            db.func.count(Sale.id).label('count'),
            db.func.sum(Sale.total_amount).label('revenue')
        ).filter(
            Sale.created_at >= start_date,
            Sale.created_at <= end_date
        ).group_by(Sale.payment_mode).all()
        
        if revenue_data:
            df = pd.DataFrame([
                {
                    'Payment Mode': r[0].value.upper(),
                    'Transactions': r[1],
                    'Revenue': r[2]
                }
                for r in revenue_data
            ])
            
            st.dataframe(df, use_container_width=True)
            
            # Pie chart
            fig = px.pie(df, values='Revenue', names='Payment Mode', title='Revenue by Payment Mode')
            st.plotly_chart(fig, use_container_width=True)
    
    elif report_type == "Top Products":
        top_products = db.query(
            Product.name,
            db.func.sum(SaleItem.quantity).label('total_sold'),
            db.func.sum(SaleItem.subtotal).label('revenue')
        ).join(SaleItem).join(Sale).filter(
            Sale.created_at >= start_date,
            Sale.created_at <= end_date
        ).group_by(Product.name).order_by(
            db.func.sum(SaleItem.quantity).desc()
        ).limit(10).all()
        
        if top_products:
            df = pd.DataFrame(top_products, columns=['Product', 'Units Sold', 'Revenue'])
            st.dataframe(df, use_container_width=True)
            
            fig = px.bar(df, x='Product', y='Units Sold', title='Top 10 Products by Units Sold')
            st.plotly_chart(fig, use_container_width=True)
    
    elif report_type == "Customer Credit Report":
        customers_with_credit = db.query(Customer).filter(
            Customer.current_credit > 0
        ).all()
        
        if customers_with_credit:
            credit_data = []
            for customer in customers_with_credit:
                credit_data.append({
                    'Customer': customer.name,
                    'Phone': customer.phone,
                    'Credit Amount': format_currency(customer.current_credit),
                    'Credit Limit': format_currency(customer.credit_limit)
                })
            
            df = pd.DataFrame(credit_data)
            st.dataframe(df, use_container_width=True)
            
            total_credit = sum(c.current_credit for c in customers_with_credit)
            st.metric("Total Outstanding Credit", format_currency(total_credit))
        else:
            st.info("No customers with outstanding credit")
    
    db.close()

def show_notifications():
    """Notifications"""
    st.title("🔔 Notifications")
    
    db = SessionLocal()
    
    notifications = db.query(Notification).filter(
        Notification.user_id == st.session_state.user['id']
    ).order_by(Notification.created_at.desc()).all()
    
    if not notifications:
        st.info("No notifications")
        db.close()
        return
    
    for notif in notifications:
        with st.container():
            if not notif.is_read:
                st.markdown("🔴 **NEW**")
            
            st.subheader(notif.title)
            st.write(notif.message)
            st.caption(notif.created_at.strftime('%Y-%m-%d %H:%M'))
            
            if not notif.is_read:
                if st.button("Mark as Read", key=f"read_{notif.id}"):
                    notif.is_read = True
                    db.commit()
                    st.rerun()
            
            st.divider()
    
    db.close()

def show_ai_assistant():
    """AI Assistant"""
    from pages import ai_assistant_module
    ai_assistant_module.show()
