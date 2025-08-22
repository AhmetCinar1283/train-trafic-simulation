import matplotlib.pyplot as plt
import matplotlib.cm as cm
from collections import defaultdict

def to_minutes(hhmm: str) -> int:
    """ "07:30" -> 450 """
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)

def to_hhmm(minutes: int) -> str:
    """ 450 -> "07:30" """
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def visualize_train_route(timeline: list, stations, color_map: str = 'tab10', show_dwell: bool = True):

    # Determine station sequences
    stations_order = [s for s in stations]
    stations_map = {name: i for i, name in enumerate(stations_order)}

    # Group timeline by train
    trains_dict = defaultdict(list)
    for rec in timeline:
        trains_dict[rec["train"]].append(rec)

    # Color Schema
    colors = cm.get_cmap(color_map, len(trains_dict))

    # Create the plot
    plt.figure(figsize=(15, len(stations_order) // 2 + 2))

    for idx, (train_no, recs) in enumerate(sorted(trains_dict.items())):
        c = colors(idx)
        
        # Sort records of each train by time
        recs.sort(key=lambda x: to_minutes(x.get("arr", x.get("dep"))))

        # Combine both stations
        for i in range(len(recs) - 1):
            r1, r2 = recs[i], recs[i+1]

            x1 = stations_map[r1["station"]]
            x2 = stations_map[r2["station"]]
            y1 = to_minutes(r1["dep"])
            y2 = to_minutes(r2["arr"])

            # Travel line
            plt.plot([x1, x2], [y1, y2], color=c, linewidth=2)

            # Print the train number on the line
            if r1['station'] != r2['station']:
                mid_x = (x1 + x2) / 2
                mid_y = (y1 + y2) / 2 - 1.1
                plt.text(mid_x, mid_y, str(train_no), color=c, ha='center', va='center', fontsize=9)

            # Dwell line (optional)
            if show_dwell and "arr" in r1 and "dep" in r1 and r1["arr"] != r1["dep"]:
                dwell_start = to_minutes(r1["arr"])
                dwell_end = to_minutes(r1["dep"])
                plt.plot([x1, x1], [dwell_start, dwell_end], color=c, alpha=0.3, linewidth=4)

    # Axis settings
    plt.xlabel("Stations")
    plt.ylabel("Time")
    plt.xticks(list(stations_map.values()), list(stations_map.keys()), rotation=90)
    plt.title("Single Track Timeline")

    for i in range(len(stations_order)):
        plt.axvline(x=i, linestyle='--', color='gray', alpha=0.5, zorder=-1)

    ymin, ymax = plt.gca().get_ylim()
    for t in range(int(ymin)-int(ymin%5), int(ymax), 5):
        plt.axhline(y=t, linestyle=':', color='lightgray', linewidth=0.7, zorder=-2)

        
    plt.gca().invert_yaxis()
    yticks = plt.gca().get_yticks()
    plt.gca().set_yticklabels([to_hhmm(int(t)) for t in yticks])

    
    plt.tight_layout()
    plt.show()

# Örnek kullanım
if __name__ == '__main__':
    # Örnek veri
    example_stations = ["Station A", "Station B", "Station C", "Station D"]
    example_timeline = [
        {"train": 101, "station": "Station A", "arr": "07:30", "dep": "07:30"},
        {"train": 101, "station": "Station B", "arr": "07:45", "dep": "07:50"},
        {"train": 101, "station": "Station C", "arr": "08:10", "dep": "08:10"},
        {"train": 101, "station": "Station D", "arr": "08:30", "dep": "08:30"},
        
        {"train": 102, "station": "Station D", "arr": "08:00", "dep": "08:00"},
        {"train": 102, "station": "Station C", "arr": "08:20", "dep": "08:25"},
        {"train": 102, "station": "Station B", "arr": "08:45", "dep": "08:45"},
        {"train": 102, "station": "Station A", "arr": "09:00", "dep": "09:00"},
    ]
    visualize_train_route(example_timeline, example_stations)
