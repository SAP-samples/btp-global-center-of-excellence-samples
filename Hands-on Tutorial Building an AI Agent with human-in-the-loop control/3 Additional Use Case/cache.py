import uuid
from gen_ai_hub.proxy.langchain.init_models import init_llm
import streamlit as st


def init_resources():
    if 'init' not in st.session_state:
        st.session_state.chat_history = [(uuid.uuid1(), 'assistant', 'Hi, I am an AI Agent providing deep insights for you.')]
        st.session_state.thread_id = uuid.uuid1()
        st.session_state.light_llm = init_llm('gpt-4o-mini', max_tokens=100, temperature=0)
        from data_agent import init_agent

        st.session_state.agent = init_agent()

        st.session_state.init = True
        st.session_state.interrupted = False

    return [st.session_state[el] for el in ['light_llm', 'agent']]

@st.cache_resource
def init_charts():
    return {}