SELECT station_code, station_name, COUNT(DISTINCT train_number) AS train_count
        FROM schedules
        GROUP BY station_code, station_name
        ORDER BY train_count DESC
        LIMIT 20;
