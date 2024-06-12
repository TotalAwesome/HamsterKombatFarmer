FROM python:3.9 
# Or any preferred Python version.
COPY hamster_client.py /home/app/hamster_client.py
COPY requirements.txt /home/app/requirements.txt
COPY strings.py /home/app/strings.py
COPY bot.py /home/app/bot.py
COPY config.py /home/app/config.py
WORKDIR /home/app

RUN pip install -r requirements.txt
CMD python ./bot.py
