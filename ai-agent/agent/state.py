from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    iot_message: dict
    agent_response: str
    sensor_type: str
    trigger: str  # "running_start" | "running_stop" | "none"
    messages: Annotated[list[BaseMessage], add_messages]
