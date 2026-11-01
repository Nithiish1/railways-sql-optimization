SELECT s1.train_number, s1.station_code, s1.station_name,
               MOD(TIMESTAMPDIFF(SECOND, s1.arrival, s1.departure) + 86400, 86400) AS halt_seconds
        FROM schedules s1
        WHERE s1.arrival IS NOT NULL AND s1.departure IS NOT NULL AND MOD(TIMESTAMPDIFF(SECOND, s1.arrival, s1.departure) + 86400, 86400) < 43200
          AND MOD(TIMESTAMPDIFF(SECOND, s1.arrival, s1.departure) + 86400, 86400) = (
              SELECT MAX(MOD(TIMESTAMPDIFF(SECOND, s2.arrival, s2.departure) + 86400, 86400))
              FROM schedules s2
              WHERE s2.train_number = s1.train_number AND s2.arrival IS NOT NULL AND s2.departure IS NOT NULL AND MOD(TIMESTAMPDIFF(SECOND, s2.arrival, s2.departure) + 86400, 86400) < 43200
          );
