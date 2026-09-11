FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends python3 git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --home-dir /home/user --uid 10001 fixture
COPY allset.tar.gz /opt/allset.tar.gz
RUN mkdir /opt/allset && tar -xzf /opt/allset.tar.gz -C /opt/allset && rm /opt/allset.tar.gz
COPY smoke.py transport.py /opt/checks/
ENV PATH=/home/user/test-tools:/opt/allset:/usr/local/bin:/usr/bin:/bin
USER fixture
WORKDIR /home/user
ENTRYPOINT ["python3", "/opt/checks/smoke.py"]
