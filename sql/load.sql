-- load.sql
-- Loads the CSVs written by convert.py into the tables from schema.sql.
--
-- Copy data/*.csv into MySQL's secure_file_priv folder first
-- (SELECT @@secure_file_priv;) and edit the three paths below if yours
-- differs from the default Windows install location.
--
-- convert.py writes missing values as empty strings, so NULLIF turns them
-- back into real NULLs on the way in.

USE indian_railways;

LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/stations.csv'
INTO TABLE stations
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 LINES
(code, @name, @state, @zone, @address, @latitude, @longitude)
SET name      = NULLIF(@name, ''),
    state     = NULLIF(@state, ''),
    zone      = NULLIF(@zone, ''),
    address   = NULLIF(@address, ''),
    latitude  = NULLIF(@latitude, ''),
    longitude = NULLIF(@longitude, '');

LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/trains.csv'
INTO TABLE trains
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 LINES
(train_number, train_name, train_type, zone,
 from_station_code, from_station_name, to_station_code, to_station_name,
 @departure, @arrival, @duration_h, @duration_m, @distance,
 @first_class, @chair_car, @sleeper, @first_ac, @second_ac, @third_ac,
 @return_train, @route_path)
SET departure    = NULLIF(@departure, ''),
    arrival      = NULLIF(@arrival, ''),
    duration_h   = NULLIF(@duration_h, ''),
    duration_m   = NULLIF(@duration_m, ''),
    distance     = NULLIF(@distance, ''),
    first_class  = NULLIF(@first_class, ''),
    chair_car    = NULLIF(@chair_car, ''),
    sleeper      = NULLIF(@sleeper, ''),
    first_ac     = NULLIF(@first_ac, ''),
    second_ac    = NULLIF(@second_ac, ''),
    third_ac     = NULLIF(@third_ac, ''),
    return_train = NULLIF(@return_train, ''),
    route_path   = NULLIF(@route_path, '');

LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/schedules.csv'
INTO TABLE schedules
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 LINES
(id, train_number, train_name, station_code, station_name,
 @arrival, @departure, @day)
SET arrival   = NULLIF(@arrival, ''),
    departure = NULLIF(@departure, ''),
    day       = NULLIF(@day, '');

-- Expected: stations 8990, trains 5208, schedules 417080
SELECT 'stations' AS table_name, COUNT(*) AS row_count FROM stations
UNION ALL SELECT 'trains', COUNT(*) FROM trains
UNION ALL SELECT 'schedules', COUNT(*) FROM schedules;
