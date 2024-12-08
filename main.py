from llm_utils import async_llm, cosine_search
from scraping_utils import scrape_all_lawyers
import asyncio
import json
from precompute import update_lawyer_data, load_lawyers_data
from typing import Dict, List, Union
from constants import EMBEDDING_CUTOFF, IS_DEBUG_MODE
import ast

async def passes_criterion(text, query: str) -> bool:
    """
    Evaluate if a lawyer passes a given criterion based on their profile.

    Args:
        lawyer_url (str): URL of the lawyer's profile
        query (str): Criterion to evaluate against

    Returns:
        bool: True if lawyer passes the criterion, False otherwise
    """
    system_prompt = """
    You are evaluating a lawyer whether they pass a given criterion.
    
    Respond in the following format:
    <thinking>...</thinking>, within which you include your detailed thought process.
    <answer>...</answer>, within which you include your final answer. "Pass" or "Fail".
    """.strip()
    
    user_prompt = f"""
    You are an expert lawyer searcher.
    Find a lawyer that meets this requirement: {query}
    Here is the lawyer's profile: {text}
    """.strip()

    print(f"USER_PROMPT: {user_prompt}")
    
    if IS_DEBUG_MODE:
        print(f"\nEvaluating criterion: '{query}' for lawyer profile...")
    response = await async_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    return response.split('<answer>')[1].split('</answer>')[0].strip() == 'Pass'

def format_result(lawyer_urls: List[str], query: str):
    print("\n" + "="*50)
    print(f"Search Results for: '{query}'")
    print("-"*50)
    if lawyer_urls:
        print("Matching lawyers:")
        for url in lawyer_urls:
            print(f"- {url}")
    else:
        print("No lawyers found matching criteria")
    print("="*50 + "\n")

async def process_search(lawyer_embeddings: Dict[str, List[float]], query: str, lawyers_dict) -> list:
    print("\nComputing similarities...")
    lawyer_urls = cosine_search(EMBEDDING_CUTOFF, lawyer_embeddings, query)
    print("\nEvaluating criteria...")
    coros = [passes_criterion(lawyers_dict[lawyer_url]['structured_data'], query) for lawyer_url in lawyer_urls]
    results = await asyncio.gather(*coros)
    filtered_urls = [url for url, passed in zip(lawyer_urls, results) if passed]
    return filtered_urls

def parse_queries(input_str: str) -> Union[List[str], None]:
    """
    Parse input string into a list of queries.
    Returns None if input is invalid or 'Q' to quit.
    """
    if input_str == 'Q':
        return None
    try:
        queries = ast.literal_eval(input_str)
        if not isinstance(queries, list):
            print("Error: Input must be a list of strings")
            return None
        return queries
    except (ValueError, SyntaxError) as e:
        print(f"Error parsing input: {e}")
        print("Please ensure your input is formatted correctly, e.g., ['query1', 'query2']")
        return None

async def handle_single_query(lawyer_embedding_task, lawyers_dict):
    """Handle single query mode"""
    query = input("Enter your query:\n")
    lawyer_urls = await process_search(lawyer_embedding_task, query, lawyers_dict)
    format_result(lawyer_urls, query)

async def handle_multiple_queries(lawyer_embedding_task, lawyers_dict):
    """Handle multiple queries mode"""
    queries_input = input("Enter your queries as ['query1', 'query2', ...] or 'Q' to exit:\n")
    queries = parse_queries(queries_input)
    if queries:
        # Collect all results first
        all_results = []
        for query in queries:
            lawyer_urls = await process_search(lawyer_embedding_task, query, lawyers_dict)
            all_results.append((query, lawyer_urls))
        
        # Print all results at the end
        for query, lawyer_urls in all_results:
            format_result(lawyer_urls, query)

async def run_program():
    # Initialize data
    await update_lawyer_data()
    lawyers_dict = load_lawyers_data()
    lawyer_embedding_task = {k: lawyers_dict[k]['embedding'] for k in lawyers_dict}

    # Command mapping
    commands = {
        'Q': None,
        'List': handle_multiple_queries,
        'Single': handle_single_query
    }

    while True:
        print("\nAvailable commands:")
        print("- 'Single': Search with a single query")
        print("- 'List': Search with multiple queries")
        print("- 'Q': Quit")
        
        command = input("Enter command: ").strip()
        
        if command == 'Q':
            break
        
        handler = commands.get(command)
        if handler:
            await handler(lawyer_embedding_task, lawyers_dict)
        else:
            print("Invalid command. Please try again.")

async def main():
    await run_program()

if __name__ == '__main__':
    asyncio.run(main())
