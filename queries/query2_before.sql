SELECT station_code, station_name,
               AVG(TIMESTAMPDIFF(SECOND, arrival, departure)) AS avg_halt_seconds,
               COUNT(*) AS stop_count
        FROM schedules
        WHERE arrival IS NOT NULL AND departure IS NOT NULL
        GROUP BY station_code, station_name
        ORDER BY avg_halt_seconds DESC
        LIMIT 20;
