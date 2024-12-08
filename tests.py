import unittest
import asyncio
from unittest.mock import patch, MagicMock
from main import process_query, load_lawyer_data

class TestLawyerSearch(unittest.TestCase):
    def setUp(self):
        # Sample test data
        self.test_lawyer_data = {
            "http://example.com/lawyer1": {
                "raw_content": "Worked on major cases for ABC Network and NBC",
                "structured_data": {
                    "name": "John Smith",
                    "experience": "Media law expert, handled TV network cases",
                    "education": "Yale Law School"
                }
            },
            "http://example.com/lawyer2": {
                "raw_content": "Corporate lawyer specializing in mergers",
                "structured_data": {
                    "name": "Jane Doe", 
                    "experience": "Corporate law",
                    "education": "Harvard Law School"
                }
            }
        }

    @patch('main.load_lawyer_data')
    async def test_tv_network_query(self, mock_load_data):
        mock_load_data.return_value = self.test_lawyer_data
        query = "lawyers who worked on cases with TV networks"
        results = await process_query(query)
        
        # Should find lawyer1 but not lawyer2
        self.assertEqual(len(results), 1)
        self.assertIn("John Smith", str(results))
        self.assertNotIn("Jane Doe", str(results))

    @patch('main.load_lawyer_data')  
    async def test_education_query(self, mock_load_data):
        mock_load_data.return_value = self.test_lawyer_data
        query = "lawyers who went to Yale"
        results = await process_query(query)
        
        self.assertEqual(len(results), 1)
        self.assertIn("John Smith", str(results))
        self.assertNotIn("Jane Doe", str(results))

    def test_load_lawyer_data(self):
        # Test that the data loading function returns a dictionary
        data = load_lawyer_data()
        self.assertIsInstance(data, dict)

def run_async_tests():
    # Helper function to run async tests
    loop = asyncio.get_event_loop()
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestLawyerSearch)
    loop.run_until_complete(asyncio.gather(
        *(test for test in test_suite if test._testMethodName.startswith('test_'))
    ))

if __name__ == '__main__':
    run_async_tests()
