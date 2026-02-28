from typing import TypedDict


class AgentState(TypedDict):
    iot_message: dict
    agent_response: str
    sensor_type: str
