
################################################################################
#   Solis local interface.
#
#   This component can retrieve data from the Solis dongle using version 5
#   of the protocol.
#
###############################################################################

import logging
import re
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import *
from .solis import Inverter
from .scanner import InverterScanner
from .services import *

_LOGGER = logging.getLogger(__name__)
_inverter_scanner = InverterScanner()


async def _do_setup_platform(hass: HomeAssistant, config, async_add_entities : AddEntitiesCallback):
    _LOGGER.debug(f'sensor.py:async_setup_platform: {config}')

    inverter_name = config.get(CONF_NAME)
    inverter_host = config.get(CONF_INVERTER_HOST)
    if inverter_host == "0.0.0.0":
        inverter_host = _inverter_scanner.get_ipaddress()


    inverter_port = config.get(CONF_INVERTER_PORT)
    inverter_sn = 123 # config.get(CONF_INVERTER_SERIAL)
    if inverter_sn == 0:
        inverter_sn = _inverter_scanner.get_serialno()

    lookup_file = config.get(CONF_LOOKUP_FILE)
    path = hass.config.path('custom_components/solis/inverter_definitions/')

    # Check input configuration.
    if inverter_host is None:
        raise vol.Invalid('configuration parameter [inverter_host] does not have a value')
    if inverter_sn is None:
        raise vol.Invalid('configuration parameter [inverter_serial] does not have a value')

    session = async_get_clientsession(hass)
    inverter = Inverter(path, inverter_sn, inverter_host, inverter_port, lookup_file, session)
    # Load the YAML configuration asynchronously without blocking the event loop
    await inverter.async_init()

    coordinator = SolisInverterCoordinator(hass, inverter)
    await coordinator.async_refresh()
    
    #  Prepare the sensor entities.
    hass_sensors = []
    for sensor in inverter.get_sensors():
        try:
            if "isstr" in sensor:
                hass_sensors.append(SolisSensorText(coordinator, inverter_name, inverter, sensor, inverter_sn))
            else:
                hass_sensors.append(SolisSensor(coordinator, inverter_name, inverter, sensor, inverter_sn))
        except BaseException as ex:
            _LOGGER.error(f'Config error {ex} {sensor}')
            raise
    hass_sensors.append(SolisStatus(coordinator, inverter_name, inverter, "status_lastUpdate", inverter_sn))
    hass_sensors.append(SolisStatus(coordinator, inverter_name, inverter, "status_connection", inverter_sn))

    _LOGGER.debug(f'sensor.py:_do_setup_platform: async_add_entities')
    _LOGGER.debug(hass_sensors)

    async_add_entities(hass_sensors)
    # Register the services with home assistant.
    register_services (hass, inverter)


class SolisInverterCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, inverter: Inverter) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=MIN_TIME_BETWEEN_UPDATES,
        )
        self.inverter = inverter

    async def _async_update_data(self):
        await self.inverter.async_update()
        return {
            "values": self.inverter.get_current_val() or {},
            "status_connection": self.inverter.status_connection,
            "status_lastUpdate": self.inverter.status_lastUpdate,
        }






# Set-up from configuration.yaml
async def async_setup_platform(hass: HomeAssistant, config, async_add_entities : AddEntitiesCallback, discovery_info=None):
    _LOGGER.debug(f'sensor.py:async_setup_platform: {config}')
    await _do_setup_platform(hass, config, async_add_entities)

# Set-up from the entries in config-flow
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    _LOGGER.debug(f'sensor.py:async_setup_entry: {entry.options}')
    await _do_setup_platform(hass, entry.options, async_add_entities)


#############################################################################################################
# This is the Device seen by Home Assistant.
#  It provides device_info to Home Assistant which allows grouping all the Entities under a single Device.
#############################################################################################################

class SolisSensor():
    """Solis Device class."""

    def __init__(self, id: str = None, device_name: str = None, model: str = None, manufacturer: str = None)  -> None:
        self.id = id
        self.device_name = device_name
        self.model = model
        self.manufacturer = manufacturer

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.id)},
            "name": self.device_name,
            "model": self.model,
            "manufacturer": self.manufacturer,
        }

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        return {
            "id": self.id,
            "integration": DOMAIN,
        }


#############################################################################################################
# This is the entity seen by Home Assistant.
#  It derives from the Entity class in HA and is suited for status values.
#############################################################################################################

class SolisStatus(SolisSensor, CoordinatorEntity):
    def __init__(self, coordinator, inverter_name, inverter, field_name, sn) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        super().__init__(sn, inverter_name, inverter.lookup_file)
        self._inverter_name = inverter_name
        self.inverter = inverter
        self._field_name = field_name
        self.p_state = None
        self.p_icon = 'mdi:magnify'
        self._sn = sn
        return

    @property
    def icon(self):
        #  Return the icon of the sensor.
        return self.p_icon

    @property
    def name(self):
        #  Return the name of the sensor.
        return "{} {}".format(self._inverter_name, self._field_name)

    @property
    def unique_id(self):
        # Return a unique_id based on the serial number
        return "{}_{}_{}".format(self._inverter_name, self._sn, self._field_name)

    @property
    def should_poll(self):
        return False

    @property
    def state(self):
        if self.coordinator.data is None:
            return self.p_state

        if self._field_name in ("status_lastUpdate", "status_connection"):
            return self.coordinator.data.get(self._field_name)

        return self.coordinator.data.get("values", {}).get(self._field_name)


#############################################################################################################
#  Entity displaying a text field read from the inverter
#   Overrides the Status entity, supply the configured icon, and updates the inverter parameters
#############################################################################################################

class SolisSensorText(SolisStatus):
    def __init__(self, coordinator, inverter_name, inverter, sensor, sn) -> None:
        SolisStatus.__init__(self, coordinator, inverter_name, inverter, sensor['name'], sn)
        if 'icon' in sensor:
            self.p_icon = sensor['icon']
        else:
            self.p_icon = ''
        return


#############################################################################################################
#  Entity displaying a numeric field read from the inverter
#   Overrides the Text sensor and supply the device class, last_reset and unit of measurement
#############################################################################################################

class SolisSensor(SolisSensorText):
    def __init__(self, coordinator, inverter_name, inverter, sensor, sn) -> None:
        SolisSensorText.__init__(self, coordinator, inverter_name, inverter, sensor, sn)
        self._device_class = sensor['class']
        if 'state_class' in sensor:
            self._state_class = sensor['state_class']
        else:
            self._state_class = None
        self.uom = sensor['uom']
        return

    @property
    def device_class(self):
        return self._device_class


    @property
    def extra_state_attributes(self):
        if self._state_class:
            return  {
                'state_class': self._state_class
            }
        else:
            return None

    @property
    def unit_of_measurement(self):
        return self.uom

