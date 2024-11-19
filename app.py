

from flask import Flask, render_template, jsonify
import os
import subprocess
import pymysql.cursors
import re
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/data')
def data():

    connection = pymysql.connect(host='localhost',
                                user='root',
                                password='',
                                db='SNMPData',
                                charset='utf8mb4',
                                cursorclass=pymysql.cursors.DictCursor)

    print("Connected!")

    count = 0
    sums = {
        'SystemUptime': 0,
        'NumberOfUsers': 0,
        'NumberOfProcesses': 0,
        'ProcessorLoad': 0,
        'InOctets': 0,
        'OutOctets': 0,
        'CPUUsage': 0,
        'MemoryUsage': 0,
        'DiskUsage': 0
    }

    command = "snmpwalk -v 2c -c public localhost"
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    if error:
        print(f"Error running snmpwalk: {error}")

    output = output.decode()

    lines = output.split("\n")

    result_dict = {}

    for line in lines:
        if "::" in line and " = " in line:
            key, value = line.split("::")[1].split(" = ",1)
            if key.strip() == 'sysUpTimeInstance':
                value = re.findall(r'\d+', value)[0]
            result_dict[key.strip()] = value.strip()

    cpu_usage = float(os.popen("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\([0-9.]*\)%* id.*/\\1/' | awk '{print 100 - $1}'").read())
    memory_usage = float(os.popen("free | grep Mem | awk '{print $3/$2 * 100.0}'").read())
    disk_usage = float(os.popen("df -h / | awk '$NF==\"/\"{printf \"%s\", $5}'").read().replace('%', ''))

    data = {
        'SystemDescription': result_dict.get('sysDescr.0', ''),

        'SystemUptime': int(re.findall(r'\d+', result_dict.get('sysUpTimeInstance', '0'))[0]),

        'SystemContact': result_dict.get('sysContact.0', ''),

        'SystemName': result_dict.get('sysName.0', ''),

        'SystemLocation': result_dict.get('sysLocation.0', ''),

        'NumberOfUsers': int(re.findall(r'\d+', result_dict.get('hrSystemNumUsers.0', '0'))[0]),

        'NumberOfProcesses': int(re.findall(r'\d+', result_dict.get('hrSystemProcesses.0', '0'))[0]),

        'ProcessorLoad': int(re.findall(r'\d+', result_dict.get('hrProcessorLoad', '0'))[0]),

        'InOctets': int(re.findall(r'\d+', result_dict.get('ifInOctets', '0'))[0]),

        'OutOctets': int(re.findall(r'\d+', result_dict.get('ifOutOctets', '0'))[0]),

        'IpAddresses': result_dict.get('ipAdEntAddr', ''),

        'CPUUsage': cpu_usage,

        'MemoryUsage': memory_usage,

        'DiskUsage': disk_usage
    }

    count += 1
    for key in sums.keys():
        sums[key] += data[key]

    averages = {key: sums[key] / count for key in sums.keys()}

    with connection.cursor() as cursor:
        sql = "INSERT INTO SystemInfo (Timestamp, SystemDescription, SystemUptime, SystemContact, SystemName, SystemLocation, NumberOfUsers, NumberOfProcesses, ProcessorLoad, InOctets, OutOctets, IpAddresses, CPUUsage, MemoryUsage, DiskUsage) VALUES (NOW(), %(SystemDescription)s, %(SystemUptime)s, %(SystemContact)s, %(SystemName)s, %(SystemLocation)s, %(NumberOfUsers)s, %(NumberOfProcesses)s, %(ProcessorLoad)s, %(InOctets)s, %(OutOctets)s, %(IpAddresses)s, %(CPUUsage)s, %(MemoryUsage)s, %(DiskUsage)s)"
        cursor.execute(sql, data)


        sql = "INSERT INTO SystemInfoAvg (Timestamp, SystemUptimeAvg, NumberOfUsersAvg, NumberOfProcessesAvg, ProcessorLoadAvg, InOctetsAvg, OutOctetsAvg, CPUUsageAvg, MemoryUsageAvg, DiskUsageAvg) VALUES (NOW(), %(SystemUptime)s, %(NumberOfUsers)s, %(NumberOfProcesses)s, %(ProcessorLoad)s, %(InOctets)s, %(OutOctets)s, %(CPUUsage)s, %(MemoryUsage)s, %(DiskUsage)s)"
        cursor.execute(sql, averages)

    print(data)
    print(averages)
    connection.commit()

    with connection.cursor() as cursor:
        sql = "SELECT * FROM SystemInfoAvg"
        cursor.execute(sql)
        data = cursor.fetchall()

    return jsonify(data)

if __name__ == 'main':
    app.run(debug=True)
