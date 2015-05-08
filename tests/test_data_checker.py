import os
import unittest
from jacqq import check_data_dirty


class TestDataChecker(unittest.TestCase):
    def setUp(self):
        self.folder = os.getcwd() + os.sep + 'datasets' + os.sep + 'dirty_data' + os.sep

    def check_data_dirty(self, details, histories, focus=None, exposure=False, weights=False):
        if focus:
            focus_path = self.folder + focus + '.csv'
        else:
            focus_path = None
        return check_data_dirty(self.folder + details + '.csv', self.folder + histories + '.csv',
                                focus_path, True, True)

    def test_clean_data(self):
        errors = self.check_data_dirty('details_clean', 'histories_clean', 'focus_clean', True, True)
        self.assertEqual(errors, [])

    def test_bad_headers(self):
        errors = self.check_data_dirty('details_bad_header', 'histories_bad_header', 'focus_bad_header', True, True)
        self.assertEqual(len(errors), 6)

    def test_missing_attributes(self):
        errors = self.check_data_dirty('details_missing_attr', 'histories_missing_attr',
                                       'focus_missing_attr', True, True)
        self.assertEqual(len(errors), 4)

    def test_missing_values(self):
        errors = self.check_data_dirty('details_empty_fields', 'histories_empty_fields',
                                       'focus_empty_fields', True, True)
        self.assertEqual(len(errors), 4)

    def test_wrong_data_types(self):
        errors = self.check_data_dirty('details_wrong_types', 'histories_wrong_types', 'focus_wrong_types', True, True)
        self.assertEqual(len(errors), 11)

    def test_all_cases(self):
        errors = self.check_data_dirty('details_all_cases', 'histories_clean', 'focus_clean', True, True)
        self.assertEqual(errors, ["File 'details_all_cases': Details data can not only contain cases"])

    def test_all_controls(self):
        errors = self.check_data_dirty('details_all_controls', 'histories_clean', 'focus_clean', True, True)
        self.assertEqual(errors, ["File 'details_all_controls': Details data can not only contain controls"])

    def test_missing_ids(self):
        errors = self.check_data_dirty('details_clean', 'histories_missing_ids')
        self.assertEqual(len(errors), 3)

    def test_start_end_dates(self):
        errors = self.check_data_dirty('details_clean', 'histories_bad_dates', 'focus_bad_dates', True, True)
        self.assertEqual(len(errors), 4)