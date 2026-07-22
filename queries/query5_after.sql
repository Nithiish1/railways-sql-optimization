SELECT train_number, station_code, station_name, halt_seconds
        FROM (
            SELECT train_number, station_code, station_name, halt_seconds,
                   RANK() OVER (PARTITION BY train_number ORDER BY halt_seconds DESC) AS rnk
            FROM q5_working_set
        ) ranked
        WHERE rnk = 1;
