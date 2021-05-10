from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from flask_caching import Cache
import sim
import time 
import threading
import requests
import json
import re

app = Flask(__name__)
api = Api(app)



# Instantiate the cache
cache = Cache()
cache.init_app(app=app, config={"CACHE_TYPE": "filesystem",'CACHE_DIR': './tmp'})

# global configuration variables
clientID=-1

# Helper function provided by the teaching staff
def get_data_from_simulation(id):
    """Connects to the simulation and gets a float signal value

    Parameters
    ----------
    id : str
        The signal id in CoppeliaSim. Possible values are 'accelX', 'accelY' and 'accelZ'.

    Returns
    -------
    data : float
        The float value retrieved from the simulation. None if retrieval fails.
    """
    if clientID!=-1:
        res, data = sim.simxGetFloatSignal(clientID, id, sim.simx_opmode_blocking)
        if res==sim.simx_return_ok:
            return data
    return None

# TODO LAB 2 - Implement the necessary functions to read and write data to your Firebase real-time database
# Import database module.
#from firebase_admin import db 
# Get a database reference to our blog.

def push_data(child, data):
    db_ref = 'https://is2021-e5b25-default-rtdb.europe-west1.firebasedatabase.app/' + child + '.json'
    requests.post(db_ref, json={'data': data, 'timestamp': time.time() })
    pass

def put_config(data):
    db_ref = 'https://is2021-e5b25-default-rtdb.europe-west1.firebasedatabase.app/config.json'
    requests.put(db_ref, json={'current_rate': data})
    pass

def get_config():
    db_ref = 'https://is2021-e5b25-default-rtdb.europe-west1.firebasedatabase.app/config.json' 
    rate = requests.get(db_ref)
    value = re.findall("\d+\.\d+", rate.text)
    
    return float(value[0])
    pass

# TODO LAB 1 - Implement the data collection loop in a thread
class DataCollection(threading.Thread):
    def __init__(self):
        value = 1.0
        threading.Thread.__init__(self)
        # initialize the current_rate value in the cache
        cache.set("current_rate", value)
        # TODO LAB 2 - Put an initial rate in the config stored in the DB
        put_config(value)
    def run(self):
        # TODO LAB 1 - Get acceleration data values (x, y and z) from the simulation and print them to the console
        while True:
            x = get_data_from_simulation('accelX')
            print(x)
            y = get_data_from_simulation('accelY')
            print(y)
            z = get_data_from_simulation('accelZ')
            print(z)
            time.sleep(get_config()) #o sleep será igual ao time rate definido pelo utilizador
            push_data('accelX', x)
            push_data('accelY', y)
            push_data('accelZ', z)
            print(get_config())
        # TODO LAB 2 - Push the data to the real-time database on Firebase
      

# TODO LAB 1 - Implement the UpdateRate resource
class UpdateRate(Resource):
    def get(self, rate):
       return cache.get("current_rate")
    def put(self, rate):
        cache.set("current_rate", rate)
        return {'current_rate':cache.get("current_rate")}


# TODO LAB 1 - Define the API resource routing
#api.add_resource(UpdateRate, '/current_rate')
api.add_resource(UpdateRate, '/update_rate/<float:rate>')

if __name__ == '__main__':
    sim.simxFinish(-1) # just in case, close all opened connections
    clientID=sim.simxStart('127.0.0.1',19997,True,True,5000,5) # Connect to CoppeliaSim
    if clientID!=-1:
        # TODO LAB 1 - Start the data collection as a daemon thread
        #data_c = threading.Thread(target=DataCollection.run(), name='Thread-collect', daemon=True)
        collect = DataCollection()
        collect.daemon = True
        collect.start()
        app.run(debug=True, threaded=True)      
    else:
        exit()
    