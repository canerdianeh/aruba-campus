#!/usr/bin/python3

# ArubaOS 8 API call framework
# (c) 2021 Ian Beyer, Aruba Networks <canerdian@hpe.com>
# This code is provided as-is with no warranties. Use at your own risk. 

import requests
import json
import warnings
import sys
import xmltodict


aosDevice = "1.2.3.4"
username = "admin"
password = "password"
httpsVerify = False


#Set things up

if httpsVerify == False :
	warnings.filterwarnings('ignore', message='Unverified HTTPS request')

baseurl = "https://"+aosDevice+":4343/v1/"


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