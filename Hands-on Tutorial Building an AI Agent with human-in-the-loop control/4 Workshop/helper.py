
from IPython.display import HTML, display
import base64
import uuid
from typing import cast, Literal
from IPython.core.display_functions import display
from gen_ai_hub.proxy.langchain import init_llm
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import interrupt, Command, Send
from pydantic import Field, BaseModel
# from helper import display_graph
from gen_ai_hub.proxy.langchain.google_vertexai import init_chat_model as google_vertexai_init_chat_model
# from tools import ExternalTimeData, get_records, post_records #, get_today
from datetime import date
import os
import urllib.parse
import uuid
from datetime import date, datetime
from typing import TypedDict
import requests
from langchain_core.tools import tool
import getpass, socket, hashlib
from dotenv import load_dotenv


def display_graph(graph):
    merm = graph.get_graph().draw_mermaid()

    html_doc = f"""<!doctype html>
    <html><head><meta charset="utf-8"></head>
    <body>
    <div class="mermaid">{merm}</div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{ startOnLoad: true }});</script>
    </body></html>
    """

    b64 = base64.b64encode(html_doc.encode("utf-8")).decode("ascii")
    display(HTML(f'''
    <iframe
    sandbox="allow-scripts"
    src="data:text/html;base64,{b64}"
    style="width:100%;height:480px;border:0;">
    </iframe>
    '''))

# os.environ["PAYROLL_API_KEY"] = "<YOUR API KEY>"
# API_KEY = os.environ.get("PAYROLL_API_KEY")
API_KEY = "KEY"

seed = f"{getpass.getuser()}@{socket.gethostname()}"
user_id = hashlib.sha256(seed.encode()).hexdigest()[:12]


get_header = {
    'Accept': 'application/json',
    'APIKey': API_KEY,
    "DataServiceVersion": "2.0"
}

post_header = {
    'Content-Type': 'application/json',
    'APIKey': API_KEY,
    "DataServiceVersion": "2.0"
}

class ExternalTimeData(TypedDict):
    startDate: str
    startTime: str
    endTime: str

def build_post_payload(data: ExternalTimeData, base_url):
    # Convert startDate to OData format and add userId
    payload = dict(data)
    payload['startDate'] = f"/Date({int(datetime.fromisoformat(data['startDate']).timestamp()) * 1000})/"
    payload['externalCode'] = str(uuid.uuid1())
    payload['userId'] = user_id
    payload["userIdNav"] = {
        "__metadata": {
            "uri": f"{base_url}User('{user_id}')"
        }
    }
    # Define url
    table = 'ExternalTimeData'
    url = f'{base_url}{table}'

    return payload, url


def process_output(stream):
    for token in stream: 
        (key, content), = token.items()
        if key == "__interrupt__":
           print(content[0])
           return True 
        if content is not None:
           content['messages'][-1].pretty_print()
    print("\n")
    return False

test_cases = [
    ("Yes, proceed with logging", True, "Clear confirmation"),
    ("No, don't do that", False, "Clear rejection"),
    ("I'm not sure", False, "Uncertainty"),
    ("Go ahead", True, "Confirmation"),
    ("That looks right", True, "Confirmation"),
    ("Wait, let me think", False, "Hesitation"),
    ("Perfect!", True, "Strong confirmation"),
    ("Actually, no", False, "Rejection"),
    ("Maybe later", False, "Indirect rejection"),
]

def unit_test(verification_llm, system_prompt):
    print("Verification test results:\n")
    for text, expected, label in test_cases:
        ans = verification_llm.invoke([('system', system_prompt), ('user', text)])
    # print(f"AI Response: {ans.content}" if ans.content else "No AI Message.")
        if ans.tool_calls:
            args = ans.tool_calls[0]['args']
            got = args['user_affirmation']
            expl = args['explanation']
        else:
            got, expl = None, "No tool call returned."
        status = "✓" if got == expected else "✗"
        print(f"{status} [{label}] '{text}' -> {got} (expected {expected}) | {expl}")