SELECT id, train_number, station_code, arrival
        FROM schedules
        WHERE id > 300000
        ORDER BY id
        LIMIT 20;
