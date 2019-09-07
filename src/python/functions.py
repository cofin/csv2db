#!/usr/bin/env python3
#
# Since: January, 2019
# Author: gvenzl
# Name: functions.py
# Description: Common functions for csv2db
#
# Copyright 2019 Gerald Venzl
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import datetime
import glob
import gzip
import os
import io
import zipfile
from enum import Enum
import csv

import config as cfg


class DBType(Enum):
    """Database type enumeration."""
    ORACLE = "oracle"
    MYSQL = "mysql"
    POSTGRES = "postgres"
    DB2 = "db2"


class ExitCodes(Enum):
    """Program return code enumeration."""
    SUCCESS = 0
    GENERIC_ERROR = 1
    DATABASE_ERROR = 3  # value 2 is reserved for wrong arguments passed via argparse


def open_file(file):
    """Opens a CSV file.

    The file can either be in plain text (.csv), zipped (.csv.zip), or gzipped (.csv.gz)

    Parameters
    ----------
    file : str
        The file to open

    Returns
    -------
    file-object
        A file object
    """
    if file.endswith(".zip"):
        zip_file = zipfile.ZipFile(file, mode="r")
        file = zip_file.open(zip_file.infolist()[0], mode="r")
        return io.TextIOWrapper(file)
    elif file.endswith(".gz"):
        return gzip.open(file, mode="rt")
    else:
        return open(file, mode='r')


def read_header(reader):
    """Reads header and returns the column list.

    This function reads the first row of the CSV file and parses it for the column names.

    Parameters
    ----------
    reader : _csv.reader
        The CSV Reader object to read the header from

    Returns
    -------
    set([])
        A set with all the column names.
    """
    return format_list(reader.__next__(), True)


def find_all_files(pattern):
    """Find all files of a given pattern.

    Parameters
    ----------
    pattern : str
        The pattern to search for

    Returns
    -------
    []
        List of files.
    """
    if os.path.isdir(pattern):
        # If path is directory find all CSV files, compressed or uncompressed
        pattern += "/*.csv*"
    return sorted(glob.glob(pattern))


def verbose(output):
    """Print verbose output.

    Parameters
    ----------
    output : str
        The output to print
    """
    if cfg.verbose:
        print(output)


def debug(output):
    """Print debug output.

    Parameters
    ----------
    output : Any
        The output to print"""
    if cfg.debug:
        if isinstance(output, list):
            output = ", ".join(output)
        elif isinstance(output, dict):
            output = ", ".join(str(key) + ": " + str(value) for key, value in output.items())
        print("DEBUG: {0}: {1}".format(datetime.datetime.now(), output))


def get_db_connection(db_type, user, password, host, port, db_name):
    """ Connects to the database.

    Parameters
    ----------
    db_type : str
        The database type
    user : str
        The database user
    password : str
        The database user password
    host : str
        The database host or ip address
    port : str
        The port to connect to
    db_name : str
        The database or service name

    Returns
    -------
    conn
        A database connection
    """

    try:
        if db_type == DBType.ORACLE.value:
            import cx_Oracle
            return cx_Oracle.connect(user,
                                     password,
                                     host + ":" + port + "/" + db_name)
        elif db_type == DBType.MYSQL.value:
            import mysql.connector
            return mysql.connector.connect(
                                       user=user,
                                       password=password,
                                       host=host,
                                       port=int(port),
                                       database=db_name)
        elif db_type == DBType.POSTGRES.value:
            import psycopg2
            return psycopg2.connect("""user='{0}' 
                                       password='{1}' 
                                       host='{2}' 
                                       port='{3}' 
                                       dbname='{4}'""".format(user, password, host, port, db_name)
                                    )
        elif db_type == DBType.DB2.value:
            import ibm_db
            import ibm_db_dbi
            conn = ibm_db.connect("UID={0};PWD={1};HOSTNAME={2};PORT={3};DATABASE={4};"
                                  .format(user, password, host, port, db_name), "", "")
            return ibm_db_dbi.Connection(conn)

        else:
            raise ValueError("Database type '{0}' is not supported.".format(db_type))
    except ModuleNotFoundError as err:
        raise ConnectionError("Database driver module is not installed: {0}. Please install it first.".format(str(err)))


def format_list(input_list, header=False):
    """Returns a formatted list of values from a CSV list input.

    Parameters
    ----------
    input_list : str
        The raw line to convert
    header : bool
        If true, values will be upper case and spaces replaced with '_'.
        This is only good for header rows in the CSV files.

    Returns
    -------
    [str,]
        A list of string values
    """

    # If empty string return None, i.e. skip empty lines
    if not input_list:
        return None

    output = []
    for col in input_list:
        val = col.replace('"', '').strip()
        # If line is a header line, i.e. column number, replace spaces with '_' and make names UPPER
        if header:
            val = val.replace(' ', '_',).upper()
        output.append(val)
    return output


def get_default_db_port(db_type):
    """Returns the default port for a database.

    Parameters
    ----------
    db_type : str
        The database type

    Returns
    -------
    str
        The default port
    """
    if db_type == DBType.ORACLE.value:
        return "1521"
    elif db_type == DBType.MYSQL.value:
        return "3306"
    elif db_type == DBType.POSTGRES.value:
        return "5432"
    elif db_type == DBType.DB2.value:
        return "50000"


def get_csv_reader(file):
    """Returns a csv reader.

    Parameters
    ----------
    file : file-object
        A file object
    """
    return csv.reader(file, delimiter=cfg.column_separator, quotechar=cfg.quote_char)
