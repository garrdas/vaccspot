from datetime import datetime
import requests
import json
import pytz
import ssl
import os
import yaml
import time
import sched
import logging

# Get dictionary of zip codes for towns
def get_zips():
    with open('zips.json') as json_file:
        zips = json.load(json_file)
    return zips


# Send email alert
def send_email_alert(provider,town,timestamp,code,link,zipcode,sender_email,sender_pw,recipient):

    # Establish server
    try:
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
            logging.error('Error:', e)

        # Construct message
        header = 'To:' + recipient + '\n' + 'From: ' + sender_email + '\n' + 'Subject: VACCSPOT: {a} {b} {c} \n'.format(a=provider, b=town, c=zipcode)
        message = """\
        \n
        Vaccspot bot found an available vaccination slot!

        Appointment(s) avaialbe at {a} {b} {f} as of {c}

        Go to {a} website now!

        CODE IN: {d}
        Link: {e}""".format(a=provider, b=town, c=timestamp, d='testing-code', e=link, f=zipcode)
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
        logging.error('Error: ', e)
   
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
    for CVS in response_json['responsePayloadData']['data']['CT']:
        if CVS['status'] != 'Fully Booked':
            open_slots.append([CVS['city'], CVS['status'], timestamp])
    
    if not open_slots:
        logging.info('No available appointments found with CVS')
        print('No CVS appointments available.')
    else:
        logging.info('Available appointments found with CVS')
    
    return open_slots


def main():
    # Configure basic logging
    logging.basicConfig(
        filename='./logs/log.log', 
        format='%(asctime)s.%(msecs)03d %(levelname)s {%(module)s} [%(funcName)s] %(message)s', 
        datefmt='%Y-%m-%d,%H:%M:%S', 
        level=logging.INFO
        )

    # Create scheduler
    s = sched.scheduler(time.time, time.sleep)

    # Read in config info
    info = yaml.safe_load(open('info.yml'))
    sender_email = info['alert']['sender']
    sender_pw = os.getenv('VACCSPOT_PASS')
    recipient = info['alert']['target']
    code = info['alert']['codein']

    # Provider website links
    links = {
        'CVS':'https://www.cvs.com/vaccine/intake/store/cvd-store-select/first-dose-select',
        'Walgreens':'https://www.walgreens.com/findcare/vaccination/covid-19/location-screening'
    }

    # Get zip codes
    zips = get_zips()

    cvs_openings = check_cvs()
    for slot in cvs_openings:

        # Get zip code if town is dict key
        zipcode = zips.get([slot[0]], 'Not Found')

        send_email_alert('CVS',slot[0],slot[2],code,links['CVS'],zipcode,sender_email,sender_pw,recipient)


def schedule_checks(sc):
    main()
    s.enter(60, 1, schedule_checks, (sc,))

print('Starting now...')
s.enter(60, 1, schedule_checks, (s,))
s.run()