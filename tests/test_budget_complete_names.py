from collections import Counter
import unittest
from scripts.analyze_vakra_output_budget_complete_v1 import comma_names


class NameChecks(unittest.TestCase):
    def test_complete_list_and_duplicate_omission(self):
        target=Counter(['A One','B Two','C Three'])
        self.assertEqual(Counter(comma_names('Names:\n\nC Three, A One, B Two')),target)
        self.assertNotEqual(Counter(comma_names('Names:\n\nA One, B Two, B Two')),target)

    def test_unexpected_format_rejected(self):
        with self.assertRaises(ValueError):comma_names('Names: A One')
        with self.assertRaises(ValueError):comma_names('Names:\n\nA One, B Two\nAnd others')


if __name__=='__main__':unittest.main()
