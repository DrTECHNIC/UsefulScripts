def parse(date_time: str) -> tuple[int, int, int, int, int, int, int]:
    day = int(date_time[:2])
    month = int(date_time[3:5])
    year = int(date_time[6:10])
    hour = int(date_time[11:13])
    minute = int(date_time[14:16])
    second = int(date_time[17:19])
    millisecond = int(date_time[20:])
    return year, month, day, hour, minute, second, millisecond

def calculate(YYYY: int, MM: int, DD: int, hh: int, mm: int, ss: int, mss: int) -> tuple[int, int, int, int, int, int, int]:
    mss = mss + 1
    if mss == 1000:
        ss, mss = ss + 1, 0
        if ss == 60:
            mm, ss = mm + 1, 0
            if mm == 60:
                hh, mm = hh + 1, 0
                if hh == 24:
                    DD, hh = DD + 1, 0
                    nMM = False
                    if MM in [1, 3, 5, 7, 8, 10, 12]:
                        if DD == 31: nMM = True
                    elif MM in [4, 6, 9, 11]:
                        if DD == 30: nMM = True
                    elif MM == 2:
                        if MM % 4 != 0 or (YYYY % 100 == 0 and YYYY % 400 != 0):
                            if DD == 28: nMM = True
                        else:
                            if DD == 29: nMM = True
                    if nMM:
                        MM, DD = MM + 1, 1
                        if MM == 13:
                            YYYY, MM = YYYY + 1, 1
    return YYYY, MM, DD, hh, mm, ss, mss

if __name__ == "__main__":
    YYYY, MM, DD, hh, mm, ss, mss = parse("27.11.2005 07:30:27:761")
    for _ in range(27112007):
        print(f"{str(DD).zfill(2)}.{str(MM).zfill(2)}.{str(YYYY).zfill(4)} {str(hh).zfill(2)}:{str(mm).zfill(2)}:{str(ss).zfill(2)}:{str(mss).zfill(3)}")
        YYYY, MM, DD, hh, mm, ss, mss = calculate(YYYY, MM, DD, hh, mm, ss, mss)
