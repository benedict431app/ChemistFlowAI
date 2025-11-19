import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal, Customer, Sale, Payment, PaymentMode
from utils import format_currency

def show():
    """Customer management module"""
    st.title("👥 Customer Management")
    
    tab1, tab2, tab3 = st.tabs(["Customers List", "Add Customer", "Customer Details"])
    
    with tab1:
        show_customers_list()
    
    with tab2:
        show_add_customer()
    
    with tab3:
        show_customer_details()

def show_customers_list():
    """Display customers list"""
    st.subheader("Customers")
    
    db = SessionLocal()
    
    # Search
    search_query = st.text_input("🔍 Search customers", placeholder="Name or phone...")
    
    if search_query:
        customers = db.query(Customer).filter(
            (Customer.name.ilike(f'%{search_query}%')) |
            (Customer.phone.ilike(f'%{search_query}%'))
        ).all()
    else:
        customers = db.query(Customer).all()
    
    if customers:
        customers_data = []
        for customer in customers:
            customers_data.append({
                'ID': customer.id,
                'Name': customer.name,
                'Phone': customer.phone,
                'Email': customer.email or 'N/A',
                'Credit': format_currency(customer.current_credit),
                'Limit': format_currency(customer.credit_limit)
            })
        
        df = pd.DataFrame(customers_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No customers found")
    
    db.close()

def show_add_customer():
    """Add new customer"""
    st.subheader("Add New Customer")
    
    name = st.text_input("Customer Name*")
    phone = st.text_input("Phone Number*")
    email = st.text_input("Email")
    address = st.text_area("Address")
    credit_limit = st.number_input("Credit Limit (KES)", min_value=0.0, step=100.0, value=0.0)
    
    if st.button("Add Customer", use_container_width=True):
        if not name or not phone:
            st.error("Name and phone are required")
        else:
            db = SessionLocal()
            
            customer = Customer(
                name=name,
                phone=phone,
                email=email if email else None,
                address=address if address else None,
                credit_limit=credit_limit
            )
            
            db.add(customer)
            db.commit()
            st.success(f"Customer '{name}' added successfully!")
            db.close()
            st.rerun()

def show_customer_details():
    """Show customer details and transactions"""
    st.subheader("Customer Details")
    
    db = SessionLocal()
    
    customer_search = st.text_input("🔍 Search customer", placeholder="Name or phone...")
    
    if customer_search:
        customers = db.query(Customer).filter(
            (Customer.name.ilike(f'%{customer_search}%')) |
            (Customer.phone.ilike(f'%{customer_search}%'))
        ).limit(10).all()
        
        if customers:
            customer_options = {f"{c.name} - {c.phone}": c.id for c in customers}
            selected_customer_key = st.selectbox("Select Customer", list(customer_options.keys()))
            selected_customer_id = customer_options[selected_customer_key]
            
            customer = db.query(Customer).filter(Customer.id == selected_customer_id).first()
            
            if customer:
                # Customer info
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Current Credit", format_currency(customer.current_credit))
                
                with col2:
                    st.metric("Credit Limit", format_currency(customer.credit_limit))
                
                with col3:
                    available_credit = customer.credit_limit - customer.current_credit
                    st.metric("Available Credit", format_currency(available_credit))
                
                st.write(f"**Email:** {customer.email or 'N/A'}")
                st.write(f"**Phone:** {customer.phone}")
                st.write(f"**Address:** {customer.address or 'N/A'}")
                
                # Purchase history
                st.subheader("Purchase History")
                
                sales = db.query(Sale).filter(Sale.customer_id == customer.id).order_by(Sale.created_at.desc()).all()
                
                if sales:
                    sales_data = []
                    for sale in sales:
                        sales_data.append({
                            'Date': sale.created_at.strftime('%Y-%m-%d'),
                            'Amount': format_currency(sale.total_amount),
                            'Paid': format_currency(sale.amount_paid),
                            'Payment': sale.payment_mode.value.upper()
                        })
                    
                    df = pd.DataFrame(sales_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No purchase history")
                
                # Payment history
                st.subheader("Payment History")
                
                payments = db.query(Payment).filter(Payment.customer_id == customer.id).order_by(Payment.created_at.desc()).all()
                
                if payments:
                    payments_data = []
                    for payment in payments:
                        payments_data.append({
                            'Date': payment.created_at.strftime('%Y-%m-%d'),
                            'Amount': format_currency(payment.amount),
                            'Mode': payment.payment_mode.value.upper(),
                            'Notes': payment.notes or 'N/A'
                        })
                    
                    df = pd.DataFrame(payments_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No payment history")
                
                # Record payment
                if customer.current_credit > 0:
                    st.subheader("Record Payment")
                    
                    payment_amount = st.number_input(
                        "Payment Amount (KES)",
                        min_value=0.0,
                        max_value=float(customer.current_credit),
                        step=1.0
                    )
                    payment_mode = st.selectbox("Payment Mode", ["Cash", "M-Pesa", "Card"])
                    payment_notes = st.text_area("Notes")
                    mpesa_ref = None
                    
                    if payment_mode == "M-Pesa":
                        mpesa_ref = st.text_input("M-Pesa Transaction ID")
                    
                    if st.button("Record Payment"):
                        payment = Payment(
                            customer_id=customer.id,
                            amount=payment_amount,
                            payment_mode=PaymentMode[payment_mode.upper()],
                            mpesa_transaction_id=mpesa_ref,
                            notes=payment_notes if payment_notes else None
                        )
                        
                        customer.current_credit -= payment_amount
                        
                        db.add(payment)
                        db.commit()
                        
                        st.success(f"Payment of {format_currency(payment_amount)} recorded!")
                        st.rerun()
        else:
            st.warning("No customers found")
    
    db.close()
