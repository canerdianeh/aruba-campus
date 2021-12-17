#!/usr/bin/python3

# ArubaOS 8 AP BSS Table CSV output via API call
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

aosDevice = None
username = None
password = None

# Parse Command Line Arguments
# 
# Credentials file is YAML - See sample file.
# Specifying any individual parameter found in the credentials file will override the value in the credentials file. 
# HTTPS verification is off by default unless -v is specified.

cli=argparse.ArgumentParser(description='Query AOS 8 Mobility Conductor and attached controllers for detailed BSS Tables and output to CSV.')

cli.add_argument("-c", "--credentials", required=False, help='Credentials File (in YAML format', default='credentials.yaml')
cli.add_argument("-t", "--target", required=False, help='Target IP Address')
cli.add_argument("-u", "--username", required=False, help='Target Username')
cli.add_argument("-p", "--password", required=False, help='Target Password')
cli.add_argument("-o", "--output", required=False, help='Output File', default="ap-lldp-neighbors.csv")
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

# Check if username was specified on CLI. Overrides values in credentials file. 

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

print("Getting Switch List...")
mcrList, mdList = getSwitches()

print("Found the following Controllers")
for md in mdList:
	print(md['Model']+" at "+md['IP Address'])

#Iterate through MDs and gather data
neighbors=[]

capflags={
'R':'Router',
'B':'Bridge',
'A':'Access Point',
'P':'Phone',
'O':'Other'
}

timestamp=datetime.datetime.now()

with open(outfile, 'w') as csvfile:
	write=csv.writer(csvfile)
	loop=0

	# Create Sheet Title

	write.writerow(["AP Neighbor Table"])
	write.writerow([timestamp.strftime("%m-%d-%Y %H:%M:%S")])
	write.writerow([""])
	
	for md in mdList:
		print("logging into controller at "+md['IP Address']+"...", end='')
		mdsession = requests.Session()
		mdbaseurl = "https://"+md['IP Address']+":"+port+"/"+api+"/"
		mdloginparams = {'username': username, 'password' : password}
		mdresponse = mdsession.get(mdbaseurl+"api/login", params = mdloginparams, headers=headers, data=payload, verify = httpsVerify)
		mdjsonData = mdresponse.json()['_global_result']

		if mdresponse.status_code == 200 :

			mdSessionToken = mdjsonData['UIDARUBA']
			print("Success")
		else :
			print("Failed!")
			sys.exit("MD Login Failed on "+md['IP Address'])
 		
		mdReqParams = {
			'UIDARUBA':mdSessionToken,
			'command':'show ap lldp neighbors'
			}

		showresponse = mdsession.get(mdbaseurl+"configuration/showcommand", params = mdReqParams, headers=headers, data=payload, verify = httpsVerify)
		neighborlist=showresponse.json()

		# Get list of data fields from the returned list
		fields=neighborlist['_meta']
		 
		# Add new fields for parsed Data
		#fields.insert(5,"PHY")
		fields.append("Controller")

		 # Add fields for expanding flags
		for flag in capflags.keys():
			fields.append(capflags[flag])

		if loop == 0:
			write.writerow(fields)
		loop += 1
		# Iterate through the list of BSS
		records = 0
		for nei in neighborlist["AP LLDP Neighbors (Updated every 60 seconds)"]:
			nei['Controller']=md['IP Address'] 

			# Bust apart the flags into their own fields 
			for flag in capflags.keys():

			# Set field to None so that it exists in the dict
				nei[capflags[flag]]=None
			   
			# Check to see if the flags field contains data
				if nei['Capabilities'] != None :

					if flag in nei['Capabilities'] :
						nei[capflags[flag]]="X"
			   
			datarow=[]

			# Iterate through the list of fields used to create the header row and append each one
			for f in fields:
				datarow.append(nei[f])

			# Add it to grand master dict that can be used for other purposes
			neighbors.append(datarow)
			# Put it in the CSV 
			write.writerow(datarow)
			records+=1
		#Move on to the next AP
		print(str(records)+" Entries")
	# Close the file handle
	csvfile.close()











	#print("Logging out of controller "+md['IP Address'])
	logoutresponse = mdsession.get(mdbaseurl+"api/logout", verify=False)
	jsonData = logoutresponse.json()['_global_result']

	if response.status_code == 200 :

		#remove 
		token = jsonData['UIDARUBA']
		del mdSessionToken
		#print("Logout successful. Token deleted.")
	else :
		del mdSessionToken
		sys.exit("Logout failed from "+md['IP Address']+":")	



## Log out of MCR and remove session


response = session.get(baseurl+"api/logout", verify=False)
jsonData = response.json()['_global_result']

if response.status_code == 200 :

	#remove 
	token = jsonData['UIDARUBA']
	del sessionToken
	print("MCR Logout successful. Token deleted.")
else :
	del sessionToken
	sys.exit("Logout failed:")