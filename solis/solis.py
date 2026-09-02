import socket
import yaml
import logging
import struct
from homeassistant.util import Throttle
from datetime import datetime
from .parser import ParameterParser
from .const import *
from custom_components.solis_direct import PySolis_direct
from asyncio import get_event_loop, sleep as asyncio_sleep


QUERY_RETRY_ATTEMPTS = 4


class Inverter:
    def __init__(self, path, serial, host, port, lookup_file, session) -> None:
        self.solisClient = None
        self._serial = serial
        self.path = path
        self._host = host
        self._port = port
        self.session = session
        self._current_val = None
        self.status_connection = "Disconnected"
        self.status_lastUpdate = "N/A"
        self.lookup_file = lookup_file
        self._LOGGER = logging.getLogger(__name__)
        if not self.lookup_file or lookup_file == "parameters.yaml":
            self.lookup_file = "deye_hybrid.yaml"
        self.parameter_definition = None

    async def async_init(self):
        """Async initialization to load YAML file without blocking the event loop."""
        def _load_yaml():
            with open(self.path + self.lookup_file) as f:
                return yaml.full_load(f)
        
        loop = get_event_loop()
        self.parameter_definition = await loop.run_in_executor(None, _load_yaml)

    def connect_to_server(self):
        if self.solisClient:
            return self.solisClient
        self._LOGGER.info(f"Connecting to Solis data logger {self._host}:{self._port}")
        self.solisClient = PySolis_direct(
            self._host, port=self._port, session=self.session
        )  # , logger=log, auto_reconnect=True, socket_timeout=15)

    async def disconnect_from_server(self):
        if self.solisClient:
            try:
                self._LOGGER.info(
                    f"Disconnecting from Solis data logger {self._host}:{self._port}"
                )
                await self.solisClient.disconnect()
            except (ConnectionError, OSError) as e:
                self._LOGGER.debug(
                    f"Ignoring disconnect error for {self._host}:{self._port} [{type(e).__name__}: {e}]"
                )
            finally:
                self.solisClient = None

    async def send_request(self, params, start, end, mb_fc, msg_id):
        length = end - start + 1
        msg = [
            mb_fc,
            (start >> 8) & 0xFF,
            start & 0xFF,
            (length >> 8) & 0xFF,
            length & 0xFF,
        ]

        try:
            response = await self.solisClient.request(msg, msg_id)
            if response is not None:
                params.parse(response, start - 1, length, msg_id)
        except Exception as e:
            self._LOGGER.warning(
                f"Request failed for register range [{start} - {end}] with exception [{type(e).__name__}: {e}]"
            )
            raise

    async def write_holding_register(self, address, value, mb_fc, msg_id):
        msg = [
            mb_fc,
            (address >> 8) & 0xFF,
            (address & 0xFF),
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]

        response = await self.solisClient.request(msg, msg_id)
        return response

    async def write_multiple_holding_registers(self, params, start, mb_fc, msg_id):
        length = len(params)
        msg = [
            mb_fc,
            (start >> 8) & 0xFF,
            start & 0xFF,
            (length >> 8) & 0xFF,
            length & 0xFF,
            (length * 2) & 0xFF,
        ]

        for param in params:
            msg.append((param >> 8) & 0xFF)
            msg.append(param & 0xFF)

        response = await self.solisClient.request(msg, msg_id)
        # For write operations, just return the response without parsing
        # Parsing is only needed for ParameterParser objects used in read operations
        return response

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        await self.get_statistics()
        return

    async def get_statistics(self):
        result = 1
        params = ParameterParser(self.parameter_definition)
        requests = self.parameter_definition["requests"]
        self._LOGGER.debug(f"Starting to query for [{len(requests)}] ranges...")

        try:
            for request in requests:
                start = request["start"]
                end = request["end"]
                mb_fc = request["mb_functioncode"]
                msg_id = request["msg_id"]

                attempts_left = QUERY_RETRY_ATTEMPTS
                while attempts_left > 0:
                    attempts_left -= 1
                    try:
                        self.connect_to_server()
                        await self.send_request(params, start, end, mb_fc, msg_id)
                        result = 1
                    except (ConnectionError, OSError, ValueError, IndexError) as e:
                        # ValueError covers client timeouts and malformed responses.
                        result = 0
                        msg = (
                            f"Querying [{start} - {end}] failed with exception [{type(e).__name__}: {e}]"
                        )
                        if attempts_left > 0:
                            self._LOGGER.debug(msg)
                        else:
                            self._LOGGER.warning(msg)
                        await self.disconnect_from_server()
                        if attempts_left > 0:
                            await asyncio_sleep(0.5)
                    if result == 0:
                        if attempts_left > 0:
                            self._LOGGER.debug(
                                f"Querying [{start} - {end}] failed, [{attempts_left}] retry attempts left"
                            )
                        else:
                            self._LOGGER.warning(
                                f"Querying [{start} - {end}] failed after retries, aborting."
                            )
                    else:
                        self._LOGGER.debug(f"Querying [{start} - {end}] succeeded")
                        break
                if result == 0:
                    self._LOGGER.warning(
                        f"Querying registers [{start} - {end}] failed, aborting."
                    )
                    break

            if result == 1:
                self._LOGGER.debug(f"All queries succeeded, exposing updated values.")
                self.status_lastUpdate = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                self.status_connection = "Connected"
                self._current_val = params.get_result()
            else:
                self.status_connection = "Disconnected"
                # Clear cached previous results to not report stale and incorrect data
                self._current_val = {}
                await self.disconnect_from_server()
        except Exception:
            self._LOGGER.warning(
                f"Querying inverter {self._serial} at {self._host}:{self._port} failed with an unexpected exception",
                exc_info=True,
            )
            self.status_connection = "Disconnected"
            # Clear cached previous results to not report stale and incorrect data
            self._current_val = {}
            await self.disconnect_from_server()

    def get_current_val(self):
        return self._current_val

    def get_sensors(self):
        params = ParameterParser(self.parameter_definition)
        return params.get_sensors()

    # Service calls
    async def service_write_holding_register(self, register, value):
        # Ensure value is a scalar, not a list
        if isinstance(value, list):
            if not value:
                raise ValueError("Cannot write empty value list to holding register")
            value = value[0]
        
        self._LOGGER.debug(
            f"Service Call: write_holding_register : [{register}], value : [{value}]"
        )
        attempts_left = QUERY_RETRY_ATTEMPTS
        while attempts_left > 0:
            attempts_left -= 1
            try:
                self.connect_to_server()
                await self.write_holding_register(register, value, 0x06, 1)
                return
            except (ConnectionError, OSError, ValueError, IndexError) as e:
                msg = f"Service Call: write_holding_register : [{register}], value : [{value}] failed with exception [{type(e).__name__}: {e}]"
                if attempts_left > 0:
                    self._LOGGER.debug(msg + f", [{attempts_left}] retry attempts left")
                else:
                    self._LOGGER.warning(msg)
                await self.disconnect_from_server()
                if attempts_left > 0:
                    await asyncio_sleep(0.5)
                else:
                    raise

    async def service_write_multiple_holding_registers(self, register, values):
        self._LOGGER.debug(
            f"Service Call: write_multiple_holding_registers: [{register}], values : [{values}]"
        )
        attempts_left = QUERY_RETRY_ATTEMPTS
        while attempts_left > 0:
            attempts_left -= 1
            try:
                self.connect_to_server()
                await self.write_multiple_holding_registers(values, register, 0x10, 1)
                return
            except (ConnectionError, OSError, ValueError, IndexError) as e:
                msg = f"Service Call: write_multiple_holding_registers: [{register}], values : [{values}] failed with exception [{type(e).__name__}: {e}]"
                if attempts_left > 0:
                    self._LOGGER.debug(msg + f", [{attempts_left}] retry attempts left")
                else:
                    self._LOGGER.warning(msg)
                await self.disconnect_from_server()
                if attempts_left > 0:
                    await asyncio_sleep(0.5)
                else:
                    raise
