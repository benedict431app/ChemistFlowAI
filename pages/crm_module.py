import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import SessionLocal, Customer, CRMInteraction
from utils import format_currency

def show():
    """CRM module"""
    st.title("📞 Customer Relationship Management")
    
    tab1, tab2, tab3 = st.tabs(["Interactions", "Schedule Follow-Up", "Follow-Up Calendar"])
    
    with tab1:
        show_interactions()
    
    with tab2:
        show_schedule_followup()
    
    with tab3:
        show_followup_calendar()

def show_interactions():
    """Show all CRM interactions"""
    st.subheader("Customer Interactions")
    
    db = SessionLocal()
    
    # Filter
    col1, col2 = st.columns(2)
    
    with col1:
        filter_type = st.selectbox("Filter by Type", ["All", "Call", "Visit", "Email", "SMS", "Other"])
    
    with col2:
        filter_status = st.selectbox("Filter by Status", ["All", "Pending", "Completed"])
    
    # Query
    query = db.query(CRMInteraction).join(Customer)
    
    if filter_type != "All":
        query = query.filter(CRMInteraction.interaction_type == filter_type.lower())
    
    if filter_status == "Pending":
        query = query.filter(CRMInteraction.is_completed == False)
    elif filter_status == "Completed":
        query = query.filter(CRMInteraction.is_completed == True)
    
    interactions = query.order_by(CRMInteraction.created_at.desc()).all()
    
    if interactions:
        interactions_data = []
        for interaction in interactions:
            interactions_data.append({
                'ID': interaction.id,
                'Customer': interaction.customer.name,
                'Type': interaction.interaction_type.upper(),
                'Date': interaction.created_at.strftime('%Y-%m-%d'),
                'Follow-Up': interaction.follow_up_date.strftime('%Y-%m-%d') if interaction.follow_up_date else 'N/A',
                'Status': 'Completed' if interaction.is_completed else 'Pending'
            })
        
        df = pd.DataFrame(interactions_data)
        st.dataframe(df, use_container_width=True)
        
        # View/Edit interaction
        interaction_id = st.number_input("Interaction ID to View/Edit", min_value=1, step=1)
        
        if st.button("Load Interaction"):
            interaction = db.query(CRMInteraction).filter(CRMInteraction.id == interaction_id).first()
            if interaction:
                st.session_state.edit_interaction = interaction
                st.rerun()
        
        if 'edit_interaction' in st.session_state:
            interaction = st.session_state.edit_interaction
            
            st.subheader(f"Interaction #{interaction.id}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Customer:** {interaction.customer.name}")
                st.write(f"**Type:** {interaction.interaction_type.upper()}")
                st.write(f"**Date:** {interaction.created_at.strftime('%Y-%m-%d %H:%M')}")
            
            with col2:
                st.write(f"**Follow-Up:** {interaction.follow_up_date.strftime('%Y-%m-%d') if interaction.follow_up_date else 'None'}")
                st.write(f"**Status:** {'Completed' if interaction.is_completed else 'Pending'}")
            
            st.write(f"**Notes:**")
            st.write(interaction.notes or 'No notes')
            
            # Mark as completed
            if not interaction.is_completed:
                if st.button("✅ Mark as Completed"):
                    interaction.is_completed = True
                    db.commit()
                    st.success("Interaction marked as completed!")
                    del st.session_state.edit_interaction
                    st.rerun()
            
            # Delete
            if st.button("🗑️ Delete Interaction"):
                db.delete(interaction)
                db.commit()
                st.success("Interaction deleted!")
                del st.session_state.edit_interaction
                st.rerun()
    else:
        st.info("No interactions found")
    
    db.close()

def show_schedule_followup():
    """Schedule a new follow-up"""
    st.subheader("Schedule Follow-Up")
    
    db = SessionLocal()
    
    # Search customer
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
            
            # Interaction details
            interaction_type = st.selectbox("Interaction Type", ["Call", "Visit", "Email", "SMS", "Other"])
            notes = st.text_area("Notes")
            
            schedule_followup = st.checkbox("Schedule Follow-Up")
            follow_up_date = None
            
            if schedule_followup:
                follow_up_date = st.date_input("Follow-Up Date", min_value=datetime.now().date())
            
            if st.button("Save Interaction", use_container_width=True):
                interaction = CRMInteraction(
                    customer_id=selected_customer_id,
                    interaction_type=interaction_type.lower(),
                    notes=notes if notes else None,
                    follow_up_date=follow_up_date if follow_up_date else None,
                    is_completed=False
                )
                
                db.add(interaction)
                db.commit()
                
                st.success("Interaction saved successfully!")
                st.rerun()
        else:
            st.warning("No customers found")
    
    db.close()

def show_followup_calendar():
    """Show follow-up calendar"""
    st.subheader("Follow-Up Calendar")
    
    db = SessionLocal()
    
    # Show upcoming follow-ups
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📅 Today's Follow-Ups")
        
        today = datetime.now().date()
        today_followups = db.query(CRMInteraction).join(Customer).filter(
            db.func.date(CRMInteraction.follow_up_date) == today,
            CRMInteraction.is_completed == False
        ).all()
        
        if today_followups:
            for followup in today_followups:
                st.warning(f"**{followup.customer.name}** - {followup.interaction_type.upper()}")
                st.caption(followup.notes or 'No notes')
                
                if st.button(f"Complete", key=f"today_{followup.id}"):
                    followup.is_completed = True
                    db.commit()
                    st.rerun()
        else:
            st.success("No follow-ups for today!")
    
    with col2:
        st.markdown("### 📆 Upcoming (Next 7 Days)")
        
        next_week = datetime.now().date() + timedelta(days=7)
        upcoming_followups = db.query(CRMInteraction).join(Customer).filter(
            CRMInteraction.follow_up_date > today,
            CRMInteraction.follow_up_date <= next_week,
            CRMInteraction.is_completed == False
        ).order_by(CRMInteraction.follow_up_date).all()
        
        if upcoming_followups:
            for followup in upcoming_followups:
                st.info(f"**{followup.follow_up_date.strftime('%Y-%m-%d')}** - {followup.customer.name}")
                st.caption(f"{followup.interaction_type.upper()} - {followup.notes or 'No notes'}")
        else:
            st.success("No upcoming follow-ups!")
    
    # All pending follow-ups
    st.divider()
    st.subheader("All Pending Follow-Ups")
    
    pending_followups = db.query(CRMInteraction).join(Customer).filter(
        CRMInteraction.follow_up_date.isnot(None),
        CRMInteraction.is_completed == False
    ).order_by(CRMInteraction.follow_up_date).all()
    
    if pending_followups:
        followups_data = []
        for followup in pending_followups:
            followups_data.append({
                'Date': followup.follow_up_date.strftime('%Y-%m-%d'),
                'Customer': followup.customer.name,
                'Phone': followup.customer.phone,
                'Type': followup.interaction_type.upper(),
                'Notes': followup.notes or 'N/A'
            })
        
        df = pd.DataFrame(followups_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No pending follow-ups")
    
    db.close()
