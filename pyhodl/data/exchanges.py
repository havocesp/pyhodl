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


""" Parse raw exchanges data """

import ciso8601
from datetime import datetime

from pyhodl.data.core import CryptoParser
from pyhodl.models.transactions import Commission


class BinanceParser(CryptoParser):
    """ Parses Binance transactions data """

    def get_coins_amounts(self, raw):
        if self.is_trade(raw):
            market = raw["symbol"]
            if market.endswith("USDT"):
                coin_buy, coin_sell = market.replace("USDT", ""), "USDT"

            coin_buy, coin_sell = market[:-3], market[-3:]

            amount_buy = float(raw["qty"])
            amount_sell = float(raw["price"]) * amount_buy

            if raw["isBuyer"]:
                return coin_buy, amount_buy, coin_sell, amount_sell

            return coin_sell, amount_sell, coin_buy, amount_buy
        elif self.is_deposit(raw):
            return raw["asset"], float(raw["amount"]), None, 0
        elif self.is_withdrawal(raw):
            return None, 0, raw["asset"], float(raw["amount"])

        return None, 0, None, 0

    def get_commission(self, raw):
        if "commissionAsset" in raw:
            return Commission(
                raw,
                raw["commissionAsset"],
                float(raw["commission"]),
                self.get_date(raw),
                self.is_successful(raw)
            )

    def get_date(self, raw):
        if self.is_trade(raw):
            return datetime.fromtimestamp(
                int(raw["time"]) / 1000  # ms -> s
            )
        elif self.is_deposit(raw):
            return datetime.fromtimestamp(
                int(raw["insertTime"]) / 1000  # ms -> s
            )
        elif self.is_withdrawal(raw):
            return datetime.fromtimestamp(
                int(raw["successTime"]) / 1000  # ms -> s
            )

    def is_successful(self, raw):
        if self.is_trade(raw):
            return "commission" in raw
        elif self.is_deposit(raw):
            return int(raw["status"]) == 1
        elif self.is_withdrawal(raw):
            return int(raw["status"]) == 6

        return False

    def is_trade(self, raw):
        return "isBuyer" in raw

    def is_deposit(self, raw):
        return "insertTime" in raw

    def is_withdrawal(self, raw):
        return "applyTime" in raw

    def build_exchange(self, exchange_name="binance"):
        return super(BinanceParser, self).build_exchange(exchange_name)


class BitfinexParser(CryptoParser):
    """ Parses Binance transactions data """

    def get_coins_amounts(self, raw):
        if self.is_trade(raw):
            coin_buy, coin_sell = raw["symbol"][:3], raw["symbol"][3:]
            buy_amount = float(raw["amount"])
            sell_amount = buy_amount * float(raw["price"])
            if raw["type"] == "Buy":
                return coin_buy, buy_amount, coin_sell, sell_amount

            return coin_sell, sell_amount, coin_buy, buy_amount
        elif self.is_deposit(raw):
            return raw["currency"], float(raw["amount"]), None, 0
        elif self.is_withdrawal(raw):
            return None, 0, raw["currency"], float(raw["amount"])

        return None, 0, None, 0

    def is_trade(self, raw):
        return raw["type"] in ["Sell", "Buy"]

    def is_withdrawal(self, raw):
        return raw["type"] == "WITHDRAWAL"

    def get_fee(self, raw):
        """
        :param raw: {}
            Raw trade
        :return: tuple (str, float)
            Coin fee and amount
        """

        if self.is_trade(raw):
            return raw["fee_currency"], abs(float(raw["fee_amount"]))
        elif self.is_deposit(raw) or self.is_trade(raw):
            return raw["currency"], abs(float(raw["fee"]))

    def get_commission(self, raw):
        fee_coin, amount = self.get_fee(raw)
        if fee_coin:
            return Commission(
                raw, fee_coin, amount, self.get_date(raw),
                self.is_successful(raw)
            )

    def get_date(self, raw):
        return datetime.fromtimestamp(int(float(raw["timestamp"])))

    def is_deposit(self, raw):
        return raw["type"] == "DEPOSIT"

    def is_successful(self, raw):
        if self.is_trade(raw):
            return float(raw["fee_amount"]) <= 0
        elif self.is_deposit(raw) or self.is_withdrawal(raw):
            return raw["status"] == "COMPLETED"

        return False

    def build_exchange(self, exchange_name="bitfinex"):
        return super().build_exchange(exchange_name)


class CoinbaseParser(CryptoParser):
    """ Parses Coinbase transactions data """

    def get_coins_amounts(self, raw):
        if self.is_trade(raw):
            coin, currency = \
                raw["amount"]["currency"], raw["native_amount"]["currency"]
            if coin != currency:  # otherwise just a fiat log to discard
                coin_buy, amount_buy = \
                    currency, abs(float(raw["native_amount"]["amount"]))
                coin_sell, amount_sell = \
                    coin, abs(float(raw["amount"]["amount"]))

                if raw["type"] == "sell":
                    return coin_buy, amount_buy, coin_sell, amount_sell

                return coin_sell, amount_sell, coin_buy, amount_buy

            return None, 0, None, 0
        elif self.is_deposit(raw):
            return raw["amount"]["currency"], \
                   abs(float(raw["amount"]["amount"])), None, 0
        elif self.is_withdrawal(raw):
            return None, 0, \
                   raw["amount"]["currency"], \
                   abs(float(raw["amount"]["amount"]))

        return None, 0, None, 0

    def is_trade(self, raw):
        return raw["type"] in ["buy", "sell"]

    def is_withdrawal(self, raw):
        amount = float(raw["amount"]["amount"])
        native_amount = float(raw["native_amount"]["amount"])
        return amount < 0 and native_amount < 0

    def get_commission(self, raw):
        try:
            commission_data = raw["network"]
            return Commission(
                commission_data,
                commission_data["transaction_fee"]["currency"],
                commission_data["transaction_fee"]["amount"],
                self.get_date(raw),
                commission_data["status"] == "confirmed"
            )
        except:
            return None

    def get_date(self, raw):
        return ciso8601.parse_datetime(raw["updated_at"])

    def is_deposit(self, raw):
        amount = float(raw["amount"]["amount"])
        native_amount = float(raw["native_amount"]["amount"])
        return amount >= 0 and native_amount >= 0

    def is_successful(self, raw):
        return raw["status"] == "completed"

    def get_transactions_list(self):
        raw = self.get_raw_data()
        for account, transactions in raw.items():
            for transaction in transactions:
                try:
                    yield self.parse_transaction(transaction)
                except:
                    print("Cannot parse transaction", transaction,
                          "of account", account)

    def build_exchange(self, exchange_name="coinbase"):
        return super().build_exchange(exchange_name)


class GdaxParser(CoinbaseParser):
    """ Parses Binance transactions data """

    def get_coins_amounts(self, raw):
        amount = float(raw["amount"])
        coin = raw["currency"]

        if amount >= 0:  # buy
            return coin, abs(amount), None, 0

        return None, 0, coin, abs(amount)

    def is_trade(self, raw):
        return "product_id" in raw["details"]

    @staticmethod
    def get_transfer_type(raw):
        """
        :param raw: {}
            Raw trade
        :return: str
            Transfer type
        """

        if raw["type"] == "transfer":
            return raw["details"]["transfer_type"]

    def is_withdrawal(self, raw):
        return self.get_transfer_type(raw) == "withdraw"

    def get_commission(self, raw):
        return None  # by default no way to check if transaction has fee or not

    def get_date(self, raw):
        return ciso8601.parse_datetime(raw["created_at"])

    def is_deposit(self, raw):
        return self.get_transfer_type(raw) == "deposit"

    def is_successful(self, raw):
        return True  # always

    def build_exchange(self, exchange_name="gdax"):
        return super().build_exchange(exchange_name)
