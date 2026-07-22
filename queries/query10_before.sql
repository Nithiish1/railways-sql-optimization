SELECT station_code, station_name, COUNT(*) AS total_stops,
               COUNT(DISTINCT train_number) AS train_count,
               AVG(TIMESTAMPDIFF(SECOND, arrival, departure)) AS avg_halt_seconds
        FROM schedules
        WHERE arrival IS NOT NULL AND departure IS NOT NULL
        GROUP BY station_code, station_name;
