from random import choice
from hamster_client import BOOST_ENERGY, HamsterClient, sleep, logging
from config import ACCOUNTS, FEATURES
from strings import DELIMITER, CYCLE_BANNER

clients = [HamsterClient(**options) for options in ACCOUNTS]

def main():
	cycle_count = 0
	print(DELIMITER)
	while True:
		cycle_count += 1
		print(CYCLE_BANNER.format(cycle_count = cycle_count))
		for client in clients:
			print(DELIMITER)
			if cycle_count == 1: 
				sleep(choice(range(10, 20)))
			else: 
				sleep(choice(range(60, 120)))
			client.sync()
			client.claim_daily_cipher()
			client.tap()
			client.buy_upgrades()
			client.check_task()
			client.make_tasks()
			client.claim_combo_reward()
			if client.is_taps_boost_available:
				client.boost(BOOST_ENERGY)
				client.sync()
				sleep(choice(range(110, 130)))
				client.tap()
			logging.info(client.log_prefix + " ".join(f"{k}: {v} |" for k, v in client.stats.items()))
		print(DELIMITER)
		delay_between_attempts_random_magnifier = FEATURES.get('delay_between_attempts_random_magnifier', 10)
		delay_between_attempts = FEATURES.get('delay_between_attempts', 60) * choice(range(1, delay_between_attempts_random_magnifier))
		sleep(choice(range(delay_between_attempts, delay_between_attempts + 120)))


if __name__ == "__main__":
    main()