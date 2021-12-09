from logging import debug

from flask import Flask, request
import os
import psycopg2
import uuid
import json
from collections import defaultdict
from flask_cors import CORS
import datetime
import time

app = Flask(__name__)
# https://stackoverflow.com/a/64657739
CORS(app, support_credentials=True)
# https://devcenter.heroku.com/articles/heroku-postgresql#connecting-in-python

DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
# https://stackoverflow.com/a/43634941
conn.autocommit = True

cursor = conn.cursor()
try:
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS availability (
        service_id varchar(64),
        user_id varchar(64),
        minimum_price varchar(64),
        PRIMARY KEY (service_id, user_id)
    );
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS availability_times (
        service_id varchar(64),
        user_id varchar(64),
        day_name varchar(64),
        start_time varchar(10),
        end_time varchar(10)
    );
    ''')
except psycopg2.Error:
    print('Error occurred while creating table')

@app.route('/health-check')
def health_check():
    return {'status': 200, 'message': "Availability"}

@app.route('/availability/add-availabilty', methods=['POST'])
def create_availability():
    data = request.get_json()
    service_id = str(data['service_id'])
    user_id = str(data['user_id'])
    min_price = str(data['minimum_price'])
    availability = dict(data['availability'])
    for k in availability:
        if type(availability[k]) == str:
            availability[k] = list(availability[k].split(","))
    query = '''
        INSERT INTO availability (service_id, user_id, minimum_price)
        VALUES (%s, %s, %s)
    '''
    cursor.execute(query, [service_id, user_id, min_price])
    for k in availability.keys():
        for a in availability[k]:
            st, et = a.split('-')
            st = time_to_int(st)
            et = time_to_int(et)
            query = '''
                    INSERT INTO availability_times (service_id, user_id, day_name, start_time, end_time)
                    VALUES (%s, %s, %s, %s, %s)
                '''
            cursor.execute(query, [service_id, user_id, k, st, et])
    conn.commit()
    return {'status': 201, 'service_id': service_id, 'user_id': user_id, "debug": availability}

@app.route('/availability/delete-availability/<service_id>/<user_id>', methods=['DELETE'])
def delete_availability(service_id, user_id):
    query = '''
        SELECT service_id, s.user_id, minimum_price, fname, lname
         FROM availability as a join (Select fname, lname, user_id from users) as s on s.user_id = a.user_id WHERE a.service_id=%s and a.user_id=%s
    '''
    cursor.execute(query, [str(service_id), str(user_id)])
    res = cursor.fetchone()
    query = '''
        Select service_id, user_id, day_name, start_time, end_time from availability_times where service_id = %s and user_id = %s
    '''
    cursor.execute(query, [str(service_id), str(user_id)])
    res_2 = cursor.fetchall()
    query = '''
        DELETE FROM availability as a WHERE a.service_id=%s and a.user_id=%s
    '''
    cursor.execute(query, [str(service_id), str(user_id)])
    query = '''
           DELETE FROM availability_times as a WHERE a.service_id=%s and a.user_id=%s
       '''
    cursor.execute(query, [str(service_id), str(user_id)])
    conn.commit()
    return {'status': 201, 'deleted_value': publish_availability(res, res_2)}

@app.route('/get-availability/<service_id>/<user_id>')
def get_availability(service_id, user_id):
    query = '''
            SELECT service_id, s.user_id, minimum_price, fname, lname
             FROM availability as a join (Select fname, lname, user_id from users) as s on s.user_id = a.user_id WHERE a.service_id=%s and a.user_id=%s
        '''
    cursor.execute(query, [str(service_id), str(user_id)])
    res = cursor.fetchone()
    query = '''
            Select service_id, user_id, day_name, start_time, end_time from availability_times where service_id = %s and user_id = %s
        '''
    cursor.execute(query, [str(service_id), str(user_id)])
    res_2 = cursor.fetchall()
    conn.commit()
    return {'status': 201, 'availability': publish_availability(res, res_2)}

@app.route('/get-availability/<service_id>')
def get_providers(service_id):
    query = '''
            SELECT service_id, s.user_id, minimum_price, fname, lname, s.profile_picture_url
             FROM availability as a join (Select fname, lname, user_id, profile_picture_url from users) as s on s.user_id = a.user_id WHERE a.service_id=%s
        '''
    cursor.execute(query, [str(service_id)])
    ans = []
    debug = []
    for res in cursor.fetchall():
        user_id = res[1]
        query = '''
                Select service_id, user_id, day_name, start_time, end_time from availability_times where service_id = %s and user_id = %s
            '''
        cursor.execute(query, [str(service_id), str(user_id)])
        res_2 = cursor.fetchall()
        # debug.append((res, res_2, user_id))
        ans.append(publish_availability(res, res_2))
    return {'status': 201, 'availability': ans}
@app.route('/get-filtered-availability/<service_id>/<min_price>/<day>/<start_time>/<end_time>')
def get_filtered_availability(service_id, min_price, day, start_time, end_time):
    if min_price.isnumeric():
        min_price = float(min_price)
    else:
        min_price = float(10000)
    if start_time.isnumeric():
        start_t = float(int(start_time) * 3600)
    else:
        start_t = float(-1)
    if end_time.isnumeric():
        end_t = float(int(end_time) * 3600)
    else:
        end_t = float(24 * 3600)
    if day == '*':
        day = '%'
    query = '''
            SELECT service_id, s.user_id, minimum_price, fname, lname, s.profile_picture_url
             FROM availability as a join (Select fname, lname, user_id, profile_picture_url from users) as s on s.user_id = a.user_id 
             WHERE a.service_id = %s and CAST(minimum_price AS float) < %s ORDER BY minimum_price
        '''
    cursor.execute(query, [str(service_id), min_price])
    # return {"debug": (cursor.fetchall(), min_price, day, start_t, end_t)}
    result = []
    for res in cursor.fetchall():
        user_id = res[1]
        # return {"debug": [str(service_id), str(user_id), str(day), start_t, end_t]}
        query = '''
                Select service_id, user_id, day_name, start_time, end_time from availability_times 
                where service_id = %s and user_id = %s and day_name LIKE %s and CAST(start_time AS float) >= %s and CAST(end_time AS float) <= %s
                ORDER BY day_name, start_time, end_time
            '''
        cursor.execute(query, [str(service_id), str(user_id), str(day), start_t, end_t])
        res_2 = cursor.fetchall()
        if res_2:
            result.append(publish_availability(res, res_2))
    return {'status': 201, 'availability': result}

@app.route('/get-all-availability')
def get_all():
    query = '''
            SELECT service_id, s.user_id, minimum_price, fname, lname
             FROM availability as a join (Select fname, lname, user_id from users) as s on s.user_id = a.user_id
        '''
    cursor.execute(query, [])
    ans = []
    for res in cursor.fetchall():
        ans.append(publish_availability(res, []))
    return {'status': 201, 'availability': ans}
@app.route('/get-all-availability-times')
def get_all_times():
    query = '''
            Select * from availability_times
        '''
    cursor.execute(query, [])
    ans = cursor.fetchall()
    return {'status': 201, 'availability': ans}
@app.route('/get-all-availability-raw')
def get_all_raw():
    query = '''
            Select * from availability
        '''
    cursor.execute(query, [])
    ans = cursor.fetchall()
    return {'status': 201, 'availability': ans}


@app.route('/get-min-price/<provider_id>/<service_id>')
def get_min_price(provider_id, service_id):
    query = '''
        select min(minimum_price) from availability where user_id=%s and service_id=%s
    '''
    cursor.execute(query, [provider_id, service_id])
    min_price = None
    result = cursor.fetchall()

    try:
        min_price = result[0][0]
    except:
        print('error')
    return {'status': 200, 'min_price': min_price}

# Helper functions
def publish_availability(availability, times):
    if not availability or len(availability) == 0:
        return None
    dic = defaultdict(lambda: [])
    for t in times:
        dic[t[2]].append(int_to_time(int(t[3])) + '-' + int_to_time(int(t[4])))
    availability_times = str(dict(dic))
    res = {
        "service_id": availability[0],
        'user_id': availability[1],
        'minimum_price': availability[2],
        'availability': availability_times,
        'fname': availability[3],
        'lname': availability[4]
    }

    if len(availability) >= 6:
        res['profile_picture'] = availability[5]
    
    return res

def time_to_int(time_string):
    date_time = datetime.datetime.strptime(time_string, "%H:%M:%S")
    a_timedelta = date_time - datetime.datetime(1900, 1, 1)
    seconds = a_timedelta.total_seconds()
    return int(seconds)
def int_to_time(time_int):
    return time.strftime('%H:%M:%S', time.gmtime(time_int))

# https://www.youtube.com/watch?v=4eQqcfQIWXw
if __name__ == '__main__':
    port = os.environ.get('PORT', 5000)
    app.run(debug=True, host='0.0.0.0', port=port)