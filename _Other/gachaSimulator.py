from random import randint


CHANCES_5_STAR = [6.799, 6.833, 6.867, 6.902, 6.936, 6.971, 7.006, 7.042, 7.077, 7.112, 7.148, 7.184, 7.22, 7.257, 7.293, 7.33, 7.366, 7.403, 7.441, 7.478, 7.516, 7.553, 7.591, 7.63, 7.668, 7.706, 7.745, 7.784, 7.823, 7.862, 7.902, 7.942, 7.982, 8.022, 8.062, 8.103, 8.143, 8.184, 8.225, 8.267, 8.308, 8.35, 8.392, 8.434, 8.476, 8.519, 8.562, 8.605, 8.648, 8.692, 8.735, 8.779, 8.823, 8.868, 8.912, 8.957, 9.002, 9.047, 9.093, 9.138, 9.184, 9.23, 9.277, 9.323, 9.37, 9.417, 9.465, 9.512, 9.56, 9.608, 9.656, 10.165, 10.7, 11.263, 11.855, 12.479, 13.136, 13.828, 14.555, 15.321, 16.128, 16.977, 17.87, 18.811, 19.801, 20.843, 21.94, 23.095, 24.31, 25.59, 26.936, 28.354, 29.846, 33.163, 36.848, 43.35, 51.0, 60.0, 75.0, 100.0]
CHANCES_4_STAR = [16.698, 16.782, 16.866, 16.951, 17.036, 17.122, 17.208, 17.294, 17.381, 17.469, 17.556, 17.645, 17.733, 17.822, 17.912, 18.002, 18.092, 18.183, 18.275, 18.367, 18.459, 18.552, 18.645, 18.739, 18.833, 18.927, 19.022, 19.118, 19.214, 19.311, 19.408, 19.505, 19.603, 19.702, 19.801, 20.843, 21.94, 23.095, 24.31, 25.59, 26.936, 28.354, 29.846, 33.163, 36.848, 43.35, 51.0, 60.0, 75.0, 100.0]
CHANCES_3_STAR = [27.936, 28.077, 28.218, 28.359, 28.502, 28.645, 28.789, 28.934, 29.079, 29.225, 29.372, 29.52, 29.668, 29.817, 29.967, 31.544, 33.205, 34.952, 36.792, 38.728, 43.031, 47.813, 56.25, 75.0, 100.0]
CHANCES_2_STAR = [31.544, 33.205, 34.952, 36.792, 38.728, 43.031, 47.813, 56.25, 75.0, 100.0]
CHANCES_1_STAR = [100.0]

def pull(statistic: dict()):
    try:
        percent = randint(0, 100000) / 1000
        statistic["pulled_total"] += 1
        if percent <= CHANCES_5_STAR[statistic["pulled_after_5_star"]]:
            statistic["pulled_after_5_star"] = 0
            statistic["pulled_after_4_star"] += 1 if statistic["pulled_after_4_star"] < 50 else 0
            statistic["pulled_after_3_star"] += 1 if statistic["pulled_after_3_star"] < 25 else 0
            statistic["pulled_after_2_star"] += 1 if statistic["pulled_after_2_star"] < 10 else 0
            print("You've got ★★★★★!", end=" ")
            if statistic["next_event_5_star"] or randint(0, 100000) / 1000 <= 50:
                statistic["next_event_5_star"] = False
                print("★ Event!")
            else:
                statistic["next_event_5_star"] = True
                print("☆ Standard!")
        else:
            if percent <= CHANCES_4_STAR[statistic["pulled_after_4_star"]]:
                statistic["pulled_after_5_star"] += 1
                statistic["pulled_after_4_star"] = 0
                statistic["pulled_after_3_star"] += 1 if statistic["pulled_after_3_star"] < 25 else 0
                statistic["pulled_after_2_star"] += 1 if statistic["pulled_after_2_star"] < 10 else 0
                print("You've got ★★★★☆!", end=" ")
                if statistic["next_event_4_star"] or randint(0, 100000) / 1000 <= 50:
                    statistic["next_event_4_star"] = False
                    print("★ Event!")
                else:
                    statistic["next_event_4_star"] = True
                    print("☆ Standard!")
            else:
                if percent <= CHANCES_3_STAR[statistic["pulled_after_3_star"]]:
                    statistic["pulled_after_5_star"] += 1
                    statistic["pulled_after_4_star"] += 1
                    statistic["pulled_after_3_star"] = 0
                    statistic["pulled_after_2_star"] += 1 if statistic["pulled_after_2_star"] < 50 else 0
                    print("You've got ★★★☆☆!", end=" ")
                    if statistic["next_event_3_star"] or randint(0, 100000) / 1000 <= 50:
                        statistic["next_event_3_star"] = False
                        print("★ Event!")
                    else:
                        statistic["next_event_3_star"] = True
                        print("☆ Standard!")
                else:
                    if percent <= CHANCES_2_STAR[statistic["pulled_after_2_star"]]:
                        statistic["pulled_after_5_star"] += 1
                        statistic["pulled_after_4_star"] += 1
                        statistic["pulled_after_3_star"] += 1
                        statistic["pulled_after_2_star"] = 0
                        print("You've got ★★☆☆☆!", end=" ")
                        if statistic["next_event_2_star"] or randint(0, 100000) / 1000 <= 50:
                            statistic["next_event_2_star"] = False
                            print("★ Event!")
                        else:
                            statistic["next_event_2_star"] = True
                            print("☆ Standard!")
                    else:
                        statistic["pulled_after_5_star"] += 1
                        statistic["pulled_after_4_star"] += 1
                        statistic["pulled_after_3_star"] += 1
                        statistic["pulled_after_2_star"] += 1
                        print("You've got ★☆☆☆☆!", end=" ")
                        if statistic["next_event_1_star"] or randint(0, 100000) / 1000 <= 50:
                            statistic["next_event_1_star"] = False
                            print("★ Event!")
                        else:
                            statistic["next_event_1_star"] = True
                            print("☆ Standard!")
    except Exception as errorMessage:
        print(errorMessage)

if __name__ == "__main__":
    statistic = {
        "pulled_total": 0,
        "pulled_after_5_star": 0,
        "pulled_after_4_star": 0,
        "pulled_after_3_star": 0,
        "pulled_after_2_star": 0,
        "next_event_5_star": False,
        "next_event_4_star": False,
        "next_event_3_star": False,
        "next_event_2_star": False,
        "next_event_1_star": False,
    }
