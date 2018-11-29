# cyborg-regidores
The Regidor promotes social participation and reforms community regulations

## Usage

Please provide a CA cert file at `conf/ca.pem`. Then start the dump: 

```shell
DEBUG=1 \
KAFKA_BOOTSTRAP_SERVERS=three-kafka-bootstrap-dh-prod-message-bus.cloud.datahub.upshift.redhat.com:443 \
./dump.py`
```