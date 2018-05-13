import eventlet
eventlet.monkey_patch(socket=True)
import os
import sys
import yaml
import json
import time
from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit
from multiprocessing import JoinableQueue
from json import loads, dumps
from math import degrees
from datetime import datetime

sys.path.append('/home/christopher/IARC-2018/Flight')

from ATC import Tower

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

queue = JoinableQueue()

CONFIG_FILENAME = "drone_configs.yml"

vehicle_config_data = None

def load_config_file():
    try:
        global vehicle_config_data 
        config_file = open(CONFIG_FILENAME, 'r')
        vehicle_config_data = yaml.load(config_file)
        config_file.close()
    except IOError:
        print("\nFailed to get configuration file, some information may not be available.\n")

def get_battery(tower_as_json):
    global vehicle_config_data 
    battery_info = {}
    battery_info["voltage"] = tower_as_json[u'voltage']
    battery_info["full_voltage"] = vehicle_config_data["battery"]["full_voltage"]
    battery_info["failsafe_voltage"] = vehicle_config_data["battery"]["failsafe_voltage"]
    current = tower.vehicle.battery.voltage - battery_info["failsafe_voltage"]
    full = battery_info["full_voltage"] - battery_info["failsafe_voltage"]
    battery_info["percent_remaining"] = (current / full if battery_info["voltage"] > battery_info["failsafe_voltage"] else 0.00)

    return battery_info

def get_velocities(tower_as_json):
    velocities = {}
    velocities['x'] = tower_as_json[u'velocity_x']
    velocities['y'] = tower_as_json[u'velocity_y']
    velocities['z'] = tower_as_json[u'velocity_z']

    return velocities

def get_attitude(tower_as_json):
    attitude_deg = {}
    attitude_deg["roll"] = degrees(tower_as_json[u'roll'])
    attitude_deg["pitch"] = degrees(tower_as_json[u'pitch'])
    attitude_deg["yaw"] = degrees(tower_as_json[u'yaw'])
    return attitude_deg

def get_pid_status(tower_as_json):
    pid_status = {}
    pid_status["alt_controller_output"] = tower_as_json[u'altitude_controller_output']
    pid_status["altitude_rc_out"] = tower_as_json[u'altitude_rc_output']
    pid_status["target_alt"] = tower_as_json[u'target_altitude']
    pid_status["pitch_controller_output"] = tower_as_json[u'pitch_controller_output']
    pid_status["pitch_rc_out"] = tower_as_json[u'pitch_rc_output']
    pid_status["target_pitch_vel"] = tower_as_json[u'target_pitch_velocity']
    pid_status["roll_controller_output"] = tower_as_json[u'roll_controller_output']
    pid_status["roll_rc_out"] = tower_as_json[u'roll_rc_output']
    pid_status["target_roll_vel"] = tower_as_json[u'target_roll_velocity']
    pid_status["yaw_controller_output"] = tower_as_json[u'yaw_controller_output']
    pid_status["yaw_rc_out"] = tower_as_json[u'yaw_rc_output']
    pid_status["target_yaw"] = degrees(tower_as_json[u'target_yaw'])
    return pid_status

def get_vehicle_status(tower_as_json):
    """Laundry list function.

    """
    if not vehicle_config_data:
        return
    status = {}
    status['battery'] = get_battery(tower_as_json)
    status['armed'] = tower_as_json[u'armed']
    status['mode'] = tower_as_json[u'mode']
    status['state'] = tower_as_json[u'state']
    status['altitude'] = tower_as_json[u'altitude']
    status['attitude'] = get_attitude(tower_as_json)
    status['airspeed'] = tower_as_json[u'airspeed']
    status['velocity'] = get_velocities(tower_as_json)
    status['hearbeat'] = int(time.mktime(datetime.utcnow().timetuple())) * 1000
    status['pid'] = get_pid_status(tower_as_json)
    return status

@app.route('/')
def index():
    return render_template("index.html")

@socketio.on('tower', namespace='/comms')
def handle_tower(json):
    global queue
    print('called on', json)
    if queue.empty():
        queue.put(json)

@socketio.on('connect')
def on_connect():
    emit('information', 'Initialization in progress...')
    load_config_file()
    emit('vehicle_update', vehicle_config_data, json=True)

@socketio.on('update_status')
def on_status():
    tower_as_json = queue.get()
    queue.task_done()
    emit('status', get_vehicle_status(json.loads(tower_as_json)))

@socketio.on('initialization')
def on_initialization(selected_vehicle_name):
    global vehicle_config_data
    global queue

    print('hello there')
    for vehicle in vehicle_config_data:
        if vehicle["name"] == selected_vehicle_name:
            vehicle_config_data = vehicle
            # print('waiting_for_data')
            # tower_as_json = queue.get()
            # queue.task_done()
            # emit('status', get_vehicle_status(json.loads(tower_as_json)))
            return

if __name__ == '__main__':
    print('eh')
    socketio.run(app)
