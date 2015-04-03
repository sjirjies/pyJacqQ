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


class TestCalculateFocusStatistic(unittest.TestCase):
    def setUp(self):
        self.focus_entity = FocusEntity('test entity')
        self.focus_point_a = FocusPoint(0, 0, self.focus_entity)
        self.focus_point_b = FocusPoint(1, 1, self.focus_entity)
        self.focus_point_c = FocusPoint(2, 2, self.focus_entity)
        self.focus_point_d = FocusPoint(3, 3, self.focus_entity)
        self.focus_point_a.point_stat.statistic = 1
        self.focus_point_b.point_stat.statistic = 2
        self.focus_point_c.point_stat.statistic = 4
        self.focus_point_d.point_stat.statistic = 8

    def test_calculate_statistic_no_points(self):
        self.focus_entity.calculate_entity_statistic()
        self.assertEqual(self.focus_entity.calculate_entity_statistic(), None,
                         'A focus entity with no points should have a Qf=None')

    def test_calculate_statistic_one_point(self):
        self.focus_entity.points = [self.focus_point_a]
        self.focus_entity.calculate_entity_statistic()
        self.assertEqual(self.focus_entity.entity_stat.statistic, 1,
                         'A focus entity with 1 point where Qft=1 should have Qf=1.')

    def test_calculate_statistic_many_points(self):
        self.focus_entity.points = [self.focus_point_a, self.focus_point_b, self.focus_point_c, self.focus_point_d]
        self.focus_entity.calculate_entity_statistic()
        self.assertEqual(self.focus_entity.entity_stat.statistic, 15)