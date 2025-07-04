import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(
    base_url="http://localhost:8001/v1",
    api_key="not-needed"
)

async def semantic_search_facts(query: str, facts: list) -> list:
    """Uses the LLM to find relevant facts based on semantic meaning."""
    if not facts:
        return []

    prompt = get_semantic_search_prompt(query, facts)
    try:
        response = await client.chat.completions.create(
            model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that performs semantic search."}, # A simple system prompt
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )
        # The prompt asks for a JSON object with a "relevant_facts" key
        result = json.loads(response.choices[0].message.content)
        return result.get("relevant_facts", [])
    except Exception as e:
        print(f"Error during semantic search: {e}")
        return []

def get_semantic_search_prompt(query: str, facts: list) -> str:
    """Creates a prompt for the LLM to perform semantic search."""
    facts_str = "\n".join(f"- {fact}" for fact in facts)
    return f"""A user is asking the following question: "{query}"

Here is a list of stored facts:
{facts_str}

Please analyze the user's question and the stored facts. Identify which of the facts are relevant to the user's question.

Return a JSON object with a single key, "relevant_facts", which is a list of the facts you identified as relevant.

Example:
User Query: "How old am I?"
Facts:
- I am 10 years old.
- My favorite food is chicken.
- I hate to eat duck.

Result:
{{
    "relevant_facts": [
        "I am 10 years old."
    ]
}}
"""