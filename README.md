# aruba-campus
Scripts for Aruba Controllers

## apdb2csv.py
Opens an API connection to an AOS8 Mobility Conductor or Mobility Controller, and performs a **show ap database long**, and outputs to a CSV file. 

## apbsstable.py
Opens an API connection to an AOS8 Mobility Conductor and retrieves a list of connected controllers, and then queries each controller with **show ap bss-table detail** and outputs to a CSV. The CSV data is also available as a dict. 

## applldpnei.py
Opens an API connection to an AOS8 Mobility Conductor and retrieves a list of connected controllers, and then queries each controller with **show ap lldp neighbors** and outputs to a CSV. The CSV data is also available as a dict. 

## usertable.py
Opens an API connection to an AOS8 Mobility Conductor and retrieves a list of connected controllers, and then queries each controller with **show user-table** and outputs to a CSV. The CSV data is also available as a dict. 

## api-framework.py
The basic framework for opening an API connection to an Aruba AOS8 controller. Also retrieves a list of connected controllers. 

## controller_data_to_xl.py
Takes a terminal session dump containing one or more of:
- show ap database [long]
- show ap lldp neighbors
- show ap ble-database [long]
and places it in an Excel named table for further processing. Uses Pandas dataframes. 

## apflags.json
JSON dict of AP flags and their human-readable descriptors
