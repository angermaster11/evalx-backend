from fastapi import APIRouter, Request, HTTPException
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain   

router = APIRouter()

@router.post("/round3")
async def ask_question(request: Request):
    data = await request.json()
    content = data.get("content")
    codespace = data.get("codespace")
    llm  = ChatOpenAI(model="gpt-4",temperature=0.2)
    template = """
    You are a Interview Simulator.
    Ask question related to {content} and {codespace}
    Ask only question in json for example - 
    {
        "question": "What is main idea of {content}?"
    }
    """
    prompt = ChatPromptTemplate.from_template(template  )
    chain = LLMChain(llm=llm, prompt=prompt)
    response = await chain.ainvoke({"content": content, "codespace": codespace})