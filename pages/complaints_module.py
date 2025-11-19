import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal, Complaint, ComplaintMessage, Customer, Notification, NotificationType

def show():
    """Complaints management module"""
    st.title("💬 Complaints & Support")
    
    tab1, tab2 = st.tabs(["All Complaints", "Complaint Details"])
    
    with tab1:
        show_complaints_list()
    
    with tab2:
        show_complaint_details()

def show_complaints_list():
    """Show all complaints"""
    st.subheader("Complaints")
    
    db = SessionLocal()
    
    # Filter
    status_filter = st.selectbox("Filter by Status", ["All", "Pending", "In Progress", "Resolved"])
    
    query = db.query(Complaint).order_by(Complaint.created_at.desc())
    
    if status_filter != "All":
        query = query.filter(Complaint.status == status_filter.lower().replace(" ", "_"))
    
    complaints = query.all()
    
    if complaints:
        complaints_data = []
        for complaint in complaints:
            customer_name = complaint.customer.name if complaint.customer else "Anonymous"
            complaints_data.append({
                'ID': complaint.id,
                'Subject': complaint.subject,
                'From': f"{customer_name} ({complaint.submitted_by_role})",
                'Status': complaint.status.replace("_", " ").title(),
                'Date': complaint.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        df = pd.DataFrame(complaints_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No complaints found")
    
    db.close()

def show_complaint_details():
    """Show and manage complaint details"""
    st.subheader("Complaint Details & Chat")
    
    db = SessionLocal()
    
    complaint_id = st.number_input("Enter Complaint ID", min_value=1, step=1)
    
    if st.button("Load Complaint"):
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if complaint:
            st.session_state.current_complaint = complaint.id
            st.rerun()
        else:
            st.error("Complaint not found")
    
    if 'current_complaint' in st.session_state:
        complaint = db.query(Complaint).filter(Complaint.id == st.session_state.current_complaint).first()
        
        if complaint:
            # Complaint header
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**ID:** {complaint.id}")
                st.write(f"**Subject:** {complaint.subject}")
            
            with col2:
                customer_name = complaint.customer.name if complaint.customer else "Anonymous"
                st.write(f"**From:** {customer_name}")
                st.write(f"**Role:** {complaint.submitted_by_role}")
            
            with col3:
                st.write(f"**Status:** {complaint.status.replace('_', ' ').title()}")
                st.write(f"**Date:** {complaint.created_at.strftime('%Y-%m-%d')}")
            
            st.write(f"**Description:**")
            st.write(complaint.description)
            
            st.divider()
            
            # Messages/Chat
            st.subheader("Conversation")
            
            messages = db.query(ComplaintMessage).filter(
                ComplaintMessage.complaint_id == complaint.id
            ).order_by(ComplaintMessage.created_at).all()
            
            for msg in messages:
                if msg.sender_role == "admin":
                    st.chat_message("assistant").write(msg.message)
                else:
                    st.chat_message("user").write(f"**{msg.sender_role.title()}:** {msg.message}")
                
                st.caption(msg.created_at.strftime('%Y-%m-%d %H:%M'))
            
            # Reply
            st.subheader("Reply to Complaint")
            
            reply_message = st.text_area("Your reply")
            
            if st.button("Send Reply"):
                if reply_message:
                    # Add message
                    message = ComplaintMessage(
                        complaint_id=complaint.id,
                        sender_role="admin",
                        message=reply_message
                    )
                    db.add(message)
                    
                    # Update status if pending
                    if complaint.status == "pending":
                        complaint.status = "in_progress"
                    
                    db.commit()
                    st.success("Reply sent!")
                    st.rerun()
                else:
                    st.warning("Please enter a message")
            
            # Update status
            st.subheader("Update Status")
            
            col1, col2 = st.columns(2)
            
            with col1:
                new_status = st.selectbox(
                    "Change Status",
                    ["pending", "in_progress", "resolved"],
                    index=["pending", "in_progress", "resolved"].index(complaint.status)
                )
            
            with col2:
                if st.button("Update Status", use_container_width=True):
                    complaint.status = new_status
                    if new_status == "resolved":
                        complaint.resolved_at = datetime.utcnow()
                    db.commit()
                    st.success("Status updated!")
                    st.rerun()
    
    db.close()
