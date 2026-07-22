SELECT DISTINCT station_code, station_name
        FROM schedules
        WHERE train_number IN (
            SELECT train_number FROM trains WHERE train_type IN ('Raj', 'Drnt')
        );
