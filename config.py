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
    
    TOKENS:
        name -> Название аккаунта. Так он будет виден в логе
        token -> токен аккаунта
        proxies -> настройки прокси, "кто знает - тот поймет". Если не нужен прокси, лучше убрать
"""

try:
    from config_local import FEATURES, TOKENS
except:

    FEATURES = {
        "buy_upgrades": True,
        "buy_decision_method": "payback",
        "delay_between_attempts": 60 * 10,
    }


    TOKENS = [
        {"name": "account1", "token": "1234567890MySeCReTt0KeN1", "proxies": {"http": "http://user:pass@10.10.10.0:8080", "https": "https://user:pass@10.10.10.0:9090"}},
        {"name": "account2", "token": "1234567890MySeCReTt0KeN2", "proxies": {"http": "http://user:pass@10.10.11.0:8080", "https": "https://user:pass@10.10.11.0:9090"}},
        {"name": "account3", "token": "1234567890MySeCReTt0KeN3", },
    ]
