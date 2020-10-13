import unittest
import anthill


class TestExample(unittest.TestCase):

    def test_one(self):
        self.assertEqual(6, 6)


if __name__ == '__main__':
    unittest.main()