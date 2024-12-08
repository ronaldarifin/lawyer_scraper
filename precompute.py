import json
import pandas as pd
from scraping_utils import scrape_lawyer
from llm_utils import async_llm, async_get_embedding
import asyncio
from constants import IS_TEST

def load_lawyers_data():
    with open('lawyer_data.json', 'r') as file:
        content = file.read().strip()
        if not content:
            return {}
        data = json.loads(content)
    return data

def load_lawyer_links():
    if IS_TEST:
        csv_file = 'test.csv'
    else:
        csv_file = 'lawyers.csv'
    return pd.read_csv(csv_file, header=None)[0].tolist()

async def update_lawyer_data():
    lawyers = load_lawyers_data()
    lawyer_links = load_lawyer_links()
    
    async def process_lawyer(lawyer_link):
        if lawyer_link not in lawyers:
            try:
                scraped_data = await scrape_lawyer(lawyer_link)
                
                system_prompt = """You are the best lawyer parser. Always respond with valid JSON format.
                The JSON should include fields like name, practice_areas, education, and experience."""
                
                user_prompt = f"""Convert the text below into structured JSON data. 
                Ensure the response is a valid JSON object.: 
                
                {scraped_data['raw_content']}"""

                structured_data_str = await async_llm(system_prompt=system_prompt, user_prompt=user_prompt)
                
                # Clean up JSON response
                structured_data_str = structured_data_str.strip()
                if structured_data_str.startswith("```json"):
                    structured_data_str = structured_data_str.split("```json")[1]
                if structured_data_str.endswith("```"):
                    structured_data_str = structured_data_str.rsplit("```", 1)[0]
                
                structured_data = json.loads(structured_data_str)

                # Format text for embedding
                lawyer_text = f"""
                {scraped_data['raw_content']}
                {' '.join([f'{k}: {v}' for k,v in structured_data.items()])}
                """
                print(lawyer_text)
                
                # Get embedding asynchronously
                embedding = (await async_get_embedding([lawyer_text]))[0]
                
                return lawyer_link, {
                    "raw_content": scraped_data["raw_content"],
                    "structured_data": structured_data,
                    "embedding": embedding
                }
            except Exception as e:
                print(f"Error processing {lawyer_link}: {str(e)}")
                return None
    
    # Create and run all tasks at once
    tasks = [process_lawyer(link) for link in lawyer_links if link not in lawyers]
    results = await asyncio.gather(*tasks)
    
    # Update lawyers dictionary and save to file
    for result in results:
        if result:
            link, data = result
            lawyers[link] = data
            print(f"Writing data for lawyer link: {link}")
            print_data = {
                "raw_content": data["raw_content"],
                "structured_data": data["structured_data"]
            }
            print(json.dumps(print_data, indent=2))
    
    # Write all results to file at once
    try:
        with open('lawyer_data.json', 'w') as f:
            json.dump(lawyers, f, indent=2)
        print("All data successfully written to lawyer_data.json")
    except Exception as e:
        print(f"Failed to write data to lawyer_data.json: {e}")

# Run the async function using asyncio
if __name__ == "__main__":
    asyncio.run(update_lawyer_data())