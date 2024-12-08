import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging
import pandas as pd
from typing import Dict, Any
import json
import re
from models import LawyerProfile
from constants import IS_TEST

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add browser-like headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

async def fetch_page(url: str, session: aiohttp.ClientSession) -> str:
    """Fetch a single page and return its HTML content"""
    try:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                return await response.text()
            else:
                logger.error(f"Error fetching {url}: Status {response.status}")
                return ""
    except Exception as e:
        logger.error(f"Exception while fetching {url}: {e}")
        return ""

def extract_main_content(html: str) -> str:
    """Extract main content from HTML, ignoring header and footer"""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove header and footer
        for elem in soup.find_all(['header', 'footer']):
            elem.decompose()
            
        # Find main content
        main_content = soup.find('main') or soup.find('div', class_='main-content')
        return main_content.get_text(strip=True) if main_content else soup.get_text(strip=True)
            
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return ""

async def scrape_lawyer_profile(url: str, session: aiohttp.ClientSession) -> dict:
    """Scrape a single lawyer's profile and return structured data"""
    html = await fetch_page(url, session)
    if not html:
        return {}
        
    raw_content = extract_main_content(html)
    parsed_data = await parse_lawyer_profile(raw_content)
    
    return {
        "url": url,
        "raw_content": raw_content,
        "structured_data": parsed_data
    }

async def scrape_all_lawyers() -> list[dict]:
    """Main function to scrape all lawyer profiles"""
    # Read URLs directly from CSV without headers
    if IS_TEST:
        csv_file = 'test.csv'
    else:
        csv_file = 'lawyers.csv'
    urls = pd.read_csv(csv_file, header=None)[0].tolist()
    
    # For testing, just use first few URLs
    test_urls = urls[:3]  # Start with 3 URLs for testing
    logger.info(f"Scraping {len(test_urls)} lawyers...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_lawyer_profile(url, session) for url in test_urls]
        results = await asyncio.gather(*tasks)
        
        # Log results
        for result in results:
            if result:  # Only log non-empty results
                logger.info(f"Successfully scraped: {result['url']}")
                logger.info(f"Content preview: {result['raw_content'][:200]}...")
        
        return results

async def parse_lawyer_profile(raw_content: str) -> Dict[str, Any]:
    """Parse lawyer profile using both regex and GPT"""
    
    # First pass: Use regex for reliable structured data
    basic_info = extract_basic_info(raw_content)
    
    try:
        # Combine regex and GPT results
        return {
            **basic_info,
        }
    except Exception as e:
        logger.error(f"Error parsing profile with GPT: {e}")
        return basic_info

def extract_basic_info(text: str) -> Dict[str, str]:
    """Extract basic information using regex"""
    info = {}
    
    # These patterns are more likely to be consistent
    extract_method = {
        
    }
    patterns = {
        'email': r'[\w\.-]+@[\w\.-]+',
        'phone': r'(?:\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',
        'bar_numbers': r'Bar No\.\s*\d+',
    }
    
    for field, pattern in patterns.items():
        if match := re.search(pattern, text):
            info[field] = match.group(0)
            
    return info

async def scrape_lawyer(url: str) -> LawyerProfile:
    logger.info(f"Scraping lawyer profile from: {url}")

    async with aiohttp.ClientSession() as session:
        result = await scrape_lawyer_profile(url, session)

        if result:
            logger.info(f"Successfully scraped: {result['url']}")
            logger.info(f"Content preview: {result['raw_content'][:200]}...")
        else:
            logger.error(f"Failed to scrape: {link}")
            
        return result