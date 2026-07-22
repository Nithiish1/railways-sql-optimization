SELECT DISTINCT sch.station_code, sch.station_name
        FROM schedules sch
        JOIN trains t ON t.train_number = sch.train_number
        WHERE t.train_type IN ('Raj', 'Drnt');
