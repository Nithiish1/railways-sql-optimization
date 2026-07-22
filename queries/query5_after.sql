SELECT train_number, train_name, train_type, to_station_code, departure, arrival, distance
        FROM trains WHERE from_station_code = 'NDLS';
