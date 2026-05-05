import re

class UnitOfInformation:
    _prefixes = " KMGTPEZY"
    _max_pow = len(_prefixes) - 1
    _units_order = [("YB", 8), ("ZB", 7), ("EB", 6), ("PB", 5), ("TB", 4), ("GB", 3), ("MB", 2), ("KB", 1), ("B", 0), ("b", -1)]
    _unit_to_attr = {"YB": "yottabytes", "ZB": "zettabytes", "EB": "exabytes", "PB": "petabytes", "TB": "terabytes","GB": "gigabytes", "MB": "megabytes", "KB": "kilobytes", "B": "bytes", "b": "bits"}

    def __init__(self, value: str):
        match = re.match(r"^(\d+) ?([KMGTPEZY])?([bB])$", value)
        if not match:
            raise TypeError("Не является значением измерения информации")
        number = int(match.group(1))
        prefix = match.group(2)
        unit = match.group(3)
        exp = 0 if prefix is None else self._prefixes.index(prefix)
        remaining_bits = number * (1024 ** exp)
        if unit == 'B': remaining_bits *= 8
        self.yottabytes, remaining_bits = divmod(remaining_bits, 8 * 1024 ** 8)
        self.zettabytes, remaining_bits = divmod(remaining_bits, 8 * 1024 ** 7)
        self.exabytes,   remaining_bits = divmod(remaining_bits, 8 * 1024 ** 6)
        self.petabytes,  remaining_bits = divmod(remaining_bits, 8 * 1024 ** 5)
        self.terabytes,  remaining_bits = divmod(remaining_bits, 8 * 1024 ** 4)
        self.gigabytes,  remaining_bits = divmod(remaining_bits, 8 * 1024 ** 3)
        self.megabytes,  remaining_bits = divmod(remaining_bits, 8 * 1024 ** 2)
        self.kilobytes,  remaining_bits = divmod(remaining_bits, 8 * 1024)
        self.bytes,      self.bits      = divmod(remaining_bits, 8)

    def __repr__(self):
        parts = []
        for unit_name, _ in self._units_order:
            attr = self._unit_to_attr[unit_name]
            val = getattr(self, attr, 0)
            if val > 0:
                parts.append(f"{val} {unit_name}")
        if not parts:
            return "UnitOfInformation(0 b)"
        return "UnitOfInformation(" + " + ".join(parts) + ")"
