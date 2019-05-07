#!/usr/bin/python3
#
# Copyright (c) Microsoft Corporation. All rights reserved.
#
# See LICENSE for license information.

import argparse
import collections
import datetime
import re
import sys


cloud_init_pattern = re.compile(r'(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d,\d\d\d) ')
iso8601_pattern = re.compile(r'(\d\d\d\d/\d\d/\d\d \d\d:\d\d:\d\d\.\d+) ')
timestamp_pattern = re.compile(r'((\d+)(\.\d+)?) ')


def make_argument_parser():
    """
    Build command line argument parser.
    :return: Parser for command line
    :rtype argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Merge multiple log files, from different sources, preserving order")
    parser.add_argument("-p", "--prefix", help="List of prefixes to be applied to log entries", nargs="+")
    parser.add_argument("--no-prefix", help="Suppress automatic generation of prefixes", action="store_true")
    parser.add_argument("-r", "--regex", help="Regex to match and capture the entire timestamp")
    parser.add_argument("-f", "--format", help="strptime format to convert the captured timestamp")
    # parser.add_argument("--colors", help="List of colors for each log", required=False, nargs="+")
    parser.add_argument("-c", "--colorize", help="Color-code log output", required=False, action="store_true")
    parser.add_argument('logfiles', nargs='+')

    return parser


def parse_datetime(line):
    """
    Parse the date and time from the beginning of a log line. If no timestamp can be recognized, return None.
    :param line: The log line to be parsed
    :return: Either a datetime or None
    """
    if custom_pattern:
        match = custom_pattern.match(line)
        if match:
            entry_datetime = datetime.datetime.strptime(match.group(1), custom_format)
            return entry_datetime

    match = iso8601_pattern.match(line)
    if match:
        entry_datetime = datetime.datetime.strptime(match.group(1), '%Y/%m/%d %H:%M:%S.%f')
        return entry_datetime

    match = cloud_init_pattern.match(line)
    if match:
        entry_datetime = datetime.datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f')
        return entry_datetime

    match = timestamp_pattern.match(line)
    if match:
        entry_datetime = datetime.datetime.utcfromtimestamp(float(match.group(1)))
        return entry_datetime

    return None


class Logfile:
    def _advance(self):
        """
        Read and accumulate saved line plus continuation lines (if any). When a line beginning with a timestamp is
        found, save that (new initial) line and the timestamp, then return the flattened accumulated array of strings.

        Invariant: All lines of the current entry have been read. The instance knows the timestamp of the *next*
        log entry, and has already read the first line of that entry, *or* EOF has been reached and the appropriate
        internal marker has been set. The instance is prepared for either timestamp() or entry() to be called.
        :rtype str[]
        """
        results = [self._line]
        while True:
            line = self._f.readline()
            if line == '':
                self._eof = True
                return results
            timestamp = parse_datetime(line)
            if timestamp is not None:
                self._line = line
                self._timestamp = timestamp
                return results
            results.append(line)

    def __init__(self, path):
        self._f = open(path, "r")
        self._eof = False
        self._timestamp = datetime.datetime.max
        self._line = ''
        self._advance()     # Ignoring any untimestamped lines at the beginning of the log

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def timestamp(self):
        if self._eof:
            raise EOFError
        return self._timestamp

    def entry(self):
        if self._eof:
            raise EOFError
        return self._advance()

    def close(self):
        self._f.close()
        self._f = None
        self._line = ''
        self._eof = True


class LogSet:
    def __init__(self, pathnames):
        self._logs = {}
        for pathname in pathnames:
            self._logs[pathname] = Logfile(pathname)

    def next_entry(self):
        """
        Find the earliest entry in the set of logs, advancing that one logfile to the next entry.
        :return: Pathname of the logfile, the entry as an array of one or more lines.
        :rtype str, str[]
        """
        if len(self._logs) == 0:
            raise EOFError
        low_path = ''
        low_timestamp = datetime.datetime.max
        to_delete = []
        for log_name, log in self._logs.items():
            try:
                timestamp = log.timestamp()
            except EOFError:
                to_delete.append(log_name)
                continue
            if timestamp <= low_timestamp:
                low_path = log_name
                low_timestamp = timestamp
        for log_name in to_delete:
            self._logs[log_name].close()
            del self._logs[log_name]
        if len(self._logs) == 0:
            # Last log hit EOF and was deleted
            raise EOFError
        return low_path, self._logs[low_path].entry()


def render(line, prefix_arg=None, color=-1):
    """
    Turn a line of text into a ready-to-display string.
    If prefix_arg is set, prepend it to the line.
    If color is set, change to that color at the beginning of the rendered line and change out before the newline (if
    there is a newline).
    :param str line: Output line to be rendered
    :param str prefix_arg: Optional prefix to be stuck at the beginning of the rendered line
    :param int color: If 0-255, insert escape codes to display the line in that color
    """
    pretext = '' if prefix_arg is None else prefix_arg
    if -1 < color < 256:
        pretext = "\x1b[38;5;{}m{}".format(str(color), pretext)
        if line[-1] == "\n":
            line = "{}\x1b[0m\n".format(line[:-1])
        else:
            line = "{}\x1b[0m".format(line)
    return "{}{}".format(pretext, line)


def main():
    args = make_argument_parser().parse_args()
    if args.logfiles is None or len(args.logfiles) < 2:
        print("Requires at least two logfiles")
        exit(1)
    elif bool(args.format) != bool(args.regex):
        print("Requires both timestamp regex and format or none")
        exit(1)

    global custom_pattern, custom_format
    if args.regex:
        custom_pattern = re.compile(args.regex.encode().decode('unicode_escape'))
        custom_format = args.format
    else:
        custom_pattern, custom_format = None, None

    prefixes = collections.defaultdict(lambda: '')
    colorize = args.colorize if sys.stdout.isatty() else False
    colors = collections.defaultdict(lambda: 15 if colorize else -1)
    index = 1
    limit = len(args.prefix) if args.prefix else 0
    no_prefix = args.no_prefix or (colorize and limit == 0)

    for path in args.logfiles:
        if not no_prefix:
            prefixes[path] = "{} ".format(args.prefix[index-1]) if index <= limit else "log{} ".format(index)
        if colorize:
            colors[path] = index
        index += 1

    merger = LogSet(args.logfiles)
    while True:
        try:
            path, entry = merger.next_entry()
        except EOFError:
            exit(0)
        for line in entry:
            print(render(line, prefixes[path], colors[path]), end='')


main()

# :vi ai sw=4 expandtab ts=4 :
