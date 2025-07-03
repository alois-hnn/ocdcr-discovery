import unittest
from tests import conformance_checking, test_log_management

class TestOCPA(unittest.TestCase):

    def test_process_execution_extraction_conformance(self):
        conformance_checking.test_process_execution_extraction()

    def test_process_execution_extraction_log_management(self):
        test_log_management.test_process_execution_extraction()

    def test_variants_log_management(self):
        test_log_management.test_variants()

    def test_process_execution_extraction_by_leading_type(self):
        test_log_management.test_process_execution_extraction__by_leading_type()

if __name__ == '__main__':
    unittest.main()