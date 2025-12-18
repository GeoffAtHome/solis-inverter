import asyncio
from solis_direct import PySolis_direct

timedate = [ 25, 12, 15, 18, 24, 52]  # DD,MM,YY,HH,MM,SS
timeInverterOn = 3
timeInverterOff = 1

def send_request(start,  params, mb_fc):
        length = len(params)
        msg = [mb_fc, (start >> 8) & 0xff, start & 0xff, (length>>8) & 0xff, length & 0xff, (length*2) & 0xff]

        for param in params:
            msg.append( (param >> 8) & 0xff)
            msg.append( param & 0xff)

        return msg

def send_register(addr, value):
        msg = [0x06, (addr >> 8) & 0xff, (addr & 0xff), (value >> 8) & 0xff, value & 0xff]
        return msg

async def getResult(modbus, id,payload):
    result = await modbus.request(payload, msg_id=id)
    return result

async def main():
    modbus = PySolis_direct("192.168.15.83", 8000)
    await modbus.connect()  
    # payload = send_request(43000,  timedate, 0x10)
    payload = send_register(43110, timeInverterOn)
    # payload = send_register(43110, timeInverterOff)
    result = await getResult(modbus, 1, payload)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
