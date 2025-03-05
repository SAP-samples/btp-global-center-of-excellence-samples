import requests, urllib3
import streamlit as st

# This example uses unverified HTTPS rquests for simplicity. However, note that these are strongly discouraged.
# Disable the corresponding warnings, see https://urllib3.readthedocs.io/en/latest/advanced-usage.html#tls-warnings
urllib3.disable_warnings()

# Configure the applicaction
st.set_page_config(page_title="BTP AI Assistant", 
                   initial_sidebar_state='collapsed')
st.title('BTP AI Assistant')
st.sidebar.write('Detailed log')
backend_api = "https://ENTERYOURURLFROMTHEAIAGENT/"

# Initial setup if application is running for the first time
def initial_setup():
    st.session_state["chat_history"] = []
    st.session_state["chat_history_debuglog"] = []
    msg_welcome = "Hello there, how can I help?"
    st.session_state["chat_history"].append({"role": "assistant", "content": msg_welcome})
    st.session_state["chat_history_debuglog"].append({"role": "assistant", "content": msg_welcome})

if "chat_history" not in st.session_state:
    initial_setup()
  
# Process user input (add to the session, get response, add response to the session)
def chat_actions():   

    # Add user input to session
    st.session_state["chat_history"].append({"role": "user", "content": st.session_state["chat_input"]})
    st.session_state["chat_history_debuglog"].append({"role": "user", "content": st.session_state["chat_input"]})

    # Get answer from api
    with st.spinner('Hold on...'):
        user_input = st.session_state["chat_input"]
        paylod = {'user_input': user_input}
        headers = {'Accept' : 'application/json', 'Content-Type' : 'application/json'}
        r = requests.get(backend_api, json=paylod, headers=headers, verify=False)
        response = r.json()
        faq_response = response['btpaiagent_response']
        faq_response_log = response['btpaiagent_response_log']

    # Add api response to the sessions
    st.session_state["chat_history"].append({"role": "assistant", "content": faq_response})
    st.session_state["chat_history_debuglog"].append({"role": "assistant", "content": faq_response_log})

# Get input from user
st.chat_input("Enter your message", on_submit=chat_actions, key="chat_input")

# Display the conversation on the main page
for i in st.session_state["chat_history"]:
    if i["role"] == 'assistant':
        st.chat_message(name=i["role"], avatar="🤖").write(i["content"])
    else:
        st.chat_message(name=i["role"], avatar="😃").write(i["content"])

# Display the conversation'a more detailed log on the side panel
for i in st.session_state["chat_history_debuglog"]:
    if i["role"] == 'assistant':
        st.sidebar.chat_message(name=i["role"], avatar="🤖").write(i["content"])
    else:
        st.sidebar.chat_message(name=i["role"], avatar="😃").write(i["content"])