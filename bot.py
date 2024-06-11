from random import choice
from hamster_client import BOOST_ENERGY, HamsterClient, sleep, logging
from config import TOKENS, FEATURES
from strings import DELIMITER
   
clients = [HamsterClient(**options) for options in TOKENS]

def main():
    while True:
        for client in clients:
            print(DELIMITER)
            client.sync()
            client.claim_daily_cipher()
            client.tap()
            if FEATURES.get('buy_upgrades', True):
                client.buy_upgrades(FEATURES.get('buy_decision_method', 'payback'))
            else:
                client.upgrades_list()
            client.check_task()
            client.claim_combo_reward()
            if client.is_taps_boost_available:
                client.boost(BOOST_ENERGY)
            logging.info(client.log_prefix + " ".join(f"{k}: {v} |" for k, v in client.stats.items()))
            print(DELIMITER)
            sleep(choice(range(1, 10)))
        sleep(FEATURES.get('delay_between_attempts', 60 * 10))

if __name__ == "__main__":
    main()