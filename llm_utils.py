from openai import OpenAI
from models import LawyerProfile
from concurrent.futures import ThreadPoolExecutor
import asyncio
import numpy as np
from typing import Dict, List
from openai import AsyncOpenAI
from constants import PRIMARY_MODEL, MINI_MODEL, EMBEDDING_MODEL_LARGE, EMBEDDING_MODEL_SMALL, IS_DEBUG_MODE, OPENAI_KEY

openai_client = OpenAI(api_key=OPENAI_KEY)
client = AsyncOpenAI(api_key=OPENAI_KEY)

async def async_get_embedding(texts, size=EMBEDDING_MODEL_LARGE):
    """
    Get embeddings for the given texts using the specified model size.

    Args:
        texts (list): List of text strings to embed.
        size (str): Model size to use for embedding. Defaults to EMBEDDING_MODEL_SMALL.

    Returns:
        list: List of embeddings (dimensions: 1536 for small, 3072 for large) for the input texts.
    """
    cleaned_texts = [text.replace('\n', ' ').replace('\t', ' ').strip() for text in texts if text]
    response = await client.embeddings.create(input=cleaned_texts, model=size)
    return [item.embedding for item in response.data]

def get_embedding(texts, size=EMBEDDING_MODEL_LARGE):
    """
    Get embeddings for the given texts using the specified model size.

    Args:
        texts (list): List of text strings to embed.
        size (str): Model size to use for embedding. Defaults to EMBEDDING_MODEL_SMALL.

    Returns:
        list: List of embeddings (dimensions: 1536 for small, 3072 for large) for the input texts.
    """
    cleaned_texts = [text.replace('\n', ' ').replace('\t', ' ').strip() for text in texts if text]
    response = openai_client.embeddings.create(input=cleaned_texts, model=size)
    return [item.embedding for item in response.data]


async def async_llm(model=MINI_MODEL, system_prompt=None, user_prompt=None, assistant_prompt = None, params = None):
    if IS_DEBUG_MODE:
        print(f"performing async_llm with prommpt: {user_prompt}")
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if assistant_prompt:
        messages.append({"role": "assistant", "content": assistant_prompt})
    if user_prompt:
        messages.append({"role": "user", "content": user_prompt})

    body = {
        "model": model,
        "messages": messages,
        "temperature": 0
    }

    if params:
        body.update(params)

    response = await client.chat.completions.create(**body)
    return response.choices[0].message.content

async def do_async(questions=None, system_prompt=None, assistant_prompt=None, model=None, params=None):
    """
    Asynchronously process multiple questions using the async_llm function.
    
    Args:
        questions (List[str]): List of questions/prompts to process. If None, uses default questions.
        system_prompt (str, optional): System prompt to use for all questions
        assistant_prompt (str, optional): Assistant prompt to use for all questions
        model (str, optional): Model to use for generation
        params (dict, optional): Additional parameters for the API call
        
    Returns:
        dict: Dictionary mapping questions to their corresponding answers
    """
    if questions is None:
        questions = ["who is tony stark", "who is benjamin franklin", "who is george washington"]
    
    coros = [
        async_llm(
            user_prompt=question,
            system_prompt=system_prompt,
            assistant_prompt=assistant_prompt,
            model=model,
            params=params
        ) for question in questions
    ]
    
    result = await asyncio.gather(*coros)
    
    qa_pairs = dict(zip(questions, result))
    
    if IS_DEBUG_MODE:
        print("\n=== Results ===")
        for question, answer in qa_pairs.items():
            print(f"\nQ: {question}")
            print(f"A: {answer}")
            print("-" * 50)
        
    return qa_pairs

def llm(model=MINI_MODEL, system_prompt=None, user_prompt=None, assistant_prompt=None, params=None):
    """
    Generate a response using the OpenAI language model.

    Args:
        model (str): The model to use for generation. Defaults to MINI_MODEL.
        system_prompt (str, optional): The system prompt to use.
        user_prompt (str, optional): The user prompt to use.
        assistant_prompt (str, optional): The assistant prompt to use.
        params (dict, optional): Additional parameters for the API call.

    Returns:
        str: The generated response from the language model.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if assistant_prompt:
        messages.append({"role": "assistant", "content": assistant_prompt})
    if user_prompt:
        messages.append({"role": "user", "content": user_prompt})

    body = {
        "model": model,
        "messages": messages,
        "temperature": 0
    }

    if params:
        body.update(params)

    response = openai_client.chat.completions.create(**body)
    return response.choices[0].message.content

def cosine_search(cutoff_threshold: float, embeddings: Dict[str, List[float]], query: str) -> List[str]:
    """
    Perform cosine similarity search between query and embeddings.
    
    Args:
        cutoff_threshold (float): Minimum similarity threshold (e.g., 0.8).
        embeddings (Dict[str, List[float]]): Dictionary of lawyer URLs to their embeddings.
        query (str): Search query to compare against.
        
    Returns:
        List[str]: List of lawyer URLs that exceed the similarity threshold, sorted by similarity.
    """
    # Enhance query
    enhanced_query = f"Find a lawyer: {query}"  # Adds context
    
    query_embedding = np.array(get_embedding([enhanced_query])[0])
    
    # Normalize query embedding for efficient cosine similarity calculation
    query_norm = np.linalg.norm(query_embedding)
    
    results = []
    for lawyer_url, lawyer_embedding in embeddings.items():
        lawyer_embedding = np.array(lawyer_embedding)
        
        # Compute cosine similarity
        similarity = np.dot(query_embedding, lawyer_embedding) / (query_norm * np.linalg.norm(lawyer_embedding))
        print(f"Lawyer URL: {lawyer_url}, Similarity: {similarity}")
        # Append results above threshold
        if similarity >= cutoff_threshold:
            results.append((lawyer_url, similarity))
    
    # Sort results by similarity in descending order and return only URLs
    return [url for url, _ in sorted(results, key=lambda x: x[1], reverse=True)]