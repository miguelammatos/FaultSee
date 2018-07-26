FROM python:3

ENTRYPOINT ["python", "-m", "lsdsuite"]

ENV PYTHONPATH=/usr/src/lsdsuite
WORKDIR ${PYTHONPATH}

COPY requirements.txt .
RUN pip install -q --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /opt/lsdsuite
