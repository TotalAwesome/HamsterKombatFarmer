"""
    FEATURES:
        1. buy_upgrades -> управление покупкой карточек. 
            True -> Включено, 
            False -> Выключено
        2. buy_decision_method -> метод покупки карточек (
            - price -> покупать самую дешевую
            - payback -> покупать ту, что быстрей всего окупится
            - profit -> покупать самую прибыльну
            - profitness -> покупать самую профитную (сколько добыча на каждый потраченный хома-рубль)
            )
        3. delay_between_attempts -> Задержка между заходами в секундах
    
    ACCOUNTS:
        name -> Название аккаунта. Так он будет виден в логе
        token -> токен аккаунта
        proxies -> настройки прокси, "кто знает - тот поймет". Если не нужен прокси, лучше убрать
        buy_upgrades -> Описано в FEATURES, можно указать для каждого аккаунта отдельно
        buy_decision_method -> Описано в FEATURES, можно указать для каждого аккаунта отдельно
"""

try:
    from config_local import FEATURES, ACCOUNTS
except:

    FEATURES = {
        "buy_upgrades": True,
        "buy_decision_method": "payback",
        "delay_between_attempts": 60 * 10,
    }


    ACCOUNTS = [
        {"name": "account1", "token": "1234567890MySeCReTt0KeN1", "proxies": {"http": "http://user:pass@10.10.10.0:8080", "https": "https://user:pass@10.10.10.0:9090"}},
        {"name": "account2", "token": "1234567890MySeCReTt0KeN2", "proxies": {"http": "http://user:pass@10.10.11.0:8080", "https": "https://user:pass@10.10.11.0:9090"}},
        {"name": "account3", "token": "1234567890MySeCReTt0KeN3", "buy_upgrades": True, "buy_decision_method": "payback",},
    ]

for account in ACCOUNTS:
    account['buy_upgrades'] = account.get('buy_upgrades', FEATURES.get('buy_upgrades', True))
    account['buy_decision_method'] = account.get('buy_decision_method', FEATURES.get('buy_decision_method', 'payback'))