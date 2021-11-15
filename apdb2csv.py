#!/usr/bin/python3

# ArubaOS 8 AP Database to CSV output via API call
# (c) 2021 Ian Beyer, Aruba Networks <canerdian@hpe.com>
# This code is provided as-is with no warranties. Use at your own risk. 

import requests
import argparse
import json
import csv
import sys
import warnings
import sys
import xmltodict
import datetime
import yaml
from yaml.loader import FullLoader
from pathlib import Path


# Set output file name

aosDevice = "1.2.3.4"
username = "admin"
password = "password"

# Parse Command Line Arguments
# 
# Credentials file is YAML - See sample file.
# Specifying any individual parameter found in the credentials file will override the value in the credentials file. 
# HTTPS verification is off by default unless -v is specified.

cli=argparse.ArgumentParser(description='Query AOS 8 controller for detailed AP database and output to CSV.')

cli.add_argument("-c", "--credentials", required=False, help='Credentials File (in YAML format', default='credentials.yaml')
cli.add_argument("-t", "--target", required=False, help='Target IP Address')
cli.add_argument("-u", "--username", required=False, help='Target Username')
cli.add_argument("-p", "--password", required=False, help='Target Password')
cli.add_argument("-o", "--output", required=False, help='Output File', default="apdb.csv")
cli.add_argument("-v", "--verify", required=False, help='Verify HTTPS', default=False, action='store_true')
cli.add_argument("-P", "--port", required=False, help="Target Port (Default is 4343)", default="4343")
cli.add_argument("-a", "--api", required=False, help="API Version (default is v1)", default="v1")

args = vars(cli.parse_args())

# print(args)

# First, Check if a credentials file was specified and set variables found therein.  

credsfile = args['credentials']
credspath = Path(credsfile)
if credspath.is_file() == False:
    print("Credentials file "+credsfile+" not found. Ignoring.")
else:
    with open(credsfile, 'r') as creds:
        target=yaml.load(creds, Loader=FullLoader)
    creds.close()

    aosDevice=target['aosDevice']
    username=target['username']
    password=target['password']
    httpsVerify=target['httpsVerify']

# Check if username was specified on CLI. Override value in credentials file. 
if args['username'] != None :
    username=args['username']

# Check if password was specified on CLI.
if args['password'] != None :
    password=args['password']

# Check if target was specified on CLI.
if args['target'] != None :
    aosDevice=args['target']

# Default Values are set in the argopts. 
httpsVerify=args['verify']
outfile=args['output']
port=args['port']
api=args['api']

#Set things up


if httpsVerify == False :
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

baseurl = "https://"+aosDevice+":"+port+"/"+api+"/"


headers = {}
payload = ""
cookies = ""

session=requests.Session()
## Log in and get session token

loginparams = {'username': username, 'password' : password}
response = session.get(baseurl+"api/login", params = loginparams, headers=headers, data=payload, verify = httpsVerify)
jsonData = response.json()['_global_result']

if response.status_code == 200 :

    #print(jsonData['status_str'])
    sessionToken = jsonData['UIDARUBA']

#    print(sessionToken)
else :
    sys.exit("Login Failed")

reqParams = {'UIDARUBA':sessionToken}

def showCmd(command, datatype):
    showParams = {
        'command' : 'show '+command,
        'UIDARUBA':sessionToken
            }
    response = session.get(baseurl+"configuration/showcommand", params = showParams, headers=headers, data=payload, verify = httpsVerify)
    #print(response.url)
    #print(response.text)
    if datatype == 'JSON' :
        #Returns JSON
        returnData=response.json()
    elif datatype == 'XML' :
        # Returns XML as a dict
        print(response.content)
        returnData = xmltodict.parse(response.content)['my_xml_tag3xxx']
    elif datatype == 'Text' :
        # Returns an array
        returnData =response.json()['_data']
    return returnData

apdb=showCmd('ap database long', 'JSON')

# This is the list of status flags in show ap database long

apflags=['1','1+','1-','2','B','C','D','E','F','G','I','J','L','M','N','P','R','R-','S','U','X','Y','c','e','f','i','o','s','u','z','p','4']

# Create file handle and open for write. 
with open(outfile, 'w') as csvfile:
 write=csv.writer(csvfile)
 
 # Get list of data fields from the returned list
 fields=apdb['_meta']
 
 # Add new fields for parsed Data
 fields.insert(5,"Uptime")
 fields.insert(6,"Uptime_Seconds")
 
 # Add fields for expanding flags
 for flag in apflags:
  fields.append("Flag_"+flag)
 write.writerow(fields)
 
 # Iterate through the list of APs
 for ap in apdb["AP Database"]:
 
   # Parse Status field into status, uptime, and uptime in seconds
   utseconds=0
   ap['Uptime']=""
   ap['Uptime_Seconds']=""
   
   # Split the status field on a space - if anything other than "Up", it will only contain one element, first element is status description. 
   status=ap['Status'].split(' ')
   ap['Status']=status[0]

   # Additional processing of the status field if the AP is up as it will report uptime in human-readable form in the second half of the Status field we just split
   if len(status)>1:
    ap['Uptime']=status[1]

    #Split the Uptime field into each time field and strip off the training character, multiply by the requisite number of seconds an tally it up. 
    timefields=status[1].split(':')
    
    if len(timefields)>3 :
        days=int(timefields.pop(0)[0:-1])
        utseconds+=days*86400
    if len(timefields)>2 :
        hours=int(timefields.pop(0)[0:-1])
        utseconds+=hours*3600
    if len(timefields)>1 :
        minutes=int(timefields.pop(0)[0:-1])
        utseconds+=minutes*60
    if len(timefields)>0 :
        seconds=int(timefields.pop(0)[0:-1])
        utseconds+=seconds
    ap['Uptime_Seconds']=utseconds

   # Bust apart the flags into their own fields 
   for flag in apflags:

    # Set field to None so that it exists in the dict
    ap["Flag_"+flag]=None
    
    # Check to see if the flags field contains data
    if ap['Flags'] != None :

     # Iterate through the list of possible flags and mark that field with an X if present
     if flag in ap['Flags'] :
      ap["Flag_"+flag]="X"
   
   # Start assembling the row to write out to the CSV, and maintain order and tranquility. 
   datarow=[]

   # Iterate through the list of fields used to create the header row and append each one
   for f in fields:
    datarow.append(ap[f])

   # Put it in the CSV 
   write.writerow(datarow)

   #Move on to the next AP

# Close the file handle
csvfile.close()

## Log out and remove session

response = session.get(baseurl+"api/logout", verify=False)
jsonData = response.json()['_global_result']

if response.status_code == 200 :

    #remove 
    token = jsonData['UIDARUBA']
    del sessionToken

else :
    del sessionToken
    sys.exit("Logout failed:")