#!/usr/bin/env python
#
# jacqq.py - Calculates Jacquez's Q statistic for space-time clustering.
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

__version__ = '0.4.1'
import sys
import os
import scipy.spatial as spatial
import scipy.stats
import collections
import datetime
import platform

import numpy as np
import argparse
import random
import csv


def _load_csv_file(filepath):
    with open(filepath, 'r') as csv_file:
        legend = {}
        contents = []
        reader = csv.reader(csv_file)
        try:
            header = next(reader)
            for line in reader:
                contents.append(line)
            for item in header:
                legend[item] = header.index(item)
        except csv.Error as error:
            sys.exit('File %s, line %d: %s' % (filepath, reader.line_num, error))
        return legend, np.array(contents, dtype=np.object)


def check_data_dirty(details_csv_path, histories_csv_path, focus_csv_path=None, exposure=False, weights=False):
    # - People who are at multiple locations at once

    def dirty_headers(all_info):
        # Make sure all headers are correct
        errors = []
        for file_name, info in all_info.items():
            schema, header, data = info
            for attribute in schema:
                column_name, column_type = attribute, schema[attribute]
                if column_name not in header:
                    errors.append("File '%s': Missing column header '%s'" % (file_name, column_name))
        return errors

    def wrong_number_attributes(all_info):
        # Make sure the number of attributes per row match the number of column headings
        errors = []
        for file_name, info in all_info.items():
            schema, header, data = info
            schema_length = len(schema)
            for index, row in enumerate(data):
                if len(row) < schema_length:
                    errors.append("File '%s': Row %d has an incorrect number of attributes" %
                                  (file_name, index+2))
        return errors

    def empty_fields(all_info):
        # Make sure none of the fields are empty
        errors = []
        for file_name, info in all_info.items():
            schema, header, data = info
            reverse_header = {val: key for key, val in header.items()}
            for row_index, row in enumerate(data):
                for field_index, field in enumerate(row):
                    if not field:
                        errors.append("File '%s': Row %d is missing value for field '%s'" %
                                      (file_name, row_index+2, reverse_header[field_index]))
        return errors

    def dirty_data_types(all_info):
        # Make sure the data types match the header types
        errors = []
        for file_name, info in all_info.items():
            schema, header, data = info
            reverse_header = {val: key for key, val in header.items()}
            for row_index, row in enumerate(data):
                for field_index, field in enumerate(row):
                    if reverse_header[field_index] in schema:
                        correct_type = schema[reverse_header[field_index]]
                        if correct_type is 'date':
                            if len(str(field)) != 8 or not str(field).isdigit():
                                errors.append("File '%s': Row %d requires date format YYYYMMDD for attribute '%s'" %
                                              (file_name, row_index+2, reverse_header[field_index]))
                        elif correct_type is float:
                            try:
                                numeric_field = float(field)
                                if reverse_header[field_index] in ('exposure_duration', 'latency'):
                                    if numeric_field < 0:
                                        errors.append("File '%s': Row %d required a non-negative value for attribute '%s'" %
                                                      (file_name, row_index+2, reverse_header[field_index]))
                            except ValueError:
                                errors.append("File '%s': Row %d requires a number for attribute '%s'" %
                                              (file_name, row_index+2, reverse_header[field_index]))
                        elif correct_type is bool:
                            if field != "0" and field != "1":
                                errors.append("File '%s': Row %d requires a 0 or 1 for attribute '%s'" %
                                              (file_name, row_index+2, reverse_header[field_index]))
        return errors

    def all_cases_or_controls(details_path, all_info):
        # Make sure there are both cases and controls
        errors = []
        details_file_name = os.path.basename(details_path)[:-4]
        det_schema, det_header, det_data = all_info[details_file_name]
        det_reverse_header = {val: key for key, val in det_header.items()}
        found_case = False
        found_control = False
        for row_index, row in enumerate(det_data):
            stat = row[det_header['is_case']]
            if stat == '0':
                found_control = True
            elif stat == "1":
                found_case = True
        if not found_case:
            errors.append("File '%s': Details data can not only contain controls" % details_file_name)
        if not found_control:
            errors.append("File '%s': Details data can not only contain cases" % details_file_name)
        return errors

    def all_ids_present(details_path, histories_path, all_info):
        errors = []
        details_file_name = os.path.basename(details_path)[:-4]
        det_schema, det_header, det_data = all_info[details_file_name]
        histories_file_name = os.path.basename(histories_path)[:-4]
        his_schema, his_header, his_data = all_info[histories_file_name]
        details_ids = set()
        for row_index, row in enumerate(det_data):
            details_ids.add(row[det_header['ID']])
        histories_ids = set()
        for row_index, row in enumerate(his_data):
            histories_ids.add(row[his_header['ID']])
        for item in details_ids:
            if item not in histories_ids:
                errors.append("Individual '%s' is in details file '%s' but not histories file '%s'" %
                              (item, details_file_name, histories_file_name))
        return errors

    def end_after_start_dates(histories_path, all_info, focus_path=None):
        errors = []
        his_file_name = os.path.basename(histories_path)[:-4]
        his_schema, his_header, his_data = all_info[his_file_name]
        groups = [(his_file_name, his_header, his_data)]
        if focus_path:
            focus_file_name = os.path.basename(focus_path)[:-4]
            focus_schema, focus_header, focus_data = all_info[focus_file_name]
            groups.append((focus_file_name, focus_header, focus_data))
        for filename, header, data in groups:
            for row_index, row in enumerate(his_data):
                start_date = row[his_header['start_date']]
                end_date = row[his_header['end_date']]
                if int(end_date) <= int(start_date):
                    errors.append("File '%s': Start date must be before end date in row %d" % (filename, row_index+2))
        return errors

    # Collect header information with the data type of that column
    details_schema = {'ID': str, 'is_case': bool}
    if exposure:
        details_schema['DOD'] = 'date'
        details_schema['latency'] = float
        details_schema['exposure_duration'] = float
    if weights:
        details_schema['weight'] = float
    space_time_schema = {'ID': str, 'start_date': 'date', 'end_date': 'date', 'x': float, 'y': float}

    # Bundle info together so the files only need to be loaded once
    path_and_schemas = {details_csv_path: details_schema, histories_csv_path: space_time_schema}
    if focus_csv_path:
        path_and_schemas[focus_csv_path] = space_time_schema
    all_file_info = {}
    for file_path, schema in path_and_schemas.items():
        header, data = _load_csv_file(file_path)
        file_name = os.path.basename(file_path)[:-4]
        all_file_info[file_name] = (schema, header, data)

    # Lower errors checks require upper checks to pass so return any errors as they are found.
    errors = dirty_headers(all_file_info)
    if errors:
        return errors

    errors = wrong_number_attributes(all_file_info)
    if errors:
        return errors

    errors = empty_fields(all_file_info)
    if errors:
        return errors

    errors = dirty_data_types(all_file_info)
    if errors:
        return errors

    errors = all_cases_or_controls(details_csv_path, all_file_info)
    if errors:
        return errors

    errors = all_ids_present(details_csv_path, histories_csv_path, all_file_info)
    if errors:
        return errors

    errors = end_after_start_dates(histories_csv_path, all_file_info, focus_path=focus_csv_path)
    if errors:
        return errors
    return errors


class _StudyStatistic:
    def __init__(self):
        self.statistic = None
        self.p_value = None
        self.shuffles_passed = 0

    def calculate_p_value(self, total_shuffles):
        # Calculate the p-value given the number of total shuffles
        self.p_value = (self.shuffles_passed + 1) / (total_shuffles + 1.0)


class _BaseQEntity:
    def __init__(self, identity):
        self.identity = identity
        self.entity_stat = _StudyStatistic()
        self.points = []

    def calculate_entity_statistic(self):
        raise NotImplementedError

    def calculate_reference_distribution(self):
        # Calculate the total point statistic for the entitiy
        stat = sum([point.reference_stat for point in self.points])
        if stat >= self.entity_stat.statistic:
            self.entity_stat.shuffles_passed += 1
        return stat


class _StudyEntity(_BaseQEntity):
    def __init__(self, identity, is_case, date_of_initial_exposure=None, date_contraction=None, case_weight=None):
        _BaseQEntity.__init__(self, identity)
        self.is_case = is_case
        self.date_of_contraction = date_contraction
        self.date_of_initial_exposure = date_of_initial_exposure
        self.case_weight = case_weight

    def calculate_entity_statistic(self):
        # Calculate Q_i
        if self.is_case:
            self.entity_stat.statistic = sum([point.point_stat.statistic for point in self.points])
        else:
            self.entity_stat.statistic = 0

    def set_temp_case_status_of_points(self, case_status):
        # Assign the case status of all points owned by this entity
        for point in self.points:
            point.temp_case_status = case_status


class _FocusEntity(_BaseQEntity):
    def __init__(self, identity):
        _BaseQEntity.__init__(self, identity)

    def calculate_entity_statistic(self):
        # Calculate Q_fi
        self.entity_stat.statistic = sum([point.point_stat.statistic for point in self.points])


class _BaseQPoint:
    def __init__(self, x, y, owner):
        self.point_stat = _StudyStatistic()
        self.x = x
        self.y = y
        self.owner = owner
        self.owner.points.append(self)
        self.neighbors = []
        self.reference_stat = 0

    def calculate_point_statistic(self, multiplier):
        raise NotImplementedError

    def calculate_reference_distribution(self, multiplier):
        raise NotImplementedError


class _StudyPoint(_BaseQPoint):
    def __init__(self, x, y, owner):
        _BaseQPoint.__init__(self, x, y, owner)
        self.temp_case_status = owner.is_case
        self.owner_is_case = owner.is_case
        self.exposed = True

    def calculate_point_statistic(self, multiplier):
        # Calculate Q_it
        if self.owner_is_case and self.exposed:
            self.point_stat.statistic = int(sum([neighbor.temp_case_status and neighbor.exposed
                                                 for neighbor in self.neighbors]) * multiplier)
        else:
            self.point_stat.statistic = 0
        return self.point_stat.statistic

    def calculate_reference_distribution(self, multiplier):
        # Calculate the Q_it value for a permutation of a Monte Carlo test
        if self.exposed and (self.owner_is_case or self.temp_case_status):
            stat = sum([neighbor.temp_case_status and neighbor.exposed for neighbor in self.neighbors])
        else:
            stat = 0
        if self.exposed and self.owner_is_case:
            self.reference_stat = stat * multiplier
        else:
            self.reference_stat = 0
        if self.reference_stat >= self.point_stat.statistic:
            self.point_stat.shuffles_passed += 1
        return stat


class _FocusPoint(_BaseQPoint):
    def __init__(self, x, y, owner):
        _BaseQPoint.__init__(self, x, y, owner)
        self.neighbor_distances = []

    def count_eligible_neighbors(self):
        # Count the number of nearby exposed cases
        return sum([neighbor.temp_case_status and neighbor.exposed for neighbor in self.neighbors])

    def calculate_point_statistic(self, multiplier):
        # Calculate Q_fit
        self.point_stat.statistic = self.count_eligible_neighbors() * multiplier
        return self.point_stat.statistic

    def calculate_reference_distribution(self, multiplier):
        # Calculate a reference Q_fit for a permutation in a Monte Carlo test
        self.reference_stat = int(self.count_eligible_neighbors() * multiplier)
        if self.reference_stat >= self.point_stat.statistic:
            self.point_stat.shuffles_passed += 1
        return self.reference_stat


class _TimeSlice:
    def __init__(self, date_of_slice):
        self.Qt = _StudyStatistic()
        self.date = date_of_slice
        self.points = []
        self.focus_points = []
        self.delta = None
        self.end_date = None

    def cache_nearest_neighbors(self, k):
        # Find and store the nearest neighbors relation for each point and focus point
        if k < 1:
            raise ValueError('Value for k should be greater than or equal to 1.')
        # The PySAL knn method requires the inputs to be numpy arrays with a specific formatting
        x = [p.x for p in self.points]
        y = [p.y for p in self.points]
        n = len(self.points)
        x = np.array(x)
        y = np.array(y)
        x = np.reshape(x, (n, 1))
        y = np.reshape(y, (n, 1))
        locations = np.hstack((x, y))
        # Get the nearest neighbors for all the points.
        knn = spatial.cKDTree(locations)
        # Now cache the nearest neighbors with the points they are neighbors of
        for point in self.points:
            # knn.query() return (array of distances, array of indexes)
            # We get k+1 points because the first result is the point itself
            neighbor_data = knn.query(np.array((point.x, point.y)), k=k + 1)
            indexes = neighbor_data[1]
            try:
                # [1:] to keep every point except the first one which is itself
                point.neighbors = np.array([self.points[index] for index in indexes[1:]], dtype=np.object)
            except TypeError:
                # In this case distance and indexes are single values
                # Scipy kdtree does not return them in an array if they are single values
                point.neighbors = [self.points[indexes]]
        # Cache nearest neighbors of any focus points
        for focus in self.focus_points:
            distances, indexes = knn.query(np.array((focus.x, focus.y)), k=k)
            try:
                focus.neighbors = np.array([self.points[index] for index in indexes], dtype=np.object)
                focus.neighbor_distances = distances
            except TypeError:
                # In this case distance and indexes are single values
                # Scipy kdtree does not return them in an array if they are single values
                focus.neighbors = [self.points[indexes]]
                focus.neighbor_distances = [distances]

    def calculate_observed_Qt_and_points_Qit(self):
        # Calculate Q_t for the time slice and Q_it for each point in this time slice
        stat = 0
        for point in self.points:
            stat += point.calculate_point_statistic(self.delta)
        self.Qt.statistic = stat // self.delta

    def calculate_observed_Qft(self):
        # Calculate Q_ft
        for focus in self.focus_points:
            focus.calculate_point_statistic(self.delta)

    def calculate_reference_distribution(self):
        # Calculate the Q_t value for a Monte Carlo test
        stat = 0
        for point in self.points:
            stat += point.calculate_reference_distribution(self.delta)
        if stat >= self.Qt.statistic:
            self.Qt.shuffles_passed += 1
        return stat

    def calculate_focus_point_distribution(self):
        # Calculate Q_fit for all focus points as part of a Monte Carlo test
        for focus in self.focus_points:
            focus.calculate_reference_distribution(self.delta)


class QStudyResults:
    """ A container for the results of an analysis using Jacquaz's Q.

    Objects of this class are an easy way of obtaining any result from
    the analysis. It essentially holds top level study details and
    nested dicts that can be indexed by individual, time slice date, or
    a combination of the two.
    Example:

    >>> details = "tests/simulation_data/input_details.csv"
    >>> histories = "tests/simulation_data/" \
                    "input_residential_histories.csv"
    >>> focus = "tests/simulation_data/input_focus.csv"
    >>> study = QStatsStudy(details, histories, focus)
    >>> r = study.run_analysis(5, True, True, correction='BINOM')
    >>> # Find out if exposure clustering was used
    >>> r.exposure_enabled
    True
    >>> # Get the number of shuffles in the Monte Carlo testing
    >>> r.number_permutation_shuffles
    99
    >>> # Get global Q as (statistic case-years, p-value, significance)
    >>> r.Q_case_years
    (279.1835616438356, 0.01, 1)
    >>> # Get the Qf statistic normalized by the number of cases
    >>> r.normalized_Qf_case_years
    1.3102739726027397
    >>> # Get all of the time slice results
    >>> r.time_slices
    OrderedDict([(20150101,
        <jacqq.QStudyTimeSliceResult object at 0x7f276e8c1080>), ... ])
    >>> # Get the Qt statistic for the slice at January 3rd, 2015
    >>> r.time_slices[20150103].stat
    (46, 0.01, 1)
    >>> # Get a list of only significant case points at that date
    >>> r.time_slices[20150103].sig_points
    OrderedDict([('JG',
        <jacqq.QStudyPointResult object at 0x7f276e880d68>), ... ])
    >>> # Get the local Q_it statistic for case 'JQ' on Jan. 3rd 2015
    >>> r.time_slices[20150103].points['JQ'].stat
    (3, 0.02, 1)
    >>> r.cases['JQ'].points[20150103].stat
    (3, 0.02, 1)
    >>> # Get only significant Q_it stats for case 'JG'
    >>> r.cases['JG'].sig_points
    OrderedDict([(20150101,
        <jacqq.QStudyPointResult object at 0x7f276e849c18>), ...])
    >>> # Find the x, y location of case 'JG' on Jan. 2nd, 2015
    >>> r.cases['JG'].points[20150102].loc
    (73.0, 124.0)
    >>> # Get the focus Q_fi results in tabular/tuple form
    >>> r.get_tabular_focus_data()
    (['id', 'Qif_case_years', 'pval', 'sig'],
        [['Away From Sources', 0.0, 1.0, 0],
        ['Large Constant', 2.052054794520548, 0.01, 1],
        ['Medium Linear', 1.8712328767123287, 0.01, 1],
        ['Small Constant', 1.3178082191780822, 0.27, 0]])
    >>> # Get the binomal test results for dates
    >>> # As (number significant statistics, p-value, significance)
    >>> r.binom.dates
    (177, 1.1102230246251565e-16, 1)
    >>> # Get time slices that have less than k+1 points
    >>> r.dates_lower_k_plus_one
    {20151231: <jacqq.QStudyTimeSliceResult object at 0x7f3ca3d9e978>}
    >>> # Write all the results to files
    >>> r.write_to_files('global.csv', 'cases.csv', 'dates.csv',
        'local_cases.csv', 'focus_results.csv', 'focus_local.csv')
    """

    def __init__(self):
        self.exposure_enabled = None
        self.case_weights_enabled = None
        self.k = None
        self.number_permutation_shuffles = None
        self.submitted_alpha = None
        self.adjusted_alpha = None
        self.alpha_adjustment_method = None
        self.Q_case_years = ()
        self.normalized_Q_case_years = 0
        self.normalized_Qf_case_years = 0
        self.Qf_case_years = ()
        self.cases = collections.OrderedDict()
        self.controls = collections.OrderedDict()
        self.sig_cases = collections.OrderedDict()
        self.focus_entities = collections.OrderedDict()
        self.sig_focus_entities = collections.OrderedDict()
        self.time_slices = collections.OrderedDict()
        self.sig_time_slices = collections.OrderedDict()
        self.number_sig_case_points = 0
        self.number_sig_focus_points = 0
        self.dates_lower_k_plus_one = {}
        self.binom = None
        self.seed = None
        self.platform = platform.system() + " " + platform.release()

    def print_results(self):
        """ Print the results to console.
        """
        # Print results
        options = self._get_globals_dict()
        for label, value in options.items():
            print("%s: %s" % (str(label), str(value)))
        print('-Global:', self.Q_case_years[0], 'pval:', self.Q_case_years[1], 'sig:', self.Q_case_years[2])
        print('-Normalized Global:', self.normalized_Q)
        for ind_id in self.cases:
            ind_stat = self.cases[ind_id].stat
            print(' Owner: %-21s Qi: %-5f pval: %.4f Sig: %s ' %
                  (ind_id, ind_stat[0], ind_stat[1], 'T' if ind_stat[2] else 'F'))
        if self.focus_entities:
            print("-Global Focus:", self.Qf_case_years[0], 'pval:', self.Qf_case_years[1], 'sig:',
                  self.Qf_case_years[2])
            print("-Normalized Global Focus:", self.normalized_Qf)
            print("-Focus Entities:")
            for focus_name in self.focus_entities:
                focus_stat = self.focus_entities[focus_name].stat
                print(' ID: %-21s Qf: %-5f pval: %.4f Sig: %s' %
                      (focus_name, focus_stat[0], focus_stat[1], 'T' if focus_stat[2] else 'F'))
        print("-Time Slices:")
        for slice_date in self.time_slices:
            tslice = self.time_slices[slice_date]
            stat = tslice.stat
            print(' Date: %-9s Delta: %-3d Qt: %-3d pval: %.4f Sig: %s' %
                  (slice_date, tslice.duration_days, stat[0], stat[1], 'T' if stat[2] else 'F'))
            for point_name in tslice.points:
                point_stat = tslice.points[point_name].stat
                print('  Owner: %-21s Qit: %-3s pval: %.4s Sig: %s' %
                      (point_name, point_stat[0], point_stat[1], 'T' if point_stat[2] else 'F'))
            if tslice.focus_points:
                for focus_name in tslice.focus_points:
                    focus_stat = tslice.focus_points[focus_name].stat
                    print('  ID: %-21s Qft: %-3d pval: %.4f Sig: %s' %
                          (focus_name, focus_stat[0], focus_stat[1], 'T' if focus_stat[2] else 'F'))

    def _get_globals_dict(self):
        # Returns a dictionary containing global results.
        g = collections.OrderedDict()
        g['exposure'] = self.exposure_enabled
        g['weights'] = self.case_weights_enabled
        g['k'] = self.k
        g['shuffles'] = self.number_permutation_shuffles
        g['submitted_alpha'] = self.submitted_alpha
        g['mt_correction'] = self.alpha_adjustment_method
        g['adjusted_alpha'] = self.adjusted_alpha
        g['seed'] = self.seed
        g['platform'] = self.platform
        g['Q_case_years'] = self.Q_case_years[0]
        g['Q_normalized_case_years'] = self.normalized_Q_case_years
        g['Q_pval'] = self.Q_case_years[1]
        g['Q_sig'] = self.Q_case_years[2]
        if self.focus_entities:
            g['Qf_case_years'] = self.Qf_case_years[0]
            g['Qf_normalized_case_years'] = self.normalized_Qf_case_years
            g['Qf_pval'] = self.Qf_case_years[1]
            g['Qf_sig'] = self.Qf_case_years[2]
        return g

    @staticmethod
    def _get_tabular_entity_data(entity_dict, stat_label, is_case):
        # Returns tabular data for entities
        entity_rows = []
        for name in entity_dict:
            row = [name, 1 if is_case else 0]
            row.extend(entity_dict[name].stat)
            entity_rows.append(row)
        header = ['id', 'is_case', stat_label, 'pval', 'sig']
        return header, entity_rows

    def get_tabular_individual_data(self):
        # TODO: Include normalized Qi
        # 'normalized' Qi is obtained by dividing Qi by exposure duration
        # units for normalized Qi are cases
        header, rows = self._get_tabular_entity_data(self.cases, 'Qi_case_years', True)
        if self.controls:
            _, control_rows = self._get_tabular_entity_data(self.controls, 'Qi_case_years', False)
            rows.extend(control_rows)
        return header, rows

    def get_tabular_date_data(self):
        """Returns tabular, normalized time slice results.

        :return: A tuple where the first item is a list of header
        labels and the second item is a list of rows populated with
        time slice data including start date, end date, Qt, p-value, and
        significance.
        """
        date_rows = []
        for slice_date in self.time_slices:
            time_slice = self.time_slices[slice_date]
            row = [slice_date, time_slice.end_date]
            row.extend(time_slice.stat)
            date_rows.append(row)
        date_header = ['start_date', 'end_date', 'Qt_cases', 'pval', 'sig']
        return date_header, date_rows

    def get_tabular_local_data(self):
        """Returns tabular, normalized local case results.

        :return: A tuple where the first item is a list of header
        labels and the second item is a list of rows populated with
        local case results data including start date, end date, id, x,
        y, Qit, p-value, and significance
        """
        local_rows = []
        for slice_date in self.time_slices:
            time_slice = self.time_slices[slice_date]
            for point_id in time_slice.points:
                point = time_slice.points[point_id]
                point_row = [slice_date, time_slice.end_date, point_id, point.loc[0], point.loc[1]]
                point_row.extend(point.stat)
                local_rows.append(point_row)
        local_header = ['start_date', 'end_date', 'id', 'x', 'y', 'Qit_days', 'pval', 'sig']
        return local_header, local_rows

    def get_tabular_focus_data(self):
        """Returns tabular, normalized focus results.

        :return: A tuple where the first item is a list of header
        labels and the second item is a list of rows populated with
        focus data including id, Qif, p-value, and significance.
        """
        entity_rows = []
        for name in self.focus_entities:
            row = [name]
            row.extend(self.focus_entities[name].stat)
            entity_rows.append(row)
        header = ['id', 'Qif_case_years', 'pval', 'sig']
        return header, entity_rows

    def get_tabular_local_focus_data(self):
        """Returns tabular, normalized local focus results.

        :return: A tuple where the first item is a list of header
        labels and the second item is a list of rows populated with
        local focus data including start date, end date, id, x, y,
        Qfit, p-value, and significance.
        """
        local_focus_rows = []
        for slice_date in self.time_slices:
            time_slice = self.time_slices[slice_date]
            for focus_point_id in time_slice.focus_points:
                focus_point = time_slice.focus_points[focus_point_id]
                focus_point_row = [slice_date, time_slice.end_date, focus_point_id, focus_point.loc[0],
                                   focus_point.loc[1]]
                focus_point_row.extend(focus_point.stat)
                local_focus_rows.append(focus_point_row)
        local_header = ['start_date', 'end_date', 'id', 'x', 'y', 'Qift_days', 'pval', 'sig']
        return local_header, local_focus_rows

    def write_to_files(self, global_file_path, cases_file_path, dates_file_path, local_file_path,
                       focus_file_path=None, focus_local_file_path=None):
        """Saves the results to normalized CSV files.

        focus_file_path and focus_local_file_path are only required the
        analysis was run with focus points.

        If a file does not exist it will be created. Include a .csv
        extension with files if you desire it.

        :param global_file_path: File path to store global results.
        :param cases_file_path: File path to store case Q_i results.
        :param dates_file_path: File path to store dates Q_t results.
        :param local_file_path: File path to store local Q_it results.
        :param focus_file_path: File poth to store focus Q_fi results.
        :param focus_local_file_path: File path to store local focus
        Q_fit results.
        """
        # Output Global Info
        global_output_file = open(global_file_path, 'w')
        study_globals = self._get_globals_dict()
        if self.binom:
            b = self.binom
            pairs = [('cases', b.cases), ('dates', b.dates), ('points', b.points)]
            if self.focus_entities:
                pairs.append(('focus', b.focus))
                pairs.append(('focus_points', b.focus_points))
            for name, binom_result in pairs:
                label = 'num_sig_' + name
                study_globals[label] = binom_result[0]
                study_globals[label + '_pval'] = binom_result[1]
                study_globals[label + '_sig'] = binom_result[2]
        global_string = ''
        for label, value in study_globals.items():
            global_string += "%s,%s\n" % (str(label), str(value))
        global_output_file.write(global_string)
        global_output_file.close()

        case_header, case_rows = self.get_tabular_individual_data()
        date_header, date_rows = self.get_tabular_date_data()
        local_header, local_rows = self.get_tabular_local_data()
        focus_header, focus_rows = self.get_tabular_focus_data()
        focus_local_header, focus_local_rows = self.get_tabular_local_focus_data()

        # Output other files
        file_params = [(cases_file_path, case_header, case_rows), (dates_file_path, date_header, date_rows),
                       (local_file_path, local_header, local_rows)]
        if self.focus_entities:
            if focus_file_path and focus_local_file_path:
                file_params.append((focus_file_path, focus_header, focus_rows))
                file_params.append((focus_local_file_path, focus_local_header, focus_local_rows))
            else:
                print("Did not export focus results since no/incomplete pathway was given for focus results.")
        else:
            print("Did not export focus results as none were specified during analysis.")
        for params in file_params:
            out_path, header, values = params
            with open(out_path, 'w') as out_file:
                writer = csv.writer(out_file, delimiter=',')
                writer.writerow(header)
                for row in values:
                    writer.writerow(row)

    def write_to_files_prefixed(self, pathway, prefix):
        if not os.path.isdir(pathway):
            os.makedirs(pathway)
        suffixes = ['global', 'individuals', 'dates', 'local', 'focus', 'focuslocal']
        paths = []
        for x in suffixes:
            paths.append(os.path.join(pathway, prefix + '_' + x + '.csv'))
        self.write_to_files(*paths)


class QStudyBinomialResults:
    """Container for the results of a binomal test for the number of
    significant statistics.

    Stores the result of a binomial test used to deal with multiple
    testing for cases, dates, points, focus entities, and focus points.
    Each value is given as
        (number of significant statistics, p-value, significance).
    """

    def __init__(self):
        self.cases = None
        self.dates = None
        self.points = None
        self.focus = None
        self.focus_points = None


class QStudyEntityResult:
    """Stores the statistical data for a case.

    .points gives a dict of point data with keys equal to the first date
    of a time slice.
    .sig_points stores a dict of only significant points
    .stat stores the case's Q_i statistic.
    """

    def __init__(self, stat):
        self.points = collections.OrderedDict()
        self.sig_points = collections.OrderedDict()
        self.stat = stat


class QStudyTimeSliceResult:
    """Stores the data relevant to a time slice.

    .points stores a dict of point statistics with keys of case ids.
    .sig_points stores a dict of only significant point stats with keys
    of case ids.
    .focus_points stores a dict of focus point stats with keys of focus
    ids.
    .sig_focus_points stores a dict of only significant focus points.
    The keys are focus ids.
    .stat stores the time slice's Q_i statistic.
    .duration gives the number of days the time slice is valid for.
    .start_date is the first date of the time slice.
    .end_date is the last date of the time slice.
    """

    def __init__(self, start_date, end_date, stat, duration):
        self.points = collections.OrderedDict()
        self.sig_points = collections.OrderedDict()
        self.focus_points = collections.OrderedDict()
        self.sig_focus_points = collections.OrderedDict()
        self.stat = stat
        self.duration_days = duration
        self.start_date = start_date
        self.end_date = end_date


class QStudyPointResult:
    """Stores location and Q_it statistic for a case.

    .loc gives the (x, y) location.
    .stat gives (Q_it, p-value, significance)
    """

    def __init__(self, stat, loc):
        self.loc = loc
        self.stat = stat


class QStatsStudy:
    """A container for Jacquez's Q statistics.

    This class is a container for all the data required to calculate
    Jacquez's Q statistics for case-control studies. Jacquez's Q is
    used to detect space-time clusters of disease exposure in such
    studies. Instances of this class can be created once with study
    data and the statistic can be performed several times with
    different options. Each result is returned as a QStudyResults
    object.

    Please note that the format for all dates is given as YYYYMMDD
    where YYYY is the year, MM is the month, and DD is the day.
    Dates are required in this format.

    The analysis requires two CSV files and a third optional one. Each
    file requires column headings, however, the column headings can be
    in any order.

    1) The first required file is the details file specifying the
    information for the cases and controls that does not change over
    time. The following columns headings are required:
        ID, is_case
    - The ID column gives a unique identifier for each case and control.
    - The is_case column in 1 if the individual is a case and 0 if they
     are a control.

    The following column headings are optional depending on analysis
    needs:
        DOD, latency, exposure_duration, weight
    -DOD is the date of diagnosis for the cases and matched controls.
    -latency is the number of days an individual is observed or
     estimated to have had the disease before diagnosis.
    - exposure_duration is the estimated number of days an individual
     was exposed to the disease.
    - weight is a float between 0 and 1 specifying an individuals
     probability of being a case during Monte Carlo testing. The weights
     can be obtained, for example, through logistic regression. The
     purpose of the weights is to account for covariates.

     2) The second required CSV file is the residential histories of all
     cases and controls with column headings:
        ID, start_date, end_date, x, y
    - ID is the identifier corresponding to the ID used in the details
     file.
    - start_date is the date of an individual's movement to a new
     location.
    - end_date is the day an individual moved out of a location.
    - x and y give the location of an individual.

    Individual movement is given as a time-series.
    For example, if person A is at location (3, 8) from 20150101 to
    20150312 and then moves to location (9, 7) until 20150422, then
    the histories csv would look like:
        ID, start_date, end_date, x, y
        A,  20150101,   20150312, 3, 8
        A,  20150312,   20150422, 9, 7

    3) The optional file is for focus locations of interest with
    headings:
        ID, start_date, end_date, x, y
    These are the same as the residential file but the IDs given here
    are created for locations of interest, such as factories.

    Information an Jacquez's Q can be found here:
        doi:  10.1186/1476-069X-4-4
        http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1083418/
    and here:
        doi:  10.1016/j.sste.2012.09.002
        http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3582034/
    """

    def __init__(self, study_details_path, study_histories_path, focus_data_path=None):
        """Create a study dataset for use with Jacquez's Q.

        :param study_details_path: The location of the details CSV file.
        :param study_histories_path: The location of the residential
        histories CSV file.
        :param focus_data_path: The location of the focus location CSV
        file. This is optional.
        """
        self._study_details_path = study_details_path
        self._study_histories_path = study_histories_path
        self._focus_data_path = focus_data_path

    def run_analysis(self, k, use_exposure, use_weights, alpha=0.05, shuffles=99, correction='BINOM', seed=None,
                     suppress_controls=False):
        """Perform Jacquez's Q.

        This method performs Jacquez's Q on the study dataset with the
        provided options and returns a QStudyResults object. Note: this
        method can be run several times with different options using the
        same QStatsStudy object, each time returning a new QStudyResults
        object.

        :param k: The number of nearest neighbors to query.
        :param use_exposure: If True, only considers cases within their
        exposure trace (the dates between initial disease exposure and
        disease formation). If false, clusters are detected based only
        on case-control status.
        Note: this option can only be used if DOD,
        latency, and exposure_duration are provided in the details file.
        :param use_weights: If True, uses weights for case-control
        shuffling during Monte Carlo testing to account for covariates.
        If false uses all individuals are assumed to have equal disease
        risk. Note: The weights must be provided in the details dataset.
        :param alpha: The value to use for significance testing.
        :param shuffles: The number of permutations of Monte Carlo
        testing to conduct. Note: This value determined the minimum
        p-value resolution. Higher values will take longer to conduct.
        :param correction: The type of correction to apply for multiple
        testing. 'FDR' applies a Benjamini-Yekutieli False Discovery
        Rate. Note that this often requires a large number of shuffles
        for any significance. 'BINOM' applies the binomial method used
        in doi: 10.1016/j.sste.2012.09.002. If any other string such as
        None is given than no correction will be used.
        :param seed: A number used to seed the random number generator.
        If none is provided, a random number between 0 and (2^32)-1 is used.
        :param suppress_controls: If set to true, only results for cases
        will be output instead of results for both cases and controls.
        :return: A QStudyResults object.
        """
        # Set the seed
        if not seed:
            seed = random.randint(0, 2**32-1)
        random.seed(seed)
        # Load the study entities
        details_legend, details_values = _load_csv_file(self._study_details_path)
        study_entities = QStatsStudy._extract_study_entities(details_legend, details_values, use_exposure, use_weights)
        # Load the residential histories
        histories_legend, histories_values = _load_csv_file(self._study_histories_path)
        if self._focus_data_path:
            focus_legend, focus_values = _load_csv_file(self._focus_data_path)
            focus_entities = QStatsStudy._extract_focus_entities(focus_legend, focus_values)
        else:
            focus_legend, focus_values, focus_entities = None, None, None
        unique_dates = QStatsStudy._extract_unique_dates(study_entities, histories_legend, histories_values,
                                                         focus_legend, focus_values, use_exposure)
        # if not self._data_in_slices_format:
        time_slices = \
            QStatsStudy._create_time_slices_from_series(unique_dates, study_entities, histories_legend,
                                                        histories_values, focus_entities=focus_entities,
                                                        f_legend=focus_legend, focus_histories=focus_values,
                                                        exposure=use_exposure)
        # TODO: Check for someone at two places at once and such
        QStatsStudy._sort_time_slices(time_slices)
        QStatsStudy._find_time_slice_deltas(time_slices)
        QStatsStudy._remove_empty_time_slices(time_slices)
        QStatsStudy._cache_neighbors_in_time_slices(time_slices, k)

        # Calculate Observed Statistic
        for time_slice in time_slices:
            time_slice.calculate_observed_Qt_and_points_Qit()
            if focus_entities:
                time_slice.calculate_observed_Qft()
        global_Q = _StudyStatistic()
        global_Q.statistic = 0
        global_Qf = _StudyStatistic()
        global_Qf.statistic = 0
        for entity in study_entities.values():
            entity.calculate_entity_statistic()
            if entity.is_case:
                global_Q.statistic += entity.entity_stat.statistic
        if focus_entities:
            for focus_entity in focus_entities.values():
                focus_entity.calculate_entity_statistic()
                global_Qf.statistic += focus_entity.entity_stat.statistic

        # Calculate Reference Statistic
        for shuffle in range(0, shuffles):
            QStatsStudy._shuffle_flags(study_entities, use_weights)
            for time_slice in time_slices:
                time_slice.calculate_reference_distribution()
                if focus_entities:
                    time_slice.calculate_focus_point_distribution()
            global_Q_reference = 0
            for entity in study_entities.values():
                global_Q_reference += entity.calculate_reference_distribution()
            if global_Q_reference >= global_Q.statistic:
                global_Q.shuffles_passed += 1
            if focus_entities:
                global_Qf_reference = 0
                for focus in focus_entities.values():
                    global_Qf_reference += focus.calculate_reference_distribution()
                if global_Qf_reference >= global_Qf.statistic:
                    global_Qf.shuffles_passed += 1

        # Calculate p-values
        for time_slice in time_slices:
            time_slice.Qt.calculate_p_value(shuffles)
            for point in time_slice.points:
                point.point_stat.calculate_p_value(shuffles)
            for focus in time_slice.focus_points:
                focus.point_stat.calculate_p_value(shuffles)
        for study_entity in study_entities.values():
            study_entity.entity_stat.calculate_p_value(shuffles)
        global_Q.calculate_p_value(shuffles)
        if focus_entities:
            for focus_entity in focus_entities.values():
                focus_entity.entity_stat.calculate_p_value(shuffles)
            global_Qf.calculate_p_value(shuffles)

        # Adjust for multiple testing if applicable
        if str(correction).upper() == 'FDR':
            correct_alpha = QStatsStudy._fdr_correction_dependent(
                QStatsStudy._extract_p_values_from_points_in_time_slices(time_slices), alpha)
        else:
            correct_alpha = alpha

        # Create the results object
        results = QStudyResults()
        results.k = k
        results.number_permutation_shuffles = shuffles
        results.seed = seed
        results.adjusted_alpha = correct_alpha
        results.submitted_alpha = alpha
        results.alpha_adjustment_method = str(correction).upper()
        results.exposure_enabled = use_exposure
        results.case_weights_enabled = use_weights
        results.Q_case_years = (global_Q.statistic / 365.0, global_Q.p_value, int(global_Q.p_value <= correct_alpha))
        results.normalized_Q = results.Q_case_years[0] / len(study_entities)
        if focus_entities:
            results.Qf_case_years = (
                global_Qf.statistic / 365.0, global_Qf.p_value, int(global_Qf.p_value <= correct_alpha))
            results.normalized_Qf = results.Qf_case_years[0] / len(focus_entities)
        # Set the individual-level statistics, Qi
        for entity_name in sorted(study_entities.keys()):
            entity = study_entities[entity_name]
            if entity.is_case:
                is_sig = int(entity.entity_stat.p_value <= correct_alpha)
                stat = (entity.entity_stat.statistic / 365.0, entity.entity_stat.p_value, is_sig)
                individual_result = QStudyEntityResult(stat)
                results.cases[entity.identity] = individual_result
                if is_sig:
                    results.sig_cases[entity.identity] = individual_result
            # Deal with control output unless it is off
            elif not suppress_controls:
                results.controls[entity.identity] = QStudyEntityResult((None, None, None))
        # Set Qfi for focus points through time
        if self._focus_data_path:
            for focus_name in sorted(focus_entities.keys()):
                focus = focus_entities[focus_name]
                is_sig = int(focus.entity_stat.p_value <= correct_alpha)
                stat = (focus.entity_stat.statistic / 365.0, focus.entity_stat.p_value, is_sig)
                focus_result = QStudyEntityResult(stat)
                results.focus_entities[focus.identity] = focus_result
                if is_sig:
                    results.sig_focus_entities[focus.identity] = focus_result
        # Set the time slice statistic Qt
        for time_slice in time_slices:
            time_is_sig = int(time_slice.Qt.p_value <= correct_alpha)
            ts_stat = (time_slice.Qt.statistic, time_slice.Qt.p_value, time_is_sig)
            time_result = QStudyTimeSliceResult(time_slice.date, time_slice.end_date, ts_stat, time_slice.delta)
            results.time_slices[time_slice.date] = time_result
            if time_is_sig:
                results.sig_time_slices[time_slice.date] = time_result
            # Keep track of dates with number points <= k
            if len(time_slice.points) <= results.k + 1:
                results.dates_lower_k_plus_one[time_slice.date] = time_result
            for study_point in time_slice.points:
                entity_id = study_point.owner.identity
                location = study_point.x, study_point.y
                if study_point.owner.is_case:
                    point_is_sig = int(study_point.point_stat.p_value <= correct_alpha)
                    qit_stat = (
                        int(study_point.point_stat.statistic / time_slice.delta), study_point.point_stat.p_value,
                        point_is_sig)
                    qit = QStudyPointResult(qit_stat, location)
                    time_result.points[entity_id] = qit
                    results.cases[entity_id].points[time_slice.date] = qit
                    if point_is_sig:
                        results.number_sig_case_points += 1
                    if time_is_sig and point_is_sig:
                        results.sig_time_slices[time_slice.date].sig_points[entity_id] = qit
                    if point_is_sig and entity_id in results.sig_cases:
                        results.sig_cases[entity_id].sig_points[time_slice.date] = qit
                # Deal with control output unless it is off
                elif not suppress_controls:
                    qit = (None, None, None)
                    results.controls[entity_id].points[time_slice.date] = QStudyPointResult(qit, location)
                    time_result.points[entity_id] = QStudyPointResult(qit, (study_point.x, study_point.y))
            if self._focus_data_path:
                for focus_point in time_slice.focus_points:
                    focus_point_is_sig = int(focus_point.point_stat.p_value <= correct_alpha)
                    qft_stat = (
                        int(focus_point.point_stat.statistic / time_slice.delta), focus_point.point_stat.p_value,
                        focus_point_is_sig)
                    qft = QStudyPointResult(qft_stat, (focus_point.x, focus_point.y))
                    focus_id = focus_point.owner.identity
                    time_result.focus_points[focus_id] = qft
                    results.focus_entities[focus_id].points[time_slice.date] = qft
                    if focus_point_is_sig:
                        results.number_sig_focus_points += 1
                    if time_is_sig and focus_point_is_sig:
                        results.sig_time_slices[time_slice.date].sig_focus_points[focus_id] = qit
                    if focus_point_is_sig and focus_id in results.sig_focus_entities:
                        results.sig_focus_entities[focus_id].sig_points[time_slice.date] = qit

        # Test the number of significant statistics if applicable
        if str(correction).upper() == 'BINOM':
            results.binom = QStudyBinomialResults()
            results.binom.cases = QStatsStudy._get_binom_sig(len(results.cases), len(results.sig_cases), alpha)
            results.binom.dates = QStatsStudy._get_binom_sig(len(results.time_slices), len(results.sig_time_slices),
                                                             alpha)

            num_point_stats = sum(len(results.time_slices[date].points) for date in results.time_slices)
            results.binom.points = QStatsStudy._get_binom_sig(num_point_stats, results.number_sig_case_points, alpha)

            results.binom.focus = QStatsStudy._get_binom_sig(len(results.focus_entities),
                                                             len(results.sig_focus_entities), alpha)

            num_fpoint_stats = sum(len(results.time_slices[date].sig_focus_points) for date in results.time_slices)
            results.binom.focus_points = QStatsStudy._get_binom_sig(num_fpoint_stats, results.number_sig_focus_points,
                                                                    alpha)

        return results

    @staticmethod
    def _get_binom_sig(total, num_sig, alpha):
        p_val = 1 - scipy.stats.binom(total, alpha).cdf(num_sig - 1)
        return num_sig, p_val, 1 if p_val <= alpha else 0

    @staticmethod
    def _extract_unique_dates(entities, point_legend, point_histories, focus_legend, focus_data, exposure=False):
        unique_dates = set()
        for row in point_histories:
            entity_id = row[point_legend['ID']]
            if entity_id in entities:
                unique_dates.add(int(row[point_legend['start_date']]))
                unique_dates.add(int(row[point_legend['end_date']]))
                if exposure:
                    unique_dates.add(int(entities[entity_id].date_of_initial_exposure))
                    unique_dates.add(int(entities[entity_id].date_of_contraction))
        if focus_legend is not None and focus_data is not None:
            for row in focus_data:
                unique_dates.add(int(row[focus_legend['start_date']]))
                unique_dates.add(int(row[focus_legend['end_date']]))
        return unique_dates

    @staticmethod
    def _collect_series_data_into_time_slice(time_slice, point_legend, point_histories, study_entities, exposure=False):
        for row in point_histories:
            entity_id = row[point_legend['ID']]
            if entity_id in study_entities:
                start_date = int(row[point_legend['start_date']])
                end_date = int(row[point_legend['end_date']])
                if start_date <= time_slice.date < end_date:
                    x, y = float(row[point_legend['x']]), float(row[point_legend['y']])
                    entity = study_entities[entity_id]
                    point = _StudyPoint(x, y, entity)
                    if exposure and (time_slice.date < entity.date_of_initial_exposure
                                     or time_slice.date >= entity.date_of_contraction):
                        point.exposed = False
                    time_slice.points.append(point)

    @staticmethod
    def _collect_series_focus_data_into_time_slice(time_slice, focus_legend, focus_histories, focus_entities):
        for row in focus_histories:
            focus_id = row[focus_legend['ID']]
            if focus_id in focus_entities:
                start_date = int(row[focus_legend['start_date']])
                end_date = int(row[focus_legend['end_date']])
                if start_date <= time_slice.date < end_date:
                    x, y = float(row[focus_legend['x']]), float(row[focus_legend['y']])
                    focus_point = _FocusPoint(x, y, focus_entities[focus_id])
                    time_slice.focus_points.append(focus_point)

    @staticmethod
    def _create_time_slices_from_series(unique_dates, study_entities, p_legend, point_histories,
                                        focus_entities=None, f_legend=None, focus_histories=None, exposure=True):
        time_slices = []
        for selected_date in unique_dates:
            time_slice = _TimeSlice(selected_date)
            QStatsStudy._collect_series_data_into_time_slice(time_slice, p_legend, point_histories,
                                                             study_entities, exposure)
            if focus_entities and focus_histories.any() and f_legend:
                QStatsStudy._collect_series_focus_data_into_time_slice(time_slice, f_legend,
                                                                       focus_histories, focus_entities)
            time_slices.append(time_slice)
        return time_slices

    @staticmethod
    def _extract_study_entities(detail_legend, data_rows, exposure=False, weights=False):
        # Returns a dictionary of individuals IDs as keys and the _Individual object as values
        # TODO: Unit test this function that creates _Individual objects
        # TODO: Make sure that date of contraction is unit tested
        study_entities = {}
        for row in data_rows:
            # TODO: Get rid of the magic strings and have them passed in from command line arguments instead
            identity = row[detail_legend['ID']]
            is_case = 1 if row[detail_legend['is_case']].lower() not in ('false', '0', 'no') else 0
            if exposure:
                date_of_diagnosis = int(row[detail_legend['DOD']])
                latency = int(row[detail_legend['latency']])
                exposure_duration = int(row[detail_legend['exposure_duration']])
                # Determine the date of contraction using the date of diagnosis and the latency
                date_of_diagnosis = datetime.datetime.strptime(str(date_of_diagnosis), "%Y%m%d")
                date_of_contraction = date_of_diagnosis - datetime.timedelta(days=int(latency))
                date_first_exposure = (date_of_diagnosis - datetime.timedelta(days=int(latency + exposure_duration)))
                date_of_contraction = int(date_of_contraction.strftime("%Y%m%d"))
                date_first_exposure = int(date_first_exposure.strftime("%Y%m%d"))
            else:
                date_of_contraction = None
                date_first_exposure = None
            if weights:
                case_weight = float(row[detail_legend['weight']])
            else:
                case_weight = None
            study_entities[identity] = (
                _StudyEntity(identity, is_case, date_first_exposure, date_of_contraction, case_weight))
        return study_entities

    @staticmethod
    def _extract_focus_entities(focus_legend, focus_data):
        focus_entities = {}
        for row in focus_data:
            identity = row[focus_legend['ID']]
            if identity not in focus_entities:
                focus_entities[identity] = _FocusEntity(identity)
        return focus_entities

    @staticmethod
    def _sort_time_slices(time_slices):
        time_slices.sort(key=lambda time_slice: time_slice.date)

    @staticmethod
    def _find_time_slice_deltas(time_slices):
        if len(time_slices) <= 1:
            return None
        for index, time_slice in enumerate(time_slices[:-1]):
            present_date = datetime.datetime.strptime(str(time_slice.date), "%Y%m%d")
            next_date = datetime.datetime.strptime(str(time_slices[index + 1].date), "%Y%m%d")
            time_slice.delta = (next_date - present_date).days
            time_slice.end_date = next_date.strftime("%Y%m%d")

    @staticmethod
    def _remove_empty_time_slices(time_slices):
        for time_slice in list(time_slices):
            if not time_slice.points or not time_slice.delta:
                for point in time_slice.points:
                    if point in point.owner.points:
                        point.owner.points.remove(point)
                for focus_point in time_slice.focus_points:
                    if focus_point in focus_point.owner.points:
                        focus_point.owner.points.remove(focus_point)
                time_slices.remove(time_slice)

    @staticmethod
    def _cache_neighbors_in_time_slices(time_slices, number_neighbors):
        if len(time_slices) == 0:
            raise ValueError('At least 1 time slice must exist.')
        for time_slice in time_slices:
            if len(time_slice.points) <= 1:
                continue
            if len(time_slice.points) <= number_neighbors:
                time_slice.cache_nearest_neighbors(len(time_slice.points) - 1)
            else:
                time_slice.cache_nearest_neighbors(number_neighbors)

    @staticmethod
    def _equal_risk_shuffle(study_entities):
        if len(study_entities) == 0:
            raise ValueError('At least 1 study entity must exist.')
        remaining_case_flags = len([entity for entity in study_entities.values() if entity.is_case])
        remaining_entities = list(study_entities.values())
        while remaining_case_flags > 0:
            random_entity = random.choice(remaining_entities)
            # Possible Speedup: remaining_entities = [e for e in remaining_entities if e is not random_entity]
            remaining_entities.remove(random_entity)
            random_entity.set_temp_case_status_of_points(True)
            remaining_case_flags -= 1
        for control in remaining_entities:
            control.set_temp_case_status_of_points(False)

    @staticmethod
    def _case_weight_shuffle(study_entities):
        if len(study_entities) == 0:
            raise ValueError("At least 1 study entity must exist.")
        remaining_case_flags = len([entity for entity in study_entities.values() if entity.is_case])
        remaining_entities = list(study_entities.values())
        remaining_entities.sort(key=lambda entity: entity.case_weight)
        while remaining_case_flags > 0:
            weights_total = sum([entity.case_weight for entity in remaining_entities])
            normalized_weight = {}
            entity_intervals = {}
            for entity in remaining_entities:
                normalized_weight[entity] = float(entity.case_weight) / weights_total
            # The first person will have an interval of 0 up to its normalized weight
            first_entity = remaining_entities[0]
            entity_intervals[first_entity] = (0, normalized_weight[first_entity])
            # The rest are based on the person before them
            if len(remaining_entities) > 1:
                for index, entity in enumerate((remaining_entities[1:])):
                    # Index is behind by 1 since we enumerated while disregarding the first entity
                    previous_entity = remaining_entities[index]
                    previous_bound = entity_intervals[previous_entity][1]
                    entity_intervals[entity] = (previous_bound, previous_bound + normalized_weight[entity])
            # Last person's range should end at 1
            last_entity = remaining_entities[-1]
            entity_intervals[last_entity] = (entity_intervals[last_entity][0], 1)
            # Pick a random number between 0 and 1
            selection = random.random()
            # Find which individual contains that number in its weight interval. That individual is a case
            for entity in remaining_entities:
                if entity_intervals[entity][0] <= selection <= entity_intervals[entity][1]:
                    remaining_entities.remove(entity)
                    entity.set_temp_case_status_of_points(True)
                    remaining_case_flags -= 1
                    break
        for control in remaining_entities:
            control.set_temp_case_status_of_points(False)

    @staticmethod
    def _shuffle_flags(study_entities, use_case_weights):
        if not use_case_weights:
            # Everybody has the same chance of being a case
            QStatsStudy._equal_risk_shuffle(study_entities)
        else:
            # Chance of being a case is based on study entity case weights
            QStatsStudy._case_weight_shuffle(study_entities)

    @staticmethod
    def _extract_p_values_from_points_in_time_slices(time_slices):
        p_values = []
        for time_slice in time_slices:
            for point in time_slice.points:
                p_values.append(point.point_stat.p_value)
            for focus in time_slice.focus_points:
                p_values.append(focus.point_stat.p_value)
        return p_values

    @staticmethod
    def _fdr_correction_dependent(dependent_p_values, alpha_value):
        # This is the False Discovery Rate as explained here:
        # Benjamini Y, Yekutieli D. The Control of the False Discovery Rate in Multiple Testing under Dependency.
        # The Annals of Statistics 2001 Aug.;29(4):1165-1188.
        if len(dependent_p_values) == 0:
            raise ValueError('Length of p-values must be greater than 0.')
        # Sort the p-values in ascending order
        dependent_p_values.sort()
        # Traverse the list backwards and find the first index where p-value <= (index * alpha / #p-values)
        number_of_p_values = len(dependent_p_values)
        # this ratio never changes so it only needs to be calculated once
        ratio = alpha_value / (number_of_p_values * sum([1.0 / i for i in range(1, number_of_p_values + 1)]))
        for index in range(1, number_of_p_values + 1):
            adjusted = index * ratio
            if dependent_p_values[index - 1] <= adjusted:
                return dependent_p_values[index - 1]
        # If none of the p-values in the list passed then return 0
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate the Jacquez Q-statistics.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     epilog="[1] Sloan CD, Jacquez GM, Gallagher CM, et al. Performance of "
                                            "cancer cluster Q-statistics for case-control residential histories. "
                                            "Spatial and spatio-temporal epidemiology. "
                                            "2012;3(4):297-310. doi:10.1016/j.sste.2012.09.002.")
    parser.add_argument('--resident', '-r', required=True, dest='histories',
                        help="Location of the residential histories file.")
    parser.add_argument('--details', '-d', required=True,
                        help="Location of individuals' status dataset. Case-control status must be given for all \
                        individuals.")
    parser.add_argument('--output_location', '-o', required=True,
                        help="Pathway to the folder to output the results.")
    parser.add_argument('--output_prefix', '-p', required=True,
                        help="The prefix to include in the file names of the output.")
    parser.add_argument('--exposure', '-e', action='store_true', default=False, dest='use_exposure',
                        help="If this flag is added then the dataset containing case-control flags must also \
                        contain columns 'DOD' and 'latency' for the date of diagnosis and the number of days of \
                        disease latency. These values must be specified for both cases and controls. The presence of \
                        this flag signals for clustering of exposure. In its absence clustering of points will be \
                        done instead.")
    parser.add_argument('--weights', '-w', action='store_true', default=False, dest='use_case_weights',
                        help="If this flag is supplied then individuals will have their case-control flags shuffled \
                        in a way that adjusts for co-variates. A 'weight' column must be supplied in the \
                        case-control dataset with values between 0 and 1. If this flag is not added then the \
                        calculation will assume equal disease risk for everyone.")
    parser.add_argument('--focus_data', '-f',
                        help="Location of the dataset containing focus points of geographic interest, \
                        such as factories. The dataset must be in time series format.")
    parser.add_argument('--neighbors', '-k', type=int, default=15,
                        help='Value K to use for number of nearest neighbors.')
    parser.add_argument('--alpha', '-a', type=float, default=0.05,
                        help='Value used to check for significance of test results.')
    parser.add_argument('--shuffles', '-s', type=int, default=99,
                        help='The number of case-control permutations to conduct when calculating pseudo p-values.')
    parser.add_argument('--correction', '-c', type=str, default='BINOM',
                        help="Correction to apply for multiple testing. "
                             "'FDR' applies a Benjamini-Yekutieli False Discovery Rate. Note that this often requires "
                             "a large number of shuffles for any significance."
                             "'BINOM' applies the binomial method used in [1]; this is the default. "
                             "If any other string such as 'NONE' is given than no correction will be used.")
    parser.add_argument('--no_inspect', '-N', action='store_true', default=False, dest='no_inspect',
                        help="Pass this flag to prevent the program from pre-parsing the data for errors.")
    parser.add_argument('--seed', type=int, default=None, dest='seed',
                        help="The seed to use with the random number generator.")
    parser.add_argument('--only-cases', '-O', action='store_true', default=False, dest='output_controls',
                        help="Pass this flag to prevent output of control results.")
    args = parser.parse_args()
    run_approved = True
    parameter_errors = ''
    if args.neighbors <= 0:
        parameter_errors += "Number of neighbors must be a positive integer.\n"
        run_approved = False
    if args.alpha <= 0 or args.alpha >= 1:
        parameter_errors += "Alpha must be a number between 0 and 1.\n"
        run_approved = False
    if args.shuffles < 9:
        parameter_errors += "Number of shuffles must be at least 9.\n"
        run_approved = False
    if parameter_errors:
        sys.stderr.write(parameter_errors)
    if not args.no_inspect:
        weights = args.use_case_weights
        errors = check_data_dirty(args.details, args.histories, args.focus_data, args.use_exposure, weights)
        error_string = ""
        if errors:
            for error in errors:
                error_string += str(error) + os.linesep
            run_approved = False
            sys.stderr.write(error_string)

    if run_approved:
        q_analysis = QStatsStudy(args.details, args.histories, args.focus_data)
        results = q_analysis.run_analysis(args.neighbors, args.use_exposure, args.use_case_weights, args.alpha,
                                          args.shuffles, args.correction, seed=args.seed,
                                          suppress_controls=args.output_controls)
        # results.print_results()
        results.write_to_files_prefixed(args.output_location, args.output_prefix)
