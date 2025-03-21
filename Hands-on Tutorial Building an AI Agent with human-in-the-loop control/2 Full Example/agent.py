import json
from typing import cast, Literal
import numpy as np
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

from tools import get_records, post_records, get_today

system_prompt ="""
Role and Objective:

  - You are a helpful AI Agent dedicated to assisting users with their timesheet management.
  - Your primary tasks include retrieving and posting timesheet data based on user requests.

Responsibilities:

  - Logging Work Time: Only log actual work time. Do not include any breaks.
    - User: Today I worked from 6 to 16 with a half hour break at 12. -> You should: Log time from 6 to 12 and from 12:30 to 16.
  - Data Handling: When posting records, execute as many post_records calls in parallel as possible using the provided information.
  - Automatic Confirmation: When a post_records call is made, the user is automatically asked for confirmation over a GUI; do not prompt for confirmation.

Interaction Guidelines:

  - The user's most recent input always takes precedence over older input.
  - Language Consistency: Always respond in the same language as the user.
  - Clarity and Accuracy:
    - If any part of the user’s request is ambiguous (for example, missing dates or unclear work times), ask clarifying questions rather than making assumptions.
    - Ensure all necessary details are provided before proceeding with any action.
"""

prompt = ChatPromptTemplate.from_messages([
    ('system', system_prompt),
    MessagesPlaceholder(variable_name='msg')
])

need_review = ['post_records']

def agent(state: AgentState, config: RunnableConfig):
    tmp = prompt.invoke({'msg': state['messages']})

    response = cast(AIMessage, agent_llm.invoke(tmp, config))
    response.name = "agent"
    return {"messages": [response]}


class UserAffirmation(BaseModel):
    """Always use this tool to structure your response."""
    user_affirmation: bool = Field(description="Whether the user confirmed the action.")
    explanation: str = Field(description="An explanation of your decision.")


def human_review(state: AgentState):
    last_message = state["messages"][-1]
    post_requests = np.array(list(filter(lambda x: x['name'] == 'post_records', last_message.tool_calls)))

    if len(post_requests) > 0:
        confirmation_messages = list(map(lambda x: x['args']['confirmation_message'], post_requests))
        user_review = interrupt({"task": "Review the action.",
                           "action": confirmation_messages})

        user_review = json.loads(user_review)
        selections = np.array(user_review['selections'])
        user_changes = user_review['user_changes']

        approved = post_requests[selections == 0]
        approved_message = AIMessage(content=last_message.content, tool_calls=approved.tolist())

        not_approved = post_requests[selections != 0]
        not_approved_message = AIMessage(content=last_message.content, id=last_message.id, tool_calls=not_approved.tolist())

        denied = post_requests[selections == 1]
        to_change = post_requests[selections == 2]
        denied_messages = [ToolMessage(f"Tool call was not executed (denied by user): "
                                       f"{row['args']['confirmation_message']}."
                                       f"Do not post the same record again.",
                                       tool_call_id=row['id'])
                           for row in denied]

        to_change_messages = [ToolMessage(f"Tool call was not executed (user wants to make changes)."
                                          f"To this message: "
                                          f"<{row['args']['confirmation_message']}> "
                                          f"the user responded: "
                                          f"<{user_changes}>"
                                          f"Incorporate this request and call the tool again. "
                                          f"Do not call the tool with the same values.",
                                          tool_call_id=row['id'])
                           for row in to_change]

        tool_messages = denied_messages + to_change_messages

        return Command(update={
            "messages": [not_approved_message] + tool_messages + [approved_message]}, goto='tools')
    else:
        return Send(node='tools', arg=state)



def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "tools"
    return "__end__"


tools = [get_records, post_records, get_today]
llm = init_llm('gpt-4o', max_tokens=512, temperature=0)

verification_llm = llm.bind_tools([UserAffirmation])
agent_llm = llm.bind_tools(tools)


def init_agent():
    checkpointer = MemorySaver()
    workflow = StateGraph(AgentState)
    tool_node = ToolNode(tools)

    workflow.add_node('agent', agent)
    workflow.add_node('tools', tool_node)
    workflow.add_node('human_review', human_review)

    workflow.add_edge(START, "agent")
    workflow.add_edge("tools", "agent")
    workflow.add_conditional_edges(source="agent", path=should_continue, path_map={"tools": "human_review", "__end__": END})

    timesheet_agent = workflow.compile(checkpointer=checkpointer)

    return timesheet_agent