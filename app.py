import streamlit as st
from agent.agent import chat
from tools.loyalty_tools import get_points_balance, get_customer_name
from config import CUSTOMER_ID, MERCHANT_ID


st.set_page_config(
    page_title="ABC Loyalty Assistant",
    page_icon="🎯",
    layout="centered"
)


st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .stChatMessage { border-radius: 12px; margin-bottom: 8px; }
        .sidebar-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 12px;
            color: white;
            margin-bottom: 16px;
        }
        .points-big {
            font-size: 2.5rem;
            font-weight: 700;
            color: white;
        }
        .points-label {
            font-size: 0.85rem;
            color: rgba(255,255,255,0.8);
        }
        .stat-box {
            background: rgba(255,255,255,0.15);
            border-radius: 8px;
            padding: 10px;
            margin-top: 8px;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_customer_data():
    name = get_customer_name(CUSTOMER_ID, MERCHANT_ID)
    balance = get_points_balance(CUSTOMER_ID, MERCHANT_ID)
    return name, balance

customer, balance = load_customer_data()


with st.sidebar:
    st.markdown("## 🎯 ABC Loyalty")
    st.markdown("---")

    # Customer card
    st.markdown(f"""
        <div class="sidebar-card">
            <div class="points-label">Welcome back,</div>
            <div style="font-size:1.3rem; font-weight:600; margin-bottom:12px;">
                {customer.get('name', 'Customer')} 👋
            </div>
            <div class="points-label">Available Points</div>
            <div class="points-big">{balance.get('available_points', 0):,}</div>
            <div style="display:flex; gap:8px; margin-top:12px;">
                <div class="stat-box" style="flex:1">
                    <div style="font-size:1.1rem; font-weight:600;">
                        {balance.get('redeemed_points', 0):,}
                    </div>
                    <div class="points-label">Redeemed</div>
                </div>
                <div class="stat-box" style="flex:1">
                    <div style="font-size:1.1rem; font-weight:600;">
                        {balance.get('expired_points', 0):,}
                    </div>
                    <div class="points-label">Expired</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)



# Main chat area 
st.markdown("## Loyalty Assistant")
st.markdown("Ask me anything about your points, coupons, and rewards.")
st.markdown("---")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Greeting message
    st.session_state.messages.append({
        "role": "assistant",
        "content": f"Hi {customer.get('name', 'there')}! 👋 I'm your ABC Loyalty Assistant. "
                   f"You have **{balance.get('available_points', 0):,} points** available. "
                   f"How can I help you today?"
    })

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle sidebar button clicks
if "pending_question" in st.session_state:
    user_input = st.session_state.pop("pending_question")

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Checking your account..."):
            # Build history excluding the current message
            history = st.session_state.messages[:-1]
            response = chat(user_input, history)
        st.markdown(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })
    st.rerun()

# Handle typed input
if user_input := st.chat_input("Ask about your points, coupons, or rewards..."):
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Checking your account..."):
            history = st.session_state.messages[:-1]
            response = chat(user_input, history)
        st.markdown(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })