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


class TestFindTimeSliceDeltas(unittest.TestCase):
    def setUp(self):
        pass

    def test_no_slices(self):
        slices = []
        find_time_slice_deltas(slices)
        self.assertEqual(slices, [], 'Finding deltas on empty input should result in empty output.')

    def test_one_slice(self):
        slice = TimeSlice(20150101)
        self.assertEqual(find_time_slice_deltas([slice]), None, 'Input of 1 slice should return None.')

    def test_two_slices(self):
        first = TimeSlice(20150101)
        second = TimeSlice(20150105)
        slices = [first, second]
        find_time_slice_deltas(slices)
        self.assertEqual(first.delta, 4, 'A period of 4 days between time slices should result in a delta of 4.')
        self.assertEqual(second.delta, None, 'The last time slice in a list of 2 should have a delta of None.')

    def test_all_ones(self):
        first = TimeSlice(20150101)
        second = TimeSlice(20150102)
        third = TimeSlice(20150103)
        fourth = TimeSlice(20150104)
        slices = [first, second, third, fourth]
        find_time_slice_deltas(slices)
        for slice in (first, second, third):
            self.assertEqual(slice.delta, 1, 'Delta should be 1 for a slice that is followed by one on the next day. '
                                             'Failed at slice %s' % str(slice.date))
        self.assertEqual(fourth.delta, None, 'Delta for the last slice should be None.')

    def test_two_slices_same_date(self):
        first = TimeSlice(20150101)
        second = TimeSlice(20150101)
        slices = [first, second]
        find_time_slice_deltas(slices)
        self.assertEqual(first.delta, 0, 'A slice followed by one on the same day should have a delta of 0.')
        self.assertEqual(second.delta, None, 'A slice preceded by one on the same day should have a delta of 0.')

    def test_typical_situation(self):
        slices = [TimeSlice(20150101), TimeSlice(20150115), TimeSlice(20150225), TimeSlice(20160305)]
        real_deltas = (14, 41, 374, None)
        find_time_slice_deltas(slices)
        for slice, delta in zip(slices, real_deltas):
            self.assertEqual(slice.delta, delta, 'Slice of date %s found with delta of %s, should be %s' %
                             (str(slice.date), slice.delta, delta))


class TestRemoveEmptyTimeSlices(unittest.TestCase):
    def setUp(self):
        pass

    def test_empty_list_of_slices(self):
        slices = []
        remove_empty_time_slices(slices)
        self.assertEqual(slices, [], 'Removing empty time slices from an empty list should not modify the empty list.')

    def test_single_slice_no_points(self):
        time_slice = TimeSlice(20150101)
        time_slice.delta = 1
        slices = [time_slice]
        remove_empty_time_slices(slices)
        self.assertEqual(slices, [], 'Slices without points should be removed.')

    def test_single_slice_no_delta(self):
        time_slice = TimeSlice(20150101)
        time_slice.points = [StudyPoint(0, 0, StudyEntity('a case', True))]
        slices = [time_slice]
        remove_empty_time_slices(slices)
        self.assertEqual(slices, [], 'Slices without a delta should be removed.')

    def test_check_removal_of_single_entity_point(self):
        entity = StudyEntity('case', True)
        point = StudyPoint(0, 0, entity)
        entity.points = [point]
        time_slice = TimeSlice(20150101)
        time_slice.points = [point]
        slice_list = [time_slice]
        remove_empty_time_slices(slice_list)
        self.assertEqual(slice_list, [], 'Time slices without a delta should be removed.')
        self.assertEqual(len(entity.points), 0, 'Entity point list should be size 0 after the only point is removed.')

    def test_remove_middle(self):
        entity = StudyEntity('some guy', True)
        first_point = StudyPoint(0, 0, entity)
        middle_point = StudyPoint(0, 1, entity)
        last_point = StudyPoint(0, 2, entity)
        entity.points = [first_point, middle_point, last_point]
        first_slice = TimeSlice(20150101)
        first_slice.delta = 1
        first_slice.points = [first_point]
        middle_slice = TimeSlice(20150102)
        middle_slice.points = [middle_point]
        last_slice = TimeSlice(20150103)
        last_slice.delta = 1
        last_slice.points = [last_point]
        time_slices = [first_slice, middle_slice, last_slice]
        remove_empty_time_slices(time_slices)
        self.assertEqual(time_slices, [first_slice, last_slice], 'Middle slice should be removed if it has no delta')
        self.assertEqual(entity.points, [first_point, last_point],
                         'Middle point should be removed from entity when slice is removed.')

    def test_remove_single_focus_point(self):
        focus_entity = FocusEntity('test focus')
        focus_point = FocusPoint(0, 0, focus_entity)
        time_slice = TimeSlice(20150101)
        time_slice.focus_points = [focus_point]
        slice_list = [time_slice]
        remove_empty_time_slices(slice_list)
        self.assertEqual(len(focus_entity.points), 0,
                         'Removing a time slice should remove contained focus points from focus entities')


class TestCacheNeighborsInTimeSlice(unittest.TestCase):
    def setUp(self):
        self.time_slice = TimeSlice(20150101)
        self.point_a = StudyPoint(0, 0, StudyEntity('a', True))
        self.point_b = StudyPoint(0, 1, StudyEntity('b', True))
        self.point_c = StudyPoint(0, 2, StudyEntity('c', True))

    def test_no_time_slices(self):
        self.assertRaises(ValueError, cache_neighbors_in_time_slices, [], 5)

    def test_single_slice_no_points(self):
        cache_neighbors_in_time_slices([self.time_slice], 5)
        self.assertEqual(self.time_slice.points, [],
                         "Caching neighbors for a time slice with no points should no alter the number of points.")

    def test_single_slice_one_point(self):
        self.time_slice.points = [self.point_a]
        cache_neighbors_in_time_slices([self.time_slice], 5)
        self.assertEqual(self.point_a.neighbors, [],
                         'Time slices with only 1 point should not cache neighbors for that point.')

    def test_single_time_slice_k_equals_zero(self):
        self.time_slice.points = [self.point_a]
        cache_neighbors_in_time_slices([self.time_slice], 0)
        self.assertEqual(self.point_a.neighbors, [], 'Caching 0 neighbors should not add any neighbors.')

    def test_single_slice_two_points_less_than_k(self):
        self.time_slice.points = [self.point_a, self.point_b]
        cache_neighbors_in_time_slices([self.time_slice], 5)
        self.assertEqual(self.point_a.neighbors, [self.point_b],
                         'Time slices with 2 points and k=5 should cache 1 neighbor.')
        self.assertEqual(self.point_b.neighbors, [self.point_a],
                         'Time slices with 2 points and k=5 should cache 1 neighbor.')

    def test_single_slice_points_equal_k(self):
        self.time_slice.points = [self.point_a, self.point_b, self.point_c]
        cache_neighbors_in_time_slices([self.time_slice], 3)
        for point in self.time_slice.points:
            self.assertEqual(len(point.neighbors), 2,
                             'If the number of points = k, then k-1 neighbors should be cached.')

    def test_single_slice_points_one_greater_than_k(self):
        self.time_slice.points = [self.point_a, self.point_b, self.point_c]
        cache_neighbors_in_time_slices([self.time_slice], 1)
        for point in self.time_slice.points:
            self.assertEqual(len(point.neighbors), 1,
                             'If number of points >= k+1, then the number of neighbors should = k')


class TestPerformEqualRiskShuffle(unittest.TestCase):
    def setUp(self):
        self.case1 = StudyEntity('case1', True)
        self.case1.points = [StudyPoint(0, 0, self.case1), StudyPoint(0, 0, self.case1)]
        self.case2 = StudyEntity('case2', True)
        self.case2.points = [StudyPoint(0, 0, self.case2), StudyPoint(0, 0, self.case2)]
        self.control1 = StudyEntity('control1', False)
        self.control1.points = [StudyPoint(0, 0, self.control1), StudyPoint(0, 0, self.control1)]
        self.control2 = StudyEntity('control2', False)
        self.control2.points = [StudyPoint(0, 0, self.control2), StudyPoint(0, 0, self.control2)]
        self.entities = {}
        for entity in [self.case1, self.case2, self.control1, self.control2]:
            self.entities[entity.identity] = entity

    def test_weighted_shuffle_maintain_case_numbers(self):
        points = list(self.case1.points)
        points.extend(self.case2.points)
        points.extend(self.control1.points)
        points.extend(self.control2.points)
        self.assertEqual(sum([point.temp_case_status for point in points]), 4, '4 points should start as cases.')
        equal_risk_shuffle(self.entities)
        self.assertEqual(sum([point.temp_case_status for point in points]), 4, '4 points should still be cases.')

    def test_single_case_remains_case(self):
        points = list(self.case1.points)
        self.assertEqual(sum([point.temp_case_status for point in points]), 2, 'Both points should be initially cases.')
        equal_risk_shuffle({'case1': self.case1})
        self.assertEqual(sum([point.temp_case_status for point in points]), 2,
                         'Both points should remain cases with shuffling performed on only a single case.')

    def test_single_control_remains_control(self):
        points = list(self.control1.points)
        self.assertEqual(sum([point.temp_case_status for point in points]), 0,
                         'Both points should be initially controls.')
        equal_risk_shuffle({'control1': self.control1})
        self.assertEqual(sum([point.temp_case_status for point in points]), 0,
                         'Both points should remain controls with shuffling performed on only a single control.')

    def test_entity_points_remain_consistent_two_entities(self):
        points = list(self.case1.points)
        points.extend(self.control1.points)
        equal_risk_shuffle({'case1': self.case1, 'control': self.control1})
        self.assertEqual(self.case1.points[0].temp_case_status, self.case1.points[1].temp_case_status,
                         'The two points of case 1 should have the same case status after shuffling.')
        self.assertEqual(self.control1.points[0].temp_case_status, self.control1.points[1].temp_case_status,
                         'The two points of control 1 should have the same case status after shuffling.')

    def test_empty_entity_dictionary_raise_exception(self):
        self.assertRaises(ValueError, equal_risk_shuffle, {})


class TestPerformWeightedRiskShuffle(unittest.TestCase):
    def setUp(self):
        self.case1 = StudyEntity('case1', True)
        self.case1.points = [StudyPoint(0, 0, self.case1), StudyPoint(0, 0, self.case1)]
        self.case2 = StudyEntity('case2', True)
        self.case2.points = [StudyPoint(0, 0, self.case2), StudyPoint(0, 0, self.case2)]
        self.control1 = StudyEntity('control1', False)
        self.control1.points = [StudyPoint(0, 0, self.control1), StudyPoint(0, 0, self.control1)]
        self.control2 = StudyEntity('control2', False)
        self.control2.points = [StudyPoint(0, 0, self.control2), StudyPoint(0, 0, self.control2)]
        self.case1.case_weight = 0.9
        self.case2.case_weight = 0.75
        self.control1.case_weight = 0.4
        self.control2.case_weight = 0.2
        self.entities = {}
        for entity in [self.case1, self.case2, self.control1, self.control2]:
            self.entities[entity.identity] = entity

    def test_weighted_shuffle_maintain_case_numbers(self):
        points = list(self.case1.points)
        points.extend(self.case2.points)
        points.extend(self.control1.points)
        points.extend(self.control2.points)
        self.assertEqual(sum([point.temp_case_status for point in points]), 4, '4 points should start as cases.')
        case_weight_shuffle(self.entities)
        self.assertEqual(sum([point.temp_case_status for point in points]), 4, '4 points should still be cases.')

    def test_single_case_remains_case(self):
        points = list(self.case1.points)
        self.assertEqual(sum([point.temp_case_status for point in points]), 2, 'Both points should be initially cases.')
        case_weight_shuffle({'case1': self.case1})
        self.assertEqual(sum([point.temp_case_status for point in points]), 2,
                         'Both points should remain cases with shuffling performed on only a single case.')

    def test_single_control_remains_control(self):
        points = list(self.control1.points)
        self.assertEqual(sum([point.temp_case_status for point in points]), 0,
                         'Both points should be initially controls.')
        case_weight_shuffle({'control1': self.control1})
        self.assertEqual(sum([point.temp_case_status for point in points]), 0,
                         'Both points should remain controls with shuffling performed on only a single control.')

    def test_entity_points_remain_consistent_two_entities(self):
        points = list(self.case1.points)
        points.extend(self.control1.points)
        case_weight_shuffle({'case1': self.case1, 'control': self.control1})
        self.assertEqual(self.case1.points[0].temp_case_status, self.case1.points[1].temp_case_status,
                         'The two points of case 1 should have the same case status after shuffling.')
        self.assertEqual(self.control1.points[0].temp_case_status, self.control1.points[1].temp_case_status,
                         'The two points of control 1 should have the same case status after shuffling.')

    def test_empty_entity_dictionary_raise_exception(self):
        self.assertRaises(ValueError, case_weight_shuffle, {})


class TestExtractPValuesFromPointsInTimeSlices(unittest.TestCase):
    def setUp(self):
        self.time_slice = TimeSlice(20150102)
        self.focus_point = FocusPoint(0, 0, FocusEntity('focus'))
        self.focus_point.point_stat.p_value = 0.04
        self.point = StudyPoint(0, 0, StudyEntity('point', True))
        self.point.point_stat.p_value = 0.03

    def test_empty_time_slices_list(self):
        time_slices = []
        extract_p_values_from_points_in_time_slices([])
        self.assertEqual(time_slices, [], 'Extracting p-values from empty list should not modify it.')

    def test_single_slice_no_points(self):
        self.assertEqual(extract_p_values_from_points_in_time_slices([self.time_slice]), [],
                         'Extracting p-values from a single time slice with no points should return an empty list.')

    def test_single_slice_single_point(self):
        self.time_slice.points = [self.point]
        p_values = extract_p_values_from_points_in_time_slices([self.time_slice])
        self.assertEqual(p_values, [0.03],
                         'A single point from a single time slices should have its p-value extracted.')

    def test_two_slices_each_two_points(self):
        entity1 = StudyEntity('1', True)
        entity2 = StudyEntity('2', True)
        point1 = StudyPoint(0, 0, entity1)
        point2 = StudyPoint(0, 1, entity2)
        point3 = StudyPoint(0, 2, entity1)
        point4 = StudyPoint(0, 3, entity2)
        point1.point_stat.p_value = 0.06
        point2.point_stat.p_value = 0.09
        point3.point_stat.p_value = 0.12
        point4.point_stat.p_value = 0.01
        first_time_slice = TimeSlice(20150101)
        first_time_slice.points = [point1, point2]
        second_time_slice = TimeSlice(20150102)
        second_time_slice.points = [point3, point4]
        p_values = extract_p_values_from_points_in_time_slices([first_time_slice, second_time_slice])
        self.assertIn(0.06, p_values, 'P-value of first point not in extracted p-values.')
        self.assertIn(0.09, p_values, 'P-value of second point not in extracted p-values.')
        self.assertIn(0.12, p_values, 'P-value of third point not it extracted p-values.')
        self.assertIn(0.01, p_values, 'P-value of fourth point not in extracted p-values.')
        self.assertEqual(len(p_values), 4, 'Length of extracted p-values not equal to the number of points.')

    def test_single_focus_point(self):
        self.time_slice.focus_points = [self.focus_point]
        self.assertEqual(extract_p_values_from_points_in_time_slices([self.time_slice]), [0.04])

    def test_single_focus_point_and_single_study_point(self):
        self.time_slice.points = [self.point]
        self.time_slice.focus_points = [self.focus_point]
        p_values = extract_p_values_from_points_in_time_slices([self.time_slice])
        self.assertEqual(len(p_values), 2)
        self.assertIn(0.03, p_values)
        self.assertIn(0.04, p_values)


class TestFalseDiscoveryRate(unittest.TestCase):
    def setUp(self):
        pass

    def test_empty_p_value_list(self):
        self.assertRaises(ValueError, fdr_correction, [], 0.05)

    def test_single_p_value_fails(self):
        self.assertEqual(fdr_correction([0.06], 0.05), 0, '0.06 should not be <= 1*(0.05/1) and should return 0.')

    def test_single_p_value_passes(self):
        self.assertEqual(fdr_correction([0.04], 0.05), 0.04, '0.04 should be <= 1*(0.05/1).')

    def test_single_p_value_equal_to_adjustment(self):
        corr = fdr_correction([0.05], 0.05)
        self.assertEqual(corr, 0.05, '0.05 should be <= 1*(0.05/1). Got %d' % corr)

    def test_fail_all(self):
        self.assertEqual(fdr_correction([0.0045, 0.0089, 0.014, 0.019, 0.023], 0.05), 0)

    def test_hit_on_greatest_p_value_with_five_elements(self):
        self.assertEqual(fdr_correction([0.0045, 0.0089, 0.014, 0.019, 0.0205], 0.05), 0.0205)

    def test_hit_on_smallest_p_value_with_five_elements(self):
        self.assertEqual(fdr_correction([0.0042, 0.0089, 0.014, 0.019, 0.023], 0.05), 0.0042)

    def test_passed_arg_p_value_equal_zero(self):
        self.assertEqual(fdr_correction([0.0001, 0.0002, 0.003, 0.005, 0.08], 0.0), 0,
                         'A passed p-value of 0 should return 0.')

    def test_typical_situation(self):
        self.assertEqual(fdr_correction([0.0045, 0.0089, 0.012, 0.019, 0.023], 0.05), 0.012)