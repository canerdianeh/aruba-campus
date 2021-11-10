# aruba-campus
Scripts for Aruba Controllers

## apdb2csv.py
Opens an API connection to an AOS8 Mobility Conductor or Mobility Controller, and performs a **show ap database long**, and outputs to a CSV file. 

## apbsstable.py
Opens an API connection to an AOS8 Mobility Conductor and retrieves a list of connected controllers, and then queries each controller with **show ap bss-table detail** and outputs to a CSV. The CSV data is also available as a dict. 

## api-framework.py
The basic framework for opening an API connection to an Aruba AOS8 controller. Also retrieves a list of connected controllers. 

## apflags.json
JSON dict of AP flags and their human-readable descriptors
