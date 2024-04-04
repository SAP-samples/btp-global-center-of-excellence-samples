# Special thanks to
# - Heiko Hotz's streamlit example https://towardsdatascience.com/build-your-own-chatgpt-like-app-with-streamlit-20d940417389
#  - Lisa Wischofsky for creating and sharing the user avatars that are used by this bot under Attribution 4.0 International (CC BY 4.0) license
#  - Source: https://www.dicebear.com/styles/adventurer 
#  - License and Disclaimer: https://creativecommons.org/licenses/by/4.0/
# - Pablo Stanley for the bot's avatar
#   - Source: https://www.dicebear.com/styles/bottts
#  - License: Free for personal and commercial use

FAQBOT_LOGGING = False

import os
import streamlit as st
from streamlit_chat import message
import hana_ml.dataframe as dataframe
from random import randint

# Get the menu for the SAP canteen in Zurich
import requests, calendar
from bs4 import BeautifulSoup
from datetime import datetime
def get_menus():
    # Scrape the canteen's website
    response = requests.get("https://circle.sv-restaurant.ch/de/menuplan/chreis-14/")
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Get current day of week
    dt = datetime.now()
    weekday_current = dt.weekday()
    
    # If called on weekend, use Monday instead
    if weekday_current < 5:
        weekday_menu = weekday_current
    else:
        weekday_menu = 0
    
    # Get date for which menu will be returned
    dates_raw = soup.find_all(class_='date')
    dates = []
    for day in dates_raw:
        dates.append(day.text)
    date = dates[0] # Past dates are removed from the restaurant page
    
    # Get menus for that date
    menus = []
    menus_raw = dates_raw = soup.find_all(id='menu-plan-tab' + str(weekday_menu))
    menus_all_raw = soup.find(id='menu-plan-tab1')
    menus_all = menus_all_raw.find_all(class_='menu-title')
    for menu in menus_all:
        if menu.text not in ['Lunch auf der Terrasse']:
            menus.append(menu.text)
    
    # Return result
    return date, weekday_menu, menus

import locale
locale.setlocale(locale.LC_ALL, 'en_GB')
def get_menus_as_sentence():
    themenu = get_menus()
    menu_flowtext = ''
    for i in range(len(themenu[2])):
        menu_flowtext += " " + str(i+1) + ") " + themenu[2][i]
    menu_flowtext = menu_flowtext.lstrip()    
    response = "On " + calendar.day_name[themenu[1]] + ", the " + themenu[0] + ", Chreis 14 serves " + menu_flowtext + "."
    return response

# SAP HANA Cloud logon credentials, hardcoded only for sandboxing
SAP_HANA_CLOUD_ADDRESS  = ""
SAP_HANA_CLOUD_PORT     = 443
SAP_HANA_CLOUD_USER     = ""
SAP_HANA_CLOUD_PASSWORD = ""

# SAP Generative AI Hub logon credentials, hardcoded only for sandboxing
os.environ["AICORE_CLIENT_ID"]      = ""
os.environ["AICORE_CLIENT_SECRET"]  = ""
os.environ["AICORE_AUTH_URL"]       = ""
os.environ["AICORE_RESOURCE_GROUP"] = ""
os.environ["AICORE_BASE_URL"]       = ""  
AI_CORE_MODEL_NAME  = 'gpt-4-32k'

# Embedding engine for end user requests
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings
embedding = OpenAIEmbeddings(proxy_model_name='text-embedding-ada-002')

# Setting page title and header
st.set_page_config(page_title="FAQ chatbot", page_icon=":speech-balloon:", initial_sidebar_state="collapsed")
st.title("FAQ chatbot")

# Sidebar
st.sidebar.title("Administration")
restart_button = st.sidebar.button("Start again", key="restart")

# Connect to SAP HANA Cloud, which has vector engine enabled
import hana_ml.dataframe as dataframe
conn = dataframe.ConnectionContext(
                                   address  = SAP_HANA_CLOUD_ADDRESS,
                                   port     = SAP_HANA_CLOUD_PORT,
                                   user     = SAP_HANA_CLOUD_USER,
                                   password = SAP_HANA_CLOUD_PASSWORD, 
                                  )
conn.connection.isconnected()

# Reset everything
if restart_button:
    del st.session_state['messages_forui'] # Removing session of messages_forui causes a restart

# Get response from LLM
def get_response(prompt):

    # Get embedding of user's request
    user_question = prompt
    user_question = user_question.capitalize()
    user_question_embedding = embedding.embed_documents((user_question)) 
    user_question_embedding_str = str(user_question_embedding[0])
 
    # Get cosine similarity with vectorised questions in SAP HANA Cloud
    sql = f'''SELECT TOP 200 "AID", "QID", "QUESTION", COSINE_SIMILARITY("QUESTION_VECTOR", TO_REAL_VECTOR('{user_question_embedding_str}')) AS SIMILARITY
        FROM FAQ_QUESTIONS
        ORDER BY "SIMILARITY" DESC, "AID", "QID" '''
    df_remote = conn.sql(sql)

    # Select at least the best n candidates, or more in case more have high similarity
    top_n = max(df_remote.filter('SIMILARITY = 1').count(), 20)

    # Retrieve the topn candidates for further processing
    df_data = df_remote.head(top_n).select('AID', 'QID', 'QUESTION').collect()
    
    # Add ROWID, which will help with data processing later
    df_data['ROWID'] = df_data['AID'].astype(str) + '-' + df_data['QID'].astype(str) + ': '
    df_data = df_data[['ROWID', 'QUESTION']]

    # Turn Pandas dataframe into block of text, for use with LLM
    candiates_str = df_data.to_string(header=False,
                                  index=False,
                                  index_names=False)

    # Get best match from LLM
    llm_prompt = f'''
    Task: which of the following candidate questions is closest to this one?
    {user_question}
    Only return the ID of the selected question, not the question itself

    -----------------------------------

    Candidate questions. Each question starts with the ID, followed by a :, followed by the question
    {candiates_str}
    '''
    from gen_ai_hub.proxy.native.openai import chat
    messages = [{"role": "system", "content": llm_prompt}
               ]
    kwargs = dict(model_name=AI_CORE_MODEL_NAME, messages=messages)
    response = chat.completions.create(**kwargs)
    llm_response = response.choices[0].message.content

    # Based on the ID, which is returned by the LLM, get the corresponding questions and answers from the FAQ
    aid = qid = matching_question = None
    if len(llm_response.split('-')) == 2:
       aid, qid = llm_response.split('-')

       # From HANA Cloud get the question from the FAQ that matches the user request best
       df_remote = conn.table('FAQ_QUESTIONS').filter(f''' "AID" = '{aid}' AND "QID" = '{qid}' ''').select('QUESTION')
       matching_question = df_remote.head(5).collect().iloc[0,0]
    
       # From HANA Cloud get the predefined answer of the above question from the FAQ
       df_remote = conn.table('FAQ_ANSWERS').filter(f''' "AID" = '{aid}'  ''').select('ANSWER')
       matching_answer = df_remote.head(5).collect().iloc[0,0]
    else:
       matching_answer = "I don't seem to have an answer for that."

    # Obtain dynamic response if needed
    if matching_answer == "ACTION: Get lunch menu":
        response = get_menus_as_sentence()
    elif matching_answer == "Hi there":
        greetings_collection = ['Hi', 'Hello', 'Hi there', 'Howdy', 'Hiya']
        response = greetings_collection[randint(0, len(greetings_collection)-1)]
        matching_question = None # To avoid having the question from the FAQ displayed in the bot
    else:
        response = matching_answer

    # Collect 1 or many responses that are to be displayed for the user
    response_collection = []
    if matching_question == None:
        response_collection.append(response)
    else:
        response_collection.append('This question from the FAQ seems to match your question: ' + matching_question)
        response_collection.append('And the answer from the FAQ is: ' + response)
    return response_collection
     
# Start a chat by greeting the user
def start_chat():

    # Welcome message hardcoded
    response = 'Hello, I am an FAQ chatbot.' 
    st.session_state['messages_forui'].append(['assistant', response])

    response = 'How can I help?' 
    st.session_state['messages_forui'].append(['assistant', response])

# Continue the chat by responding to each request individually
def continue_chat(prompt):
    if(FAQBOT_LOGGING):
        print("FAQBot logging, prompt: " + prompt)
    st.session_state['messages_forui'].append(['user', prompt])

    response_collection = get_response(prompt)
    if(FAQBOT_LOGGING):
        print("FAQBot logging. response_collection: " + str(response_collection))

    for response in response_collection: 
        st.session_state['messages_forui'].append(['assistant', response])
    return response_collection 

# Initialise session state variables
if 'messages_forui' not in st.session_state:
    st.session_state['messages_forui'] = []
    # Start the chat (request initial message from the bot to start)
    start_chat()

# Container to display the chat history
response_container = st.container()
# Container to display the prompt in which the users enters their message
container = st.container()

# Display the user's prompt for text input
with container:
    user_input = st.chat_input(placeholder="Your message", key=None, max_chars=None, disabled=False, on_submit=None, args=None, kwargs=None)
    
    # On input from user:
    if  user_input:
        output = continue_chat(user_input)

# Display the conversation flow
if st.session_state['messages_forui']:
    with response_container:
        for i in range(len(st.session_state['messages_forui'])):
            spoken = st.session_state['messages_forui'][i]
            if spoken[0] == 'assistant':
                message(spoken[1], key=str(i), avatar_style='bottts', seed='Miss%20kitty') 
            elif spoken[0] == 'user':
                message(spoken[1], is_user=True, key=str(i) + '_user', avatar_style='adventurer', seed='Abby')