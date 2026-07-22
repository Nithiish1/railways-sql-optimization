-- schema.sql
-- Raw table definitions for the Indian Railways optimization project.
-- Deliberately NO indexes beyond primary keys at this stage --
-- baseline (unoptimized) performance is captured first, before
-- any indexing/partitioning work begins.
--
-- NOTE: code-like columns are sized generously because the real source
-- data has data-quality issues -- some values that should be short
-- codes appear instead as long, malformed text. This is documented in
-- the project's data-quality notes rather than silently truncated.

CREATE DATABASE IF NOT EXISTS indian_railways;
USE indian_railways;

DROP TABLE IF EXISTS schedules;
DROP TABLE IF EXISTS trains;
DROP TABLE IF EXISTS stations;

CREATE TABLE stations (
    code        VARCHAR(100)  PRIMARY KEY,
    name        VARCHAR(150),
    state       VARCHAR(50),
    zone        VARCHAR(20),
    address     VARCHAR(255),
    latitude    DECIMAL(10,6),
    longitude   DECIMAL(10,6)
);

CREATE TABLE trains (
    train_number       VARCHAR(50)   PRIMARY KEY,
    train_name         VARCHAR(150),
    train_type         VARCHAR(20),
    zone               VARCHAR(20),
    from_station_code  VARCHAR(150),
    from_station_name  VARCHAR(150),
    to_station_code    VARCHAR(150),
    to_station_name    VARCHAR(150),
    departure          TIME NULL,
    arrival             TIME NULL,
    duration_h         INT,
    duration_m         INT,
    distance            INT,
    first_class        TINYINT,
    chair_car          TINYINT,
    sleeper            TINYINT,
    first_ac           TINYINT,
    second_ac          TINYINT,
    third_ac           TINYINT,
    return_train       VARCHAR(255),
    route_path         TEXT
);

CREATE TABLE schedules (
    id            INT PRIMARY KEY,
    train_number  VARCHAR(50),
    train_name    VARCHAR(150),
    station_code  VARCHAR(150),
    station_name  VARCHAR(150),
    arrival       TIME NULL,
    departure     TIME NULL,
    day           INT
);