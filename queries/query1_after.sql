SELECT station_code, station_name,
           AVG(MOD(TIMESTAMPDIFF(SECOND, arrival, departure) + 86400, 86400)) AS avg_halt_seconds,
           COUNT(*) AS stop_count
    FROM schedules
    WHERE arrival IS NOT NULL AND departure IS NOT NULL AND MOD(TIMESTAMPDIFF(SECOND, arrival, departure) + 86400, 86400) < 43200
    GROUP BY station_code, station_name
    HAVING stop_count >= 20
    ORDER BY avg_halt_seconds DESC, station_code
    LIMIT 20;
