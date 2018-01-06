# !/usr/bin/python3
# coding: utf_8

# Copyright 2017-2018 Stefano Fogarollo
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


""" Tools """

import numpy as np

from pyhodl.config import INFINITY

LONG_DEC_FORMAT = "{0:.5f}"
SHORT_DEC_FORMAT = "{0:.3f}"


def get_actual_class_name(class_name):
    """
    :param class_name: str
        Class name of object
    :return: str
        Actual class name (without all path)
    """

    return str(type(class_name)).split("'")[-2].split(".")[-1]


def callable_to_str(func, args, kwargs):
    """
    :param func: callback function
        Function to wrap
    :param args: *
        args for callback function
    :param kwargs: **
        kwargs for callback function
    :return: str
        Name of function
    """

    return str(func.__name__) + "(" + str(args) + "," + str(kwargs) + ")"


def normalize(val, min_val, max_val, min_range=-1.0, max_range=1.0):
    """
    :param val: float
        Value to normalize
    :param min_val: float
        Min value of value
    :param max_val: float
        Msx value of value
    :param min_range: float
        Min value of range
    :param max_range: float
        Max value of value
    :return: float
        Normalized var in range
    """

    if val >= max_val:
        return max_range

    if val <= min_range:
        return min_range

    ratio = (val - min_val) / (max_val - min_val)
    return min_range + ratio * (max_range - min_range)


def is_nan(candidate):
    """
    :param candidate: float, str
        Candidate to check
    :return: bool
        True iff is considered NotANumber
    """

    return str(candidate) == "nan"


def remove_same_coordinates(x_data, y_val):
    """
    :param x_data: [] of *
        List of data on x-axis
    :param y_val: [] of float
        List of values
    :return: tuple ([] of *, [] of float)
        Original list minus the points with same x-coordinate
    """

    coordinates = {}
    for x_coord, y_coord in zip(x_data, y_val):
        if x_coord not in coordinates:  # not already in
            coordinates[x_coord] = [y_coord]
        else:  # there was another point
            coordinates[x_coord].append(y_coord)  # create bucket

    for x_coord, y_coord in coordinates.items():  # manage buckets
        coordinates[x_coord] = np.average(y_coord)  # average of bucket

    return list(coordinates.keys()), list(coordinates.values())


def num_to_str(num, form="short"):
    """
    :param num: float
        Number to convert to string
    :param form: str
        Format to use. Must be in ["short", "long"]
    :return: str
        Convert to str using the specified format
    """

    form = SHORT_DEC_FORMAT if form == "short" else LONG_DEC_FORMAT
    return form.format(num)


def get_relative_percentage(new, last):
    """
    :param new: float
        New value
    :param last: float
        Last value
    :return: float in [0, 100]
        Percentage increase (or decrease) since last value
    """

    if new is None or last is None:  # cannot produce result
        return 0.0

    new = float(new)
    last = float(last)
    if last == 0 and new != 0:
        return INFINITY

    ratio = (new / last - 1.0)
    return 100.0 * ratio


def get_relative_delta(new, last):
    """
    :param new: float
        New value
    :param last: float
        Last value
    :return: float
        Increase (or decrease) since last value
    """

    new = float(new)
    last = float(last)

    if new is None or last is None:  # cannot produce result
        return 0.0

    return new - last
