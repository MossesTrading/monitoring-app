import boto3
import psutil
import mysql.connector
from datetime import datetime
import os
from fastapi import FastAPI

app = FastAPI()

# AWS Setup
ses_client = boto3.client('ses', region_name='us-east-1')  # Ubah region jika perlu
ec2_client = boto3.client('ec2', region_name='eu-west-2')
rds_client = boto3.client('rds', region_name='eu-west-2')

# Fungsi untuk mendapatkan data jaringan EC2
def get_network_data(instance_id):
    response = ec2_client.describe_instance_status(InstanceIds=[instance_id])
    network_data = response['InstanceStatuses'][0]['SystemStatus']['Network']
    return f"Data In: {network_data['Inbound']} | Data Out: {network_data['Outbound']}"

# Fungsi untuk mendapatkan informasi proses
def get_running_processes():
    running_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'status']):
        running_processes.append(f"PID: {proc.info['pid']} | Name: {proc.info['name']} | Status: {proc.info['status']}")
    return running_processes

# Fungsi untuk mendapatkan status EC2
def get_ec2_status():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    storage = psutil.disk_usage('/')
    total_ram = round(memory.total / (1024 ** 3), 2)  # Convert bytes to GB
    total_cpu = psutil.cpu_count(logical=False)  # Number of physical CPUs
    disk_usage = f"{storage.used / (1024 ** 3):.2f} GB of {storage.total / (1024 ** 3):.2f} GB used"
    
    return {
        "CPU Usage": f"{cpu_usage}%",
        "RAM Usage": f"{memory.percent}%",
        "Storage Usage": f"{storage.percent}%",
        "Total RAM": f"{total_ram} GB",
        "Total CPU": f"{total_cpu} vCPUs",
        "Disk Usage": disk_usage
    }

# Fungsi untuk mendapatkan status MySQL
def get_mysql_status():
    conn = mysql.connector.connect(
        host="mossestrading.cf4ye0uykuul.eu-west-2.rds.amazonaws.com",
        user="admin",
        password="novrizal161192",
        database="stock_news_db"
    )
    cursor = conn.cursor()
    cursor.execute("SHOW TABLE STATUS")
    tables_info = cursor.fetchall()
    table_info = []
    total_db_size = 0
    for table in tables_info:
        table_name = table[0]
        data_size = table[6]
        total_db_size += data_size
        last_update = table[12] if table[12] else "No update"
        data_age = (datetime.now() - last_update).days if last_update != "No update" else 0
        table_info.append(f"Table: {table_name} | Last Update: {last_update} | Data Age (days): {data_age} | Size: {data_size / (1024*1024):.2f} MB")
    
    total_db_size_gb = total_db_size / (1024 * 1024 * 1024)
    return table_info, total_db_size_gb

# Fungsi untuk estimasi tagihan AWS
def get_aws_bill():
    cost_client = boto3.client('ce', region_name='us-east-1')
    response = cost_client.get_cost_and_usage(
        TimePeriod={'Start': '2025-04-01', 'End': '2025-04-30'},
        Granularity='DAILY',
        Metrics=['UnblendedCost']
    )
    cost = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
    return f"${cost}"

# Fungsi untuk mendapatkan daftar file di EC2
def get_ec2_files(directory='/'):
    excluded_dirs = ['/proc', '/sys', '/dev', '/mnt', '/run', '/var', '/tmp']
    file_list = []
    for root, dirs, files in os.walk(directory):
        if any(root.startswith(excluded_dir) for excluded_dir in excluded_dirs):
            continue
        for file in files:
            if file.endswith('.py'):
                file_list.append(os.path.join(root, file))
    return file_list

# Endpoint untuk laporan
@app.get("/generate_report/")
def generate_report():
    instance_id = 'i-056922892323ce753'
    network_data = get_network_data(instance_id)
    running_processes = get_running_processes()
    ec2_status = get_ec2_status()
    mysql_status, total_db_size = get_mysql_status()
    aws_bill = get_aws_bill()
    ec2_files = get_ec2_files()

    # Susun laporan
    report = {
        "EC2 Network Data": network_data,
        "EC2 Status": ec2_status,
        "Running Processes": running_processes,
        "MySQL Database Status": mysql_status,
        "Total Database Usage (GB)": total_db_size,
        "AWS Bill Estimation": aws_bill,
        "Files in EC2": ec2_files
    }
    return report

