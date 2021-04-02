from datetime import datetime
import requests
import smtplib
import json
import pytz
import ssl
import os
import csv
import yaml
import time
import sched
import logging

# Read json files
def read_json(file):
    with open(file) as json_file:
        output_file = json.load(json_file)
    return output_file

# Read csv files
def read_csv(file):
    output_file = []
    with open(file) as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            output_file.append(row)
    return output_file


# Send email alert
def send_email_alert(provider,town,timestamp,zipcode,sender_email,sender_pw,recipient):

    try:
        # Establish server
        smtpserver = smtplib.SMTP("smtp.gmail.com", 587)
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.ehlo

        # Log in
        try:
            smtpserver.login(sender_email, sender_pw)
            logging.debug('Successful login')
        except Exception as e:
            logging.debug('Could not log in, check env vars')
            logging.error('Error: {}'.format(str(e)))

        # Construct message
        header = 'To:' + recipient + '\n' + 'From: ' + sender_email + '\n' + 'Subject: VACCSPOT: {} {} {} \n'.format(provider, town, zipcode)
        message = """\
\n
Vaccspot bot found an available vaccination slot!

Appointment(s) avaialbe at {a} {b} {c} as of {d}

Go to {a} website now!""".format(a=provider, b=town, c=zipcode, d=timestamp)
        payload = header + message

        # Send email
        try:
            smtpserver.sendmail(sender_email, recipient, payload)
        except Exception as e:
            logging.debug('Unable to send email, check security setting for email account')
            logging.error('Error: {}'.format(str(e)))
        
        smtpserver.close()
    
    except Exception as e:
        logging.debug('Could not establish SMTP server')
        logging.error('Error: {}'.format(str(e)))
   
    return


# Send Walgreens priority email alert
def wal_priority_email_alert(town,address,zipcode,timestamp,number_of_slots,sender_email,sender_pw,recipient,vaccine_types,app_types):
    provider = 'Walgreens'
    try:
        # Establish server
        smtpserver = smtplib.SMTP("smtp.gmail.com", 587)
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.ehlo

        # Log in
        try:
            smtpserver.login(sender_email, sender_pw)
            logging.debug('Successful login')
        except Exception as e:
            logging.debug('Could not log in, check env vars')
            logging.error('Error: {}'.format(str(e)))

        # Construct message
        header = 'To:' + recipient + '\n' + 'From: ' + sender_email + '\n' + 'Subject: PRIORITY VACCSPOT: {} {} {} \n'.format(provider,town,zipcode)
        message = """\
\n
Vaccspot bot found an available Pfizer vaccination slot!

There are {f} appointment(s) avaialbe at {a} {b} {c} {d} as of {e}

Current vaccines available: {g}

Current appointment types available: {h}

Go to {a} website now!""".format(a=provider, b=address, c=town, d=zipcode, e=timestamp, f=number_of_slots, g=vaccine_types, h=app_types)
        payload = header + message

        # Send email
        try:
            smtpserver.sendmail(sender_email, recipient, payload)
        except Exception as e:
            logging.debug('Unable to send email, check security setting for email account')
            logging.error('Error: {}'.format(str(e)))
        smtpserver.close()
    
    except Exception as e:
        logging.debug('Could not establish SMTP server')
        logging.error('Error: {}'.format(str(e)))
   
    return


# Check CVS for available appointments
def check_cvs():
    logging.debug('Called check_cvs')

    # Define parameters
    open_slots = []
    timestamp = datetime.now(pytz.timezone('America/New_York')).strftime("%m/%d/%y %H:%M:%S")
    url = 'https://www.cvs.com/immunizations/covid-19-vaccine.vaccine-status.CT.json?vaccineinfo'
    headers = {'referer': 'https://www.cvs.com/immunizations/covid-19-vaccine?icid=coronavirus-lp-nav-vaccine'}
    
    # Send request
    try:
        req = requests.get(url, headers=headers)
        logging.debug('Request successful')
    except Exception as e:
        logging.error('Error with CVS request:', e)
        return e
    
    # Parse response
    response_headers = req.headers
    response_json = req.json()

    # Added for debugging
    with open('walgreens_raw_response.json', 'w') as outfile:
        json.dump(response_json, outfile)

    for CVS in response_json['responsePayloadData']['data']['CT']:
        if CVS['status'] != 'Fully Booked':
            open_slots.append([CVS['city'], CVS['status'], timestamp])
    
    if not open_slots:
        logging.info('No available appointments found with CVS')
        print('No CVS appointments available at {}'.format(timestamp))
    else:
        logging.info('Available appointments found with CVS')

    # Added for debugging
    with open('cvs_open_slots.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        for row in open_slots:
            writer.writerow(row)
    
    return open_slots


# Check Walgreens for available appointments
def check_walgreens():
    logging.debug('Called check_walgreens')

    open_slots = []
    vaccine_types = {}
    timestamp = datetime.now(pytz.timezone('America/New_York')).strftime("%m/%d/%y %H:%M:%S")
    wal_url = 'https://www.vaccinespotter.org/api/v0/stores/CT/walgreens.json'
    
    try:
        req = requests.get(wal_url)
        logging.debug('Request successful')
    except Exception as e:
        print('Error with request:', e)
        return e
    
    response_json = req.json()

    # Added for debugging
    with open('walgreens_raw_response.json', 'w') as outfile:
        json.dump(response_json, outfile)

    for wal in response_json:
        if wal['appointments']:

            pfizer = False
            
            town = wal['city']
            address = wal['address']
            zipcode = wal['postal_code']

            number_of_slots = 0
            vaccine_types = set()
            app_types = set()

            for app in wal['appointments']:
                number_of_slots += 1
                for vaccine_type in app['vaccine_types']:
                    if vaccine_type.lower() == 'pfizer':
                        pfizer = True
                    vaccine_types.add(vaccine_type)
                for app_type in app['appointment_types']:
                    app_types.add(app_type)

            vaccine_types = list(vaccine_types)
            app_types = list(app_types)
            open_slots.append([pfizer, town, address, zipcode, timestamp, number_of_slots, vaccine_types, app_types])

    if not open_slots:
        logging.info('No available appointments at Walgreens')
        print('No Walgreens appointments available at {}'.format(timestamp))
    else:
        logging.info('Available appointments found at Walgreens')

    # Added for debugging
    with open('walgreens_open_slots.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        for row in open_slots:
            writer.writerow(row)

    return open_slots


def triage_cvs(cvs_priority_towns, open_slots):
    priority_slots = []
    other_slots = []
    for slot in open_slots:
        if slot[0] in cvs_priority_towns:
            priority_slots.append(slot)
        else:
            other_slots.append(slot)

    # Added for debugging
    with open('cvs_priority.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        for row in priority_slots:
            writer.writerow(row)

    return priority_slots, other_slots


def triage_walgreens(open_slots):
    priority_slots = []
    other_slots = []
    for slot in open_slots:
        if slot[0] == True:
            priority_slots.append(slot)
        else:
            other_slots.append(slot)

    # Added for debugging
    with open('walgreens_priority.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        for row in priority_slots:
            writer.writerow(row)

    return priority_slots, other_slots


def handle_cvs_cache(cvs_priority_cache, cvs_priority_slots):
    
    # Need to add logging
    changed_slots = []
    index = 2
    
    if cvs_priority_cache:
        for slot in cvs_priority_slots:

            # Cache can't include timestamp or it will always be different
            temp_slot = slot[:index] + slot[index+1:]

            if temp_slot not in cvs_priority_cache: # this will always be true if timestamp included
                cvs_priority_cache.append(temp_slot)
                changed_slots.append(slot)
    else:
        for slot in cvs_priority_slots:

            # Cache can't include timestamp or it will always be different
            temp_slot = slot[:index] + slot[index+1:]

            cvs_priority_cache.append(temp_slot)
            changed_slots.append(slot)

    with open('cvs_high_priority_cache.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        for row in cvs_priority_slots:
            writer.writerow(row)

    return changed_slots


def handle_walgreens_cache(walgreens_priority_cache, wal_priority_slots):
    
    # Need to add logging
    changed_slots = []

    if walgreens_priority_cache:
        for slot in wal_priority_slots:
            key = slot[2] + slot[1]
            index = 2

            # Cache can't include timestamp or it will always be different
            temp_slot = slot[:index] + slot[index+1:]
            
            if key not in walgreens_priority_cache.keys():
                changed_slots.append(slot)
                walgreens_priority_cache[key] = temp_slot
            
            elif walgreens_priority_cache[key] != temp_slot:
                changed_slots.append(slot)
                walgreens_priority_cache[key] = temp_slot
    
    else:
        for slot in wal_priority_slots:
            key = slot[2] + slot[1]
            index = 2

            # Cache can't include timestamp or it will always be different
            temp_slot = slot[:index] + slot[index+1:]
            
            changed_slots.append(slot)
            walgreens_priority_cache[key] = temp_slot

    with open('walgreens_high_priority_cache.json', 'w') as outfile:
        json.dump(walgreens_priority_cache, outfile)

    return changed_slots


def main():
    # Configure basic logging
    logging.basicConfig(
        filename='./logs/log.log', 
        format='%(asctime)s.%(msecs)03d %(levelname)s {%(module)s} [%(funcName)s] %(message)s', 
        datefmt='%Y-%m-%d,%H:%M:%S', 
        level=logging.INFO
        )

    # Update daily
    # cvs_priority_details = {
    #     0: {
    #     'town': 'WINDSOR',
    #     'address': '484 WINDSOR AVE',
    #     'zipcode': '06095'
    #     },
    #     1: {
    #     'town': 'WINDSOR',
    #     'address': '219 BROAD ST',
    #     'zipcode': '06095'
    #     },
    #     2: {
    #     'town': 'WINDSOR LOCKS',
    #     'address': '90 MAIN ST',
    #     'zipcode': '06096'
    #     },
    #     3: {
    #     'town': 'COLCHESTER',
    #     'address': '119 SOUTH MAIN ST',
    #     'zipcode': '06415'
    #     },
    #     4: {
    #     'town': 'ANSONIA',
    #     'address': '24-26 PERSHING DR',
    #     'zipcode': '06401'
    #     },
    #     5: {
    #     'town': 'ENFIELD',
    #     'address': '875 ENFIELD ST',
    #     'zipcode': '06082'
    #     },
    #     6: {
    #     'town': 'WILLIMANTIC',
    #     'address': '1200 MAIN ST',
    #     'zipcode': '06226'
    #     }
    # }

    # Update daily
    cvs_priority_towns = ['MERIDEN','PLAINVILLE','BLOOMFIELD','WINDSOR','WINDSOR LOCKS','COLCHESTER','ANSONIA','ENFIELD','WILLIMANTIC']

    # Read in config info
    info = yaml.safe_load(open('info.yml'))
    sender_email = info['alert']['sender']
    sender_pw = os.getenv('VACCSPOT_PASS')
    recipient = info['alert']['target']

    # Fetch CVS cache if it exists
    if os.path.isfile('cvs_high_priority_cache.csv'):
        cvs_cache = read_csv('cvs_high_priority_cache.csv')
    else:
        cvs_cache = []

    # Fetch Walgreens cache if it exists
    if os.path.isfile('walgreens_high_priority_cache.json'):
        walgreens_cache = read_json('walgreens_high_priority_cache.json')
    else:
        walgreens_cache = {}

    # Get zip codes
    zips = read_json('zips.json')

    # Check appointments from CVS website
    cvs_openings = check_cvs()
    cvs_priority_slots, cvs_other_slots = triage_cvs(cvs_priority_towns, cvs_openings)
    cvs_changed_slots = handle_cvs_cache(cvs_cache, cvs_priority_slots)
    
    # If changed since last time around
    if cvs_changed_slots:
        for slot in cvs_changed_slots:
            # Get zip code if town is dict key
            zipcode = zips.get(slot[0], 'Not Found')
            
            send_email_alert('CVS',slot[0],slot[2],zipcode,sender_email,sender_pw,recipient)

    for slot in cvs_other_slots:
        pass
        # # Get zip code if town is dict key
        # zipcode = zips.get(slot[0], 'Not Found')
        
        # send_email_alert('CVS',slot[0],slot[2],zipcode,sender_email,sender_pw,recipient)

    # Check Walgreens appointments from Vaccine Spotter
    wal_openings = check_walgreens()
    wal_priority_slots, wal_other_slots = triage_walgreens(wal_openings)
    wal_changed_slots = handle_walgreens_cache(walgreens_cache, wal_priority_slots)

    # If changed since last time around
    if wal_changed_slots:
        for slot in wal_changed_slots:
            wal_priority_email_alert(slot[1],slot[2],slot[3],slot[4],slot[5],sender_email,sender_pw,recipient,slot[6],slot[7])
    for slot in wal_other_slots:
        wal_priority_email_alert(slot[1],slot[2],slot[3],slot[4],slot[5],sender_email,sender_pw,recipient,slot[6],slot[7])


def schedule_checks(sc):
    main()
    s.enter(60*5, 1, schedule_checks, (sc,)) # Run every 5 minutes


# Create scheduler
s = sched.scheduler(time.time, time.sleep)

print('Starting now...')
s.enter(0, 1, schedule_checks, (s,))
s.run()