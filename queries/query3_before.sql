SELECT s1.train_number, s1.station_code, s1.station_name, s1.halt_seconds
        FROM q_working_set s1
        WHERE s1.halt_seconds = (
            SELECT MAX(s2.halt_seconds) FROM q_working_set s2 WHERE s2.train_number = s1.train_number
        );
