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
defaultfile="ap-bss-table"
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
cli.add_argument("-o", "--output", required=False, help='Output File', default=defaultfile)
cli.add_argument("-j", "--json", required=False, help='Output to JSON', default=False, action="store_true")
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

outjson=False 
if args['json']: outjson=True

outfile=args['output']
port=args['port']
api=args['api']

#Set things up


if httpsVerify == False :
	warnings.filterwarnings('ignore', message='Unverified HTTPS request')

if aosDevice == None:
	exit()
if username == None:
	exit()
if password == None:
	exit()

baseurl = "https://"+aosDevice+":"+port+"/"+api+"/"


headers = {}
payload = ""
cookies = ""

session=requests.Session()

## Log in to Mobility Condusctor and get session token

loginparams = {'username': username, 'password' : password}
response = session.get(baseurl+"api/login", params = loginparams, headers=headers, data=payload, verify = httpsVerify)
jsonData = response.json()['_global_result']

if response.status_code == 200 :

	#print(jsonData['status_str'])
	sessionToken = jsonData['UIDARUBA']

#	print(sessionToken)
else :
	sys.exit("Conductor Login Failed - Could not get session token")

reqParams = {'UIDARUBA':sessionToken}


## Define Functions

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
		if device['Type'] == 'MD':
			controllers.append(device)
			#print('Found Mobility Conductor '+device['Model']+ ' with IP address '+device['IP Address'])
		else:
			conductors.append(device)
			#print('Found Mobility Controller '+device['Model']+ ' with IP address '+device['IP Address'])
	return(conductors, controllers)


# Get list of Mobility Conductors and Mobility Controllers in the environment. 

#print("Getting Switch List...")
mcrList, mdList = getSwitches()

mcrHostname=aosDevice

for mcr in mcrList:
	if mcr['IP Address'] == aosDevice :
		mcrHostname = mcr['Name']

print("Found the following Controllers on Mobility Conductor "+mcrHostname)
for md in mdList:
	print(md['Model']+" "+md['Name']+" at "+md['IP Address'])

#Iterate through MDs and gather data
bsslist=[]

bssflags={
'K':'802.11k',
'W':'802.11w',
'3':'WPA3',
'O':'OWE Transition OWE BSS',
'o':'OWE Transition open BSS',
'M':'WPA3-SAE mixed mode',
'I':'Imminent VAP Down',
'D':'VLAN Discovered'
}

timestamp=datetime.datetime.now()

#If using default output filename, send to timestamped file in output folder, otherwise go with what the user specified. 

if outfile == defaultfile :
	csvfilename="./output/"+mcrHostname+"_"+timestamp.strftime("%Y%m%d_%H%M")+"_"+outfile+'.csv'
	#jsonfilename="./output/"+mcrHostname+"_"+timestamp.strftime("%Y%m%d_%H%M")+"_"+outfile+'.json'
else:
	csvfilename = outfile+'.csv'
	#jsonfilename = outfile+'.json'

#Reset entry counter

totalEntries=0

with open(csvfilename, 'w') as csvfile:
	write=csv.writer(csvfile)
	loop=0

	# Create Sheet Title

	write.writerow(["AP BSS Table"])
	write.writerow(["Conductor:",mcrHostname])
	write.writerow(["Date Retrieved:",timestamp.strftime("%m-%d-%Y %H:%M:%S")])
	write.writerow([""])
	
	for md in mdList:
		if md['Status'] == 'up' :
			valid = False
			## valid only set to True if we get a token. 

			
			## Add code here to skip from a denylist. 


			#print("logging into controller at "+md['IP Address']+"...", end='')

			mdsession = requests.Session()
			mdbaseurl = "https://"+md['IP Address']+":"+port+"/"+api+"/"
			mdloginparams = {'username': username, 'password' : password}
			mdresponse = mdsession.get(mdbaseurl+"api/login", params = mdloginparams, headers=headers, data=payload, verify = httpsVerify)
			mdjsonData = mdresponse.json()['_global_result']

			
			if mdresponse.status_code == 200 :

				mdSessionToken = mdjsonData['UIDARUBA']
				valid=True
				#print("Success")
			else :
				print("Login to "+md['Name']+" Failed. Unable to get session token.")
				#sys.exit("MD Login Failed on "+md['IP Address'])
	 		


			if valid: 
				mdReqParams = {
					'UIDARUBA':mdSessionToken,
					'command':'show ap bss-table details'
					}

				showresponse = mdsession.get(mdbaseurl+"configuration/showcommand", params = mdReqParams, headers=headers, data=payload, verify = httpsVerify)
				bsstable=showresponse.json()

				# Get list of data fields from the returned list
				fields=bsstable['_meta']
				 
				# Add new fields for parsed Data
				fields.insert(5,"PHY")
				fields.insert(5,"Band")
				fields.insert(7,"Max-EIRP")
				fields.insert(7,"EIRP")
				fields.insert(7,"Channel")
				fields.insert(15,"Uptime_Seconds")
				fields.append("Controller_IP")
				fields.append("Controller_Name")

				 # Add fields for expanding flags
				for flag in bssflags.keys():
					fields.append(bssflags[flag])

				if loop == 0:
					write.writerow(fields)
				loop += 1
				# Iterate through the list of BSS
				records = 0
				for bss in bsstable["Aruba AP BSS Table"]:
					bss['Band']=None
					bss['PHY']=None
					bss['Channel']=None
					bss['EIRP']=None
					bss['Max-EIRP']=None
					bss['Uptime_Seconds']=0
					bss['Controller_IP']=md['IP Address']
					bss['Controller_Name']=md['Name']

					# Parse Status field into status, uptime, and uptime in seconds
					  
					#Split the Uptime field into each time field and strip off the training character, multiply by the requisite number of seconds an tally it up. 
					timefields=bss['tot-t'].split(':')
					    
					if len(timefields)>3 :
						days=int(timefields.pop(0)[0:-1])
						bss['Uptime_Seconds']+=days*86400
					if len(timefields)>2 :
						hours=int(timefields.pop(0)[0:-1])
						bss['Uptime_Seconds']+=hours*3600
					if len(timefields)>1 :
						minutes=int(timefields.pop(0)[0:-1])
						bss['Uptime_Seconds']+=minutes*60
					if len(timefields)>0 :
						seconds=int(timefields.pop(0)[0:-1])
						bss['Uptime_Seconds']+=seconds

					if '-' in bss['phy']:
						physplit=bss['phy'].split('-')
						bss['Band']=physplit[0]
						bss['PHY']=physplit[1]

					if 'N/A' not in bss['ch/EIRP/max-EIRP']:
						
						chansplit=bss['ch/EIRP/max-EIRP'].split('/')
						bss['Channel']=chansplit[0]
						bss['EIRP']=chansplit[1]
						bss['Max-EIRP']=chansplit[2]
					# Bust apart the flags into their own fields 
					for flag in bssflags.keys():

					# Set field to None so that it exists in the dict
						bss[bssflags[flag]]=None
					   
					# Check to see if the flags field contains data
						if bss['flags'] != None :

							if flag in bss['flags'] :
								bss[bssflags[flag]]="X"
					   
					datarow=[]

					# Iterate through the list of fields used to create the header row and append each one
					for f in fields:
						datarow.append(bss[f])

					# Add it to grand master dict that can be used for other purposes
					bsslist.append(datarow)
					# Put it in the CSV 
					write.writerow(datarow)
					records+=1
					#Move on to the next AP

				# Sum up and log out
				totalEntries+=records
				print("Processed "+str(records)+" Entries from "+md['Name'])
				logoutresponse = mdsession.get(mdbaseurl+"api/logout", verify=False)
				jsonData = logoutresponse.json()['_global_result']

				if response.status_code == 200 :
					token = jsonData['UIDARUBA']
					del mdSessionToken
					#print("MD Logout from "+md['Name']+" at "+md['IP Address']+" successful. Token deleted.")
				else :
					del mdSessionToken
					print("Logout failed from "+md['IP Address']+". Session token may remain in memory.")	
			else:
				print("Controller has no valid token. Skipping. ")
		else :
			print("Controller is down. Skipping "+md['Name']+" at "+md['IP Address'])

	# Close the file handle
	csvfile.close()
	print("Wrote "+str(totalEntries)+" records from "+str(len(mdList))+" controllers to "+csvfilename)



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