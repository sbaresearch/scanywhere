FROM python

WORKDIR /check-ip-connectivity/


ADD https://raw.githubusercontent.com/sbaresearch/scanywhere/main/utils/ip_utils.py .

ADD main.py .
RUN pip install requests

CMD ["python", "./main.py"] 
