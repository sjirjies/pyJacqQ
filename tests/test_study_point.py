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

from .imports_for_testing import *


class TestStudyPointNeighborSum(unittest.TestCase):
    def setUp(self):
        self.case_exposed_1 = StudyPoint(1, 1, StudyEntity('n_case1_exposed', True))
        self.control_exposed = StudyPoint(2, 2, StudyEntity('n_cont1_exposed', False))
        self.case_exposed_2 = StudyPoint(3, 3, StudyEntity('n_case2_exposed', True))
        self.case_not_exposed = StudyPoint(4, 4, StudyEntity('n_case3_not_exposed', True))
        self.control_not_exposed = StudyPoint(5, 5, StudyEntity('n_cont2_not_exposed', False))
        self.case_not_exposed.exposed = False
        self.control_not_exposed.exposed = False

    def test_point_initialized_with_no_neighbors(self):
        point = StudyPoint(0, 0, StudyEntity('point', True))
        self.assertEqual(point.neighbors, [], 'A point should not initialize with neighbors.')

    def test_neighbor_sum_control(self):
        point = StudyPoint(0, 0, StudyEntity('control', False))
        stat = point.calculate_point_statistic(1)
        self.assertEqual(stat, 0, 'A control should have a neighbor sum of 0.')

    def test_neighbor_sum_not_exposed(self):
        point = StudyPoint(0, 0, StudyEntity('not exposed', True))
        point.exposed = False
        stat = point.calculate_point_statistic(1)
        self.assertEqual(stat, 0,
                         'A non-exposed point should have a neighbors sum of 0.')

    def test_neighbor_sum_no_neighbors_for_exposed_case(self):
        point = StudyPoint(0, 0, StudyEntity('no neighbors', True))
        stat = point.calculate_point_statistic(1)
        self.assertEqual(stat, 0,
                         'Neighbor sum for exposed case with no neighbors should be 0.')

    def test_neighbor_sum_single_exposed_case(self):
        point = StudyPoint(0, 0, StudyEntity('case with single exposed case neighbor', True))
        point.neighbors = [self.case_exposed_1]
        stat = point.calculate_point_statistic(1)
        self.assertEqual(stat, 1,
                         'Neighbor sum should be 1 for %s.' % point.owner.identity)

    def test_neighbor_sum_single_non_exposed_case(self):
        point = StudyPoint(0, 0, StudyEntity('case with single non-exposed case neighbor', True))
        point.neighbors = [self.case_not_exposed]
        stat = point.calculate_point_statistic(1)
        self.assertEqual(stat, 0,
                         'Neighbor sum should be 0 for %s.' % point.owner.identity)

    def test_neighbor_sum_single_exposed_control(self):
        point = StudyPoint(0, 0, StudyEntity('case with single exposed control neighbor', True))
        point.neighbors = [self.control_exposed]
        stat = point.calculate_point_statistic(1)
        self.assertEqual(stat, 0,
                         'Neighbor sum should be 0 for %s.' % point.owner.identity)

    def test_neighbor_sum_single_non_exposed_control(self):
        point = StudyPoint(0, 0, StudyEntity('case with single non-exposed control neighbor', True))
        point.neighbors = [self.control_not_exposed]
        stat = point.calculate_point_statistic(1)
        self.assertEqual(stat, 0,
                         'Neighbor sum should be 0 for %s' % point.owner.identity)

    def test_neighbor_sum_combined_situations(self):
        point = StudyPoint(0, 0, StudyEntity('typical case', True))
        point.neighbors = [self.case_exposed_1, self.control_exposed, self.case_exposed_2,
                           self.case_not_exposed, self.control_not_exposed]
        stat = point.calculate_point_statistic(1)
        self.assertEqual(stat, 2,
                         'A case with 2 exposed-case neighbors should have neighbor sum of 2.')


class TestStudyPointObservedQit(unittest.TestCase):
    def setUp(self):
        self.case_exposed_1 = StudyPoint(1, 1, StudyEntity('n_case1_exposed', True))
        self.control_exposed = StudyPoint(2, 2, StudyEntity('n_cont1_exposed', False))
        self.case_exposed_2 = StudyPoint(3, 3, StudyEntity('n_case2_exposed', True))

    def test_Qit_properly_assigned(self):
        point = StudyPoint(0, 0, StudyEntity('point', True))
        point.neighbors = [self.control_exposed, self.case_exposed_1, self.case_exposed_2]
        point.calculate_point_statistic(1)
        self.assertEqual(point.point_stat.statistic, 2, 'A case with 2 exposed case neighbors should have a Qit of 2.')

    def test_proper_initial_status(self):
        self.assertTrue(self.case_exposed_1.temp_case_status, 'Point belonging to case should start with case status.')
        self.assertFalse(self.control_exposed.temp_case_status,
                         'Point belonging to a control should start without case status.')


class TestStudyPointReferenceDistribution(unittest.TestCase):
    def setUp(self):
        self.point = StudyPoint(0, 0, StudyEntity('point', True))
        self.case_exposed_1 = StudyPoint(1, 1, StudyEntity('n_case1_exposed', True))
        self.control_exposed = StudyPoint(2, 2, StudyEntity('n_cont1_exposed', False))
        self.case_exposed_2 = StudyPoint(3, 3, StudyEntity('n_case2_exposed', True))

    def test_increment_shuffles_passed(self):
        self.point.point_stat.statistic = 1
        self.point.neighbors = [self.case_exposed_2, self.case_exposed_1, self.control_exposed]
        case_two_dist = self.point.calculate_reference_distribution(1)
        self.assertEqual(self.point.reference_stat, 2,
                         'Case with 2 exposed case neighbors should return a reference statistic of 2. Returned %s' %
                         str(case_two_dist))
        self.assertEqual(self.point.point_stat.shuffles_passed, 1,
                         "Shuffles passed should increment if a reference stat is greater than the observed stat.")
        self.point.point_stat.shuffles_passed = 0
        self.point.neighbors = [self.case_exposed_1]
        self.point.calculate_reference_distribution(1)
        self.assertEqual(self.point.reference_stat, 1,
                         'Case with 1 exposed case neighbors should return a reference statistic of 1.')
        self.assertEqual(self.point.point_stat.shuffles_passed, 1,
                         "Shuffles passed should increment if a reference stat is equal to the observed stat.")

    def test_shuffle_pass_fails(self):
        self.point.point_stat.statistic = 2
        self.point.neighbors = [self.case_exposed_1]
        self.point.calculate_reference_distribution(1)
        self.assertEqual(self.point.reference_stat, 1,
                         'Case with 1 exposed case neighbor should return a reference statistic of 1.')
        self.assertEqual(self.point.point_stat.shuffles_passed, 0,
                         'Shuffles passed should not increment if a reference stat is less than the observed stat.')