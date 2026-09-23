#!/usr/bin/env python3
"""BlueZ pairing agent with native desktop menu prompts, including keyboards."""
import sys
import gi
gi.require_version('Gio','2.0')
from gi.repository import Gio, GLib
from desktop import menu, ask, notify

XML='''<node><interface name="org.bluez.Agent1">
<method name="Release"/>
<method name="RequestPinCode"><arg type="o" direction="in"/><arg type="s" direction="out"/></method>
<method name="DisplayPinCode"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
<method name="RequestPasskey"><arg type="o" direction="in"/><arg type="u" direction="out"/></method>
<method name="DisplayPasskey"><arg type="o" direction="in"/><arg type="u" direction="in"/><arg type="q" direction="in"/></method>
<method name="RequestConfirmation"><arg type="o" direction="in"/><arg type="u" direction="in"/></method>
<method name="RequestAuthorization"><arg type="o" direction="in"/></method>
<method name="AuthorizeService"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
<method name="Cancel"/>
</interface></node>'''

bus=Gio.bus_get_sync(Gio.BusType.SYSTEM,None)
loop=GLib.MainLoop()
agent='/org/rice/BluetoothAgent'
addr=sys.argv[1]

def call(path,interface,method,params=None):
    return bus.call_sync('org.bluez',path,interface,method,params,None,Gio.DBusCallFlags.NONE,10000,None)
objects=call('/','org.freedesktop.DBus.ObjectManager','GetManagedObjects').unpack()[0]
device=next((path for path,ifaces in objects.items() if ifaces.get('org.bluez.Device1',{}).get('Address')==addr),None)
if not device:
    notify('Device is no longer available. Rescan and try again.');sys.exit(1)

def method(conn,sender,path,iface,name,params,invocation):
    args=params.unpack()
    if args and name not in ('Release','Cancel') and args[0]!=device:
        invocation.return_dbus_error('org.bluez.Error.Rejected','Unexpected device');return
    result=None
    if name in ('RequestPinCode','RequestPasskey'):
        value=ask('Bluetooth PIN' if name=='RequestPinCode' else 'Bluetooth passkey')
        if value is None or (name=='RequestPasskey' and (not value.isdigit() or int(value)>999999)):
            invocation.return_dbus_error('org.bluez.Error.Rejected','Canceled');return
        result=GLib.Variant('(s)',(value,)) if name=='RequestPinCode' else GLib.Variant('(u)',(int(value),))
    elif name in ('RequestConfirmation','RequestAuthorization','AuthorizeService'):
        prompt=f'Confirm matching code: {args[1]:06d}' if name=='RequestConfirmation' else 'Allow Bluetooth pairing?'
        if menu('Bluetooth', ['Cancel','Confirm'],message=prompt)!=1:
            invocation.return_dbus_error('org.bluez.Error.Rejected','Canceled');return
    elif name in ('DisplayPinCode','DisplayPasskey'):
        notify('Enter this code on your Bluetooth device: '+str(args[1]))
    invocation.return_value(result)

registration=bus.register_object(agent,Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0],method,None,None)
call('/org/bluez','org.bluez.AgentManager1','RegisterAgent',GLib.Variant('(os)',(agent,'KeyboardDisplay')))

def paired(conn,result,*unused):
    try:
        conn.call_finish(result)
        call(device,'org.freedesktop.DBus.Properties','Set',GLib.Variant('(ssv)',('org.bluez.Device1','Trusted',GLib.Variant('b',True))))
        call(device,'org.bluez.Device1','Connect')
        notify('Bluetooth device paired and connected.')
    except GLib.Error as exc:
        notify('Bluetooth: '+exc.message)
    finally: loop.quit()

try:
    if objects[device]['org.bluez.Device1'].get('Paired'):
        call(device,'org.freedesktop.DBus.Properties','Set',GLib.Variant('(ssv)',('org.bluez.Device1','Trusted',GLib.Variant('b',True))))
        call(device,'org.bluez.Device1','Connect')
    else:
        notify('Pairing… keep your device in pairing mode.')
        bus.call('org.bluez',device,'org.bluez.Device1','Pair',None,None,Gio.DBusCallFlags.NONE,90000,None,paired,None)
        loop.run()
finally:
    call('/org/bluez','org.bluez.AgentManager1','UnregisterAgent',GLib.Variant('(o)',(agent,)))
    bus.unregister_object(registration)
