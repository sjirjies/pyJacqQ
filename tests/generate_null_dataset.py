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

import os
import csv
import argparse

# This script generates a null data set where all outputs are 0 when passed through Jacquez's Q.

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a lattice of pentagon case-control points",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('x_size', type=int, help="Number of clusters to form in the x direction.")
    parser.add_argument('y_size', type=int, help="Number of clusters to form in the y direction.")
    parser.add_argument('histories_data', help="Location to write individuals' residential history.")
    parser.add_argument('details_data', help="Location to write individuals' status data set.")
    parser.add_argument('focus_data', help="Location to write focus data set")
    args = parser.parse_args()

    lattice_size_y = args.x_size
    lattice_size_x = args.y_size

    case_locations = []
    for xi in range(0, lattice_size_x):
        for yi in range(0, lattice_size_y):
            case_locations.append((2+(10*xi), 2+(10*yi)))

    focus_locations = []
    for xi in range(0, lattice_size_x - 1):
        for yi in range(0, lattice_size_y - 1):
            focus_locations.append((7+(10*xi), 7+(10*yi)))

    # Generate details data
    csv_file = open(args.details_data, 'w')
    try:
        writer = csv.writer(csv_file)
        writer.writerow(('ID', 'is_case'))
        for case_index, case_point in enumerate(case_locations):
            writer.writerow(('case_'+str(case_index+1), 1))
            for control_name in ('A', 'B', 'C', 'D', 'E'):
                writer.writerow(('control_'+str(case_index+1)+control_name, 0))
    finally:
        csv_file.close()

    # Generate time series data
    csv_file = open(args.histories_data, 'w')
    try:
        writer = csv.writer(csv_file)
        writer.writerow(('ID', 'start_date', 'end_date', 'x', 'y'))
        start_date = '20150101'
        end_date = '20150102'
        for id_index, case_point in enumerate(case_locations):
            writer.writerow(('case_'+str(id_index+1), start_date, end_date, case_point[0], case_point[1]))
            writer.writerow(('control_'+str(id_index+1)+'A', start_date, end_date, case_point[0], case_point[1]-2))
            writer.writerow(('control_'+str(id_index+1)+'B', start_date, end_date, case_point[0]+2, case_point[1]))
            writer.writerow(('control_'+str(id_index+1)+'C', start_date, end_date, case_point[0]+1, case_point[1]+1))
            writer.writerow(('control_'+str(id_index+1)+'D', start_date, end_date, case_point[0]-1, case_point[1]+1))
            writer.writerow(('control_'+str(id_index+1)+'E', start_date, end_date, case_point[0]-2, case_point[1]))
    finally:
        csv_file.close()
    print("Finished generating null dataset")

    # Generate focus data
    csv_file = open(args.focus_data, 'w')
    try:
        writer = csv.writer(csv_file)
        writer.writerow(('ID', 'start_date', 'end_date', 'x', 'y'))
        start_date = '20150101'
        end_date = '20150102'
        for index, location in enumerate(focus_locations):
            writer.writerow(('focus_' + str(index+1), start_date, end_date, location[0], location[1]))
    finally:
        csv_file.close()