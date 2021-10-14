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
        is_monday varchar(2),
        is_tuesday varchar(2),
        is_wednesday varchar(2),
        is_thursday varchar(2),
        is_friday varchar(2),
        is_saturday varchar(2),
        is_sunday varchar(2),
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
    is_monday = "1" if 'monday' in data['availability'] else "0"
    is_tuesday = "1" if 'tuesday' in data['availability'] else "0"
    is_wednesday = "1" if 'wednesday' in data['availability'] else "0"
    is_thursday = "1" if 'thursday' in data['availability'] else "0"
    is_friday = "1" if 'friday' in data['availability'] else "0"
    is_saturday = "1" if 'saturday' in data['availability'] else "0"
    is_sunday = "1" if 'sunday' in data['availability'] else "0"
    query = '''
        INSERT INTO availability (service_id, user_id, minimum_price, is_monday, is_tuesday, is_wednesday, is_thursday, is_friday, is_saturday, is_sunday)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    cursor.execute(query, [service_id, user_id, min_price, is_monday, is_tuesday, is_wednesday, is_thursday, is_friday, is_saturday, is_sunday])
    conn.commit()
    return {'status': 201, 'service_id': service_id, 'user_id': user_id}

@app.route('/availability/delete-availability/<service_id>/<user_id>', methods=['DELETE'])
def delete_availability(service_id, user_id):
    query = '''
        SELECT * FROM availability as a WHERE a.service_id=%s and a.user_id=%s
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
           SELECT * FROM availability as a WHERE a.service_id=%s and a.user_id=%s
       '''
    cursor.execute(query, [str(service_id), str(user_id)])
    res = cursor.fetchone()
    return {'status': 201, 'reviews': publish_availability(res)}

# Helper functions
def publish_availability(availability):
    if not availability or len(availability) == 0:
        return None
    res = {
        "service_id": availability[0],
        'user_id': availability[1],
        'minimum_price': availability[2],
        'is_monday': True if availability[3] == 1 else False,
        'is_tuesday': True if availability[4] == 1 else False,
        'is_wednesday': True if availability[5] == 1 else False,
        'is_thursday': True if availability[6] == 1 else False,
        'is_friday': True if availability[7] == 1 else False,
        'is_saturday': True if availability[8] == 1 else False,
        'is_sunday': True if availability[9] == 1 else False,
    }
    return res

# https://www.youtube.com/watch?v=4eQqcfQIWXw
if __name__ == '__main__':
    port = os.environ.get('PORT', 5000)
    app.run(debug=True, host='0.0.0.0', port=port)