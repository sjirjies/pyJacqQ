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

from imports_for_testing import *


class TestStudyStatistic(unittest.TestCase):
    def setUp(self):
        self.stat = StudyStatistic()

    def test_statistic_correct_initialization(self):
        self.assertIsNone(self.stat.p_value, "P-value should not start with a value.")
        self.assertEqual(self.stat.shuffles_passed, 0, "Shuffles passed should start at 0.")

    def test_calculate_p_value_zero(self):
        self.stat.calculate_p_value(999)
        self.assertAlmostEqual(self.stat.p_value, 0.001, "P-value should be 0.001 with 0 of 999 shuffles passed.")

    def test_calculate_p_value_one(self):
        self.stat.shuffles_passed = 999
        self.stat.calculate_p_value(999)
        self.assertEqual(self.stat.p_value, 1, "P-value should be 1 with all shuffles passed.")

    def test_calculate_p_value_between(self):
        self.stat.shuffles_passed = 749
        self.stat.calculate_p_value(999)
        self.assertAlmostEqual(self.stat.p_value, 0.75, "P-value should be ~0.75 with ~75% of shuffles passed.")
