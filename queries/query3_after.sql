SELECT train_number, station_code, station_name, halt_seconds
        FROM (
            SELECT train_number, station_code, station_name,
                   MOD(TIMESTAMPDIFF(SECOND, arrival, departure) + 86400, 86400) AS halt_seconds,
                   RANK() OVER (PARTITION BY train_number ORDER BY MOD(TIMESTAMPDIFF(SECOND, arrival, departure) + 86400, 86400) DESC) AS rnk
            FROM schedules
            WHERE arrival IS NOT NULL AND departure IS NOT NULL AND MOD(TIMESTAMPDIFF(SECOND, arrival, departure) + 86400, 86400) < 43200
        ) ranked
        WHERE rnk = 1;
