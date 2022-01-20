#!/usr/bin/env python3
#coding: utf-8

'''vmconfig.py'''
'''Based on VMKey (https://github.com/Bigouden/VMKey)'''
'''Configures initial console-based setup for Aruba virtual Mobility Conductor (and soon, Mobility Controllers)'''
'''(c) 2022 Ian Beyer, Aruba Networks'''
'''Use at your own risk, this code has not been extensively tested'''


import argparse
import atexit
import socket
import sys
from pyVim import connect
from pyVmomi import vim
import yaml
from yaml.loader import FullLoader
import socket
import struct
from datetime import datetime

import time
import pprint

wait_time = 2/100

def cidr_to_netmask(cidr):
    network, net_bits = cidr.split('/')
    host_bits = 32 - int(net_bits)
    netmask = socket.inet_ntoa(struct.pack('!I', (1 << 32) - (1 << host_bits)))
    return network, netmask

# Source : https://gist.github.com/MightyPork/6da26e382a7ad91b5496ee55fdc73db2
# Description HIDCode : ('KEY_NAME', 'HEX_CODE', [('VALUE1', [ 'MODIFIER1', 'MODIFIER2', ... ]), ('VALUE2', [ 'MODIFIER1', 'MODIFIER2', ... ]), ... ])
HIDCODE = [
        ('KEY_A', '0x04', [('a', []), ('A', ['KEY_LEFTSHIFT'])]),
        ('KEY_B', '0x05', [('b', []), ('B', ['KEY_LEFTSHIFT'])]),
        ('KEY_C', '0x06', [('c', []), ('C', ['KEY_LEFTSHIFT'])]),
        ('KEY_D', '0x07', [('d', []), ('D', ['KEY_LEFTSHIFT'])]),
        ('KEY_E', '0x08', [('e', []), ('E', ['KEY_LEFTSHIFT'])]),
        ('KEY_F', '0x09', [('f', []), ('F', ['KEY_LEFTSHIFT'])]),
        ('KEY_G', '0x0a', [('g', []), ('G', ['KEY_LEFTSHIFT'])]),
        ('KEY_H', '0x0b', [('h', []), ('H', ['KEY_LEFTSHIFT'])]),
        ('KEY_I', '0x0c', [('i', []), ('I', ['KEY_LEFTSHIFT'])]),
        ('KEY_J', '0x0d', [('j', []), ('J', ['KEY_LEFTSHIFT'])]),
        ('KEY_K', '0x0e', [('k', []), ('K', ['KEY_LEFTSHIFT'])]),
        ('KEY_L', '0x0f', [('l', []), ('L', ['KEY_LEFTSHIFT'])]),
        ('KEY_M', '0x10', [('m', []), ('M', ['KEY_LEFTSHIFT'])]),
        ('KEY_N', '0x11', [('n', []), ('N', ['KEY_LEFTSHIFT'])]),
        ('KEY_O', '0x12', [('o', []), ('O', ['KEY_LEFTSHIFT'])]),
        ('KEY_P', '0x13', [('p', []), ('P', ['KEY_LEFTSHIFT'])]),
        ('KEY_Q', '0x14', [('q', []), ('Q', ['KEY_LEFTSHIFT'])]),
        ('KEY_R', '0x15', [('r', []), ('R', ['KEY_LEFTSHIFT'])]),
        ('KEY_S', '0x16', [('s', []), ('S', ['KEY_LEFTSHIFT'])]),
        ('KEY_T', '0x17', [('t', []), ('T', ['KEY_LEFTSHIFT'])]),
        ('KEY_U', '0x18', [('u', []), ('U', ['KEY_LEFTSHIFT'])]),
        ('KEY_V', '0x19', [('v', []), ('V', ['KEY_LEFTSHIFT'])]),
        ('KEY_W', '0x1a', [('w', []), ('W', ['KEY_LEFTSHIFT'])]),
        ('KEY_X', '0x1b', [('x', []), ('X', ['KEY_LEFTSHIFT'])]),
        ('KEY_Y', '0x1c', [('y', []), ('Y', ['KEY_LEFTSHIFT'])]),
        ('KEY_Z', '0x1d', [('z', []), ('Z', ['KEY_LEFTSHIFT'])]),
        ('KEY_1', '0x1e', [('1', []), ('!', ['KEY_LEFTSHIFT'])]),
        ('KEY_2', '0x1f', [('2', []), ('@', ['KEY_LEFTSHIFT'])]),
        ('KEY_3', '0x20', [('3', []), ('#', ['KEY_LEFTSHIFT'])]),
        ('KEY_4', '0x21', [('4', []), ('$', ['KEY_LEFTSHIFT'])]),
        ('KEY_5', '0x22', [('5', []), ('%', ['KEY_LEFTSHIFT'])]),
        ('KEY_6', '0x23', [('6', []), ('^', ['KEY_LEFTSHIFT'])]),
        ('KEY_7', '0x24', [('7', []), ('&', ['KEY_LEFTSHIFT'])]),
        ('KEY_8', '0x25', [('8', []), ('*', ['KEY_LEFTSHIFT'])]),
        ('KEY_9', '0x26', [('9', []), ('(', ['KEY_LEFTSHIFT'])]),
        ('KEY_0', '0x27', [('0', []), (')', ['KEY_LEFTSHIFT'])]),
                
        ('KEY_ENTER', '0x28', [('', [])]),
        ('KEY_ESC', '0x29', [('', [])]),
        ('KEY_BACKSPACE', '0x2a', [('', [])]),
        ('KEY_TAB', '0x2b', [('', [])]),
        ('KEY_SPACE', '0x2c', [(' ', [])]),
        ('KEY_MINUS', '0x2d', [('-', []), ('_', ['KEY_LEFTSHIFT'])]),
        ('KEY_EQUAL', '0x2e', [('=', []), ('+', ['KEY_LEFTSHIFT'])]),
        ('KEY_LEFTBRACE', '0x2f', [('[', []), ('{', ['KEY_LEFTSHIFT'])]),
        ('KEY_RIGHTBRACE', '0x30', [(']', []), ('}', ['KEY_LEFTSHIFT'])]),
        ('KEY_BACKSLASH', '0x31', [('\\', []), ('|', ['KEY_LEFTSHIFT'])]),
        ('KEY_SEMICOLON', '0x33', [(';', []), (':', ['KEY_LEFTSHIFT'])]),
        ('KEY_APOSTROPHE', '0x34', [('\'', []), ('"', ['KEY_LEFTSHIFT'])]),
        ('KEY_GRAVE', '0x35', [('`', []), ('~', ['KEY_LEFTSHIFT'])]),
        ('KEY_COMMA', '0x36', [(',', []), ('<', ['KEY_LEFTSHIFT'])]),
        ('KEY_DOT', '0x37', [('.', []), ('>', ['KEY_LEFTSHIFT'])]),
        ('KEY_SLASH', '0x38', [('/', []), ('?', ['KEY_LEFTSHIFT'])]),
        ('KEY_CAPSLOCK', '0x39', []),
        ('KEY_F1', '0x3a', [('', [])]),
        ('KEY_F2', '0x3b', [('', [])]),
        ('KEY_F3', '0x3c', [('', [])]),
        ('KEY_F4', '0x3d', [('', [])]),
        ('KEY_F5', '0x3e', [('', [])]),
        ('KEY_F6', '0x3f', [('', [])]),
        ('KEY_F7', '0x40', [('', [])]),
        ('KEY_F8', '0x41', [('', [])]),
        ('KEY_F9', '0x42', [('', [])]),
        ('KEY_F10', '0x43', [('', [])]),
        ('KEY_F11', '0x44', [('', [])]),
        ('KEY_F12', '0x45', [('', [])]),
        ('KEY_DELETE', '0x4c', [('', [])]),
        ('CTRL_ALT_DEL', '0x4c', [('', ['CTRL', 'ALT'])]),
        ('CTRL_A', '0x04', [('', ['CTRL'])]),
        ('CTRL_C', '0x06', [('', ['CTRL'])]),
        ('CTRL_E', '0x08', [('', ['CTRL'])]),
        ('CTRL_P', '0x13', [('', ['CTRL'])]),
        ('CTRL_K', '0x0e', [('', ['CTRL'])]),
        ('CTRL_X', '0x1b', [('', ['CTRL'])])
    ]

def key_to_hid(input_key):
    '''Convert KEY to HID'''
    for key, code, values in HIDCODE:
        if input_key == key:
            key, modifiers = values[0]
            return code, modifiers
    return False

def character_to_hid(char):
    '''Convert CHARACTER to HID'''
    for hid in HIDCODE:
        code, values = hid[1:]
        for word, modifiers in values:
            if char == word:
                return code, modifiers
    return False

def hid_to_hex(hid):
    '''Convert HID to HEX'''
    return int(hid, 16) << 16 | 7

def key_stroke(virtual_machine, hid, debug=False):
    '''Sent KEYSTROKE to VIRTUAL MACHINE'''
    code, modifiers = hid
    tmp = vim.UsbScanCodeSpecKeyEvent()
    modifier = vim.UsbScanCodeSpecModifierType()
    if "KEY_LEFTSHIFT" in modifiers:
        modifier.leftShift = True
    if "KEY_RIGHTALT" in modifiers:
        modifier.rightAlt = True
    if "CTRL" in modifiers:
        modifier.leftControl = True
    if "ALT" in modifiers:
        modifier.leftAlt = True
    tmp.modifiers = modifier
    tmp.usbHidCode = hid_to_hex(code)
    inject_hid = vim.UsbScanCodeSpec()
    inject_hid.keyEvents = [tmp]
    virtual_machine.PutUsbScanCodes(inject_hid)
    if debug:
        print("Send : Keystroke: { code: %s, modifiers: %s } on VM : %s" % (code, modifiers, virtual_machine.name))

def get_vm(vmhost,vmachine):
    '''Get VIRTUAL MACHINE'''
    try:
        virtual_machine = None
        print("Connecting to VMWare host at %s @ %s : %s" % (vmhost['user'], vmhost['host'], vmhost['port']))
        socket.setdefaulttimeout(vmhost['timeout'])
        esxi = connect.SmartConnectNoSSL(host=vmhost['host'], user=vmhost['user'], pwd=vmhost['pass'], port=vmhost['port'])
        atexit.register(connect.Disconnect, esxi)
        entity_stack = esxi.content.rootFolder.childEntity
        while entity_stack:
            entity = entity_stack.pop()
            if entity.name == vmachine:
                print("Found matching VM named "+entity.name)
                virtual_machine = entity
                del entity_stack[0:len(entity_stack)]
                return virtual_machine
            if hasattr(entity, 'childEntity'):
                entity_stack.extend(entity.childEntity)
            if isinstance(entity, vim.Datacenter):
                entity_stack.append(entity.vmFolder)
        if not isinstance(virtual_machine, vim.VirtualMachine):
            msg = "Virtual Machine %s not found." % vmachine
            sys.exit(msg)
    except vim.fault.InvalidLogin:
        msg = "Cannot complete login due to an incorrect user name or password."
        sys.exit(msg)
    except socket.timeout as exception:
        msg = "Unable to connect to %s:%s (%s)" % (vmhost['host'], vmhost['port'], exception)
        sys.exit(msg)
    except socket.gaierror as exception:
        msg = "Unable to resolve %s (%s)" % (vmhost['host'], exception)
        sys.exit(msg)

def delete_line():
    key_stroke(VIRTUAL_MACHINE, key_to_hid('CTRL_A'), debug=args['debug'])
    time.sleep(wait_time)
    key_stroke(VIRTUAL_MACHINE, key_to_hid('CTRL_K'), debug=args['debug'])


def send_str_cr(value):
    for char in value:
        key_stroke(VIRTUAL_MACHINE, character_to_hid(char), debug=args['debug'])
        time.sleep(wait_time)
    key_stroke(VIRTUAL_MACHINE, key_to_hid('KEY_ENTER'), debug=args['debug'])


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description="Configure Aruba virtual controller/conductor initial settings using the vSphere API")
    cli.add_argument('-c','--config', help="Configuration File", default="vmconfig.yaml")
    cli.add_argument('-d','--debug', action='store_true', help="Enable debug mode")
    cli.add_argument('-s','--simulate', action='store_true', help="Simulate Actions")


    args = vars(cli.parse_args())

    sim = False
    if args['simulate'] == True : sim = True 
    
    with open(args['config'],'r') as settings:
        config = yaml.safe_load(settings)

    if args['debug'] : pprint.pprint(config) 

    #exit()
    
    for device in config['controllers']:
        print ("Processing Configuration for "+device['name']+"...")
        VIRTUAL_MACHINE = get_vm(config['vm'], device['name'])

        # Start at Beginning
        key_stroke(VIRTUAL_MACHINE, key_to_hid('CTRL_X'), debug=args['debug']) if not sim else print("simulated: CTRL_X")
        time.sleep(wait_time)

        if device['type'] == 'mm':
            print("Device is a Mobility Conductor. ")
            # System Name
            delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
            send_str_cr(device['name']) if not sim else print("simulated: %s" %device['name'])


            # LAYER 2 CONFIGURATION
            port=device['mgmt']

            print("Configuring L2 Management port on %s in %s mode on VLAN %s..." % (port['id'], port['mode'], port['vlan']))
            
            # Management VLAN ID
            delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
            send_str_cr(str(port['vlan'])) if not sim else print("simulated: %s" % port['vlan'])

     
            # Management Port
            delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
            send_str_cr(port['id']) if not sim else print("simulated: %s" %port['id'])
            # Management Port Mode
            delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
            send_str_cr(port['mode']) if not sim else print("simulated: %s" %port['mode'])

            if port['mode'] == 'trunk' :
                # Management Port Trunk Native VLAN
                delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                send_str_cr(port['vlan']) if not sim else print("simulated: %s" %port['vlan'])
            

            # IPv4 CONFIGURATION
            print("Configuring L3 Management...")
            ip4 = device['ip']['v4']

            if ip4['addr'] != None :
                print(" Configuring IPv4 on "+ip4['addr']+"...")
                # Do you wish to configure IPV4 address on vlan
                delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                send_str_cr('yes') if not sim else print("simulated: yes")
                
                net4, mask4=cidr_to_netmask(ip4['addr'])
                  
                # Enter VLAN interface IP address:
                delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                send_str_cr(net4) if not sim else print("simulated: %s" % net4)

                #Enter VLAN interface subnet mask:
                delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                send_str_cr(mask4) if not sim else print("simulated: %s" % mask4)
                
                # Enter IP Default Gateway [none]
                if ip4['gw'] != None:
                    delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                    send_str_cr(ip4['gw']) if not sim else print("simulated: %s" % ip4['gw'])
                else:
                    key_stroke(VIRTUAL_MACHINE, key_to_hid('KEY_ENTER'), debug=FILE.debug) if not sim else print("simulated: KEY_ENTER")
           
                # Enter DNS IP address [none]
                if ip4['dns'] != None:
                    delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                    send_str_cr(ip4['dns']) if not sim else print("simulated: %s" % ip4['dns'])
                else:
                    key_stroke(VIRTUAL_MACHINE, key_to_hid('KEY_ENTER'), debug=FILE.debug) if not sim else print("simulated: KEY_ENTER")
            else: 
                # Do you wish to configure IPV4 address on vlan
                print(" No IPv4 configured.")
                delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                send_str_cr('no') if not sim else print("simulated: no")


            ## IPv6 CONFIGURATION

            ip6 = device['ip']['v6']

            if ip6['addr'] != None :
                print(" Configuring IPv6 on %s/%s..." % (ip6['addr'], ip6['prefix']))

                # Do you wish to configure IPV4 address on vlan
                delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                send_str_cr('yes') if not sim else print("simulated: yes")
                            
                # Enter VLAN interface IP address:
                delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                send_str_cr(ip6['addr']) if not sim else print("simulated: %s" % ip6['addr'])

                #Enter VLAN interface IPv6 Prefix:
                delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                send_str_cr(ip6['prefix']) if not sim else print("simulated: %s" % ip6['prefix'])
                
                # Enter IPv6 Default Gateway [none]
                if ip6['gw'] != None:
                    delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                    send_str_cr(ip4['gw']) if not sim else print("simulated: %s" % ip6['gw'])
                else:
                    key_stroke(VIRTUAL_MACHINE, key_to_hid('KEY_ENTER'), debug=FILE.debug) if not sim else print("simulated: KEY_ENTER")
           
                # Enter DNS IPv6 address [none]
                if ip6['dns'] != None:
                    delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                    send_str_cr(ip6['dns']) if not sim else print("simulated: %s" % ip6['dns'])
                else:
                    key_stroke(VIRTUAL_MACHINE, key_to_hid('KEY_ENTER'), debug=FILE.debug) if not sim else print("simulated: KEY_ENTER")
            else: 
                # Do you wish to configure IPV6 address on vlan
                print(" No IPv6 configured.")
                delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
                send_str_cr('no') if not sim else print("simulated: no")

            utc=datetime.utcnow()
            utctime=utc.strftime("%H:%M:%S")
            utcdate=utc.strftime("%m/%d/%Y")


            print("Configuring System for %s/%s" % (device['cc'], device['tz']))
            print("Current UTC Date/Time is %s %s" % (utcdate, utctime))
            # Enter Country Code (ISO-3166):
            delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
            send_str_cr(device['cc']) if not sim else print("simulated: %s" % device['cc'])
            delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
            send_str_cr('yes') if not sim else print("simulated: yes")

            # Enter the Controller's IANA Time Zone:
            delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
            send_str_cr(device['tz']) if not sim else print("simulated: %s" % device['tz'])

            # Enter Time in UTC

            delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
            send_str_cr(utctime) if not sim else print("simulated: %s" % utctime)
            delete_line() if not sim else print("simulated: CTRL_A, CTRL_K")
            send_str_cr(utcdate) if not sim else print("simulated: %s" % utcdate)

            # Enter Password for admin login
            print("setting admin account password to '"+device['pw']+"'")
            send_str_cr(device['pw']) if not sim else print("simulated: %s" % device['pw'])
            send_str_cr(device['pw']) if not sim else print("simulated: %s" % device['pw'])

            # Do you wish to accept the changes?

            send_str_cr('yes') if not sim else print("simulated: yes")
                  
        if device['type'] == 'md':
            print("Device is a Mobility Controller. ")
            ''' More code to come here '''

