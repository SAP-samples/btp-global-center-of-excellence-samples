import uuid
from gen_ai_hub.proxy.langchain.init_models import init_llm
import streamlit as st


def init_resources():
    from agent import init_agent
    if 'init' not in st.session_state:
        st.session_state.chat_history = [(uuid.uuid1(), 'assistant', 'Hi, I am an AI Agent helping you with your timesheet management.')]
        st.session_state.thread_id = uuid.uuid1()
        st.session_state.light_llm = init_llm('gpt-4o-mini', temperature=0)
        st.session_state.agent = init_agent()
        st.session_state.init = True
        st.session_state.interrupted = False

    return [st.session_state[el] for el in ['light_llm', 'agent']]
