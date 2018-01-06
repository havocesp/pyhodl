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


""" Analyze transactions in exchanges """

from datetime import datetime

import numpy as np
from hal.streams.pretty_table import pretty_format_table

from pyhodl.config import DATE_TIME_KEY, VALUE_KEY, NAN
from pyhodl.core.models.wallets import Wallet
from pyhodl.data.balance import parse_balance, save_balance
from pyhodl.data.coins import DEFAULT_FIAT
from pyhodl.utils.misc import is_nan, num_to_str, get_relative_delta, \
    get_relative_percentage, get_ratio, print_balance, get_percentage


class CryptoExchange:
    """ Exchange dealing with crypto-coins """

    def __init__(self, transactions, exchange_name):
        """
        :param transactions: [] of Transaction
            List of transactions
        """

        self.transactions = transactions
        if not self.transactions:
            raise ValueError("Creating exchange with no past transaction!")
        self.exchange_name = str(exchange_name)

    def get_transactions_count(self):
        """
        :return: int
            Number of transactions
        """

        return len(self.transactions)

    def get_first_transaction(self):
        """
        :return: Transaction
            First transaction done (with respect to time)
        """

        first = self.transactions[0]
        for transaction in self.transactions:
            if transaction.date < first.date:
                first = transaction
        return first

    def get_last_transaction(self):
        """
        :return: Transaction
            Last transaction done (with respect to time)
        """

        last = self.transactions[0]
        for transaction in self.transactions:
            if transaction.date > last.date:
                last = transaction
        return last

    def get_transactions(self, rule):
        """
        :param rule: func
            Evaluate this function on each transaction as a filter
        :return: generator of [] of Transaction
            List of transactions done between the dates
        """

        for transaction in self.transactions:
            if rule(transaction):
                yield transaction

    def build_wallets(self):
        """
        :return: {} of str -> Wallet
            Build a wallet for each currency traded and put trading history
            there
        """

        wallets = {}  # get only successful transactions
        transactions = self.get_transactions(lambda x: x.successful)
        for transaction in transactions:
            for coin in transaction.get_coins():
                if coin not in wallets:
                    wallets[coin] = Wallet(coin)

                wallets[coin].add_transaction(transaction)

        return wallets


class Portfolio:
    """ Contains wallets, of also different coins """

    def __init__(self, wallets, portfolio_name=None):
        self.wallets = wallets
        self.portfolio_name = str(portfolio_name) if portfolio_name else None

    def get_transactions_dates(self):
        """
        :return: [] of datetime
            List of all dates of all transactions of all wallets
        """

        dates = []
        for wallet in self.wallets:
            dates += wallet.dates()
        return sorted(dates)

    def get_current_balance(self, currency=DEFAULT_FIAT):
        """
        :return: [] of {}
            List of current balance by wallet
        """

        balances = [
            {
                "symbol": wallet.base_currency,
                "balance": wallet.balance(),
                VALUE_KEY: wallet.balance(currency, True)
            }
            for wallet in self.wallets
        ]
        tot_balance = self.sum_total_balance(balances)

        for i, balance in enumerate(balances):  # add price and %
            balances[i]["price"] = get_ratio(
                balance[VALUE_KEY],
                balance["balance"]
            )
            balances[i]["percentage"] = get_percentage(
                balance[VALUE_KEY],
                tot_balance
            )

        balances = sorted([
            balance for balance in balances if float(balance["balance"]) > 0.0
        ], key=lambda x: x[VALUE_KEY], reverse=True)

        return balances

    @staticmethod
    def get_balances_from_deltas(deltas):
        """
        :param deltas: [] of {}
            List of delta by transaction date
        :return: [] of {}
            List of subtotal balances by transaction date
        """

        if not deltas:
            return []

        deltas = sorted([
            delta for delta in deltas if delta[VALUE_KEY] != NAN
        ], key=lambda x: x[DATE_TIME_KEY])
        balances = [deltas[0]]
        for delta in deltas[1:]:
            balances.append({
                DATE_TIME_KEY: delta[DATE_TIME_KEY],
                VALUE_KEY: balances[-1][VALUE_KEY] + delta[VALUE_KEY]
            })
        return balances

    @staticmethod
    def sum_total_balance(balances):
        """
        :param balances: [] of {}
            List of raw balances
        :return: float
            Total balance (without counting NaN values)
        """

        if isinstance(balances, dict):
            return Portfolio.sum_total_balance(balances.values())

        return sum([
            balance[VALUE_KEY] for balance in balances
            if isinstance(balance, dict) and not is_nan(balance[VALUE_KEY])
        ])

    def get_crypto_fiat_balance(self, currency):
        """
        :return: tuple ([] of datetime, [] of float, [] of float)
            List of dates, balances of crypto coins and fiat balances
        """

        dates = self.get_transactions_dates()
        crypto_values = np.zeros(len(dates))  # zeros
        fiat_values = np.zeros(len(dates))

        for wallet in self.wallets:
            balances = wallet.get_balance_array_by_date(dates, currency)
            if wallet.is_crypto():
                crypto_values += balances
            else:
                fiat_values += balances
        return dates, crypto_values.tolist(), fiat_values.tolist()

    def show_balance(self, last=None, save_to=None):
        """
        :param save_to: str
            Path to file where to save balance data
        :param last: str
            Path to file where to read balance data
        :return: float
            Total balance
        """

        last = parse_balance(last) if last else None
        balances = self.get_current_balance()
        pretty_table = self._pretty_balances(balances, last)
        now = datetime.now()

        print(pretty_table)
        total_value = self.sum_total_balance(balances)
        last_time = last[DATE_TIME_KEY] if last else None
        if last:
            last_total_balance = sum([
                float(coin[VALUE_KEY])
                for symbol, coin in last.items() if symbol != DATE_TIME_KEY
            ])
            delta = get_relative_delta(total_value, last_total_balance)
            percentage = get_relative_percentage(
                total_value,
                last_total_balance
            )
            print_balance(total_value, delta, percentage, last_time)

        if save_to:
            save_balance(balances, save_to, timestamp=now)

        last_total = self.sum_total_balance(last) if last else None
        return total_value, last_total, last_time

    @staticmethod
    def _pretty_balances(balances, last):
        """
        :param balances: [] of {}
            List of balances of each coin
        :param last: {}
            Dict with last balance data
        :return: str
            Pretty table with balance data
        """

        table = [
            Portfolio._pretty_balance(balance, last) for balance in balances
        ]
        return pretty_format_table(
            [
                "symbol", "balance", "$ value", "$ price per coin", "%",
                "$ delta", "% delta"
            ], table
        )

    @staticmethod
    def _pretty_balance(balance, last):
        current_val = balance[VALUE_KEY]
        last_val = last[balance["symbol"]][VALUE_KEY] \
            if last and balance["symbol"] in last else None

        return [
            str(balance["symbol"]),
            num_to_str(balance["balance"]),
            num_to_str(balance[VALUE_KEY]) + " $",
            num_to_str(balance["price"]) + " $",
            num_to_str(balance["percentage"]) + " %",
            num_to_str(get_relative_delta(current_val, last_val)) + " $",
            num_to_str(get_relative_percentage(current_val, last_val)) + " %"
        ]