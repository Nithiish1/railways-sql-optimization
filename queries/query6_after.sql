SELECT id, train_number, station_code, arrival
        FROM schedules
        WHERE id > 423375
        ORDER BY id
        LIMIT 20;
