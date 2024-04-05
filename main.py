from flask import request,jsonify,session
from config import app,db
import requests
import json
import time
from datetime import datetime
import calendar
import threading

scheduleOneTime_active_threads = {}
scheduleOneTime_interrupt_events = {}
scheduleDaily_active_threads = {}
scheduleDaily_interrupt_events = {}
dailyReport_active_threads = {}
dailyReport_interrupt_events = {}

def scheduleOneTime_thread(plantID, hour, min, date, month, year):
    name = threading.current_thread().name
    print(f"scheduleOneTime : {name} started for {plantID}")
    i = 0
    while not scheduleOneTime_interrupt_events[plantID].is_set():
        print(f"scheduleOneTime : {name} iteration no. {i+1} for {plantID}")
        curr_day = datetime.now().day
        curr_mon = datetime.now().month
        curr_yr = datetime.now().year
        curr_hr = datetime.now().hour
        curr_min = datetime.now().minute

        if (curr_day, curr_mon, curr_yr, curr_hr, curr_min) == (date, month, year, hour, min):
            print(f"scheduleOneTime : {name} matched for {plantID}")

            dailyReport_task_thread = threading.Thread(target=dailyReport_thread, args=(plantID, hour, min, date, month, year))
            dailyReport_task_thread.start()

            dailyReport_active_threads[plantID] = dailyReport_task_thread
            
            break
        else:
            time.sleep(5)
        
        i += 1
    
    print(f"scheduleOneTime : {name} completed for {plantID}")

def scheduleDaily_thread(plantID, hour, min, date, month, year):
    name = threading.current_thread().name
    print(f"scheduleDaily : {name} started for {plantID}")
    i = 0

    lastDate = calendar.monthrange(year,month)[1]

    min += 5
    if(min >= 60):
        min = 0
        hour += 1
    if(hour >= 24):
        hour = 0
        date += 1
    if(date >= lastDate):
        date = 1
        month += 1
    if(month >= 13):
        month = 1
        year += 1

    while not scheduleDaily_interrupt_events[plantID].is_set():
        print("mins: ",min)
        print(f"scheduleDaily : {name} iteration no. {i+1} for {plantID}")
        curr_day = datetime.now().day
        curr_mon = datetime.now().month
        curr_yr = datetime.now().year
        curr_hr = datetime.now().hour
        curr_min = datetime.now().minute

        if (curr_day, curr_mon, curr_yr, curr_hr, curr_min) == (date, month, year, hour, min):
            print(f"scheduleDaily : {name} matched for {plantID}")

            lastDate = calendar.monthrange(year,month)[1]

            date += 1
            if(date >= lastDate):
                date = 1
                month += 1
            if(month >= 13):
                month = 1
                year += 1

            db.reference(f'/{plantID}/CD/DD').set(date)
            db.reference(f'/{plantID}/CD/MM').set(month)
            db.reference(f'/{plantID}/CD/YY').set(year)            

            dailyReport_task_thread = threading.Thread(target=dailyReport_thread, args=(plantID, hour, min, date, month, year))
            dailyReport_task_thread.start()

            dailyReport_active_threads[plantID] = dailyReport_task_thread

            # min += 1
            # if (min == 60):
            #     hour += 1
            #     min = 0
            # break
        else:
            time.sleep(5)
        
        i += 1
    
    print(f"scheduleDaily : {name} completed for {plantID}")

def pushDailyReport(plantID, hour, min, date, month, year):
    data_dict = {}
    key_dict = {}
    keys = func_keys(plantID)
    for  key in keys:
        data = db.reference(f"{plantID}/Robot/{key}").order_by_key().limit_to_last(1).get()
        for item in data.items():
            try:
                data_dict[key] = dict(item[1])
                key_dict[key] = item[0]
            except Exception as e:
                print(f"Error updating data_dict for key '{key}': {e}")
                print("Problematic data:", item[1])

    robotsInstalled = len(data_dict.keys())
    otherError = ""
    networkError = ""

    statusON = []

    for key,val in data_dict.items(): 
        for itemKey, itemVal in val.items():
            if(itemKey == 'ST'):
                if(itemVal == 1):
                    statusON.append(key)
             

    for key,val in data_dict.items(): 
        for itemKey, itemVal in val.items():
            if(itemKey == "ER"):
                if(itemVal != 0):
                    otherError += "," + str(key)[1]

    for key,val in key_dict.items():
        timeCheck = datetime.strptime(val, '%d-%m-%y %H:%M:%S')
        current_time = datetime.now()
        time_difference = current_time - timeCheck
        minutes_difference = time_difference.total_seconds() / 60
        if(minutes_difference > 2):
            networkError += "," + str(key)[1]

    if(len(otherError) == 0):
        otherErrorLen = 0
    else:
        otherErrorLen = len(otherError[1:].split(','))

    if(len(networkError) == 0):
        networkErrorLen = 0
    else:
        networkErrorLen = len(networkError[1:].split(','))
    
    workingRobots = robotsInstalled - (networkErrorLen + otherErrorLen)

    print(robotsInstalled,networkError,otherError,workingRobots)

    timeKey = str(year)[2:] + "-" + str(month).zfill(2) + "-" + str(date).zfill(2) + " " + str(hour).zfill(2) + ":" + str(min).zfill(2)

    db.reference(f'/{plantID}/DR/{timeKey}/RI').set(robotsInstalled)
    db.reference(f'/{plantID}/DR/{timeKey}/WR').set(workingRobots)
    db.reference(f'/{plantID}/DR/{timeKey}/OE').set(otherError[1:])
    db.reference(f'/{plantID}/DR/{timeKey}/NE').set(networkError[1:])

def dailyReport_thread(plantID, hour, min, date, month, year):
    name = threading.current_thread().name
    print(f"dailyReport : {name} started for {plantID}")
    i = 0

    lastDate = calendar.monthrange(year,month)[1]

    # hour += 1
    # min += 55
    # if(min >= 60):
    #     min = 60 - min
    #     hour += 1
    # if(hour >= 24):
    #     hour = 0
    #     date += 1
    # if(date >= lastDate):
    #     date = 1
    #     month += 1
    # if(month >= 13):
    #     month = 1
    #     year += 1

    while not dailyReport_interrupt_events[plantID].is_set():
        print(f"dailyReport : {name} iteration no. {i+1} for {plantID}")
        curr_day = datetime.now().day
        curr_mon = datetime.now().month
        curr_yr = datetime.now().year
        curr_hr = datetime.now().hour
        curr_min = datetime.now().minute

        if (curr_day, curr_mon, curr_yr, curr_hr, curr_min) == (date, month, year, hour, min):
            print(f"dailyReport : {name} matched for {plantID}")
            pushDailyReport(plantID, hour, min, date, month, year)
            break
        else:
            time.sleep(5)
        
        i += 1
    
    print(f"dailyReport : {name} completed for {plantID}")

def funcForClearingAllTHeThreads(plantID):
    global scheduleOneTime_active_threads
    global scheduleOneTime_interrupt_events
    global scheduleDaily_active_threads
    global scheduleDaily_interrupt_events 
    global dailyReport_active_threads
    global dailyReport_interrupt_events

    if plantID in scheduleDaily_active_threads:
        scheduleDaily_interrupt_events[plantID].set()
        scheduleDaily_active_threads[plantID].join()

    if plantID in dailyReport_active_threads:
        dailyReport_interrupt_events[plantID].set()
        dailyReport_active_threads[plantID].join()

    if plantID in scheduleOneTime_active_threads:
        scheduleOneTime_interrupt_events[plantID].set()
        scheduleOneTime_active_threads[plantID].join()


def taskSchedulerForOneTimeOperation(plantID, hour, min, date, month, year):
    
    funcForClearingAllTHeThreads(plantID)
    
    scheduleOneTime_interrupt_events[plantID] = threading.Event()
    scheduleOneTime_interrupt_events[plantID].clear()
    dailyReport_interrupt_events[plantID] = threading.Event()
    dailyReport_interrupt_events[plantID].clear()

    scheduleOneTime_task_thread = threading.Thread(target=scheduleOneTime_thread, args=(plantID, hour, min, date, month, year))
    scheduleOneTime_task_thread.start()

    scheduleOneTime_active_threads[plantID] = scheduleOneTime_task_thread

def taskSchedulerForDailyOperations(plantID, hour, min, date, month, year):
    
    funcForClearingAllTHeThreads(plantID)

    scheduleDaily_interrupt_events[plantID] = threading.Event()
    scheduleDaily_interrupt_events[plantID].clear()
    dailyReport_interrupt_events[plantID] = threading.Event()
    dailyReport_interrupt_events[plantID].clear()

    scheduleDaily_task_thread = threading.Thread(target=scheduleDaily_thread, args=(plantID, hour, min, date, month, year))
    scheduleDaily_task_thread.start()

    scheduleDaily_active_threads[plantID] = scheduleDaily_task_thread


@app.route('/push-time/<plantID>',methods = ['PUT'])
def push_time(plantID):
    get_data = request.get_json()
    hour = int(get_data['hour'])
    min = int(get_data['minute'])
    date = int(get_data['date'])
    month = int(get_data['month'])
    year = int(get_data['year'])

    print(get_data)
    db.reference(f'/{plantID}/CD/H').set(str(hour).zfill(2))
    db.reference(f'/{plantID}/CD/M').set(str(min).zfill(2))
    db.reference(f'/{plantID}/CD/DD').set(str(date).zfill(2))
    db.reference(f'/{plantID}/CD/MM').set(str(month).zfill(2))
    db.reference(f'/{plantID}/CD/YY').set(str(year))
    db.reference(f'/{plantID}/CD/SF').set(0)
    db.reference(f'/{plantID}/CD/UID').set(254)

    if(get_data['scheduleDaily']):
        # db.reference(f'/{plantID}/CD/SD').set(1)
        taskSchedulerForDailyOperations(plantID, hour, min, date, month, year)
    
    else:
        # db.reference(f'/{plantID}/CD/SD').set(0)
        taskSchedulerForOneTimeOperation(plantID, hour, min, date, month, year)

    return "200"

@app.route('/stop-schedule-daily/<plantID>')
def stop_scheduled_daily(plantID):
    global scheduleDaily_active_threads
    global scheduleDaily_interrupt_events 
    global dailyReport_active_threads
    global dailyReport_interrupt_events

    if plantID in scheduleDaily_active_threads:
        scheduleDaily_interrupt_events[plantID].set()
        scheduleDaily_active_threads[plantID].join()

    if plantID in dailyReport_active_threads:
        dailyReport_interrupt_events[plantID].set()
        dailyReport_active_threads[plantID].join()

def func_keys(plantID):
    database_url = 'https://test-35f13-default-rtdb.firebaseio.com/'
    node_path = f"{plantID}/Robot.json?shallow=true"
    url = f'{database_url}{node_path}'
    response = requests.get(url)
    if response.status_code == 200:
        keys = list(response.json().keys())
    else:
        print("Error:", response.status_code, response.text)

    robot_list = {}
    idx = 0
    for key in keys :
        robot_list[idx] = key
        idx += 1

    return keys

@app.route('/get-daily-report/<plantID>')
def getDailyReport(plantID):
    data = db.reference(f"{plantID}/DR").order_by_key().limit_to_last(1).get()
    return jsonify(data)

@app.route('/get-monthly-report/<plantID>')
def getMonthlyReport(plantID):
    data = db.reference(f"/{plantID}/DR").get()
    return jsonify(data)

@app.route('/robot-list/<plantID>')
def get_robot_list(plantID):
    return jsonify(func_keys(plantID))


@app.route('/get-cd/<plantID>')
def get_cd(plantID):
    get_data = db.reference(f"/{plantID}/CD").get()
    return jsonify(get_data)


@app.route('/all-robot-data/<plantID>')
def index(plantID):
    data_dict = {}
    keys = func_keys(plantID)
    for  key in keys:
        data = db.reference(f"{plantID}/Robot/{key}").order_by_key().limit_to_last(1).get()
        data_dict[key] = data
        # for item in data.items():
        #     try:
        #         data_dict[key] = dict(item[1])
        #     except Exception as e:
        #         print(f"Error updating data_dict for key '{key}': {e}")
        #         print("Problematic data:", item[1])

    return json.dumps(data_dict)

@app.route('/all-robot-keys/<plantID>')
def robotKeys(plantID):
    data_dict = {}
    keys = func_keys(plantID)
    for  key in keys:
        data = db.reference(f"{plantID}/Robot/{key}").order_by_key().limit_to_last(1).get()
        for item in data.items():
            try:
                data_dict[key] = item[0]
            except Exception as e:
                print(f"Error updating data_dict for key '{key}': {e}")
                print("Problematic data:", item[1])

    return json.dumps(data_dict)

@app.route('/push-stop/<plantID>')
def stop_robot(plantID):
    db.reference(f'/{plantID}/CD/SF').set(1)
    db.reference(f'/{plantID}/CD/UID').set(254)
    return "200"

@app.route('/push-on/<plantID>/<robot_id>')
def on_particular_robot(plantID,robot_id):
    db.reference(f'/{plantID}/CD/UID').set(int(robot_id[-1]))
    return "200"
        
if(__name__ == "__main__"):
    # app.run(host = "192.168.1.9",debug=True)
    app.run(debug=True)