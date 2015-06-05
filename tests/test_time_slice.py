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


class TestTimeSlice(unittest.TestCase):
    def setUp(self):
        self.point_a = StudyPoint(0, 0, StudyEntity('A', True))
        self.point_b = StudyPoint(2, 2, StudyEntity('B', True))
        self.point_c = StudyPoint(3, 2, StudyEntity('C', True))
        self.point_d = StudyPoint(4, 3, StudyEntity('D', True))
        self.point_e = StudyPoint(2, 6, StudyEntity('E', False))
        self.point_f = StudyPoint(1, 7, StudyEntity('F', False))
        self.point_g = StudyPoint(0, 7, StudyEntity('G', False))
        self.points = [self.point_a, self.point_b, self.point_c, self.point_d, self.point_e, self.point_f, self.point_g]
        self.slice = TimeSlice(20150101)
        self.slice.delta = 1

    def assert_neighbor_relations(self, should_be_neighbors):
        for point in should_be_neighbors:
            for neighbor in should_be_neighbors[point]:
                self.assertEqual(len(should_be_neighbors[point]), len(point.neighbors),
                                 'Lengths of lists for %s do not match. Point Neighbors: %s, Real Neighbors: %s' %
                                 (str(point.owner.identity),
                                  str([p.owner.identity for p in point.neighbors]),
                                  str([p.owner.identity for p in should_be_neighbors[point]])))
                self.assertIn(neighbor, point.neighbors, 'Neighbor %s is not recorded in %s for point %s.' %
                              (str(neighbor.owner.identity),
                               str([n.owner.identity for n in point.neighbors]),
                               str(point.owner.identity)))

    def test_init_conditions(self):
        slice = TimeSlice(20150101)
        self.assertEqual(slice.delta, None, 'Time slices should start with a time delta of None.')
        self.assertEqual(slice.date, 20150101, 'Initial date of a time slice should be the date passed to it.')

    def test_raise_error_on_zero_k(self):
        self.assertRaises(ValueError, self.slice.cache_nearest_neighbors, 0)

    def test_cache_two_points_one_neighbor(self):
        self.slice.points = [self.point_a, self.point_b]
        self.slice.cache_nearest_neighbors(1)
        self.assertEqual(self.point_a.neighbors, [self.point_b], 'Point A should contain point B as a neighbor.')
        self.assertEqual(self.point_b.neighbors, [self.point_a], 'Point B should contain point A as a neighbor.')

    def test_cache_seven_points_two_neighbors(self):
        self.slice.points = self.points
        self.slice.cache_nearest_neighbors(2)
        should_be_neighbors = {self.point_a: (self.point_b, self.point_c),
                               self.point_b: (self.point_c, self.point_d),
                               self.point_c: (self.point_b, self.point_d),
                               self.point_d: (self.point_b, self.point_c),
                               self.point_e: (self.point_f, self.point_g),
                               self.point_f: (self.point_e, self.point_g),
                               self.point_g: (self.point_e, self.point_f)}
        self.assert_neighbor_relations(should_be_neighbors)

    def test_cache_focus_points(self):
        self.slice.points = self.points
        focus_point = FocusPoint(0, 0, FocusEntity('focus'))
        self.slice.focus_points = [focus_point]
        self.slice.cache_nearest_neighbors(2)
        self.assertEqual(len(self.slice.focus_points[0].neighbors), 2)
        self.assertEqual(self.slice.focus_points[0].neighbors[0], self.point_a)
        self.assertEqual(self.slice.focus_points[0].neighbors[1], self.point_b)

    def test_calculate_stat_no_points(self):
        self.assertEqual(self.slice.points, [])
        self.assertIsNone(self.slice.Qt.statistic, "Qt should be initialized to None.")
        self.slice.calculate_observed_Qt_and_points_Qit()
        self.assertEqual(self.slice.Qt.statistic, 0, "Qt should be 0 if calculated with no points.")

    def test_calculate_stat_one_case_no_neighbors(self):
        self.slice.points = [self.point_a]
        self.slice.calculate_observed_Qt_and_points_Qit()
        self.assertEqual(self.slice.Qt.statistic, 0, "Qt should be 0 if none of the points have neighbors.")

    def assert_several_Qit(self, points_and_stats_dict):
        for point in points_and_stats_dict:
            self.assertEqual(point.point_stat.statistic, points_and_stats_dict[point],
                             'Point %s should have Qit=%s not %s.' %
                             (point.owner.identity, str(points_and_stats_dict[point]), str(point.point_stat.statistic)))

    def test_calculate_stat_three_points_two_neighbors(self):
        self.slice.points = [self.point_b, self.point_c, self.point_e]
        self.slice.cache_nearest_neighbors(2)
        self.assert_neighbor_relations({self.point_b: (self.point_c, self.point_e),
                                        self.point_c: (self.point_b, self.point_e),
                                        self.point_e: (self.point_b, self.point_c)})
        self.slice.calculate_observed_Qt_and_points_Qit()
        self.assert_several_Qit({self.point_b: 1, self.point_c: 1, self.point_e: 0})
        self.assertEqual(self.slice.Qt.statistic, 2,
                         "Total Qt should equal 2 given 2 cases, 1 control, and k=2.")

    def test_calculate_stat_several_points_two_neighbors(self):
        self.slice.points = self.points
        self.slice.cache_nearest_neighbors(2)
        self.slice.calculate_observed_Qt_and_points_Qit()
        self.assert_several_Qit({self.point_a: 2, self.point_b: 2, self.point_c: 2, self.point_d: 2, self.point_e: 0,
                                 self.point_f: 0, self.point_g: 0})
        self.assertEqual(self.slice.Qt.statistic, 8, "Time slice should have Qt = 8 with 4 cases each Qit = 2.")

    def test_reference_lower_than_observed(self):
        self.slice.points = self.points
        self.slice.cache_nearest_neighbors(2)
        self.slice.calculate_observed_Qt_and_points_Qit()
        # Flip all case-control flags
        for point in self.slice.points:
            point.temp_case_status = not point.temp_case_status
        self.assertEqual(sum([point.temp_case_status for point in self.slice.points]), 3,
                         'Flipping 4 cases and 3 controls to opposite status should result in 3 cases.')
        self.slice.calculate_reference_distribution()
        self.assertEqual(self.slice.Qt.shuffles_passed, 0)

    def test_reference_equal_to_observed(self):
        self.assertEqual(self.slice.Qt.shuffles_passed, 0, 'Shuffles passed should not increase with a lower reference')
        self.slice.points = self.points
        self.slice.cache_nearest_neighbors(2)
        self.slice.calculate_observed_Qt_and_points_Qit()
        self.slice.calculate_reference_distribution()
        self.assertEqual(self.slice.Qt.shuffles_passed, 1, 'Shuffles passed should increase with the same reference')

    def test_reference_greater_than_observed(self):
        self.slice.points = self.points
        self.slice.cache_nearest_neighbors(2)
        self.slice.calculate_observed_Qt_and_points_Qit()
        # Make all points temporary cases
        for point in self.slice.points:
            point.temp_case_status = True
        self.slice.calculate_reference_distribution()
        self.assertEqual(self.slice.Qt.shuffles_passed, 1, 'Shuffles passed should increase with a larger reference.')