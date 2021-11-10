#!/usr/bin/python3

import requests
import json
import csv
import sys
import warnings
import sys
import xmltodict
import datetime



aosDevice = "1.2.3.4"
username = "admin"
password = "password"
httpsVerify = False
outfile="BSS_Table.csv"

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

print("Getting Switch List...")
mcrList, mdList = getSwitches()

print("Found the following Controllers")
for md in mdList:
	print(md['Model']+" at "+md['IP Address'])

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

with open(outfile, 'w') as csvfile:
	write=csv.writer(csvfile)
	loop=0

	# Create Sheet Title

	write.writerow(["AP BSS Table"])
	write.writerow([timestamp.strftime("%m-%d-%Y %H:%M:%S")])
	write.writerow([""])
	
	for md in mdList:
		print("logging into controller at "+md['IP Address']+"...", end='')
		mdsession = requests.Session()
		mdbaseurl = "https://"+md['IP Address']+":4343/v1/"
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
		fields.append("Controller")

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
			bss['Controller']=md['IP Address'] 

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