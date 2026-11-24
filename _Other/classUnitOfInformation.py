import re


class UnitOfInformation:
    _prefixes = " KMGTPEZY"
    _units_order = [("YB", 8 * 1024 ** 8), ("ZB", 8 * 1024 ** 7), ("EB", 8 * 1024 ** 6), ("PB", 8 * 1024 ** 5), ("TB", 8 * 1024 ** 4), ("GB", 8 * 1024 ** 3), ("MB", 8 * 1024 ** 2), ("KB", 8 * 1024), ("B", 8), ("b", 1)]
    _unit_to_attr = {"YB": "yottabytes", "ZB": "zettabytes", "EB": "exabytes", "PB": "petabytes", "TB": "terabytes", "GB": "gigabytes", "MB": "megabytes", "KB": "kilobytes", "B": "bytes", "b": "bits"}
    _unit_multipliers = {"b": 1, "B": 8, "KB": 8 * 1024, "MB": 8 * 1024 ** 2, "GB": 8 * 1024 ** 3, "TB": 8 * 1024 ** 4, "PB": 8 * 1024 ** 5, "EB": 8 * 1024 ** 6, "ZB": 8 * 1024 ** 7, "YB": 8 * 1024 ** 8}

    def __init__(self, value: int | float | str | dict = 0):
        if   isinstance(value, int):
            if value < 0:
                raise ValueError("Отрицательное количество бит недопустимо")
            self._total_bits = value
        elif isinstance(value, float):
            if value < 0:
                raise ValueError("Отрицательное количество бит недопустимо")
            self._total_bits = int(value)
        elif isinstance(value, str):
            match = re.fullmatch(r"(\d+)\s?([KMGTPEZY])?([bB])", value)
            if not match:
                raise TypeError("Не является значением измерения информации")
            number = int(match.group(1))
            prefix = match.group(2)
            unit = match.group(3)
            exp = 0 if prefix is None else self._prefixes.index(prefix)
            total_bits = number * (1024 ** exp)
            if unit == 'B': total_bits *= 8
            self._total_bits = total_bits
        elif isinstance(value, dict):
            total_bits = 0
            for unit, amount in value.items():
                if not isinstance(amount, int) or amount < 0:
                    raise ValueError(f"Значение для '{unit}' должно быть неотрицательным целым")
                if unit not in self._unit_multipliers:
                    raise KeyError(f"Неизвестная единица измерения: '{unit}'")
                total_bits += amount * self._unit_multipliers[unit]
            self._total_bits = total_bits
        else:
            raise TypeError("Ожидается строка, целое, дробное число или словарь")
        self._calc_fields()

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

    # ---------- арифметика ----------
    def __add__(self, other):
        if isinstance(other, UnitOfInformation):
            return UnitOfInformation._from_bits(self._total_bits + other._total_bits)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, UnitOfInformation):
            return UnitOfInformation._from_bits(self._total_bits - other._total_bits)
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            if other < 0:
                return UnitOfInformation._from_bits(0)
            new_bits = round(self._total_bits * other)
            return UnitOfInformation._from_bits(new_bits)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, UnitOfInformation):
            if other._total_bits == 0:
                raise ZeroDivisionError("Деление на ноль")
            return self._total_bits / other._total_bits
        if isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("Деление на ноль")
            new_bits = round(self._total_bits / other)
            return UnitOfInformation._from_bits(new_bits)
        return NotImplemented

    def __floordiv__(self, other):
        if isinstance(other, UnitOfInformation):
            if other._total_bits == 0:
                raise ZeroDivisionError("Деление на ноль")
            return self._total_bits // other._total_bits
        if isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("Деление на ноль")
            new_bits = int(self._total_bits // other)
            return UnitOfInformation._from_bits(new_bits)
        return NotImplemented

    def __mod__(self, other):
        if isinstance(other, UnitOfInformation):
            if other._total_bits == 0:
                raise ZeroDivisionError("Модуль ноль")
            return UnitOfInformation._from_bits(self._total_bits % other._total_bits)
        if isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("Модуль ноль")
            return UnitOfInformation._from_bits(self._total_bits % int(other))
        return NotImplemented

    # ---------- сокращённые операторы присваивания ----------
    def __iadd__(self, other):
        return self.__sub__(other)

    def __isub__(self, other):
        return self.__sub__(other)

    def __imul__(self, other):
        return self.__mul__(other)

    def __itruediv__(self, other):
        return self.__truediv__(other)

    def __ifloordiv__(self, other):
        return self.__floordiv__(other)

    def __imod__(self, other):
        return self.__mod__(other)

    # ---------- сравнение ----------
    def __eq__(self, other):
        if not isinstance(other, UnitOfInformation):
            return NotImplemented
        return self._total_bits == other._total_bits

    def __lt__(self, other):
        if not isinstance(other, UnitOfInformation):
            return NotImplemented
        return self._total_bits < other._total_bits

    def __le__(self, other):
        if not isinstance(other, UnitOfInformation):
            return NotImplemented
        return self._total_bits <= other._total_bits

    def __gt__(self, other):
        if not isinstance(other, UnitOfInformation):
            return NotImplemented
        return self._total_bits > other._total_bits

    def __ge__(self, other):
        if not isinstance(other, UnitOfInformation):
            return NotImplemented
        return self._total_bits >= other._total_bits

    # ---------- преобразования в базовые типы ----------
    def to_int(self) -> int:
        return self._total_bits

    def to_float(self) -> float:
        return float(self._total_bits)

    def to_str(self) -> str:
        if self._total_bits == 0:
            return "0b"
        for unit_name, multiplier in self._units_order:
            if self._total_bits % multiplier == 0:
                value = self._total_bits // multiplier
                return f"{value}{unit_name}"
        return f"{self._total_bits}b"

    def to_bool(self) -> bool:
        return self._total_bits != 0

    def to_dict(self) -> dict:
        result = {}
        for unit_name, _ in self._units_order:
            attr = self._unit_to_attr[unit_name]
            val = getattr(self, attr, 0)
            if val > 0:
                result[unit_name] = val
        return result

    # ---------- внутренние ----------
    def _calc_fields(self):
        memory = self._total_bits
        self.yottabytes, memory    = divmod(memory, 8 * 1024 ** 8)
        self.zettabytes, memory    = divmod(memory, 8 * 1024 ** 7)
        self.exabytes,   memory    = divmod(memory, 8 * 1024 ** 6)
        self.petabytes,  memory    = divmod(memory, 8 * 1024 ** 5)
        self.terabytes,  memory    = divmod(memory, 8 * 1024 ** 4)
        self.gigabytes,  memory    = divmod(memory, 8 * 1024 ** 3)
        self.megabytes,  memory    = divmod(memory, 8 * 1024 ** 2)
        self.kilobytes,  memory    = divmod(memory, 8 * 1024)
        self.bytes,      self.bits = divmod(memory, 8)

    def to_bits(self) -> int:
        return self._total_bits

    @classmethod
    def _from_bits(cls, bits: int):
        obj = cls.__new__(cls)
        obj._total_bits = max(0, bits)
        obj._calc_fields()
        return obj
