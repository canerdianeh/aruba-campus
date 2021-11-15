#!/usr/bin/python3

# ArubaOS 8 API call framework
# (c) 2021 Ian Beyer, Aruba Networks <canerdian@hpe.com>
# This code is provided as-is with no warranties. Use at your own risk. 

import requests
import argparse
import json
import warnings
import sys
import xmltodict
import yaml
from yaml.loader import FullLoader
from pathlib import Path

# Set defaults

aosDevice = "1.2.3.4"
username = "admin"
password = "password"

# Parse Command Line Arguments
# 
# Credentials file is YAML - See sample file.
# Specifying any individual parameter found in the credentials file will override the value in the credentials file. 
# HTTPS verification is off by default unless -v is specified.

cli=argparse.ArgumentParser(description='Basic Aruba AOS8 API Framework')

cli.add_argument("-c", "--credentials", required=False, help='Credentials File (in YAML format', default='credentials.yaml')
cli.add_argument("-t", "--target", required=False, help='Target IP Address')
cli.add_argument("-u", "--username", required=False, help='Target Username')
cli.add_argument("-p", "--password", required=False, help='Target Password')
cli.add_argument("-o", "--output", required=False, help='Output File', default="output.csv")
cli.add_argument("-v", "--verify", required=False, help='Verify HTTPS', default=False, action='store_true')
cli.add_argument("-P", "--port", required=False, help="Target Port", default="4343")
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

#	print(sessionToken)
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
		#print(response.content)
		returnData = xmltodict.parse(response.content)['my_xml_tag3xxx']
	elif datatype == 'Text' :
		# Returns an array
		returnData =response.json()['_data']
	return returnData


def getSwitches():
	switches=showCmd('switches', 'JSON')
	conductors=[]
	controllers=[]
	for device in switches['All Switches']:
		if device['Type'] == 'master' or device['Type'] == 'conductor':
			conductors.append(device)
			#print('Found Mobility Conductor '+device['Model']+ ' with IP address '+device['IP Address'])
		else:
			controllers.append(device)
			#print('Found Mobility Controller '+device['Model']+ ' with IP address '+device['IP Address'])
	return(conductors, controllers)


# Get list of Mobility Conductors and Mobility Controllers in the environment. 

mcrList, mdList = getSwitches()


# This is where you do stuff. 



## Log out and remove session


response = session.get(baseurl+"api/logout", verify=False)
jsonData = response.json()['_global_result']

if response.status_code == 200 :

	#remove 
	token = jsonData['UIDARUBA']
	del sessionToken
	#print("Logout successful. Token deleted.")
else :
	del sessionToken
	sys.exit("Logout failed:")