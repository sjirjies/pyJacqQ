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


class TestCalculateObservedQi(unittest.TestCase):
    def setUp(self):
        self.entity = StudyEntity('case', True)
        self.point_1 = StudyPoint(0, 0, self.entity)
        self.point_1.point_stat.statistic = 5
        self.point_2 = StudyPoint(0, 1, self.entity)
        self.point_2.point_stat.statistic = 2

    def test_calculate_Qi_control(self):
        control = StudyEntity('control', False)
        control.calculate_entity_statistic()
        self.assertEqual(control.entity_stat.statistic, 0, 'A control should have an observed Qi of 0.')

    def test_calculate_Qi_case_no_points(self):
        self.entity.points = []
        self.entity.calculate_entity_statistic()
        self.assertEqual(self.entity.entity_stat.statistic, 0, 'A case with no points should have an observed Qi of 0.')

    def test_calculate_Qi_case_single_point(self):
        self.entity.points = [self.point_1]
        self.entity.calculate_entity_statistic()
        self.assertEqual(self.entity.entity_stat.statistic, 5, 'A case with a single point with Qit = 5 should have a Qi of 5.')

    def test_calculate_Qi_multiple_points(self):
        self.entity.points = [self.point_1, self.point_2]
        self.entity.calculate_entity_statistic()
        self.assertEqual(self.entity.entity_stat.statistic, 7, 'A case with two points with Qit = 5 & 2 should have Qi = 7.')


class TestCalculateReferenceStat(unittest.TestCase):
    def setUp(self):
        self.entity = StudyEntity('entity', True)
        self.entity.entity_stat.statistic = 3
        self.point_1 = StudyPoint(0, 0, self.entity)
        self.point_1.reference_stat = 3
        self.point_2 = StudyPoint(0, 1, self.entity)
        self.point_2.reference_stat = 4
        self.point_3 = StudyPoint(0, 2, self.entity)
        self.point_3.reference_stat = 2

    def test_return_reference_stat(self):
        self.entity.points = [self.point_1]
        self.assertEqual(self.entity.calculate_reference_distribution(), 3,
                         'Calculation of reference stat should return 3 for a single point with Qit = 3.')

    def test_increment_shuffles_reference_equal(self):
        self.entity.points = [self.point_1]
        self.entity.calculate_reference_distribution()
        self.assertEqual(self.entity.entity_stat.shuffles_passed, 1,
                         'Equal reference and observed stat should increment shuffles passed.')

    def test_increment_shuffles_reference_greater(self):
        self.entity.points = [self.point_2]
        self.entity.calculate_reference_distribution()
        self.assertEqual(self.entity.entity_stat.shuffles_passed, 1,
                         'Reference stat greater than observed stat should increment shuffles passed.')

    def test_fail_to_increment_shuffles_reference_less(self):
        self.entity.points = [self.point_3]
        self.entity.calculate_reference_distribution()
        self.assertEqual(self.entity.entity_stat.shuffles_passed, 0,
                         'A reference stat less than the observed stat should not increase shuffles passed.')


class TestSetTempStatusOfPoints(unittest.TestCase):
    def setUp(self):
        self.entity = StudyEntity('entity', True)
        self.point1 = StudyPoint(0, 0, self.entity)
        self.point2 = StudyPoint(0, 1, self.entity)
        self.point1.temp_case_status = True
        self.point2.temp_case_status = False

    def test_set_status_no_points(self):
        self.entity.points = []
        self.entity.set_temp_case_status_of_points(True)
        self.assertEquals(self.entity.points, [],
                          'Entity with no points should still have no points after setting point status.')

    def test_pre_status_of_points(self):
        self.assertTrue(self.point1.temp_case_status, 'Point1 should begin with case status.')
        self.assertFalse(self.point2.temp_case_status, 'Point2 should begin without case status.')

    def test_set_status_to_case(self):
        self.entity.set_temp_case_status_of_points(True)
        self.assertTrue(self.point1.temp_case_status, 'Point1 should retain case status.')
        self.assertTrue(self.point2.temp_case_status, 'Point2 should have been converted to case status.')

    def test_set_status_to_control(self):
        self.entity.set_temp_case_status_of_points(False)
        self.assertFalse(self.point1.temp_case_status, 'Point1 should no longer have case status.')
        self.assertFalse(self.point2.temp_case_status, 'Point2 should still not have case status.')