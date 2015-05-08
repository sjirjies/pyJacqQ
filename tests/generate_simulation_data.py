# This file is part of jacqq.py
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

import random
import string
import datetime
import csv
import sys
import argparse
import math


class SimIndividual:
    case_exposure_threshold = 4000
    max_moves = 2

    def __init__(self, identity, start_x, start_y, start_date, latency):
        """Create a simulated individual.

        :param identity: A unique identifier for the individual.
        :param start_x: The starting x location.
        :param start_y: The starting y location.
        :param start_date: The first date the individual exists.
        :param latency: The modeled length of time the disease in dormant in the individual after it's developed.
        """
        self.identity = identity
        self.locations = [(start_x, start_y)]
        self.location_dates = [start_date]
        self.accumulated_exposure = 0
        self.has_case_status = False
        self.date_of_initial_exposure = None
        self.date_of_contraction = None
        self.date_of_diagnosis = None
        self.latency_duration = latency
        self.risk_weight = random.random()

    def accumulate_exposure(self, exposure_amount, exposure_date):
        """Expose the individual to disease-causing contamination.

        :param exposure_amount: The amount of contamination to expose.
        :param exposure_date: The date of the contamination exposure.
        """
        if not self.date_of_initial_exposure:
            self.date_of_initial_exposure = exposure_date
        self.accumulated_exposure += exposure_amount
        if self.accumulated_exposure >= SimIndividual.case_exposure_threshold and not self.has_case_status:
            self.has_case_status = True
            self.date_of_contraction = exposure_date
            self.date_of_diagnosis = exposure_date + datetime.timedelta(days=self.latency_duration)

    def move(self, x_move, y_move, move_date):
        """Move the individual to a different location.

        :param x_move: The new x location.
        :param y_move: The new y location.
        :param move_date: The date of the movement.
        """
        current_x = self.locations[-1][0]
        current_y = self.locations[-1][1]
        self.locations.append((current_x + x_move, current_y + y_move))
        self.location_dates.append(move_date)

    def get_current_location(self):

        """Get the current x,y location of the individual.

        :rtype : The latest, or current, location of the individual.
        """
        return self.locations[-1]


class ExposureSource:
    def __init__(self, strength, radius, x, y, linear):
        """Create a source of disease-causing contamination.

        :param strength: The strength of the contamination.
        :param radius: The radius of influence of the source.
        :param x: The x location of the source.
        :param y: The y location of the source.
        :param linear: If true, strength decreases linearly from the source. If false, strength is constant.
        """
        self.strength = strength
        self.radius = radius
        self.x = x
        self.y = y
        self.is_linear = linear


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a simulated disease exposure test data set.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-n', type=int, default=500,
                        help="Total number of individuals in the study.", dest='number_individuals')
    parser.add_argument('-m', type=int, default=3,
                        help='Number of moves for each individual.', dest='num_moves')
    parser.add_argument('-l', type=int, default=73,
                        help='Number of days of latency between disease and diagnosis.', dest='latency')
    parser.add_argument('histories_data', help="Location to write individuals' residential history.")
    parser.add_argument('details_data', help="Location to write individuals' status data set.")
    parser.add_argument('focus_data', help="Location to write focus data set")
    args = parser.parse_args()

    # Run the simulation
    start_date = datetime.date(2015, 1, 1)
    simulation_days = args.latency * 5

    DistanceSource = ExposureSource(75, 75, 90, 90, linear=True)
    ConstantLargeSource = ExposureSource(20, 120, -75, -75, linear=False)
    ConstantSmallSource = ExposureSource(40, 40, 130, -120, linear=False)

    sources = [DistanceSource, ConstantLargeSource, ConstantSmallSource]
    exposure_duration = args.latency * 2
    # explosion = (75, 100, -75)
    # explosion_day = (simulation_days//3)*5
    # print("Disease Explosion %d days in on %s" %
    #      (explosion_day, (start_date + datetime.timedelta(days=explosion_day)).strftime("%Y%m%d")))
    min_move_dist = 15
    max_move_dist = 100

    def increment_label(label):
        if len(label) == 1:
            if label == 'Z':
                return 'AA'
            else:
                return string.ascii_uppercase[string.ascii_uppercase.index(label) + 1]
        else:
            if label[0] == 'Z':
                return 'A' + increment_label(label[1:])
            else:
                return string.ascii_uppercase[string.ascii_uppercase.index(label[0]) + 1] + label[1:]

    def alpha_labels():
        label = 'A'
        while True:
            yield label[::-1]
            label = increment_label(label)

    labels = alpha_labels()
    individuals = []
    move_dates = {}
    start_radius = 200
    for i in range(args.number_individuals):
        theta = random.random() * 2
        radius = random.randint(0, start_radius)
        x, y = int(math.cos(theta*math.pi) * radius), int(math.sin(theta*math.pi) * radius)
        ind = SimIndividual(next(labels), x, y, start_date, args.latency)
        individuals.append(ind)
        dates_for_ind = []
        for offset in random.sample(range(0, simulation_days), args.num_moves):
            dates_for_ind.append(start_date + datetime.timedelta(days=offset))
        move_dates[ind] = dates_for_ind
    for day_number in range(1, simulation_days):
        current_day = start_date + datetime.timedelta(days=day_number)
        for person in individuals:
            if current_day in move_dates[person]:
                theta = random.random() * 2
                move_distance = random.randint(min_move_dist, max_move_dist)
                x_move = int(math.cos(theta*math.pi) * move_distance)
                y_move = int(math.sin(theta*math.pi) * move_distance)
                person.move(x_move, y_move, current_day)
            for source in sources:
                x, y = person.get_current_location()
                distance_to_source = math.hypot((x - source.x), (y - source.y))
                if source.is_linear:
                    if distance_to_source <= source.radius:
                        exposure = source.strength - distance_to_source
                    else:
                        exposure = 0
                else:
                    exposure = source.strength if distance_to_source <= source.radius else 0
                if exposure > 0:
                    person.accumulate_exposure(exposure, current_day)
        # Check for exposure explosion
        # if day_number == explosion_day:
        #     for person in individuals:
        #         x, y = person.get_current_location()
        #         distance_to_explosion = math.hypot((x - explosion[1]), (y - explosion[2]))
        #         if distance_to_explosion <= explosion[0]:
        #             person.accumulate_exposure(SimIndividual.case_exposure_threshold, current_day)
    # Give everyone a last date
    for person in individuals:
        person.location_dates.append(person.location_dates[-1] + datetime.timedelta(days=1))

    cases = [ind for ind in individuals if ind.has_case_status]
    controls = [ind for ind in individuals if not ind.has_case_status]
    print('CASES:', len(cases))
    print('CONTROLS:', args.number_individuals - len(cases))
    # Randomly match cases to controls
    if len(cases) == 0:
        print("No cases generated. Exiting.")
        sys.exit(1)
    for control in controls:
        case = random.choice(cases)
        control.date_of_initial_exposure = case.date_of_initial_exposure
        control.date_of_contraction = case.date_of_contraction
        control.date_of_diagnosis = case.date_of_diagnosis

    # Generate focus data
    focus_file = args.focus_data
    csv_file = open(focus_file, 'w')
    try:
        writer = csv.writer(csv_file)
        writer.writerow(('ID', 'start_date', 'end_date', 'x', 'y'))
        first_date = start_date.strftime("%Y%m%d")
        end_date = (start_date + datetime.timedelta(days=simulation_days)).strftime("%Y%m%d")
        writer.writerow(('Large Constant', first_date, end_date, ConstantLargeSource.x, ConstantLargeSource.y))
        writer.writerow(('Medium Linear', first_date, end_date, DistanceSource.x, DistanceSource.y))
        writer.writerow(('Small Constant', first_date, end_date, ConstantSmallSource.x, ConstantSmallSource.y))
        writer.writerow(('Away From Sources', first_date, end_date, -150, 150))
        # writer.writerow(('On Explosion', first_date, end_date, explosion[1], explosion[2]))
    finally:
        csv_file.close()
    print("Wrote %s" % args.focus_data)

    # Generate details data
    details_file = args.details_data
    csv_file = open(details_file, 'w')
    try:
        writer = csv.writer(csv_file)
        writer.writerow(('ID', 'is_case', 'DOD', 'latency', 'weight', 'exposure_duration'))
        for person in individuals:
            # exposure_duration = (person.date_of_diagnosis - person.date_of_initial_exposure).days
            writer.writerow((person.identity, 1 if person.has_case_status else 0,
                             person.date_of_diagnosis.strftime("%Y%m%d"), person.latency_duration, person.risk_weight,
                             exposure_duration))
    finally:
        csv_file.close()
    print("Wrote %s" % args.details_data)

    # Generate time series data
    file_location = args.histories_data
    csv_file = open(file_location, 'w')
    try:
        writer = csv.writer(csv_file)
        writer.writerow(('ID', 'start_date', 'end_date', 'x', 'y'))
        for person in individuals:
            for index, location in enumerate(person.locations):
                writer.writerow((person.identity, person.location_dates[index].strftime("%Y%m%d"),
                                 person.location_dates[index+1].strftime("%Y%m%d"), location[0], location[1]))
    finally:
        csv_file.close()
    print("Wrote %s" % args.histories_data)
