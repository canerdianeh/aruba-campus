#!/usr/bin/python3

# Converts the following AOS CLI outputs from terminal capture to Excel Named Tables:
# show ap database [long] (From Mobility Conductor or AOS 6/8 Mobility Controller)
# show ap lldp neighbors (from AOS 6/8 Mobility Controller)
# show ap ble-database [long] (From AOS 8 Mobility Controller)
# show ap bss-table details (From AOS)
# Capture output from terminal session or AirRecorder after issuing "no paging" command. 

# Python Module Dependencies:
# pandas
# xlsxwriter

# (c) 2023 HPE Aruba Networking
# Author: Ian Beyer, High Touch Services (ian.beyer@hpe.com)

from __future__ import print_function
import re
import sys
import csv
import json
from pprint import pprint
import pandas as pd

# File name argument #1
try:
	fileName=str(sys.argv[1])
except:
	print("Exception: Enter file to use and a format ('lldp', 'db', or 'ble' )")
	exit()
if '.txt' not in fileName and '.log' not in fileName:
	print('Invalid file name entered.')
	exit()

#----------------------------------------------------------------------------------------------------------------------------------------------------------

# Fun With Flags
apflags={
'1':'802.1X EAP-PEAP',
'1+':'802.1X EST',
'1-':'802.1X Factory Cert',
'2':'IKE v2',
'4':'WiFi Uplink',
'B':'Built-In',
'C':'Cellular RAP',
'D':'Dirty/No Config',
'E':'Reg Domain Mismatch',
'F':'Failed 802.1X Auth',
'G':'No Such Group',
'I':'Inactive',
'J':'USB Cert at AP',
'L':'Unlicensed',
'M':'Mesh Node',
'N':'Duplicate Name',
'P':'PPPoE AP',
'R':'Remote AP',
'R-':'RAP Req Auth',
'S':'Standby-Mode AP',
'T':'Thermal Shutdown',
'U':'Unprovisioned',
'X':'Maintenance Mode',
'Y':'Mesh Recovery',
'b':'bypass AP1x Timeout',
'c':'CERT-Based RAP',
'e':'Custom EST Cert',
'f':'No spectrum FFT',
'i':'Indoor',
'o':'Outdoor',
'p':'Deep Sleep',
'r':'Power Restricted',
's':'LACP Striping',
't':'Temperature Restricted',
'u':'Custom-Cert RAP',
'z':'Datazone AP'
}

lldpcaps={
	'R':'Router',
	'B':'Bridge',
	'A':'Access Point',
	'P':'Phone',
	'O':'Other'
}

bssflags={
'a':'Airslice policy',
'A':'Airslice app monitoring',
'c':'MBO Cellular Data Capable BSS',
'd':'Deferred Delete Pending',
'D':'VLAN Discovered',
'E':'Enhanced-open BSS without transition mode',
'I':'Imminent VAP Down',
'K':'802.11k Enabled',
'm':'Agile Multiband (MBO) BSS',
'M':'WPA3-SAE mixed mode BSS',
'o':'Enhanced-open transition mode open BSS',
'O':'Enhanced-open BSS with transition mode',
'r':'802.11r Enabled',
't':'Broadcast TWT Enabled',
'T':'Individual TWT Enabled',
'W':'802.11W Enabled',
'x':'MBSSID Tx BSS',
'3':'WPA3 BSS'
'z':'',
'Z':''
}

bssfwd={
'T':'Tunnel', 
'S':'Split', 
'D':'Decrypt Tunnel', 
'B':'Bridge',
'Bs':'standard', 
'Bp':'persistent', 
'Bb':'backup', 
'Ba':'always', 
'n':'anyspot'	
}

bsscluster={
'U':'UAC',
'A':'AAC',
'sU':'Standby UAC',
'sA':'Standby AAC'
}

# define function to convert uptime field to actual seconds

def time_to_sec(timefield) :
	utseconds=0
	tf=timefield.split(':')
	if len(tf)>3 :
		days=int(tf.pop(0)[0:-1])
		utseconds+=days*86400
	if len(tf)>2 :
		hours=int(tf.pop(0)[0:-1])
		utseconds+=hours*3600
	if len(tf)>1 :
		minutes=int(tf.pop(0)[0:-1])
		utseconds+=minutes*60
	if len(tf)>0 :
		seconds=int(tf.pop(0)[0:-1])
		utseconds+=seconds
	return(utseconds)

#Initialize vars

filedata=""
apheaders=[]
lldpheaders=[]
bleheaders=[]
bssheaders=[]

apdb=[]
lldp=[]
ble=[]
bss=[]
datatype=""

# Crack open the file
with open(fileName) as input_raw:
	print("Opening "+ fileName + " for read")
	for device in input_raw:

		#Remove Trailing Newline
		device=device.rstrip()
		
		# Add second space to put status and uptime in separate fields
		device=re.sub(r'Up ', 'Up  ', device)

		# Split into fields on double whitespace
		fields=re.split(r'\s{2,}',device) 

		linetype=""
		
		# Is there an IP address in the line? 
		if re.search(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', device):
			if len(fields) >5: # If more than 5 fields, this is a data line, otherwise ignore it
				linetype="data" # Line matched IP address - treating as AP/BLE data

		# Is the number of returned fields over 5 (This means it's actual meaningful data, even without an IP)		
		elif len(fields)>5:
			if fields[0]=="Name": # First field of "Name" indicates it's an AP database header
				linetype="header"
				fields.insert(5,'Uptime') # Create a new column
				datatype="apdb"
				apheaders=fields # Capture the headers

			elif fields[2]=="BLE MAC": # Check third column to see if it's BLE database header
				datatype="ble"
				bleheaders=fields # Capture the headers
		
			elif fields[0]=="AP": # First field of "AP" indicates it's an LLDP database header		
				linetype="header"
				lldpheaders=fields
				datatype="lldp"

			elif fields[0]=="bss":
				linetype="header"
				bssheaders=fields
				datatype="bss"
				if fields[4]=="phy":
					bssver="8.0"			
				elif fields[4]=="band/ht-mode/bandwidth":
					bssver="8.9"

			# The rest of these are to ignore visual elements with no data	
			elif re.search(r'-{2,}',fields[0]):
				linetype="fluff"
			elif fields[0] == "--":
				linetype="fluff"
			elif fields[0] == "----":
				linetype="fluff"
			
			# OK, it must be data then. 
			else:	
				linetype="data"

		# Ignore any other extraneous stuff in the line
		else:
			linetype="fluff"

		# Initialize data row dict

		datarow={}
		print(linetype+": "+device)
		if linetype == "data":

			if datatype == "apdb":
				if fields[4] == "Down": # If down, there will be an empty field where uptime should be
					fields.insert(5,'') #Insert the empty uptime field
				
				# If field 6 is an IP address, there is an empty flag field that got missed in the split.
				if re.search(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', fields[6]): 
					fields.insert(6,'') # Insert the empty flags field

				# We should no have 15 fields

				if len(fields)==14: # If there are only 14 fields, there is an empty username field at the end 
					fields.append('') #Add empty username field
				elif len(fields)==13: # If there are only 13 fields, there is a missing username and likely empty port field 
					fields.append('') #Add empty username field
					fields.insert(11,'') # Add empty port field

				
				# Turn AP Entry into a JSON dict
				index=0
				for f in apheaders:
					datarow[f]=fields[index]
					index +=1

				# Add additional data

				# Compute uptime in seconds so we don't have to do it in Excel

				uptime=0
				if fields[4]=="Up":
					uptime=time_to_sec(fields[5])

				datarow['Uptime Seconds']=uptime

				# Parse flags and add them to the dict 
				for flag in apflags.keys():
					datarow[apflags[flag]]='' #comment out if you don't want 30 columns of empty flags
					if datarow['Flags']!=None:
						if flag in datarow['Flags']:
							datarow[apflags[flag]]=True

				# Append dict to the list 
				apdb.append(datarow)

			elif datatype == "lldp":
				if len(fields)==7: # If there are only 7 fields, the capabilities field at the end is missing
					fields.append('') # Add empty Capabilities field

				# turn it into a JSON dict
				index=0
				for f in lldpheaders:
					datarow[f]=fields[index]
					index +=1

				# Parse Capabilities
				for cap in lldpcaps.keys():
					datarow[lldpcaps[cap]]=''
					if datarow['Capabilities']!=None:
						if cap in datarow['Capabilities']:
							datarow[lldpcaps[cap]]=True

				# Append dict to the LLDP list
				lldp.append(datarow)

			elif datatype == "ble":
				# Not really any additional processing needed here. 
				
				# turn it into a JSON dict
				index=0
				for f in bleheaders:
					datarow[f]=fields[index]
					index +=1

				# Append dict to the BLE list
				ble.append(datarow)

			elif datatype == "bss":
				#hdrlen=len(bssheaders)
				#fldlen=len(fields)
				
				# turn it into a JSON dict
				index=0
				for f in bssheaders:
					datarow[f]=fields[index]
					index +=1

				datarow['Uptime Seconds']=time_to_sec(datarow['tot-t'])
				datarow['cluster']=bsscluster[datarow['cluster']]
				datarow['Forwarding Mode']=bssfwd[datarow['fm']]
				datarow.pop('fm')

				chans=datarow['ch/EIRP/max-EIRP'].split('/')
				datarow['channel']=chans[0]
				datarow['EIRP']=chans[1]
				datarow['Max EIRP']=chans[2]
				datarow.pop('ch/EIRP/max-EIRP')
				datarow['band']=''
				datarow['phy']=''
				datarow['chan width']=''

				# Parse flags
				if datarow['flags']=='-':
					datarow['flags']=''
				else:
					for flag in bssflags.keys():
						datarow[bssflags[flag]]=''
						if datarow['flags']!=None:
							if flag in datarow['flags']:
								datarow[bssflags[flag]]=True
					
				if bssver == "8.0":
					bandphy=datarow['phy'].split('-')
					bands{'a':'5GHz', 'g':'2.4GHz'}
					datarow['band']=bands[bandphy[0]]

					if len(bandphy)>1: 
						datarow['phy']=bandphy[1]
					else:
						datarow['phy']=''

				elif bssver == "8.9":

					bandphy=datarow['band/ht-mode/bandwidth'].split('/')
					datarow.pop('band/ht-mode/bandwidth')
					datarow['band']=bandphy[0]
					datarow['phy']=bandphy[1]
					datarow['chan width']=bandphy[2]

				#else:


				# Append dict to the BSS list
				bss.append(datarow)


# Print Summary:

print("AP Database: "+str(len(apdb))+" Entries")
print("LLDP Neighbors: "+str(len(lldp))+" Entries")
print("BLE Database: "+str(len(ble))+" Entries")
print("BSS Table: "+str(len(bss))+" Entries")


# Create an Excel file
xl=pd.ExcelWriter(re.sub(r'\.[aA-zZ0-9]{1,4}', '', fileName) + '.xlsx', engine='xlsxwriter')
wb=xl.book


# Are there entries in the AP Database? 
if len(apdb)>0 : 
	apdf=pd.DataFrame.from_dict(apdb) 		# Create pandas dataframe from the JSON list of dicts
	apmacs=apdf['Wired MAC Address']
	apserials=apdf['Serial #']
	apuptimesec=apdf['Uptime Seconds']
	apdf=apdf.drop(columns=['Wired MAC Address','Serial #','Uptime Seconds'])
	apdf.insert(loc=0,column='Wired MAC', value=apmacs)
	apdf.insert(loc=1,column='AP Serial', value=apserials)
	apdf.insert(loc=9,column='Uptime Seconds', value=apuptimesec)


	apdf.to_excel(xl, sheet_name='AP Database', startrow=1, header=True, index=False)  # Create an Excel sheet with the data

	ws=xl.sheets['AP Database']

	# Turn it into a named table
	(max_row, max_col)=apdf.shape
	column_settings=[]
	for header in apdf.columns:
		column_settings.append({'header': header})
	ws.add_table(0,0,max_row, max_col -1, {'columns': column_settings,'name':'APDatabase'})
	ws.set_column(0, max_col -1,12)

# Are there entries in the LLDP Neighborlist?
if len(lldp)>0 : 
	lldpdf=pd.DataFrame.from_dict(lldp) 		# Create pandas dataframe from the JSON list of dicts
	lldpdf.to_excel(xl, sheet_name='LLDP Neighbors', header=True, index=False) # Create an Excel sheet with the data
	ws=xl.sheets['LLDP Neighbors']

	# Turn it into a named table
	(max_row, max_col)=lldpdf.shape
	column_settings=[]
	for header in lldpdf.columns:
		column_settings.append({'header': header})
	ws.add_table(0,0,max_row, max_col -1, {'columns': column_settings, 'name':'LLDPNeighbors'})
	ws.set_column(0, max_col -1,12)

# Are there entries in the BLE Database? 
if len(ble)>0 : 
	bledf=pd.DataFrame.from_dict(ble) 		# Create pandas dataframe from the JSON list of dicts
	blemacs=bledf['BLE MAC']
	bledf=bledf.drop(columns=['BLE MAC'])
	bledf.insert(loc=0,column='BLE MAC', value=blemacs)
	bledf.to_excel(xl, sheet_name='BLE Database', header=True, index=False) # Create an Excel sheet with the data
	ws=xl.sheets['BLE Database']

	# Turn it into a named table
	(max_row, max_col)=bledf.shape
	column_settings=[]
	for header in bledf.columns:
		column_settings.append({'header': header})
	ws.add_table(0,0,max_row, max_col -1, {'columns': column_settings, 'name':'BLEDatabase'})
	ws.set_column(0, max_col -1,12)

# Are there entries in the BSS Database? 
if len(bss)>0 : 
	bssdf=pd.DataFrame.from_dict(bss) 		# Create pandas dataframe from the JSON list of dicts
	print(bssdf)
	bssband=bssdf['band']
	bssphy=bssdf['phy']
	bssch=bssdf['channel']
	bsscw=bssdf['chan width']
	bsseirp=bssdf['EIRP']
	bssmaxeirp=bssdf['Max EIRP']
	bssuts=bssdf['Uptime Seconds']
	bssac=bssdf['active-clients']
	bsssc=bssdf['standby-clients']
	
	bssdf=bssdf.drop(columns=['band','phy','channel','chan width','EIRP','Max EIRP','Uptime Seconds','active-clients','standby-clients'])
	bssdf.insert(loc=7,column='Band', value=bssband)
	bssdf.insert(loc=8,column='PHY', value=bssphy)
	bssdf.insert(loc=9,column='Channel', value=bssch)
	bssdf.insert(loc=10,column='Channel Width', value=bsscw)
	bssdf.insert(loc=11,column='EIRP', value=bsseirp)
	bssdf.insert(loc=12,column='Max EIRP', value=bssmaxeirp)
	bssdf.insert(loc=15,column='Uptime Seconds', value=bssuts)
	bssdf.insert(loc=6,column='Standby Clients', value=bsssc)
	bssdf.insert(loc=6,column='Active Clients', value=bssac)

	bssdf.rename(columns={'bss':'BSSID','ess':'ESSID','ip':'Device IP','ap name':'AP Name','in-t(s)':'Inactive Time','cluster':'Cluster Name','datazone':'Data Zone Name','cur-cl': 'Clients', 'acl':'ACL', 'acl-state':'ACL State','tot-t':'Uptime','mtu':'MTU'}, inplace=True)

	bssdf.to_excel(xl, sheet_name='BSS Table', header=True, index=False) # Create an Excel sheet with the data
	ws=xl.sheets['BSS Table']

	# Turn it into a named table
	(max_row, max_col)=bssdf.shape
	column_settings=[]
	for header in bssdf.columns:
		column_settings.append({'header': header})
	ws.add_table(0,0,max_row, max_col -1, {'columns': column_settings, 'name':'BSSDatabase'})
	ws.set_column(0, max_col -1,12)


# Write out the Excel file and we're done!

print("Run complete. Data is contained in "+re.sub(r'\.[aA-zZ0-9]{1,4}', '', fileName) + '.xlsx')
xl.close()



