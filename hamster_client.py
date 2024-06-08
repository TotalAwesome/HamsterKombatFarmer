import re
import logging

from base64 import b64decode
from requests import Session
from time import time, sleep
from strings import URL_BOOSTS_FOR_BUY, URL_BUY_BOOST, URL_BUY_UPGRADE, \
    URL_SYNC, URL_TAP, URL_UPGRADES_FOR_BUY, HEADERS, BOOST_ENERGY, URL_CHECK_TASK, \
    URL_CLAIM_DAILY_COMBO, MSG_BUY_UPGRADE, MSG_BAD_RESPONSE, MSG_SESSION_ERROR, \
    MSG_COMBO_EARNED, MSG_TAP, MSG_CLAIMED_COMBO_CARDS, MSG_SYNC, URL_CONFIG, \
        URL_CLAIM_DAILY_CIPHER, MSG_CIPHER, MSG_CRYPTED_CIPHER, MORSE_CODE_DICT
    

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s   %(message)s")


def timestamp():
    return int(time())


def sorted_by_profit(prepared):
    return sorted(prepared, key=lambda x: x["profitPerHourDelta"], reverse=True)


def sorted_by_profit_per_coin(prepared):
    return sorted(prepared, key=lambda x: x["profitness"], reverse=True)


def sorted_by_price(prepared):
    return sorted(prepared, key=lambda x: x["price"], reverse=False)


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


class HamsterClient(Session):

    name = None
    state = None
    boosts = None
    upgrades = None
    task_checked_at = None
    

    def __init__(self, token, name="NoName") -> None:
        super().__init__()
        headers = HEADERS.copy()
        headers["Authorization"] = f"Bearer {token}"
        self.headers = headers
        self.request = retry(super().request)
        self.name = name

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
        data = {
            "count": taps_count,
            "availableTaps": self.available_taps - taps_count,
            "timestamp": timestamp(),
        }
        self.post(URL_TAP, json=data).json()
        logging.info(self.log_prefix + MSG_TAP.format(taps_count=taps_count))

    def boost(self, boost_name=BOOST_ENERGY):
        data = {"boostId": boost_name, "timestamp": timestamp()}
        self.post(URL_BUY_BOOST, json=data)

    def upgrade(self, upgrade_name):
        data = {"upgradeId": upgrade_name, "timestamp": timestamp()}
        return self.post(URL_BUY_UPGRADE, json=data)

    def upgrdades_list(self):
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
    

    def get_sorted_upgrades(self):
        """
            1. Фильтруем карточки 
                - доступные для покупки
                - не просроченные
                - с пассивным доходом
                - без ожидания перезарядки
            2. Сортируем по профитности на каждую потраченную монету
        """

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
                item['profitness'] = item['profitPerHourDelta'] / item['price']
                prepared.append(item)
        if prepared:
            sorted_items = [i for i in sorted_by_profit_per_coin(prepared)[:50] if i['price'] <= self.balance]
            return sorted_items
        return []

    def buy_upgrades(self):
        """ Покупаем лучшие апгрейды на всю котлету """
        while True:
            self.upgrdades_list()
            if sorted_upgrades := self.get_sorted_upgrades():
                upgrade = sorted_upgrades[0]
                if upgrade['price'] <= self.balance:
                    result = self.upgrade(upgrade['id'])
                    if result.status_code == 200:
                        self.state = result.json()["clickerUser"]
                    logging.info(self.log_prefix + MSG_BUY_UPGRADE.format(**upgrade))
                    sleep(1)
                else:
                    break
            else:
                break

    def claim_combo_reward(self):
        """ Если вдруг насобирал комбо - нужно получить награду """
        combo = self.upgrades.get('dailyCombo', {})
        upgrades =  combo.get('upgradeIds', [])
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
