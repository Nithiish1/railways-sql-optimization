SELECT station_code, station_name, COUNT(*) AS total_stops,
           COUNT(DISTINCT train_number) AS train_count,
           AVG(MOD(TIMESTAMPDIFF(SECOND, arrival, departure) + 86400, 86400)) AS avg_halt_seconds
    FROM schedules
    WHERE arrival IS NOT NULL AND departure IS NOT NULL AND MOD(TIMESTAMPDIFF(SECOND, arrival, departure) + 86400, 86400) < 43200
    GROUP BY station_code, station_name
;
