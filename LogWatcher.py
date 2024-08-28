import re
import os
import time
import csv
import json
import requests
from datetime import datetime, timedelta
import creds

# Define pattern to detect errors in the log files
ERROR_PATTERN = re.compile(r'ERROR|error|Error')

# Buffer to store errors
error_buffer = []

# Time interval to send emails
EMAIL_SEND_INTERVAL = timedelta(minutes=10)

# Last email send time
last_email_time = datetime.now()

def read_logfile_paths_from_csv(csv_file):
    log_files = []
    with open(csv_file, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            main_path = row['MainPath'].strip().strip('"')
            file_path = row['FilePath'].strip().strip('"')
            full_path = os.path.join(main_path, file_path)
            full_path = os.path.normpath(full_path)
            log_files.append(full_path)
    return log_files

def create_json_object(log_file, error_message):
    error_data = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'log_file': log_file,
        'error_message': error_message.strip()
    }
    return error_data

def send_email_alert(errors):
    if not errors:
        return

    body_content = "<html lang='en'><body><h1>ERRORS</h1><ul>"
    for error in errors:
        body_content += f"<li>{error['date']} - {error['log_file']}: {error['error_message']}</li>"
    body_content += "</ul></body></html>"

    email_content = {
        "token": creds.token,
        "commaSeperatedRecipients": creds.receiver_email,
        "from": creds.sender_email,
        "subject": "Error Opencom task",
        "body": body_content,
        "emailId": "",
        "Attachments": []
    }

    response = requests.post(creds.email_api_url, json=email_content)
    if response.status_code == 200:
        print("Email alert sent successfully.")
    else:
        print(f"Failed to send email alert. Status code: {response.status_code}")

def monitor_logs(log_files):
    global last_email_time

    file_pointers = {log_file: open(log_file, 'r') for log_file in log_files}
    try:
        while True:
            for log_file, file_pointer in file_pointers.items():
                where = file_pointer.tell()
                line = file_pointer.readline()
                if not line:
                    file_pointer.seek(where)
                    continue
                if ERROR_PATTERN.search(line):
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    if current_date in line:
                        error_json = create_json_object(log_file, line)
                        print(json.dumps(error_json, indent=4))
                        error_buffer.append(error_json)
            
            current_time = datetime.now()
            if current_time - last_email_time >= EMAIL_SEND_INTERVAL:
                send_email_alert(error_buffer)
                error_buffer.clear()
                last_email_time = current_time

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping log monitoring.")
    finally:
        for file_pointer in file_pointers.values():
            file_pointer.close()
        # Send remaining errors in the buffer before exiting
        send_email_alert(error_buffer)

if __name__ == '__main__':
    log_files = read_logfile_paths_from_csv('LogFiler.csv')
    monitor_logs(log_files)