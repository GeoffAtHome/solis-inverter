import struct

class ParameterParser:
    def __init__(self, lookups):
        self.result = {}
        self._lookups = lookups
        return

    def parse (self, rawData):
        msg_id = int.from_bytes(rawData[0:1],'little')
        if rawData != None:
            for i in self._lookups['parameters']:
                if msg_id == i['msg_id']:
                    for j in i['items']:
                        self.try_parse_field(rawData, j)
        return

    def get_result(self):
        return self.result


    def try_parse_field (self, rawData, definition):
        rule = definition['rule']
        if rule == 1:
            self.try_parse_unsigned(rawData, definition)
        elif rule == 2:
            self.try_parse_ascii(rawData, definition)
        return

    def do_validate(self, title, value, rule):
        if 'min' in rule:
            if rule['min'] > value:
                if 'invalidate_all' in rule:
                    raise ValueError(f'Invalidate complete dataset ({title} ~ {value})')
                return False

        if 'max' in rule:
            if rule['max'] < value:
                if 'invalidate_all' in rule:
                    raise ValueError(f'Invalidate complete dataset ({title} ~ {value})')
                return False

        return True

    def try_parse_signed (self, rawData, definition, start, length):
        title = definition['name']
        scale = definition['scale']
        value = 0
        found = True
        shift = 0
        maxint = 0
        for r in definition['registers']:
            index = r - start   # get the decimal value of the register'
            if (index >= 0) and (index < length):
                maxint <<= 16
                maxint |= 0xFFFF
                temp = rawData[index]
                value += (temp & 0xFFFF) << shift
                shift += 16
            else:
                found = False
        if found:
            if 'offset' in definition:
                value = value - definition['offset']

            if value > maxint/2:
                value = (value - maxint) * scale
            else:
                value = value * scale

            if 'validation' in definition:
                if not self.do_validate(title, value, definition['validation']):
                    return

            if self.is_integer_num (value):
                self.result[title] = int(value)
            else:
                self.result[title] = value

        return

    def try_parse_unsigned (self, rawData, definition):
        title = definition['name']
        scale = definition['scale']
        offset = definition['offset']
        value = int.from_bytes(rawData[offset:offset+2], 'big', signed=True)/scale
        if self.is_integer_num (value):
            self.result[title] = int(value)
        else:
            self.result[title] = value

        return


    def lookup_value (self, value, options):
        for o in options:
            if (o['key'] == value):
                return o['value']
        return value


    def try_parse_ascii (self, rawData, definition):
        title = definition['name']
        start = definition['start']
        end = definition['end']
        value = rawData[start:end].decode("ascii")
        self.result[title] = value
        return


    def get_sensors (self):
        result = []
        for i in self._lookups['parameters']:
            for j in i['items']:
                result.append(j)
        return result

    def is_integer_num(self, n):
        if isinstance(n, int):
            return True
        if isinstance(n, float):
            return n.is_integer()
        return False
