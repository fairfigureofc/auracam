#!/usr/bin/env python3
"""BlueZ BLE peripheral bridge to the local AuraCam session server."""
import dbus,dbus.service,json
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from ble_protocol import Protocol

SERVICE='9d7a0001-64d8-4ef1-9b9e-7127ba10ca00'
COMMAND='9d7a0002-64d8-4ef1-9b9e-7127ba10ca00'
RESPONSE='9d7a0003-64d8-4ef1-9b9e-7127ba10ca00'
PROP='org.freedesktop.DBus.Properties';OM='org.freedesktop.DBus.ObjectManager'
GATT='org.bluez.GattCharacteristic1'
class Rejected(dbus.DBusException):_dbus_error_name='org.bluez.Error.NotPermitted'
class Node(dbus.service.Object):
    def __init__(self,bus,path,interface,props):
        self.path=path;self.interface=interface;self.props=props;super().__init__(bus,path)
    @dbus.service.method(PROP,in_signature='s',out_signature='a{sv}')
    def GetAll(self,interface):return self.props if interface==self.interface else {}

class Characteristic(Node):
    def __init__(self,bus,path,uuid,flags,bridge):
        super().__init__(bus,path,GATT,{'UUID':uuid,'Service':dbus.ObjectPath('/org/auracam/service0'),'Flags':dbus.Array(flags,signature='s')})
        self.bridge=bridge
    @dbus.service.method(GATT,in_signature='aya{sv}',out_signature='')
    def WriteValue(self,value,options):
        if self.props['UUID']!=COMMAND:raise Rejected('Read only')
        self.bridge.claim(str(options.get('device','')))
        self.bridge.pending.extend(bytes(value))
        if len(self.bridge.pending)>4096:self.bridge.pending.clear();raise Rejected('Command too large')
        if b'\n' in self.bridge.pending:
            raw,_,extra=self.bridge.pending.partition(b'\n');self.bridge.pending.clear()
            if extra:raise Rejected('One command at a time')
            self.bridge.protocol.command(raw)
    @dbus.service.method(GATT,in_signature='a{sv}',out_signature='ay')
    def ReadValue(self,options):
        if self.props['UUID']!=RESPONSE:raise Rejected('Write only')
        self.bridge.claim(str(options.get('device','')))
        offset=int(options.get('offset',0));return dbus.Array(self.bridge.protocol.reply[offset:],signature='y')
class App(dbus.service.Object):
    def __init__(self,bus):
        super().__init__(bus,'/org/auracam');self.bus=bus;self.owner=None;self.pending=bytearray();self.protocol=Protocol()
        self.nodes=[Node(bus,'/org/auracam/service0','org.bluez.GattService1',{'UUID':SERVICE,'Primary':True}),Characteristic(bus,'/org/auracam/service0/command',COMMAND,['write','encrypt-write'],self),Characteristic(bus,'/org/auracam/service0/response',RESPONSE,['read','encrypt-read'],self)]
    def claim(self,device):
        if not device:raise Rejected('Device required')
        if self.owner and self.owner!=device:
            try:connected=bool(dbus.Interface(self.bus.get_object('org.bluez',self.owner),PROP).Get('org.bluez.Device1','Connected'))
            except dbus.DBusException:connected=False
            if connected:raise Rejected('Another controller is connected')
        if device!=self.owner:self.pending.clear();self.protocol=Protocol();self.owner=device
    @dbus.service.method(OM,out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):return {n.path:{n.interface:n.props} for n in self.nodes}
class Advertisement(Node):
    @dbus.service.method('org.bluez.LEAdvertisement1',in_signature='',out_signature='')
    def Release(self):pass

class Agent(dbus.service.Object):
    @dbus.service.method('org.bluez.Agent1',in_signature='',out_signature='')
    def Release(self):pass
    @dbus.service.method('org.bluez.Agent1',in_signature='o',out_signature='')
    def RequestAuthorization(self,device):print('AuraCam agent: authorizing incoming pairing',flush=True)
    @dbus.service.method('org.bluez.Agent1',in_signature='ou',out_signature='')
    def RequestConfirmation(self,device,passkey):print('AuraCam agent: confirming Just Works pairing',flush=True)
    @dbus.service.method('org.bluez.Agent1',in_signature='os',out_signature='')
    def AuthorizeService(self,device,uuid):
        if str(uuid).lower()!=SERVICE:raise Rejected('Only AuraCam is supported')
    @dbus.service.method('org.bluez.Agent1',in_signature='',out_signature='')
    def Cancel(self):print('AuraCam agent: pairing canceled',flush=True)

def main():
    DBusGMainLoop(set_as_default=True);bus=dbus.SystemBus()
    objects=dbus.Interface(bus.get_object('org.bluez','/'),OM).GetManagedObjects()
    adapters=[p for p,i in objects.items() if 'org.bluez.GattManager1' in i and 'org.bluez.LEAdvertisingManager1' in i]
    if not adapters:raise SystemExit('No BLE peripheral adapter. Check bluetooth service and rfkill.')
    adapter=bus.get_object('org.bluez',adapters[0]);dbus.Interface(adapter,PROP).Set('org.bluez.Adapter1','Powered',dbus.Boolean(True))
    agent=Agent(bus,'/org/auracam/agent')
    manager=dbus.Interface(bus.get_object('org.bluez','/org/bluez'),'org.bluez.AgentManager1')
    manager.RegisterAgent('/org/auracam/agent','NoInputNoOutput');manager.RequestDefaultAgent('/org/auracam/agent')
    print('AuraCam pairing agent registered as default (NoInputNoOutput)',flush=True)
    app=App(bus);advertisement=Advertisement(bus,'/org/auracam/advertisement','org.bluez.LEAdvertisement1',{'Type':'peripheral','ServiceUUIDs':dbus.Array([SERVICE],signature='s'),'LocalName':'AuraCam Pi'})
    loop=GLib.MainLoop()
    registered={'app':False,'advertisement':False}
    def failed(error):
        print('BLE registration failed:',error,flush=True);loop.quit()
    def advertised():
        registered['advertisement']=True
        print('AuraCam BLE ready. Keep session_server.py running on port 8080.',flush=True)
    def application_ready():
        registered['app']=True
        dbus.Interface(adapter,'org.bluez.LEAdvertisingManager1').RegisterAdvertisement(advertisement.path,{},reply_handler=advertised,error_handler=failed)
    # BlueZ calls back into GetManagedObjects/GetAll during registration: run the GLib loop.
    dbus.Interface(adapter,'org.bluez.GattManager1').RegisterApplication('/org/auracam',{},reply_handler=application_ready,error_handler=failed)
    def disconnected(interface,changed,invalidated,path=None):
        if interface=='org.bluez.Device1' and path==app.owner and changed.get('Connected')==False:
            app.owner=None;app.pending.clear();app.protocol=Protocol()
    bus.add_signal_receiver(disconnected,dbus_interface=PROP,signal_name='PropertiesChanged',path_keyword='path')
    try:loop.run()
    finally:
        if registered['advertisement']:dbus.Interface(adapter,'org.bluez.LEAdvertisingManager1').UnregisterAdvertisement(advertisement.path)
        if registered['app']:dbus.Interface(adapter,'org.bluez.GattManager1').UnregisterApplication('/org/auracam')
    if not registered['advertisement']:raise SystemExit(1)
if __name__=='__main__':main()
