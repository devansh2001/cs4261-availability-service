from logging import debug

from flask import Flask, request
import os
import psycopg2
import uuid
import json
from collections import defaultdict
from flask_cors import CORS

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
        `day` varchar(64),
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
        st, et = availability[k].split('-')
        query = '''
                INSERT INTO availability_times (service_id, user_id, `day`, start_time, end_time)
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
        Select service_id, user_id, `day`, start_time, end_time from availability_times where user_id = %s and service_id = %s
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
            Select service_id, user_id, `day`, start_time, end_time from availability_times where user_id = %s and service_id = %s
        '''
    cursor.execute(query, [str(service_id), str(user_id)])
    res_2 = cursor.fetchall()
    conn.commit()
    return {'status': 201, 'availability': publish_availability(res, res_2)}

@app.route('/get-availability/<service_id>')
def get_providers(service_id):
    query = '''
            SELECT service_id, s.user_id, minimum_price, availability, fname, lname, s.profile_picture_url
             FROM availability as a join (Select fname, lname, user_id, profile_picture_url from users) as s on s.user_id = a.user_id WHERE a.service_id=%s
        '''
    cursor.execute(query, [str(service_id)])
    ans = []
    for res in cursor.fetchall():
        user_id = res[1]
        query = '''
                Select service_id, user_id, `day`, start_time, end_time from availability_times where user_id = %s and service_id = %s
            '''
        cursor.execute(query, [str(service_id), str(user_id)])
        res_2 = cursor.fetchall()
        ans.append(publish_availability(res, res_2))
    return {'status': 201, 'availability': ans}

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
    ans = []
    return {'status': 201, 'availability': ans}
# Helper functions
def publish_availability(availability, times):
    if not availability or len(availability) == 0:
        return None
    dic = defaultdict(lambda: [])
    for t in times:
        dic[t[2]].append(str(t[3]) + '-' + str(t[4]))
    availability_times = json.dumps(dic)
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

# https://www.youtube.com/watch?v=4eQqcfQIWXw
if __name__ == '__main__':
    port = os.environ.get('PORT', 5000)
    app.run(debug=True, host='0.0.0.0', port=port)