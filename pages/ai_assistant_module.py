import streamlit as st
from datetime import datetime
from database import SessionLocal, ChatMessage
from utils import get_ai_response

def show():
    """AI Assistant module"""
    st.title("🤖 AI Assistant - Powered by Cohere")
    
    st.info("💡 Ask me anything about pharmacy operations, medicines, store policies, or general pharmacy questions!")
    
    db = SessionLocal()
    
    # Load chat history
    chat_history = db.query(ChatMessage).filter(
        ChatMessage.user_id == st.session_state.user['id']
    ).order_by(ChatMessage.created_at).all()
    
    # Display chat history
    for msg in chat_history:
        with st.chat_message(msg.role):
            st.write(msg.message)
    
    # Chat input
    user_message = st.chat_input("Ask me anything...")
    
    if user_message:
        # Save user message
        user_msg = ChatMessage(
            user_id=st.session_state.user['id'],
            role="user",
            message=user_message
        )
        db.add(user_msg)
        db.commit()
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_message)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Prepare chat history for context
                history = [{'role': msg.role, 'message': msg.message} for msg in chat_history]
                
                ai_response = get_ai_response(user_message, history)
                st.write(ai_response)
        
        # Save AI response
        ai_msg = ChatMessage(
            user_id=st.session_state.user['id'],
            role="assistant",
            message=ai_response
        )
        db.add(ai_msg)
        db.commit()
        
        st.rerun()
    
    # Clear history option
    if st.button("🗑️ Clear Chat History"):
        db.query(ChatMessage).filter(ChatMessage.user_id == st.session_state.user['id']).delete()
        db.commit()
        st.success("Chat history cleared!")
        st.rerun()
    
    db.close()
