#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Christoph Rist"
__copyright__ = "Copyright 2017, risteon"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Christoph Rist"


import argparse
import os.path
import sys
import csv
import decimal  # < fixed point types and arithmetic
from typing import List
from datetime import datetime
import dateutil.parser

# todo      develop a smart method to parse currency strings without
# todo      the need for predefined currencies
KNOWN_CURRENCIES = {'EUR', 'BT', 'LTC', 'RP', 'GNO', 'XMR', 'ETC', 'ETH', 'XLM', 'DASH'}


class CurrencyPair:
    def __init__(self):
        self.counter = None
        self.base = None

    @classmethod
    def from_str(cls, s):
        cp = CurrencyPair()
        for c in KNOWN_CURRENCIES:
            p = s.find(c)
            if p != -1:
                s = s.replace(c, 'X'*len(c))
                first = (p, c)
                break
        else:
            raise RuntimeError("Could not parse currency pair '{}'".format(s))

        for c in KNOWN_CURRENCIES:
            p = s.find(c)
            if p != -1:
                s.replace(c, 'X'*len(c))
                second = (p, c)
                break
        else:
            raise RuntimeError("Could not parse currency pair '{}'".format(s))

        assert first[0] != second[0]
        if first[0] < second[0]:
            cp.counter = second[1]
            cp.base = first[1]
        else:
            cp.counter = first[1]
            cp.base = second[1]
        return cp


class Trade:
    def __init__(self):
        self.stamp = None
        self.currency_pair = None
        self.volume = 0.0

    @classmethod
    def from_dict(cls, values):
        t = Trade()
        t.stamp = dateutil.parser.parse(values['time'])
        t.currency_pair = CurrencyPair.from_str(values['pair'])
        t.volume = decimal.Decimal(values['vol'])
        t.price = decimal.Decimal(values['price'])
        t.buy = True if values['type'] == 'buy' else False
        return t


class Holding:
    def __init__(self):
        self._sum = decimal.Decimal()
        self._entries = []

    def add_value(self, value, counter_price, stamp):
        assert value >= 0
        self._entries.append((value, counter_price, stamp))
        self._entries.sort(key=lambda e: e[2])
        self._sum += value

    def withdraw(self, value, counter_price):
        assert value >= 0
        if value > self._sum:
            raise RuntimeError("Not enough funds available.")
        self._sum -= value
        r = []
        profit = decimal.Decimal()
        while True:
            if self._entries[0][0] < value:
                r.append(self._entries[0])
                value -= self._entries[0][0]
                profit += self._entries[0][0] * (counter_price - self._entries[0][1])
                self._entries.pop(0)
            elif self._entries[0][0] == value:
                r.append(self._entries[0])
                profit += value * (counter_price - self._entries[0][1])
                self._entries.pop(0)
                break
            else:
                r.append((value, self._entries[0][1], self._entries[0][2]))
                profit += value * (counter_price - self._entries[0][1])
                self._entries[0] = self._entries[0][0] - value, self._entries[0][1], self._entries[0][2]
                break

        return r, profit


def read_from_csv(filepath) -> List[Trade]:
    with open(filepath) as f:
        trades = []
        c_reader = csv.reader(f, delimiter=',')
        header = next(c_reader)
        for row in c_reader:
            values = dict(zip(header, row))
            trades.append(Trade.from_dict(values))
        return trades


def analyze(trades):
    trades.sort(key=lambda t: t.stamp)

    # currency -> current holdings
    holdings = dict()

    for trade in trades:
        if trade.currency_pair.counter != 'EUR':
            print('TODO: skipping pair {}/{}.'.format(trade.currency_pair.base, trade.currency_pair.counter))

        currency = trade.currency_pair.base
        if currency not in holdings:
            holdings[currency] = Holding()

        if trade.buy:
            holdings[currency].add_value(trade.volume, trade.price, trade.stamp)
        else:
            r, profit = holdings[currency].withdraw(trade.volume, trade.price)
            print("Sold currency {} with profit {} at {}".format(currency, profit, trade.stamp))
            for a in r:
                print("{} for {}, bought on {}".format(a[0], a[1], a[2]))


def is_valid_file(x):
    """
    'Type' for argparse - checks that file exists but does not open.
    """
    if not os.path.exists(x):
        raise argparse.ArgumentTypeError("{0} does not exist".format(x))
    return x


def main():
    # arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('file', metavar='csv file', type=is_valid_file,
                        help="Exported .csv file from kraken")

    args = parser.parse_args()

    try:
        decimal.getcontext().prec = 8
        trades = read_from_csv(args.file)
        analyze(trades)
    except KeyError:
        print("Invalid input file.", file=sys.stderr)


if __name__ == "__main__":
    main()
