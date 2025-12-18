from datetime import timedelta

DOMAIN = 'solis'

DEFAULT_PORT_INVERTER = 8000
DEFAULT_LOOKUP_FILE = 'solis_hybrid.yaml'
LOOKUP_FILES = [
    'solis_hybrid.yaml',
    'custom_parameters.yaml'
]

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=10)

CONF_INVERTER_HOST = 'inverter_host'
CONF_INVERTER_PORT = 'inverter_port'
CONF_LOOKUP_FILE = 'lookup_file'

SENSOR_PREFIX = 'Solis'
