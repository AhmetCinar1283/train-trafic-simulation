import heapq
from datetime import datetime, timedelta
from visualize_train_route import visualize_train_route


class Station:
    def __init__(self, name):
        self.name = name
        self.connections = {}  # {next_station: { 'exp': travel_time_minutes, 'normal': travel_time_minutes}}
        self.min_stop = { 'exp': 0, 'normal': 0 }  # min wait
        self.st_idx = None
        self.trains_here = []

    def connect(self, other_station, travel_time_exp, travel_time_normal):
        self.connections[other_station] = { 'exp': travel_time_exp, 'normal': travel_time_normal }

class Train:
    def __init__(self, id, isexp, route, start_time):
        self.id = id
        self.isexp = isexp
        self.route = route  # [stationA, stationB, ...]
        self.current_index = 0
        self.time = start_time
        self.logs = []

    def log(self, station, arr, dep):
        self.logs.append({
            'train': self.id,
            'station': station.name,
            'arr': arr.strftime("%H:%M"),
            'dep': dep.strftime("%H:%M")
        })

    def next_station(self, how_many_next_station=1):
        if self.current_index + how_many_next_station < len(self.route):
            return self.route[self.current_index + how_many_next_station]
        return None


class Simulation:
    def __init__(self,
                 station_names,
                 stations_arr_exp,
                 stations_arr_normal,
                 stations_wait_exp,
                 stations_wait_normal,
                 trains_data
                 ):
        self.events = []
        self.occupied = {}
        self.stations = self.set_stations(station_names, stations_arr_exp, stations_arr_normal, stations_wait_exp, stations_wait_normal)
        self.trains = self.set_trains(trains_data)
        self.station_times = { 
                              "arrival": {'exp': stations_arr_exp, 'normal': stations_arr_normal},
                              'wait': {'exp': stations_wait_exp, 'normal': stations_wait_normal}
                              }
        self.timeline = []
        self.expres_max_wait = 5

    #--------------------------------
    # HELPERS
    #--------------------------------
    # Stations are created based on the data received.
    def set_stations(self, station_names, stations_arr_exp, stations_arr_normal, stations_wait_exp, stations_wait_normal):
        stations = [Station(name) for name in station_names]
        for i, (station, starr_exp, starr_normal, stwait_exp, stwait_normal) in enumerate(zip(stations, stations_arr_exp, stations_arr_normal, stations_wait_exp, stations_wait_normal)):
            if i < (len(stations)-1):
                station.connect(stations[i+1], starr_exp, starr_normal)
            if i > 0:
                station.connect(stations[i-1], stations_arr_exp[i-1], stations_arr_normal[i-1])
            station.min_stop = { 'exp': stwait_exp, 'normal': stwait_normal }
            station.st_idx = i
        return stations
    
    def set_trains(self, trains_data):
        trains = []
        for data in trains_data:
            start = data['route_start']
            end = data['route_end']
            isexp = list(str(data['no']))[1] == '2' if len(list(str(data['no']))) > 1 else False

            if start <= end:
                train = Train(data['no'], isexp, self.stations[start:end+1], data['start_time'])
            else:
                train = Train(data['no'], isexp, self.stations[end:start+1][::-1], data['start_time'])
            trains.append(train)
            
            station = train.route[train.current_index]
            station.trains_here.append({ 'train': train, 'arrival': train.time, 'isexp': train.isexp })

            # automatically starts the event
            heapq.heappush(self.events, (train.time, train.id, train))
        return trains
    
    # -----------------------------
    # Process train events
    # -----------------------------
    def is_opposite_segment_occupied(self, segment, old_dep_time):
        if segment in self.occupied and self.occupied[segment]['arrival_next'] > old_dep_time:
            wait = self.occupied[segment]['arrival_next'] - old_dep_time
            new_dep_time = old_dep_time + wait
            return True, new_dep_time
        else:
            new_dep_time = old_dep_time
            return False, new_dep_time
    
    def is_opposite_station_occupied(self, train, old_dep_time):
        next_station = train.next_station()
        station = train.next_station(0)
        
        train_list = []
        for train_data in next_station.trains_here:
            waiting_train = train_data['train']
            waitin_train_next_station = waiting_train.next_station()
            if waitin_train_next_station == station:
                waitin_train_station = waiting_train.next_station(0)
                waiting_time = waitin_train_station.connections[waitin_train_next_station]['exp' if waiting_train.isexp else 'normal']
                waiting_time = old_dep_time + timedelta(minutes=waiting_time)
                
                train_list.append([True, waiting_time, waiting_train.isexp])

        isOccupied_station = any([t[0] for t in train_list])
        next_wait_timeSta = max([t[1] for t in train_list], default=None)
        next_is_there_list_expres = any([t[2] for t in train_list])
        
        return isOccupied_station, next_wait_timeSta, next_is_there_list_expres
    

    def control_this_station(self, train, myisexp, old_dep_time):
        station = train.next_station(0)
        next_station = train.next_station()
        travel_time = station.connections[next_station]['exp' if train.isexp else 'normal']
        next_arrive_time = old_dep_time + timedelta(minutes=travel_time)
        train_list = []
        
        for train_data in station.trains_here:
            this_station_train = train_data['train']
            this_station_arrival = train_data['arrival']
            if this_station_train != train or this_station_arrival <= old_dep_time + timedelta(minutes=self.expres_max_wait):
                this_station_next = this_station_train.next_station()
                if this_station_next == next_station:
                    train_list.append((True, this_station_arrival, this_station_train.isexp))

        this_is_there_list_expres = any([t[2] for t in train_list])
        
        if myisexp:
            return 'Go', old_dep_time
        else:
            if this_is_there_list_expres:
                exp_wait_time = [t[1] for t in train_list if t[2]]
                max_wait_time = max(exp_wait_time, default=datetime.min)
                new_dep_time = max(old_dep_time+timedelta(minutes=1), max_wait_time)
                
                if next_arrive_time - max_wait_time > timedelta(minutes=self.expres_max_wait):
                    return 'Wait', new_dep_time
                else:
                    return 'Go', old_dep_time
            else:
                return 'Go', old_dep_time

    def control_back(self, train, myisexp, old_dep_time):
        station = train.next_station(0)
        next_station = train.next_station()

        travel_time = station.connections[next_station]['exp' if train.isexp else 'normal']
        arrival_time = old_dep_time + timedelta(minutes=travel_time)
        
        back_time = 0
        station_list = []
        segment_list = []
        index = 0
        last_calc_station = station
        while back_time < travel_time:
            index -= 1
            if station.st_idx + index < 0:
                break
            back_station = self.stations[station.st_idx + index]
            back_segment = tuple(sorted([last_calc_station.name, back_station.name]))
            
            back_time += back_station.connections[last_calc_station]['exp']
            
            station_list.append(back_station)
            segment_list.append(back_segment)
            last_calc_station = back_station
        
        for sta in station_list:

            for train_data in sta.trains_here:
                if train_data['isexp']:
                    if train_data['arrival'] > arrival_time - timedelta(minutes=self.expres_max_wait):
                        return 'Go', old_dep_time
                    else:
                        return 'Wait', old_dep_time + timedelta(minutes=1)

        return 'Go', old_dep_time

    def can_train_proceed(self, train, segment, old_dep_time):
        myisexp = train.isexp
        
        isOccupied_segment, wait_timeSeg = self.is_opposite_segment_occupied(segment, old_dep_time)
        isOccupied_nextStation, next_wait_timeSta, next_is_there_list_expres = self.is_opposite_station_occupied(train, old_dep_time)

        if myisexp:
            if isOccupied_segment:
                return 'Wait', wait_timeSeg
            else:
                return 'Go', wait_timeSeg

        else:
            if isOccupied_segment:
                return 'Wait', wait_timeSeg
            else:
                if isOccupied_nextStation:
                    if next_is_there_list_expres:
                        return 'Wait', max(next_wait_timeSta, wait_timeSeg)
                    else:
                        decision_here, wait_time_ThisSta = self.control_this_station(train, myisexp, old_dep_time)
                        decision_back, wait_time_back = self.control_back(train, myisexp, old_dep_time)
                        decision = 'Go' if decision_here == 'Go' and decision_back == 'Go' else 'Wait'
                        wait_time = min(wait_time_ThisSta, wait_time_back) if decision == 'Go' else max(wait_time_ThisSta, wait_time_back)
                        wait_time = max(wait_time, old_dep_time+timedelta(minutes=1))
                        return decision, wait_time
                else:
                    decision_here, wait_time_ThisSta = self.control_this_station(train, myisexp, old_dep_time)
                    decision_back, wait_time_back = self.control_back(train, myisexp, old_dep_time)
                    decision = 'Go' if decision_here == 'Go' and decision_back == 'Go' else 'Wait'
                    wait_time = max(wait_time_ThisSta, wait_time_back)
                    wait_time = max(wait_time, old_dep_time+timedelta(minutes=1))
                    return decision, wait_time

    # ------------------------------
    # CORE
    #------------------------------
    def run(self):
        i = 0
        while self.events and i < 1000:
            i += 1
            current_time, _, train = heapq.heappop(self.events)

            # Have we reached our target/destination
            if train.current_index >= len(train.route):
                continue

            station = train.route[train.current_index]
            arr_time = max(train.time, current_time)
            dep_time = arr_time + timedelta(minutes=station.min_stop['exp' if train.isexp else 'normal'])

            train.log(station, arr_time, dep_time)

            # Have we reached the last station?
            next_station = train.next_station()
            if not next_station:
                continue
            
            travel_time = station.connections[next_station]['exp' if train.isexp else 'normal']
            segment = tuple(sorted([station.name, next_station.name]))

            # Conflict control
            decision, new_dep_time = self.can_train_proceed(train, segment, dep_time)
            
            if decision == 'Go':
                train.logs[-1]['dep'] = new_dep_time.strftime("%H:%M")

                arrival_next = dep_time + timedelta(minutes=travel_time)

                self.occupied[segment] = {
                    "arrival_next": arrival_next,
                    "isexp": train.isexp,
                    "train": train
                }


                train.current_index += 1
                train.time = arrival_next

                station.trains_here = list(filter(lambda t: t['train'] != train, station.trains_here))
                next_station.trains_here.append({'train': train, 'arrival': train.time, 'isexp': train.isexp})

                heapq.heappush(self.events, (train.time, train.id, train))
            elif decision == 'Wait':
                train.logs[-1]['dep'] = new_dep_time.strftime("%H:%M")
                heapq.heappush(self.events, (new_dep_time, train.id, train))

    #-------------------------------
    # RESULTS
    #-------------------------------
    def merge_station_logs(self, logs):
        merged = []
        i = 0
        while i < len(logs):
            current = logs[i]
            train_id = current['train']
            station = current['station']

            # Başlangıç zamanları
            min_arr = datetime.strptime(current['arr'], "%H:%M")
            max_dep = datetime.strptime(current['dep'], "%H:%M")

            j = i + 1
            while j < len(logs):
                next_log = logs[j]
                if next_log['train'] == train_id and next_log['station'] == station:
                    next_arr = datetime.strptime(next_log['arr'], "%H:%M")
                    next_dep = datetime.strptime(next_log['dep'], "%H:%M")

                    if next_arr == max_dep:
                        max_dep = next_dep
                        j += 1
                    else:
                        break
                else:
                    break
                
            # Birleştirilmiş kayıt ekle
            merged.append({
                'train': train_id,
                'station': station,
                'arr': min_arr.strftime("%H:%M"),
                'dep': max_dep.strftime("%H:%M")
            })

            i = j

        return merged
        
    def visualize_result(self):
        for t in self.trains:
            for log in self.merge_station_logs(t.logs):
                self.timeline.append(log)
                print(log)
        station_names = [st.name for st in self.stations]
        visualize_train_route(self.timeline, station_names, color_map='tab20', show_dwell=True)



if __name__ == "__main__":
    # DATASET
    station_names = ["ESKİŞEHİR", "KIZILİNLER", "GÖKÇEKISIK", "PORSUK", "S. PINAR", "ULUKÖY", "ALAYUNT", "KÜTAHYA", "D.ÖREN", "K.ÖREN", "GÜZELYURT", "KAYI", "TAVŞANLI", "GÖLCÜK", "EMİRLER", "DEMİRLİ", "DEĞİRMİSAZ", "BALIKÖY", "ALÖVE", "GÖKÇEDAĞ", "NALLIKAYA", "PRİBEYLER", "SİNDİRLER", "DURSUNBEY", "SELİMAĞA", "G. DERE", "DADA", "MEZİTLER", "SARFAKLAR", "NUSRAT", "MAHMUDİYE", "BALIKESİR"]
    stations_arr_exp = [14,8,12,10,6,12,7,12,7,8,10,9,10,3,13,12,16,15,7,14,7,21,14,12,10,13,15,12,8,11,19,0]
    stations_arr_normal = [16,10,17,15,11,16,11,24,12,9,11,7,15,3,21,17,19,19,9,20,11,29,27,25,23,18,18,17,11,17,20,0]
    stations_wait_exp = [0,0,0,0,1,0,1,0,0,0,0,0,3,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    stations_wait_normal = [0,0,0,0,0,0,0,15,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0,0,0,0,0,0,0,0]
    
    # Trains
    start1 = datetime.strptime("05:05", "%H:%M")
    start2 = datetime.strptime("08:51", "%H:%M")
    start3 = datetime.strptime("06:20", "%H:%M")
    start4 = datetime.strptime("05:25", "%H:%M")
    trains_data = [
        { 'no': 61353, 'route_start': 0, 'route_end': len(station_names)-1, 'start_time': start1},
        { 'no': 62352, 'route_start': 0, 'route_end': len(station_names)-1, 'start_time': start2},
        { 'no': 60351, 'route_start': 0, 'route_end': len(station_names)-1, 'start_time': start3},
        { 'no': 82166, 'route_start': len(station_names)-1, 'route_end': 0, 'start_time': start4},
        { 'no': 83164, 'route_start': len(station_names)-2, 'route_end': 0, 'start_time': start3},
        { 'no': 82167, 'route_start': len(station_names)-1, 'route_end': 0, 'start_time': start2},
        { 'no': 91165, 'route_start': len(station_names)-1, 'route_end': 0, 'start_time': start1},
    ]
    
    sim = Simulation(
        station_names,
        stations_arr_exp,
        stations_arr_normal,
        stations_wait_exp,
        stations_wait_normal,
        trains_data
        )

    sim.run()
    sim.visualize_result()