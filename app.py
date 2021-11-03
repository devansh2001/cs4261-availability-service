from logging import debug

from flask import Flask, request
import os
import psycopg2
import uuid
import json
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
        availability varchar(2048),
        PRIMARY KEY (service_id, user_id)
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
    # is_monday = "1" if 'monday' in data['availability'] else "0"
    # is_tuesday = "1" if 'tuesday' in data['availability'] else "0"
    # is_wednesday = "1" if 'wednesday' in data['availability'] else "0"
    # is_thursday = "1" if 'thursday' in data['availability'] else "0"
    # is_friday = "1" if 'friday' in data['availability'] else "0"
    # is_saturday = "1" if 'saturday' in data['availability'] else "0"
    # is_sunday = "1" if 'sunday' in data['availability'] else "0"
    availability = str(data['availability'])
    query = '''
        INSERT INTO availability (service_id, user_id, minimum_price, availability)
        VALUES (%s, %s, %s, %s)
    '''
    cursor.execute(query, [service_id, user_id, min_price, availability])
    conn.commit()
    return {'status': 201, 'service_id': service_id, 'user_id': user_id}

@app.route('/availability/delete-availability/<service_id>/<user_id>', methods=['DELETE'])
def delete_availability(service_id, user_id):
    query = '''
        SELECT service_id, s.user_id, minimum_price, availability, fname, lname
         FROM availability as a join (Select fname, lname, user_id from users) as s on s.user_id = a.user_id WHERE a.service_id=%s and a.user_id=%s
    '''
    cursor.execute(query, [str(service_id), str(user_id)])
    res = cursor.fetchone()
    query = '''
        DELETE FROM availability as a WHERE a.service_id=%s and a.user_id=%s
    '''
    cursor.execute(query, [str(service_id), str(user_id)])
    conn.commit()
    return {'status': 201, 'deleted_value': publish_availability(res)}

@app.route('/get-availability/<service_id>/<user_id>')
def get_availability(service_id, user_id):
    query = '''
            SELECT service_id, s.user_id, minimum_price, availability, fname, lname
             FROM availability as a join (Select fname, lname, user_id from users) as s on s.user_id = a.user_id WHERE a.service_id=%s and a.user_id=%s
        '''
    cursor.execute(query, [str(service_id), str(user_id)])
    res = cursor.fetchone()
    return {'status': 201, 'availability': publish_availability(res)}

@app.route('/get-availability/<service_id>')
def get_providers(service_id):
    query = '''
            SELECT service_id, s.user_id, minimum_price, availability, fname, lname
             FROM availability as a join (Select fname, lname, user_id from users) as s on s.user_id = a.user_id WHERE a.service_id=%s
        '''
    cursor.execute(query, [str(service_id)])
    ans = []
    for res in cursor.fetchall():
        ans.append(publish_availability(res))
    return {'status': 201, 'availability': ans}

@app.route('/get-all-availability')
def get_all():
    query = '''
            SELECT service_id, s.user_id, minimum_price, availability, fname, lname
             FROM availability as a join (Select fname, lname, user_id from users) as s on s.user_id = a.user_id
        '''
    cursor.execute(query, [])
    ans = []
    for res in cursor.fetchall():
        ans.append(publish_availability(res))
    return {'status': 201, 'availability': ans}

# Helper functions
def publish_availability(availability):
    if not availability or len(availability) == 0:
        return None
    res = {
        "service_id": availability[0],
        'user_id': availability[1],
        'minimum_price': availability[2],
        'availability': availability[3],
        'fname': availability[4],
        'lname': availability[5]
    }
    return res

# https://www.youtube.com/watch?v=4eQqcfQIWXw
if __name__ == '__main__':
    port = os.environ.get('PORT', 5000)
    app.run(debug=True, host='0.0.0.0', port=port)