SELECT id, train_number, station_code, arrival
        FROM schedules
        ORDER BY id
        LIMIT 20 OFFSET 300000;
