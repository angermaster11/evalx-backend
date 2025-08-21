from typing_extensions import TypedDict

class State(TypedDict):
    mode: str
    file_path: str
    content: str
    output: dict | None
