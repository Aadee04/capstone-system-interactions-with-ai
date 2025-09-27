from langchain.tools import tool

@tool
def talk_to_user(message: str = "") -> str:
    """Continue a conversation with the user. Input is the message in string. Output displays message to the user, and is always successful."""
    return message
