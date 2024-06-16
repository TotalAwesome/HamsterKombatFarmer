import re
import logging

from random import choice
from base64 import b64decode
from requests import Session, get as requests_get
from time import time, sleep
from strings import URL_BOOSTS_FOR_BUY, URL_BUY_BOOST, URL_BUY_UPGRADE, \
    URL_SYNC, URL_TAP, URL_UPGRADES_FOR_BUY, HEADERS, BOOST_ENERGY, URL_CHECK_TASK, \
    URL_CLAIM_DAILY_COMBO, MSG_BUY_UPGRADE, MSG_BAD_RESPONSE, MSG_SESSION_ERROR, \
    MSG_COMBO_EARNED, MSG_TAP, MSG_CLAIMED_COMBO_CARDS, MSG_SYNC, URL_CONFIG, \
    URL_CLAIM_DAILY_CIPHER, MSG_CIPHER, MSG_CRYPTED_CIPHER, MORSE_CODE_DICT, \
    URL_CHECK_IP, MSG_PROXY_CHECK_ERROR, MSG_PROXY_IP, MSG_PROXY_CONNECTION_ERROR


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s   %(message)s")


def timestamp():
    return int(time())


def sorted_by_profit(prepared):
    return sorted(prepared, key=lambda x: x["profitPerHourDelta"], reverse=True)


def sorted_by_profitness(prepared):
    return sorted(prepared, key=lambda x: x['profitPerHourDelta'] / x['price'], reverse=True)


def sorted_by_price(prepared):
    return sorted(prepared, key=lambda x: x["price"], reverse=False)


def sorted_by_payback(prepared):
    return sorted(prepared, key=lambda x: x['price'] / x['profitPerHourDelta'], reverse=False)


def retry(func):
    def wrapper(*args, **kwargs):
        while True:
            sleep_time = 10
            try:
                result = func(*args, **kwargs)
                if result.status_code in (200, 201, 202):
                    return result
                else:
                    logging.info(MSG_BAD_RESPONSE.format(status=result.status_code, text=result.text))
                    sleep(sleep_time)
                    sleep_time += 1
            except Exception as error:
                logging.error(MSG_SESSION_ERROR.format(error=error))
                sleep(1)

    return wrapper


def check_proxy(proxies):
    try:
        response = requests_get(URL_CHECK_IP, proxies=proxies)
        if response.status_code == 200:
            logging.info(MSG_PROXY_IP.format(ip=response.json()['origin']))
            return True
        else:
            logging.error(MSG_PROXY_CHECK_ERROR.format(status_code=response.status_code))
    except Exception as error:
        logging.error(MSG_PROXY_CONNECTION_ERROR.format(error=error))


class HamsterClient(Session):

    name = None
    state = None
    boosts = None
    upgrades = None
    task_checked_at = None

    def __init__(self, token, name="NoName", proxies=None, **kwargs) -> None:
        super().__init__()
        self.features = kwargs
        self.headers = HEADERS.copy()
        self.headers["Authorization"] = f"Bearer {token}"
        self.request = retry(super().request)
        self.name = name
        if proxies and check_proxy(proxies):
            self.proxies = proxies

    def get_cipher_data(self):
        result = self.post(URL_CONFIG).json()
        return result['dailyCipher']

    def claim_daily_cipher(self):
        """
        Разгадываем морзянку
        """
        cipher_data = self.get_cipher_data()
        if not cipher_data['isClaimed']:
            raw_cipher = cipher_data['cipher']
            logging.info(MSG_CRYPTED_CIPHER.format(cipher=raw_cipher))
            re_result = re.search('\d+', raw_cipher[3:])
            if re_result:
                str_len = re_result[0]
                raw_cipher = raw_cipher.replace(str_len, "", 1)
                raw_cipher = raw_cipher.encode()
                cipher = b64decode(raw_cipher).decode()
                morse_cipher = "  ".join((MORSE_CODE_DICT.get(char, " ") for char in cipher))
                logging.info(MSG_CIPHER.format(cipher=cipher + " | " + morse_cipher))
                self.post(URL_CLAIM_DAILY_CIPHER, json={"cipher": cipher})

    def sync(self):
        logging.info(self.log_prefix + MSG_SYNC)
        try:
            response = self.post(url=URL_SYNC)
            self.state = response.json()["clickerUser"]
        except Exception as e:
            pass

    def check_task(self):
        """ Получение ежедневной награды """
        data = {"taskId":"streak_days"}
        if not self.task_checked_at or time() - self.task_checked_at >= 60 * 60:
            self.post(URL_CHECK_TASK, json=data)
            self.task_checked_at = time()

    def tap(self):
        taps_count = self.available_taps or self.recover_per_sec
        data = {"count": taps_count,
                "availableTaps": self.available_taps - taps_count,
                "timestamp": timestamp()}
        self.post(URL_TAP, json=data).json()
        logging.info(self.log_prefix + MSG_TAP.format(taps_count=taps_count))

    def boost(self, boost_name=BOOST_ENERGY):
        data = {"boostId": boost_name, "timestamp": timestamp()}
        self.post(URL_BUY_BOOST, json=data)

    def upgrade(self, upgrade_name):
        data = {"upgradeId": upgrade_name, "timestamp": timestamp()}
        return self.post(URL_BUY_UPGRADE, json=data)

    def upgrades_list(self):
        self.upgrades = self.post(URL_UPGRADES_FOR_BUY).json()

    def boosts_list(self):
        self.boosts = self.post(URL_BOOSTS_FOR_BUY).json()

    @property
    def balance(self):
        if self.state:
            return self.state["balanceCoins"]

    @property
    def level(self):
        if self.state:
            return self.state["level"]

    @property
    def available_taps(self):
        if self.state:
            return self.state["availableTaps"]

    @property
    def recover_per_sec(self):
        if self.state:
            return self.state["tapsRecoverPerSec"]

    @property
    def is_taps_boost_available(self):
        self.boosts_list()
        if not self.boosts:
            return
        for boost in self.boosts["boostsForBuy"]:
            if (
                boost["id"] == BOOST_ENERGY
                and boost["cooldownSeconds"] == 0
                and boost["level"] <= boost["maxLevel"]
            ):
                return True

    def get_sorted_upgrades(self, method):
        """
            1. Фильтруем карточки
                - доступные для покупки
                - не просроченные
                - с пассивным доходом
                - без ожидания перезарядки
            2. Сортируем по профитности на каждую потраченную монету
        """
        methods = dict(payback=sorted_by_payback,
                       price=sorted_by_price,
                       profit=sorted_by_profit,
                       profitness=sorted_by_profitness)
        prepared = []
        for upgrade in self.upgrades.get("upgradesForBuy"):
            if (
                upgrade["isAvailable"]
                and not upgrade["isExpired"]
                and upgrade["profitPerHourDelta"] > 0
                and not upgrade.get("cooldownSeconds")
            ):
                item = upgrade.copy()
                if 'condition' in item :
                    item.pop('condition')
                prepared.append(item)
        if prepared:
            sorted_items = [i for i in methods[method](prepared)] # if i['price'] <= self.balance]
            return sorted_items
        return []

    def buy_upgrades(self):
        """ Покупаем лучшие апгрейды на всю котлету """
        if self.features['buy_upgrades']:
            counter = 0
            num_purchases_per_cycle = self.features['num_purchases_per_cycle']
            while True:
                self.upgrades_list()
                if sorted_upgrades := self.get_sorted_upgrades(self.features['buy_decision_method']):
                    upgrade = sorted_upgrades[0]
                    if upgrade['price'] <= self.balance \
                    and self.balance > self.features['min_cash_value_in_balance'] \
                    and num_purchases_per_cycle and counter < num_purchases_per_cycle:
                        result = self.upgrade(upgrade['id'])
                        if result.status_code == 200:
                            self.state = result.json()["clickerUser"]
                        logging.info(self.log_prefix + MSG_BUY_UPGRADE.format(**upgrade))
                        counter += 1
                        sleep(choice(range(1, 10)))
                    else:
                        break
                else:
                    break
        else:
            self.upgrades_list()

    def claim_combo_reward(self):
        """ Если вдруг насобирал комбо - нужно получить награду """
        combo = self.upgrades.get('dailyCombo', {})
        upgrades = combo.get('upgradeIds', [])
        combo_cards = " ".join(upgrades)
        logging.info(self.log_prefix + MSG_CLAIMED_COMBO_CARDS.format(cards=combo_cards))
        if combo and len(upgrades) == 3:
            if combo.get('isClaimed') is False:
                result = self.post(URL_CLAIM_DAILY_COMBO)
                if result.status_code == 200:
                    self.state = result.json()["clickerUser"]
                    logging.info(self.log_prefix + MSG_COMBO_EARNED.format(coins=combo['bonusCoins']))

    @property
    def stats(self):
        return {
            "уровень" : self.level,
            "энергия" : self.available_taps,
            'баланс' : self.balance,
            "доход в час" : self.state['earnPassivePerHour']
        }

    @property
    def log_prefix(self):
        return f"[{self.name}]\t "
