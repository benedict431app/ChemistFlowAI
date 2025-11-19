import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal, Customer, Sale, Payment, Complaint, ComplaintMessage, User, UserRole, Notification, NotificationType
from auth import get_admin_display_name
from utils import format_currency

def show():
    """Customer dashboard"""
    pharmacy_name = get_admin_display_name()
    
    st.sidebar.title(f"💊 {pharmacy_name}")
    st.sidebar.write(f"Welcome, {st.session_state.user['username']}!")
    st.sidebar.caption("Customer Portal")
    
    menu = st.sidebar.selectbox(
        "Navigation",
        ["My Account", "Purchase History", "Payments", "Support", "AI Assistant"]
    )
    
    if st.sidebar.button("Logout", use_container_width=True):
        from app import logout
        logout()
    
    if menu == "My Account":
        show_account()
    elif menu == "Purchase History":
        show_purchase_history()
    elif menu == "Payments":
        show_payments()
    elif menu == "Support":
        show_support()
    elif menu == "AI Assistant":
        show_ai_assistant()

def get_customer_account():
    """Get customer account linked to user"""
    db = SessionLocal()
    customer = db.query(Customer).filter(Customer.user_id == st.session_state.user['id']).first()
    db.close()
    return customer

def show_account():
    """Show customer account details (read-only)"""
    st.title("👤 My Account")
    
    customer = get_customer_account()
    
    if not customer:
        st.warning("No customer account linked. Please contact the pharmacy.")
        
        # Allow linking to existing customer record
        st.subheader("Link to Existing Account")
        st.info("If you have made purchases before, we can link your account.")
        
        phone = st.text_input("Enter your phone number")
        
        if st.button("Find My Account"):
            if phone:
                db = SessionLocal()
                existing_customer = db.query(Customer).filter(Customer.phone == phone).first()
                
                if existing_customer:
                    if existing_customer.user_id is None:
                        existing_customer.user_id = st.session_state.user['id']
                        db.commit()
                        st.success("Account linked successfully!")
                        st.rerun()
                    else:
                        st.error("This customer account is already linked to another user")
                else:
                    st.error("No account found with that phone number")
                
                db.close()
        
        return
    
    # Display account info (read-only)
    st.subheader("Account Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Credit", format_currency(customer.current_credit))
    
    with col2:
        st.metric("Credit Limit", format_currency(customer.credit_limit))
    
    with col3:
        available = customer.credit_limit - customer.current_credit
        st.metric("Available Credit", format_currency(available))
    
    st.info("ℹ️ Account details are read-only. Contact the pharmacy to update your information.")
    
    # Display info
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Name:** {customer.name}")
        st.write(f"**Phone:** {customer.phone}")
    
    with col2:
        st.write(f"**Email:** {customer.email or 'N/A'}")
        st.write(f"**Address:** {customer.address or 'N/A'}")

def show_purchase_history():
    """Show purchase history (read-only)"""
    st.title("🛒 Purchase History")
    
    customer = get_customer_account()
    
    if not customer:
        st.warning("No customer account linked")
        return
    
    db = SessionLocal()
    
    # Filter by date
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("From Date", datetime.now().date() - pd.Timedelta(days=30))
    
    with col2:
        end_date = st.date_input("To Date", datetime.now().date())
    
    sales = db.query(Sale).filter(
        Sale.customer_id == customer.id,
        Sale.created_at >= start_date,
        Sale.created_at <= end_date
    ).order_by(Sale.created_at.desc()).all()
    
    if sales:
        sales_data = []
        for sale in sales:
            sales_data.append({
                'Date': sale.created_at.strftime('%Y-%m-%d %H:%M'),
                'Amount': format_currency(sale.total_amount),
                'Paid': format_currency(sale.amount_paid),
                'Payment': sale.payment_mode.value.upper(),
                'Balance': format_currency(sale.total_amount - sale.amount_paid)
            })
        
        df = pd.DataFrame(sales_data)
        st.dataframe(df, use_container_width=True)
        
        # Total summary
        total_purchases = sum(s.total_amount for s in sales)
        total_paid = sum(s.amount_paid for s in sales)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Purchases", format_currency(total_purchases))
        
        with col2:
            st.metric("Total Paid", format_currency(total_paid))
    else:
        st.info("No purchase history found for the selected period")
    
    db.close()

def show_payments():
    """Show payment history and current credit status"""
    st.title("💳 Payments & Credit")
    
    customer = get_customer_account()
    
    if not customer:
        st.warning("No customer account linked")
        return
    
    db = SessionLocal()
    
    # Current status
    st.subheader("Credit Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Outstanding Credit", format_currency(customer.current_credit))
    
    with col2:
        st.metric("Credit Limit", format_currency(customer.credit_limit))
    
    with col3:
        available = customer.credit_limit - customer.current_credit
        st.metric("Available Credit", format_currency(available))
    
    if customer.current_credit > 0:
        st.warning(f"⚠️ You have an outstanding credit balance of {format_currency(customer.current_credit)}. Please make a payment at the pharmacy.")
    else:
        st.success("✅ No outstanding credit balance")
    
    # Payment history
    st.subheader("Payment History")
    
    payments = db.query(Payment).filter(
        Payment.customer_id == customer.id
    ).order_by(Payment.created_at.desc()).all()
    
    if payments:
        payments_data = []
        for payment in payments:
            payments_data.append({
                'Date': payment.created_at.strftime('%Y-%m-%d %H:%M'),
                'Amount': format_currency(payment.amount),
                'Mode': payment.payment_mode.value.upper(),
                'Reference': payment.mpesa_transaction_id or 'N/A',
                'Notes': payment.notes or 'N/A'
            })
        
        df = pd.DataFrame(payments_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No payment history")
    
    db.close()

def show_support():
    """Customer support and complaints"""
    st.title("💬 Support & Complaints")
    
    customer = get_customer_account()
    
    db = SessionLocal()
    
    tab1, tab2 = st.tabs(["My Complaints", "Submit New Complaint"])
    
    with tab1:
        if customer:
            complaints = db.query(Complaint).filter(
                Complaint.customer_id == customer.id
            ).order_by(Complaint.created_at.desc()).all()
            
            if complaints:
                for complaint in complaints:
                    with st.expander(f"{complaint.subject} - {complaint.status.replace('_', ' ').title()}"):
                        st.write(f"**Status:** {complaint.status.replace('_', ' ').title()}")
                        st.write(f"**Submitted:** {complaint.created_at.strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Description:** {complaint.description}")
                        
                        # Messages
                        messages = db.query(ComplaintMessage).filter(
                            ComplaintMessage.complaint_id == complaint.id
                        ).order_by(ComplaintMessage.created_at).all()
                        
                        if messages:
                            st.write("**Conversation:**")
                            for msg in messages:
                                if msg.sender_role == "admin":
                                    st.info(f"**Admin:** {msg.message}")
                                else:
                                    st.write(f"**You:** {msg.message}")
                                st.caption(msg.created_at.strftime('%Y-%m-%d %H:%M'))
                        
                        # Reply
                        reply = st.text_input(f"Reply to complaint #{complaint.id}", key=f"reply_{complaint.id}")
                        
                        if st.button(f"Send Reply", key=f"send_{complaint.id}"):
                            if reply:
                                message = ComplaintMessage(
                                    complaint_id=complaint.id,
                                    sender_role="customer",
                                    message=reply
                                )
                                db.add(message)
                                db.commit()
                                st.success("Reply sent!")
                                st.rerun()
            else:
                st.info("No complaints submitted")
        else:
            st.warning("Link your customer account to view complaints")
    
    with tab2:
        st.subheader("Submit a Complaint")
        
        subject = st.text_input("Subject")
        description = st.text_area("Description")
        
        if st.button("Submit Complaint"):
            if subject and description:
                complaint = Complaint(
                    customer_id=customer.id if customer else None,
                    submitted_by_role="customer",
                    subject=subject,
                    description=description,
                    status="pending"
                )
                
                db.add(complaint)
                db.commit()
                
                # Notify admin
                admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
                if admin:
                    notification = Notification(
                        user_id=admin.id,
                        notification_type=NotificationType.COMPLAINT,
                        title="New Customer Complaint",
                        message=f"Customer {st.session_state.user['username']} submitted: {subject}",
                        is_read=False
                    )
                    db.add(notification)
                    db.commit()
                
                st.success("Complaint submitted successfully! We'll respond as soon as possible.")
                st.rerun()
            else:
                st.error("Please fill in all fields")
    
    db.close()

def show_ai_assistant():
    """AI Assistant"""
    from pages import ai_assistant_module
    ai_assistant_module.show()
