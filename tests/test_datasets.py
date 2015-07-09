# This file is part of a test for jacqq.py
# Copyright (C) 2015 Saman Jirjies - sjirjies(at)asu(dot)edu.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
from nose.tools import assert_almost_equals
import os
import csv

from jacqq import QStatsStudy
from jacqq import _load_csv_file as load_csv_file

# TODO: Test the dates with less than k+1 points


class DataTestHelper:
    round_digits = 8

    def __init__(self, folder_name, k=5, exposure=False, weights=False, alpha=0.05, shuffles=99, correction=None,
                 suppress_controls=True):
        self.k = k
        self.exposure = exposure
        self.weights = weights
        self.alpha = alpha
        self.shuffles = shuffles
        self.correction = correction
        self.suppress_controls = suppress_controls
        folder = os.getcwd() + os.sep + 'datasets' + os.sep + folder_name + os.sep
        self.folder = folder
        self.folder_name = folder_name
        study = QStatsStudy(folder + 'details.csv', folder + 'histories.csv', folder + 'focus.csv')
        self.results = study.run_analysis(self.k, self.exposure, self.weights, self.alpha,
                                          self.shuffles, self.correction, suppress_controls=suppress_controls)
        self.correct_global = self.load_csv_int_dict(folder + 'correct_global.csv')
        self.test_alpha_assignment()
        self.test_exposure_assignment()
        self.test_weights_assignment()
        self.test_alpha_assignment()
        self.test_shuffles_assignment()
        self.test_correction_assignment()
        self.test_global_Q()
        self.test_global_Qf()
        self.test_local_results()
        self.test_focus_results()
        self.test_focus_local_results()
        self.test_cases_result()
        self.test_date_results()

    @staticmethod
    def extract_attributes(legend, rows, attributes):
        modified_rows = []
        for row in rows:
            collected_attributes = []
            for attr in attributes:
                if row[legend[attr]] is None:
                    val = ""
                else:
                    try:
                        val = float(row[legend[attr]])
                        val = round(val, DataTestHelper.round_digits)
                    except ValueError:
                        val = str(row[legend[attr]])
                collected_attributes.append(str(val))
            modified_rows.append(tuple(collected_attributes))
        return modified_rows

    @staticmethod
    def convert_row_to_legend(row):
        legend = {}
        for index, item in enumerate(row):
            legend[item] = index
        return legend

    @staticmethod
    def load_csv_int_dict(file_path):
        with open(file_path, 'r') as csv_file:
            dictionary = {}
            csv_reader = csv.reader(csv_file)
            for line in csv_reader:
                dictionary[line[0]] = line[1]
            return dictionary

    def check_correct(self, correct_rows, result_rows, attributes, file_name):
        correct_length, result_length = len(correct_rows), len(result_rows)
        assert correct_length == result_length, \
            "Different number of correct rows (%s) than result rows (%s)" % (correct_length, result_length)
        for correct in correct_rows:
            if correct not in result_rows:
                print(correct_rows)
                print(result_rows)
            assert correct in result_rows, \
                "Row with correct values %s not found in %s results with attributes %s in folder '%s'." \
                % (str(correct), file_name, attributes, self.folder_name)

    def test_data_set(self, attributes, file_name, results):
        correct_legend, correct_rows = load_csv_file(self.folder + file_name)
        result_legend, result_rows = results
        correct_rows = DataTestHelper.extract_attributes(correct_legend, correct_rows, attributes)
        legend = DataTestHelper.convert_row_to_legend(result_legend)
        result_rows = DataTestHelper.extract_attributes(legend, result_rows, attributes)
        self.check_correct(correct_rows, result_rows, attributes, file_name)

    def test_k_assignment(self):
        assert self.results.k == self.k, \
            "Output value for k (%s) not input k (%s)" % (str(self.results.k), str(self.k))

    def test_exposure_assignment(self):
        assert self.results.exposure_enabled == self.exposure, \
            "Input exposure (%s) not output exposure (%s)" % (str(self.results.exposure_enabled), str(self.exposure))

    def test_weights_assignment(self):
        assert self.results.case_weights_enabled == self.weights, \
            "Input weight option (%s) not output weight (%s)" % (str(self.results.case_weights_enabled), str(self.weights))

    def test_alpha_assignment(self):
        assert self.results.submitted_alpha == self.alpha, \
            "Input alpha (%s) not equal to output alpha (%s)" % (str(self.results.submitted_alpha), str(self.alpha))

    def test_shuffles_assignment(self):
        perm_shuffles = self.results.number_permutation_shuffles
        assert perm_shuffles == self.shuffles, \
            "Output shuffles (%s) does not match input shuffles (%s)" % (str(perm_shuffles), str(self.shuffles))

    def test_correction_assignment(self):
        adj_method = self.results.alpha_adjustment_method
        input_corr = str(self.correction).upper()
        assert adj_method == input_corr, \
            "Output correction method (%s) does not match input method (%s)" % (str(adj_method), input_corr)

    def test_global_Q(self):
        q_result = self.results.Q_case_years[0]
        correct_result = float(self.correct_global['Q_case_years'])
        assert_almost_equals(q_result, correct_result,
                             msg="Result Q (%f) does not match correct Q (%f) in '%s'" %
                                 (q_result, correct_result, self.folder_name))

    def test_global_Qf(self):
        qf_result = self.results.Qf_case_years[0]
        correct_result = float(self.correct_global['Qf_case_years'])
        assert_almost_equals(qf_result, correct_result, places=6,
                             msg="Result Qf (%f) does not match correct Qf (%f) in '%s'" %
                                 (qf_result, correct_result, self.folder_name))

    def test_local_results(self):
        attributes = ('start_date', 'end_date', 'x', 'y', 'id', 'Qit_days')
        local_results = self.results.get_tabular_local_data()
        self.test_data_set(attributes, 'correct_local.csv', local_results)

    def test_focus_results(self):
        attributes = ('id', 'Qif_case_years')
        self.test_data_set(attributes, 'correct_focus.csv', self.results.get_tabular_focus_data())

    def test_focus_local_results(self):
        attributes = ('start_date', 'end_date', 'id', 'x', 'y', 'Qift_days')
        self.test_data_set(attributes, 'correct_focus_local.csv', self.results.get_tabular_local_focus_data())

    def test_cases_result(self):
        attributes = ('id', 'Qi_case_years')
        self.test_data_set(attributes, 'correct_cases.csv', self.results.get_tabular_individual_data())

    def test_date_results(self):
        attributes = ('start_date', 'end_date', 'Qt_cases')
        self.test_data_set(attributes, 'correct_dates.csv', self.results.get_tabular_date_data())


class TestDataSets(unittest.TestCase):
    def test_null_data(self):
        DataTestHelper('nullset', k=5)

    def test_exposure_data(self):
        DataTestHelper('exposure', k=5, exposure=True)

    def test_simple_data(self):
        DataTestHelper('simple', k=5)

    def test_tiny_data(self):
        DataTestHelper('tiny', k=3)

    def weights_strong_data(self):
        DataTestHelper('weights_strong', k=5, weights=True)

    def test_exposure_with_control_output(self):
        DataTestHelper('exposure-control-output', k=5, exposure=True, suppress_controls=False)

    def test_simple_with_control_output(self):
        DataTestHelper('simple-control-output', k=5, suppress_controls=False)