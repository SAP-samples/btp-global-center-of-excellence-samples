#!/usr/bin/env python
import asyncio
import json
from time import time
from langgraph.types import Command
from streamlit import session_state
from cache import *

st.set_page_config(page_title='Hands-On Timesheet Management Agent')

light_model, agent = init_resources()

review_icons = {
    0: ":material/check_circle:",  #approval
    1: ":material/cancel:",        #denial
    2: ":material/edit:"           #change
}

def resume_execution(id):
    meta_data = st.session_state[id]
    input_field_id = meta_data['input-id']
    review_id = meta_data['ids']
    st.session_state[id]['enabled'] = False
    review_feedback = [st.session_state[id] for id in review_id]
    user_changes = st.session_state[input_field_id]
    review_info = {'selections': review_feedback, 'user_changes': user_changes}
    command = Command(resume=json.dumps(review_info))
    st.session_state.command = command

def display_review_container(item):
    id, _, review = item
    if id not in st.session_state:
        st.session_state[id] = {'len': len(review), 'enabled': True, 'ids': [f'{id}-{i}' for i in range(len(review))], 'input-id': f'{id}-input'}
    meta_data = st.session_state[id]
    container = st.container(border=True)
    with container:
        st.subheader('Review changes')
        for i, text in enumerate(review):
            col1, col2 = st.columns([0.75, 0.25], vertical_alignment='center')
            with col1:
                st.write(text)
            with col2:
                st.pills('Review', range(3), format_func=lambda x: review_icons[x], selection_mode='single', key=f'{id}-{i}', label_visibility='collapsed', disabled=not meta_data['enabled'])
        st.write('---')
        all_reviewed = all([st.session_state[id] is not None for id in meta_data['ids']])
        col1, col2 = st.columns([0.85, 0.15], vertical_alignment='center')
        with col1:
            st.text_input('Changes', label_visibility='collapsed', placeholder='(Optional: Explain changes)', key=f'{id}-input', disabled=not meta_data['enabled'])
        with col2:
            st.button('SUBMIT', key=f'{id}-button', on_click=resume_execution, args=(id,), type='primary', disabled=not meta_data['enabled'] or not all_reviewed)

def display_chat_item(item):
    iid, item_type, item_content = item
    if item_type == 'status':
        with st.status(label=item_content['title'], state='complete'):
            st.write(item_content['explanation'])
    elif item_type == 'review':
        display_review_container(item)
    else:
        with st.chat_message(item_type): #avatar=f'{item_type}.png'
            st.markdown(item_content)

def append_chat(item_type, item_content, display=True):
    """Append item to chat history and display it."""
    item = (uuid.uuid1(), item_type, item_content)
    st.session_state.chat_history.append(item)
    if display:
        display_chat_item(item)

async def generate_status(queue):

    start = time()
    status = st.status('Reasoning')
    placeholder = status.empty()
    explanation = ""

    while True:
        message = await queue.get()
        if message is None:
            break
        tool_calls = message.tool_calls
        content = message.content

        if tool_calls:
            tool_info = [{'name': call['name'], 'args': call['args']} for call in tool_calls]
            input = f"Previous actions: {explanation} Tool info: {tool_info}, Reasoning: {content}"
            explainable_prompt = """
            Provide a concise explanation of the actions taken by updating the previous explanation.
            Write in the present participle keep it very short.
            The actions are performed by an agent helping the user log his work time. 
            Write as if you were taking the actions.
            """
            explanation = light_model.invoke([('system', explainable_prompt), ('user', input)]).content
            title = light_model.invoke([('system', 'Provide a concise title for the action. E.g.: Collecting information.'), ('user', input)]).content
        else:
            title = 'Reasoning'

        status.update(label=title)
        details = explanation
        placeholder.write(f"{details}")

    #update status
    time_delta = int(time() - start)
    title = f'The agent acted for {time_delta} seconds.'
    status.update(label=title, state='complete')
    append_chat('status', {'title': title, 'explanation': explanation}, display=False)

async def process_stream(updates):

    #display current status
    queue = asyncio.Queue(maxsize=1)
    gen_status_task  = asyncio.create_task(generate_status(queue))
    await asyncio.sleep(0)

    answer = ''
    for update in updates:
        if '__interrupt__' in update:
            print(f'Interrupt caught: {update}')
            st.session_state.interrupted = True
            answer = update['__interrupt__'][0].value['action']
        elif 'agent' in update:
            message = update['agent']['messages'][-1]
            print(message.pretty_repr())
            await queue.put(message)
            await asyncio.sleep(0)
            answer = message.content

    await queue.put(None)
    await gen_status_task

    return answer




def generate_response(user_input):
    config = {"configurable": {"thread_id": str(st.session_state.thread_id)}}

    if isinstance(user_input, (dict, Command)):
        text_response = asyncio.run(process_stream(agent.stream(user_input, config, stream_mode='updates')), debug=True)
    else:
        raise Exception(f'Invalid input type.')

    return text_response




def handle_input(user_input):
    if not user_input and not 'command' in st.session_state:
        return

    #interrupted
    if 'command' in st.session_state:
        user_input = st.session_state.command
        del st.session_state.command
        session_state.interrupted = False
    #not interrupted
    else:
        append_chat('user', user_input)
        user_input = {'messages': [('user', user_input)]}

    answer = generate_response(user_input)

    if st.session_state.interrupted:
        append_chat('review', list(answer))
    else:
        append_chat('assistant', answer)


def render_page():
    user_input = st.chat_input('Write your question:')
    st.title('Timesheet Management Agent')
    for message in st.session_state.chat_history:
        display_chat_item(message)
    handle_input(user_input)


render_page()