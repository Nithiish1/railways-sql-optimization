SELECT train_number, train_name, arrival, departure
        FROM schedules
        WHERE station_code = 'CNB' AND arrival BETWEEN '06:00:00' AND '10:00:00'
        ORDER BY arrival;
