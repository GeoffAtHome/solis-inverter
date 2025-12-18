"""pysolis_direct.py"""
import asyncio
import aiohttp
import logging
from .crc import CrcModbus

log = logging.getLogger(__name__)

QUERY_RETRY_ATTEMPTS = 2

crcmod16 = CrcModbus()

class NoSocketAvailableError(Exception):
    """No Socket Available Error"""
    pass


class PySolis_direct:
    """
    The PySolis_directAsync class establishes a TCP connection to a Solarman V5 data
    logging stick on a call to connect() and exposes methods to send/receive
    Modbus RTU requests and responses asynchronously.

    For more detailed information on the Solarman V5 Protocol, see
    :doc:`solarmanv5_protocol`

    :param address: IP address or hostname of data logging stick
    :type address: str
    :param serial: Serial number of the data logging stick (not inverter!)
    :type serial: int
    :param port: TCP port to connect to data logging stick, defaults to 8000
    :type port: int, optional
    :param mb_slave_id: Inverter Modbus slave ID, defaults to 1
    :type mb_slave_id: int, optional
    :param auto_reconnect: Auto reconnect to the data logging stick on error
    :type auto_reconnect: bool, optional

    Basic example:
       >>> import asyncio
       >>> from pysolis_direct import PySolis_directAsync
       >>> modbus = PySolis_directAsync("192.168.1.10", 123456789)
       >>> modbus2 = PySolis_directAsync("192.168.1.11", 123456790)
       >>> loop = asyncio.get_event_loop()
       >>> loop.run_until_complete(asyncio.gather(*[modbus.connect(), modbus2.connect()], return_exceptions=True)
       >>>
       >>> print(loop.run_until_complete(modbus.read_input_registers(register_addr=33022, quantity=6)))
       >>> print(loop.run_until_complete(modbus2.read_input_registers(register_addr=33022, quantity=6)))

    See :doc:`examples` directory for further examples.

    """

    def __init__(self, address, port, session=None) -> None:
        """Constructor"""
        self.address = address
        self.results = []
        self.port = port
        self.connected = False
        self._session = session if session else aiohttp.ClientSession()
        self.reader: asyncio.StreamReader = None  # noqa
        self.writer: asyncio.StreamWriter = None  # noqa

    async def connect(self) -> None:
        """
        Connect to the data logging stick and start the socket reader loop

        :return: None
        :raises NoSocketAvailableError: When connection cannot be established

        """
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.address, self.port
            )
            self.connected = True

        except:
            raise NoSocketAvailableError(f"Cannot open connection to {self.address}:{self.port}")

    async def reconnect(self) -> None:
        """
        Reconnect to the data logging stick. Called automatically if the auto-reconnect option is enabled

        :return: None
        :raises NoSocketAvailableError: When connection cannot be re-established

        """
        if self.connected == False:
            await self.connect()

    async def endSession(self) -> None:
        await self._session.close()


    async def disconnect(self) -> None:
        """
        Disconnect the socket and set a signal for the reader thread to exit

        :return: None

        """
        if self.connected:
            self.connected = False
            self.writer.write(b"")
            await self.writer.drain()
            self.writer.close()
            await self.writer.wait_closed()


    async def readTask(self):
        buf = await self.reader.read(1024)
        self.results.append(buf)
        return buf

    @staticmethod
    def getPayloadWithCheckSum( message):
        messageInBytes = bytes(message)
        checksum = crcmod16(messageInBytes)
        return messageInBytes + checksum.to_bytes(2,byteorder='little')

    @staticmethod
    def bytes_to_words_16(data):
        words = []
        for i in range(0, len(data), 2):
            word = int.from_bytes(data[i:i+2], byteorder='big')
            words.append(word)
        return words


    async def writeTask(self, msg_id, payload):
        payloadWithChecksum = self.getPayloadWithCheckSum(bytes([msg_id]) +bytes(payload))
        self.writer.write(payloadWithChecksum)
        await self.writer.drain()


    async def request(self, message, msg_id = 42):
        """Read holding registers from modbus slave (Modbus function code 3)

        :param register_addr: Modbus register start address
        :type register_addr: int
        :param quantity: Number of registers to query
        :type quantity: int

        :return: List containing register values
        :rtype: list[int]

        """
        if self.connected == False:
            await self.connect()

        tasks = []
        tasks.append(asyncio.ensure_future(self.readTask()))
        tasks.append(asyncio.ensure_future(self.writeTask(msg_id, message)))

        try:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=10.0)
        except asyncio.exceptions.TimeoutError:
            raise ValueError("The long operation timed out, but we've handled it.")

        except asyncio.exceptions.CancelledError:
            raise ValueError("The cancel error.")

        except:
            raise ValueError("Failed to write")

        result = self.results[0]
        self.results = []

        if(len(result) > 0 and msg_id == result[0]):
            return self.bytes_to_words_16(result[1:len(result)-1])

        return None

