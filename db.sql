CREATE TABLE availability (
    service_id varchar(64),
    user_id varchar(64),
    minimum_price varchar(64),
    availability varchar(2048)
);
 CREATE TABLE IF NOT EXISTS availability_times (
        service_id varchar(64),
        user_id varchar(64),
        `day` varchar(64),
        start_time varchar(10),
        end_time varchar(10)
);