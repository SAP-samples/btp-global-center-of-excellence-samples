import uuid
from gen_ai_hub.proxy.langchain.init_models import init_llm
import streamlit as st
from langchain_core.messages import AIMessage
from handle_db import retrieve_recent_summary, get_conn

conn = get_conn()
competitor_briefing = retrieve_recent_summary(conn)

def init_resources():
    if 'init' not in st.session_state:
        st.session_state.thread_id = uuid.uuid1()
        st.session_state.light_llm = init_llm('gemini-2.0-flash', max_tokens=100, temperature=0)
        from agent import init_agent

        st.session_state.agent = init_agent(competitor_briefing)
        summary = AIMessage(content=competitor_briefing)
        st.session_state.chat_history = [(uuid.uuid1(), 'assistant', competitor_briefing)]
        update_payload = {"messages": [summary]}
        st.session_state.agent.update_state({"configurable": {"thread_id": st.session_state.thread_id}}, update_payload)

        st.session_state.init = True
        st.session_state.interrupted = False

    return [st.session_state[el] for el in ['light_llm', 'agent']]

@st.cache_resource
def init_charts():
    return {}