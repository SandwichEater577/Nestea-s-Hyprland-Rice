#!/usr/bin/env python3
"""Native monochrome desktop controls, using the existing desktop backends."""
import concurrent.futures
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, Gio, GLib, GtkLayerShell, Pango
import desktop as backend
import display
import mpris
import update_check
from private_data import load_private_data

POOL = concurrent.futures.ThreadPoolExecutor(max_workers=1)
ROOT = Path(__file__).parent
CODE = runpy.run_path(str(Path.home()/'.local/bin/vscode-menu'))


def friendly_sink(sink):
    name = sink.get('description', sink['name'])
    port = sink.get('active_port', '')
    if isinstance(port, dict): port = port.get('name', '')
    if 'bluez' in sink['name']: return name, 'Bluetooth audio', 'audio-headphones-symbolic'
    if 'hdmi' in sink['name'].lower(): return 'Display audio', name, 'video-display-symbolic'
    if 'headphone' in port: return 'Headphones', 'Built-in headphone jack', 'audio-headphones-symbolic'
    if 'alsa' in sink['name']: return 'Laptop speakers', 'Built-in audio', 'audio-speakers-symbolic'
    return name, 'Audio output', 'audio-speakers-symbolic'


def sound_data():
    return dict(sinks=json.loads(backend.run('pactl','-f','json','list','sinks',check=True)),
                default=backend.run('pactl','get-default-sink'),
                streams=json.loads(backend.run('pactl','-f','json','list','sink-inputs',check=True)),
                volume=backend.run('wpctl','get-volume',backend.SINK), boost=backend.BOOST.exists())


def route_output(name):
    backend.run('pactl','set-default-sink',name,check=True)
    for stream in json.loads(backend.run('pactl','-f','json','list','sink-inputs',check=True)):
        backend.run('pactl','move-sink-input',stream['index'],name,check=True)
    value=backend.run('wpctl','get-volume',backend.SINK)
    if not backend.BOOST.exists() and value and float(value.split()[1])>1:
        backend.run('wpctl','set-volume',backend.SINK,'1.0',check=True)


def wifi_data():
    rows=[backend.fields(line) for line in backend.nm('-t','-f','SSID,SIGNAL,SECURITY','device','wifi','list','--rescan','no').splitlines()]
    nearby={}
    for row in rows:
        if len(row)==3 and row[0] and (row[0] not in nearby or int(row[1])>int(nearby[row[0]][1])):
            nearby[row[0]]=row
    active=backend.nm('-g','GENERAL.CON-UUID','device','show').splitlines()
    saved=[]
    for uuid,kind,name in backend.profiles():
        ssid=backend.nm('-g','802-11-wireless.ssid','connection','show','uuid',uuid)
        saved.append(dict(uuid=uuid,name=name,ssid=ssid,active=uuid in active,scan=nearby.get(ssid)))
    preferred=load_private_data().get('preferred_connection_uuids', [])
    saved.sort(key=lambda p: (not p['active'],p['uuid'] not in preferred,p['scan'] is None,p['name']))
    return dict(saved=saved,nearby=nearby,enabled=backend.nm('radio','wifi')=='enabled',
                connectivity=backend.nm('networking','connectivity'),paused=(backend.STATE/'hotspot-paused').exists())


def bluetooth_data():
    controller=backend.run('bluetoothctl','show')
    devices=[]
    for line in backend.run('bluetoothctl','devices').splitlines():
        parts=line.split(' ',2)
        if len(parts)!=3: continue
        info=backend.run('bluetoothctl','info',parts[1])
        devices.append(dict(address=parts[1],name=parts[2],connected='Connected: yes' in info,paired='Paired: yes' in info))
    preferred=load_private_data().get('preferred_device_addresses', [])
    devices.sort(key=lambda d:(not d['connected'],d['address'] not in preferred,not d['paired'],d['name']))
    return dict(available=bool(controller),enabled='Powered: yes' in controller,devices=devices)


def settings_data():
    fields=backend.run('brightnessctl','-m').split(',')
    brightness=int(fields[3].rstrip('%')) if len(fields)>3 else None
    battery=next(iter(Path('/sys/class/power_supply').glob('BAT*')),None)
    battery_text=(battery/'capacity').read_text().strip()+'% · '+(battery/'status').read_text().strip() if battery else ''
    try:
        displays=len(display.display_data()['external'])
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        displays=0
    backend_file=Path.home()/'.local/state/rice/ui-backend'
    shell=backend_file.read_text().strip() if backend_file.is_file() else 'lua'
    if shell not in ('lua','quickshell','cpp'):shell='lua'
    return dict(brightness=brightness,battery=battery_text,profile=backend.run('tlpctl','get'),displays=displays,shell=shell,
                time_format=backend.run(str(Path.home()/'.local/bin/rice-clock'),'get') or '24h',media=mpris.options(),
                update=update_check.status())


def media_data():
    return mpris.get_state(('loop','shuffle','metadata'))


# Small widget builders shared by the docked Panel and centered UpdatesOverlay.
def make_label(text,css=None):
    label=Gtk.Label(label=str(text),xalign=0)
    label.set_max_width_chars(28)
    label.set_ellipsize(Pango.EllipsizeMode.END)
    if css:label.get_style_context().add_class(css)
    return label


def make_wrap_label(text,css=None):
    # Update summaries and descriptions run long, so they wrap instead of
    # ellipsizing the way make_label does.
    label=Gtk.Label(label=str(text),xalign=0)
    label.set_line_wrap(True)
    label.set_max_width_chars(44)
    if css:label.get_style_context().add_class(css)
    return label


def make_icon(name,size=20):
    icon=Gtk.Image.new_from_icon_name(name,Gtk.IconSize.BUTTON)
    icon.set_pixel_size(size)
    return icon


def make_icon_button(icon,tip,fn):
    button=Gtk.Button()
    button.get_style_context().add_class('icon-button')
    button.set_tooltip_text(tip)
    button.add(make_icon(icon,16))
    button.connect('clicked',lambda *_:fn())
    return button


def make_section(body,title):
    body.pack_start(make_label(title,'section'),False,False,0)
    group=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
    group.get_style_context().add_class('group')
    body.pack_start(group,False,False,0)
    return group


def make_row(parent,title,subtitle,icon,fn=None,selected=False,tail=None,wrap_title=False,subtitle_emphasis=None):
    row=Gtk.Button() if fn else Gtk.Box()
    row.get_style_context().add_class('device-row')
    if selected:row.get_style_context().add_class('selected')
    box=Gtk.Box(spacing=12)
    box.pack_start(make_icon(icon),False,False,0)
    text=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
    head=make_wrap_label(title,'row-title') if wrap_title else make_label(title,'row-title')
    text.pack_start(head,False,False,0)
    if subtitle:
        sub=make_label(subtitle,'subtitle')
        if subtitle_emphasis and subtitle_emphasis in subtitle:
            before,word,after=subtitle.partition(subtitle_emphasis)
            sub.set_markup(GLib.markup_escape_text(before)+f'<b>{GLib.markup_escape_text(word)}</b>'+GLib.markup_escape_text(after))
        sub.set_tooltip_text(subtitle)
        text.pack_start(sub,False,False,0)
    box.pack_start(text,True,True,0)
    if tail:box.pack_end(tail,False,False,0)
    elif selected:box.pack_end(make_icon('object-select-symbolic',16),False,False,0)
    elif fn:box.pack_end(make_icon('go-next-symbolic',14),False,False,0)
    if fn:
        row.add(box)
        row.connect('clicked',lambda *_:fn())
    else:row.pack_start(box,True,True,0)
    parent.pack_start(row,False,False,0)
    return row


def make_action_button(parent,title,fn,primary=False):
    button=Gtk.Button(label=title)
    button.get_style_context().add_class('primary' if primary else 'secondary')
    button.connect('clicked',lambda *_:fn())
    parent.pack_start(button,False,False,0)
    return button


class Panel(Gtk.ApplicationWindow):
    def __init__(self,app,page):
        super().__init__(application=app)
        self.app=app
        self.set_title('Desktop controls')
        self.set_name('rice-overlay')
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_visual(self.get_screen().get_rgba_visual())
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self,'rice-controls')
        GtkLayerShell.set_layer(self,GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_exclusive_zone(self,-1)
        GtkLayerShell.set_keyboard_mode(self,GtkLayerShell.KeyboardMode.EXCLUSIVE)
        for edge in (GtkLayerShell.Edge.TOP,GtkLayerShell.Edge.BOTTOM,GtkLayerShell.Edge.LEFT,GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self,edge,True)
        # Leave the top strip uncovered so the bar stays clickable while a
        # panel is open (the power button needs three rapid clicks).
        GtkLayerShell.set_margin(self,GtkLayerShell.Edge.TOP,40)
        self.connect('key-press-event',self.key)
        self.connect('destroy',self.cleanup)
        self.generation=0
        self.closed=False
        self.page=None
        self.anchor_left=page=='audio'
        self.timers=set()
        self.pending_values={}
        self.busy=False
        self.history=[]
        self.shell=Gtk.EventBox()
        self.shell.set_visible_window(False)
        self.shell.connect('button-press-event',lambda *_: self.close_panel())
        self.add(self.shell)
        self.revealer=Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.revealer.set_transition_duration(200)
        self.revealer.set_valign(Gtk.Align.START)
        self.revealer.set_halign(Gtk.Align.START if self.anchor_left else Gtk.Align.END)
        self.shell.add(self.revealer)
        self.card=Gtk.EventBox()
        self.card.set_name('panel')
        self.card.set_visible_window(True)
        self.card.connect('button-press-event',lambda *_: True)
        self.card.set_valign(Gtk.Align.START)
        self.card.set_halign(Gtk.Align.END)
        self.card.set_margin_top(6)
        self.card.set_margin_start(10)
        self.card.set_margin_end(10)
        self.card.set_margin_bottom(12)
        self.card.set_size_request(380,-1)
        self.revealer.add(self.card)
        self.layout=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
        self.layout.set_border_width(20)
        self.card.add(self.layout)
        self.header=Gtk.Box(spacing=10)
        self.layout.pack_start(self.header,False,False,0)
        self.back=self.icon_button('go-previous-symbolic','Back',self.go_back)
        self.header.pack_start(self.back,False,False,0)
        self.title=self.label('', 'title')
        self.header.pack_start(self.title,True,True,0)
        self.spinner=Gtk.Spinner()
        self.header.pack_start(self.spinner,False,False,0)
        self.refresh=self.icon_button('view-refresh-symbolic','Refresh',lambda:self.load(self.page,remember=False))
        self.header.pack_start(self.refresh,False,False,0)
        self.header.pack_start(self.icon_button('window-close-symbolic','Close',self.close_panel),False,False,0)
        self.feedback=self.label('', 'feedback')
        self.feedback.set_line_wrap(True)
        self.layout.pack_start(self.feedback,False,False,0)
        self.scroller=Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_propagate_natural_height(True)
        monitor=self.get_display().get_primary_monitor() or self.get_display().get_monitor(0)
        self.scroller.set_max_content_height(max(280,min(680,monitor.get_geometry().height-160)))
        self.layout.pack_start(self.scroller,True,True,0)
        self.body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        self.scroller.add(self.body)
        self.footer=self.label('Esc to close', 'footer')
        self.layout.pack_start(self.footer,False,False,0)
        self.show_all()
        self.feedback.hide()
        self.load(page,remember=False)
        GLib.idle_add(lambda: self.revealer.set_reveal_child(True))

    def cleanup(self,*_):
        self.closed=True
        for timer in list(self.timers): GLib.source_remove(timer)
        self.timers.clear()
        # Apply the final slider position even if the popup closes during debounce.
        for job in list(self.pending_values.values()): POOL.submit(job)
        self.pending_values.clear()

    def close_panel(self,*_):
        if getattr(self,'closing',False):return True
        self.closing=True
        self.revealer.set_reveal_child(False)
        GLib.timeout_add(205,lambda:(self.destroy(),False)[1])
        return True

    def key(self,widget,event):
        if event.keyval==Gdk.KEY_Escape: return self.close_panel()
        if event.keyval==Gdk.KEY_Left and event.state & Gdk.ModifierType.MOD1_MASK:
            self.go_back();return True
        return False

    def label(self,text,css=None):
        return make_label(text,css)

    def icon(self,name,size=20):
        return make_icon(name,size)

    def icon_button(self,icon,tip,fn):
        return make_icon_button(icon,tip,fn)

    def section(self,title):
        return make_section(self.body,title)

    def row(self,parent,title,subtitle,icon,fn=None,selected=False,tail=None):
        return make_row(parent,title,subtitle,icon,fn,selected,tail)

    def switch_row(self,parent,title,subtitle,active,fn,icon):
        switch=Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.set_active(active)
        switch.connect('state-set',lambda _,state:self.switch_action(fn,state))
        self.row(parent,title,subtitle,icon,tail=switch)
        return switch

    def switch_action(self,fn,state):
        fn(state)
        # The default handler must run so the switch actually moves.
        return False

    def slider(self,parent,title,value,maximum,fn,icon='audio-volume-high-symbolic'):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        box.get_style_context().add_class('slider-block')
        head=Gtk.Box(spacing=8)
        head.pack_start(self.icon(icon,16),False,False,0)
        head.pack_start(self.label(title,'row-title'),True,True,0)
        number=self.label(f'{round(value)}%','value')
        head.pack_end(number,False,False,0)
        box.pack_start(head,False,False,0)
        scale=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0 if title!='Brightness' else 2,maximum,1)
        scale.set_value(value)
        scale.set_draw_value(False)
        scale.set_hexpand(True)
        key=id(scale)
        timer=[None]
        def changed(widget):
            value=round(widget.get_value())
            number.set_text(f'{value}%')
            if timer[0]:
                GLib.source_remove(timer[0]);self.timers.discard(timer[0])
            self.pending_values[key]=lambda:fn(value)
            def commit():
                self.timers.discard(timer[0]);timer[0]=None
                job=self.pending_values.pop(key,None)
                if job:self.work(job,refresh=False,busy=False)
                return False
            timer[0]=GLib.timeout_add(90,commit)
            self.timers.add(timer[0])
        scale.connect('value-changed',changed)
        box.pack_start(scale,False,False,0)
        parent.pack_start(box,False,False,0)
        return scale

    def work(self,fn,done=None,refresh=True,busy=True):
        generation=self.generation
        if busy:
            self.busy=True;self.body.set_sensitive(False);self.spinner.start();self.spinner.show()
        future=POOL.submit(fn)
        def complete(f):
            def deliver():
                if self.closed or generation!=self.generation:return False
                if busy:
                    self.busy=False;self.body.set_sensitive(True);self.spinner.stop();self.spinner.hide()
                try:result=f.result()
                except Exception as exc:
                    self.feedback.set_text(str(exc).splitlines()[0][:160]);self.feedback.show();return False
                self.feedback.hide()
                if done:done(result)
                elif refresh:self.load(self.page,remember=False)
                return False
            GLib.idle_add(deliver)
        future.add_done_callback(complete)

    def reset_body(self):
        for child in self.body.get_children():child.destroy()

    def load(self,page,remember=True):
        if remember and self.page:self.history.append(self.page)
        self.page=page
        self.generation+=1
        self.revealer.set_halign(Gtk.Align.START if self.anchor_left else Gtk.Align.END)
        self.title.set_text({'audio':'Sound','network':'Wi-Fi','nearby':'Nearby networks','bluetooth':'Bluetooth','display':'Displays','settings':'Quick settings','power':'Power','code':'VS Code','media':'Media'}.get(page,page))
        self.back.set_visible(bool(self.history))
        self.refresh.set_visible(page not in ('power','confirm'))
        self.feedback.hide()
        self.reset_body()
        self.body.pack_start(self.label('Loading…','subtitle'),False,False,0)
        self.body.show_all()
        loaders={'audio':sound_data,'network':wifi_data,'nearby':wifi_data,'bluetooth':bluetooth_data,'display':display.display_data,'settings':settings_data,'code':CODE['recent_projects'],'media':media_data}
        if page=='power':self.render_power();return
        self.work(loaders[page],done=lambda data:self.render(page,data))

    def go_back(self):
        if self.history:self.load(self.history.pop(),remember=False)
        else:self.close_panel()

    def render(self,page,data):
        self.reset_body()
        getattr(self,'render_'+page)(data)
        self.body.show_all()
        self.back.set_visible(bool(self.history))

    def render_audio(self,data):
        volume=data['volume']
        if not volume:
            self.body.pack_start(self.label('No audio output available','subtitle'),False,False,0);return
        level=round(float(volume.split()[1])*100)
        group=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        group.get_style_context().add_class('group')
        self.body.pack_start(group,False,False,0)
        self.slider(group,'Volume',level,150 if data['boost'] else 100,
                    lambda v:backend.run('wpctl','set-volume','-l','1.5' if backend.BOOST.exists() else '1.0',backend.SINK,f'{v}%',check=True))
        self.switch_row(group,'Mute','', 'MUTED' in volume,lambda state:self.work(lambda:backend.run('wpctl','set-mute',backend.SINK,'1' if state else '0',check=True)),'audio-volume-muted-symbolic')
        self.switch_row(group,'Volume boost','Allow volume above 100%',data['boost'],lambda state:self.work(lambda:backend.audio('boost')),'audio-volume-high-symbolic')
        outputs=self.section('Output device')
        for sink in data['sinks']:
            name,detail,icon=friendly_sink(sink)
            self.row(outputs,name,detail,icon,lambda s=sink:self.work(lambda:route_output(s['name'])),sink['name']==data['default'])
        if data['streams']:
            apps=self.section('Applications')
            for stream in data['streams']:
                name=stream.get('properties',{}).get('application.name','Application')
                level=int(next(iter(stream['volume'].values()))['value_percent'].rstrip('%'))
                self.slider(apps,name,level,100,lambda v,s=stream:backend.run('pactl','set-sink-input-volume',s['index'],f'{v}%',check=True),'multimedia-player-symbolic')

    def wifi_name(self,ssid):
        return load_private_data().get('wifi_labels', {}).get(ssid, ssid)

    def bluetooth_name(self,name):
        return load_private_data().get('bluetooth_labels', {}).get(name, name)

    def signal_icon(self,signal):
        quality='excellent' if signal>=75 else 'good' if signal>=50 else 'ok' if signal>=25 else 'weak'
        return 'network-wireless-signal-'+quality+'-symbolic'

    def render_network(self,data):
        self.wifi=data
        radio=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.body.pack_start(radio,False,False,0)
        self.switch_row(radio,'Wi-Fi','Wireless connections',data['enabled'],lambda state:self.work(lambda:backend.nm('radio','wifi','on' if state else 'off',check=True)),'network-wireless-symbolic')
        group=self.section('Your networks')
        for saved in data['saved']:
            scan=saved['scan']
            detail='Connected' if saved['active'] else ('Available · '+scan[1]+'%' if scan else 'Out of range')
            if saved['active'] and data['connectivity'] in ('limited','portal','none'):detail+=' · No internet'
            # Connect directly; the smaller information button opens management actions.
            holder=Gtk.Box(spacing=2)
            group.pack_start(holder,False,False,0)
            content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            holder.pack_start(content,True,True,0)
            row=self.row(content,self.wifi_name(saved['ssid']),detail,self.signal_icon(int(scan[1])) if scan else 'network-wireless-offline-symbolic',
                         lambda p=saved:self.network_details(p) if p['active'] or not p['scan'] else self.work(lambda:backend.nm('--wait','20','connection','up','uuid',p['uuid'],check=True)),saved['active'])
            row.set_tooltip_text(saved['ssid'])
            info=self.icon_button('view-more-symbolic','Network options',lambda p=saved:self.network_details(p))
            info.set_valign(Gtk.Align.CENTER);holder.pack_end(info,False,False,0)
        self.row(self.body,'Other networks','Find a new connection','list-add-symbolic',lambda:self.load('nearby'))
        self.switch_row(self.body,'Prefer phone hotspot','Connect automatically when it appears',not data['paused'],lambda state:self.work(lambda:self.hotspot(state)),'phone-symbolic')
        self.row(self.body,'Connection details','IP address, gateway and internet status','dialog-information-symbolic',self.diagnostics)

    def hotspot(self,enabled):
        path=backend.STATE/'hotspot-paused'
        if enabled:path.unlink(missing_ok=True)
        else:path.touch()

    def network_details(self,p):
        self.reset_body()
        self.title.set_text(self.wifi_name(p['ssid']))
        self.history.append('network');self.back.show()
        self.row(self.body,p['ssid'],'Connected' if p['active'] else 'Saved network','network-wireless-symbolic')
        self.row(self.body,'Disconnect' if p['active'] else 'Connect','', 'network-wireless-symbolic',lambda:self.work(lambda:backend.nm('connection','down' if p['active'] else 'up','uuid',p['uuid'],check=True),done=lambda _:self.load('network',remember=False)))
        self.row(self.body,'Forget network','Remove the saved connection','edit-delete-symbolic',lambda:self.confirm('Forget this network?',p['ssid'],lambda:self.work(lambda:backend.nm('connection','delete','uuid',p['uuid'],check=True),done=lambda _:self.load('network',remember=False)),'Forget'))
        self.body.show_all()

    def render_nearby(self,data):
        self.row(self.body,'Scan again','Refresh nearby networks','view-refresh-symbolic',lambda:self.work(lambda:backend.nm('device','wifi','rescan',check=True)))
        known={p['ssid']:p for p in data['saved']}
        group=self.section('Available networks')
        for ssid,signal,security in sorted(data['nearby'].values(),key=lambda r:int(r[1]),reverse=True):
            detail=f'{signal}% signal · '+('Open' if security in ('','--') else 'Secured')
            self.row(group,ssid,detail,self.signal_icon(int(signal)),lambda s=ssid,sec=security:self.connect_wifi(s,sec,known.get(s)))
        if not data['nearby']:self.row(group,'No networks found','Turn on Wi-Fi, then scan again','network-wireless-offline-symbolic')

    def connect_wifi(self,ssid,security,known):
        if known:
            self.work(lambda:backend.nm('--wait','20','connection','up','uuid',known['uuid'],check=True),done=lambda _:self.load('network',remember=False));return
        if security in ('','--'):
            self.work(lambda:backend.nm('device','wifi','connect',ssid,check=True),done=lambda _:self.load('network',remember=False));return
        self.reset_body();self.title.set_text('Join network')
        self.row(self.body,ssid,'Enter the network password','network-wireless-symbolic')
        entry=Gtk.Entry();entry.set_visibility(False);entry.set_placeholder_text('Password');entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.body.pack_start(entry,False,False,0)
        def join():
            password=entry.get_text()
            if not password:return
            def connect():
                p=subprocess.run(['nmcli','--ask','device','wifi','connect',ssid],input=password+'\n',text=True,capture_output=True,timeout=60)
                if p.returncode:raise RuntimeError('Could not connect. Check the password and try again.')
            self.work(connect,done=lambda _:self.load('network',remember=False))
        self.action_button(self.body,'Connect',join,primary=True)
        entry.connect('activate',lambda *_:join())
        self.body.show_all();entry.grab_focus()

    def diagnostics(self):
        def data():
            devices=[backend.fields(line) for line in backend.nm('-t','-f','DEVICE,TYPE,STATE','device').splitlines()]
            lines=[]
            for d in devices:
                if len(d)==3 and d[1] in ('wifi','ethernet') and d[2]=='connected':
                    for prop,title in [('GENERAL.CONNECTION','Connection'),('IP4.ADDRESS','Address'),('IP4.GATEWAY','Gateway'),('IP4.DNS','DNS')]:
                        lines.append((title,backend.nm('-g',prop,'device','show',d[0])))
            return [('Internet',backend.nm('networking','connectivity','check'))]+lines
        def show(lines):
            self.reset_body();self.title.set_text('Connection details');self.history.append('network');self.back.show()
            for title,value in lines:self.row(self.body,title,value or 'Unavailable','dialog-information-symbolic')
            self.body.show_all()
        self.work(data,done=show)

    def render_bluetooth(self,data):
        if not data['available']:
            self.row(self.body,'Bluetooth unavailable','No adapter detected','bluetooth-disabled-symbolic');return
        self.switch_row(self.body,'Bluetooth','Discover and connect devices',data['enabled'],lambda state:self.work(lambda:backend.run('bluetoothctl','power','on' if state else 'off',check=True)),'bluetooth-symbolic')
        group=self.section('Devices')
        for device in data['devices']:
            detail='Connected' if device['connected'] else ('Paired · Click to connect' if device['paired'] else 'New device · Click to pair')
            holder=Gtk.Box(spacing=2);group.pack_start(holder,False,False,0)
            content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);holder.pack_start(content,True,True,0)
            self.row(content,self.bluetooth_name(device['name']),detail,'bluetooth-symbolic',lambda d=device:self.bluetooth_device(d),device['connected'])
            options=self.icon_button('view-more-symbolic','Device options',lambda d=device:self.bluetooth_details(d))
            options.set_valign(Gtk.Align.CENTER);holder.pack_end(options,False,False,0)
        if not data['devices']:self.row(group,'No devices yet','Put your device in pairing mode','bluetooth-symbolic')
        self.row(self.body,'Add a device','Scan nearby · about 8 seconds','list-add-symbolic',self.scan_bluetooth)
        self.row(self.body,'Audio output','Choose where sound plays','audio-headphones-symbolic',lambda:self.load('audio'))

    def scan_bluetooth(self):
        def scan():
            backend.run('bluetoothctl','power','on',check=True)
            backend.run('bluetoothctl','--timeout','8','scan','on',timeout=12)
        self.work(scan)

    def bluetooth_device(self,d):
        if not d['connected']:
            if d['paired']:self.work(lambda:backend.run('bluetoothctl','connect',d['address'],check=True))
            else:
                # Release exclusive keyboard focus so the BlueZ agent's confirmation can appear.
                self.close_panel()
                subprocess.Popen(['python3',str(ROOT/'bluetooth_pair.py'),d['address']],start_new_session=True)
            return
        self.bluetooth_details(d)

    def bluetooth_details(self,d):
        self.reset_body();self.title.set_text(self.bluetooth_name(d['name']));self.history.append('bluetooth');self.back.show()
        self.row(self.body,'Disconnect' if d['connected'] else 'Connect','Keep this device paired','bluetooth-symbolic',lambda:self.work(lambda:backend.run('bluetoothctl','disconnect' if d['connected'] else 'connect',d['address'],check=True),done=lambda _:self.load('bluetooth',remember=False)))
        self.row(self.body,'Forget device','Pair again to reconnect','edit-delete-symbolic',lambda:self.confirm('Forget device?',d['name'],lambda:self.work(lambda:backend.run('bluetoothctl','remove',d['address'],check=True),done=lambda _:self.load('bluetooth',remember=False)),'Forget'))
        self.body.show_all()

    def render_settings(self,data):
        update=data.get('update') or {}
        group=self.section('Rice update')
        waiting=update_check.pending_updates(update)
        if waiting:
            # The row exists only while an update is still new; Ignore flips it
            # out of sight and the update stays in Update history.
            sha,entry=waiting[0]
            detail=entry.get('summary') or 'New commits ready'
            if len(waiting)>1:detail=f"{len(waiting)} new updates · {detail}"
            # Ignore sits beside Download, not inside it: one button cannot
            # contain another, and it needs its own click target.
            holder=Gtk.Box(spacing=6)
            group.pack_start(holder,False,False,0)
            content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            holder.pack_start(content,True,True,0)
            self.row(content,'Download update',detail,'software-update-available-symbolic',
                     lambda s=sha:self.app.open_updates(s))
            ignore=Gtk.Button(label='Ignore')
            ignore.get_style_context().add_class('secondary')
            ignore.set_valign(Gtk.Align.CENTER)
            ignore.set_tooltip_text('Hide this update · it stays in Update history')
            ignore.connect('clicked',lambda *_,s=sha:self.work(lambda:update_check.ignore(s)))
            holder.pack_end(ignore,False,False,0)
        elif update.get('available'):
            # Offline fallback: the head moved but no commit messages were read yet.
            self.row(group,'Download update','New commits ready','software-update-available-symbolic',
                     lambda:self.app.open_updates(update.get('sha','')))
        elif update.get('error'):
            self.row(group,'Update check failed',update['error'],'dialog-information-symbolic',
                     lambda:self.work(lambda:update_check.check()))
        else:
            checked=update_check.ago(update.get('checked'))
            self.row(group,'Rice is up to date',
                     f'Last checked {checked} · check again' if checked else 'Check now · checked every 30 minutes',
                     'view-refresh-symbolic',lambda:self.work(lambda:update_check.check()))
        group=self.section('Clock · change this anytime')
        choices=Gtk.Box(spacing=5);choices.set_homogeneous(True);group.pack_start(choices,False,False,0)
        for value,label in [('24h','24 hour · 21:30'),('12h','12 hour · 09:30 PM')]:
            self.action_button(choices,label,lambda v=value:self.work(lambda:backend.run(str(Path.home()/'.local/bin/rice-clock'),'set',v,check=True)),primary=data['time_format']==value)
        if data['brightness'] is not None:
            group=self.section('Display')
            self.slider(group,'Brightness',data['brightness'],100,lambda v:backend.run('brightnessctl','set',f'{v}%',check=True),'display-brightness-symbolic')
        power=self.section('Power mode')
        choices=Gtk.Box(spacing=5);choices.set_homogeneous(True);power.pack_start(choices,False,False,0)
        for label,profile in [('Saver','power-saver'),('Balanced','balanced'),('Fast','performance')]:
            self.action_button(choices,label,lambda p=profile:self.work(lambda:backend.run('tlpctl','set',p,check=True)),primary=data['profile']==profile)
        shell=self.section('Desktop shell')
        for key,label,icon,sub in [('lua','Lua / Waybar','preferences-system-symbolic','Full bar generated from Lua sources'),
                                   ('quickshell','QuickShell','view-grid-symbolic','QML bar with live reload'),
                                   ('cpp','C++ / ASM','applications-engineering-symbolic','Native GTK bar with x86-64 ASM contrast')]:
            self.row(shell,label,sub,icon,lambda k=key:self.switch_shell(k),selected=data['shell']==key)
        media=self.section('Media sources')
        for key,label,detail in [('desktop_spotify','Spotify app','Show its playback controls while open'),
                                 ('browser_media','Browser players','Spotify Web, SoundCloud, YouTube Music and other MPRIS sites')]:
            self.switch_row(media,label,detail,bool(data['media'].get(key,False)),
                lambda state,k=key:self.work(lambda:backend.run(str(Path.home()/'.local/bin/rice-media'),'set',k,'on' if state else 'off',check=True)),
                'audio-x-generic-symbolic')
        group=self.section('Quick controls')
        for name,detail,icon,page in [('Sound','Volume and output devices','audio-volume-high-symbolic','audio'),('Wi-Fi','Networks and connection','network-wireless-symbolic','network'),('Bluetooth','Headphones and other devices','bluetooth-symbolic','bluetooth')]:
            self.row(group,name,detail,icon,lambda p=page:self.load(p))
        self.row(group,'Media','Playback and source controls','media-playback-start-symbolic',lambda:self.load('media'))
        if data['displays']:
            self.row(group,'Displays',f"{data['displays']} external display{'s' if data['displays'] != 1 else ''} connected",'video-display-symbolic',lambda:self.load('display'))
        if data['battery']:self.row(self.body,'Battery',data['battery'],'battery-good-symbolic')
        self.row(self.body,'System monitor','CPU, memory and processes','power-profile-performance-symbolic',lambda:self.launch(['kitty','btop']))
        self.row(self.body,'Desktop configuration','Personalize this desktop','preferences-system-symbolic',lambda:self.launch(['code',str(Path.home()/'.local/share/rice/source')]))
        self.row(self.body,'Share an idea','Suggest a feature or improvement on GitHub','chat-message-new-symbolic',lambda:self.open_url(update_check.ISSUES))
        # Bottom of Settings: the full history lives in a centered overlay.
        self.row(self.body,'Update history','Every update · new, old and ignored','document-open-recent-symbolic',lambda:self.app.open_updates())

    def open_url(self,url):
        try:
            Gio.AppInfo.launch_default_for_uri(url,None)
            self.close_panel()
        except GLib.Error:
            self.launch(['xdg-open',url])

    def switch_shell(self,choice):
        # ui-backend validates the choice, persists it and restarts the bar.
        self.work(lambda:backend.run(str(Path.home()/'.local/bin/ui-backend'),choice,check=True),
                  done=lambda _:self.load('settings',remember=False))

    def render_media(self,data):
        if not data:
            self.row(self.body,'No player active','Enable Spotify or browser media in Quick settings','audio-x-generic-symbolic')
            return
        name=data['_name']
        meta=data.get('Metadata') or {}
        title=meta.get('xesam:title') or 'Current track'
        artist=meta.get('xesam:artist') or ''
        self.row(self.body,'Spotify' if name=='spotify' else 'Browser media',
                 f'{artist} · {title}' if artist else title,'audio-x-generic-symbolic')
        group=self.section('Playback')
        for label,action,icon in [('Previous','previous','media-skip-backward-symbolic'),
                                  ('Play / pause','toggle','media-playback-start-symbolic'),
                                  ('Next','next','media-skip-forward-symbolic')]:
            self.row(group,label,'',icon,lambda a=action:self.work(lambda:backend.run(str(Path.home()/'.local/bin/rice-media'),a,check=True)))
        if data.get('Shuffle') in ('On','Off'):
            self.row(group,'Shuffle','On' if data['Shuffle']=='On' else 'Off','media-playlist-shuffle-symbolic',
                     lambda:self.work(lambda:backend.run(str(Path.home()/'.local/bin/waybar-spotify'),'--toggle-shuffle',check=True)))
        if data.get('LoopStatus') in ('None','Playlist','Track'):
            self.row(group,'Repeat',data['LoopStatus'],'media-playlist-repeat-symbolic',
                     lambda:self.work(lambda:backend.run(str(Path.home()/'.local/bin/waybar-spotify'),'--cycle-repeat',check=True)))

    def render_display(self,data):
        internal=data['internal']
        if internal:
            group=self.section('Laptop')
            self.row(group,internal.get('model') or internal['name'],
                     f"{internal['name']} · {internal['width']}×{internal['height']} · {internal['scale']}× scale",
                     'computer-symbolic')
        if not data['external']:
            self.row(self.body,'No external display','Connect HDMI, DisplayPort or USB-C','video-display-symbolic')
            return
        for monitor in data['external']:
            group=self.section(monitor.get('model') or monitor['name'])
            mirrored=bool(internal and str(monitor['mirrorOf']) in (str(internal['id']),internal['name']))
            current='Mirroring laptop' if mirrored else 'Extended desktop'
            self.row(group,monitor['name'],
                     f"{current} · {monitor['width']}×{monitor['height']} · {monitor['refreshRate']:.0f} Hz",
                     'video-display-symbolic')
            actions=Gtk.Box(spacing=6)
            actions.set_homogeneous(True)
            group.pack_start(actions,False,False,0)
            if internal:
                self.action_button(actions,'Mirror laptop',
                                   lambda name=monitor['name']:self.work(lambda:display.apply_layout(name,'mirror')),
                                   primary=mirrored)
            self.action_button(actions,'Extend right',
                               lambda name=monitor['name']:self.work(lambda:display.apply_layout(name,'extend')),
                               primary=not mirrored)

    def action_button(self,parent,title,fn,primary=False):
        return make_action_button(parent,title,fn,primary)

    def render_power(self):
        self.reset_body();self.spinner.stop();self.spinner.hide();self.body.set_sensitive(True)
        group=self.section('Session')
        for name,detail,icon,fn in [('Lock','Keep your session running','system-lock-screen-symbolic',lambda:self.launch([str(Path.home()/'.local/bin/lock-screen')])),('Sleep','Resume where you left off','weather-clear-night-symbolic',lambda:self.work(lambda:backend.run('systemctl','suspend',check=True),done=lambda _:self.close_panel()))]:
            self.row(group,name,detail,icon,fn)
        group=self.section('Power')
        for name,detail,icon,cmd in [('Log out','End the current session','system-log-out-symbolic',['hyprctl','dispatch','hl.dsp.exit()']),('Restart','Restart this computer','system-reboot-symbolic',['systemctl','reboot']),('Shut down','Power off this computer','system-shutdown-symbolic',['systemctl','poweroff'])]:
            self.row(group,name,detail,icon,lambda n=name,c=cmd:self.confirm(n+'?','Save your work before continuing.',lambda:self.work(lambda:backend.run(*c,check=True),done=lambda _:self.close_panel()),n))
        self.body.show_all()

    def confirm(self,title,detail,fn,verb):
        self.reset_body();self.title.set_text(title)
        self.body.pack_start(self.label(detail,'subtitle'),False,False,0)
        actions=Gtk.Box(spacing=10)
        self.body.pack_start(actions,False,False,0)
        cancel=self.action_button(actions,'Cancel',lambda:self.load(self.page,remember=False))
        self.action_button(actions,verb,fn,primary=True)
        actions.set_homogeneous(True)
        self.body.show_all();cancel.grab_focus()

    def render_code(self,projects):
        group=self.section('Open')
        self.row(group,'Continue in VS Code','Focus your most recent window','utilities-terminal-symbolic',lambda:self.call_and_close(CODE['focus']))
        self.row(group,'Open folder','Choose a project on this computer','folder-open-symbolic',lambda:self.pick_folder())
        self.row(group,'New window','Start with an empty editor','window-new-symbolic',lambda:self.launch(['code','--new-window']))
        if projects:
            group=self.section('Recent projects')
            for path in projects[:5]:
                self.row(group,Path(path).name,str(Path(path).parent).replace(str(Path.home()),'~'),'folder-symbolic',lambda p=path:self.launch(['code','--new-window',p]))
        self.row(self.body,'More project actions','Workspaces and desktop configuration','view-more-symbolic',lambda:self.launch([str(Path.home()/'.local/bin/vscode-menu'),'legacy']))

    def pick_folder(self):
        self.close_panel()
        subprocess.Popen([str(Path.home()/'.local/bin/vscode-menu'),'folder'],start_new_session=True)

    def launch(self,args):
        subprocess.Popen(args,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.close_panel()

    def call_and_close(self,fn):
        fn();self.close_panel()


class UpdatesOverlay(Gtk.Window):
    """Centered update window: the full history, or one update's details.

    A layer surface with no anchored edge lands in the middle of the screen,
    like a floating terminal; Panel docks to the right edge instead. App opens
    it only after closing the panel, because one surface owns the keyboard.
    """

    def __init__(self,app,sha=None):
        super().__init__(application=app)
        self.set_title('Rice updates')
        self.set_name('rice-overlay')
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_visual(self.get_screen().get_rgba_visual())
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self,'rice-updates')
        GtkLayerShell.set_layer(self,GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self,GtkLayerShell.KeyboardMode.EXCLUSIVE)
        self.connect('key-press-event',self.key)
        card=Gtk.EventBox()
        card.set_name('panel')
        card.set_visible_window(True)
        card.connect('button-press-event',lambda *_:True)
        card.set_size_request(440,-1)
        self.add(card)
        self.layout=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
        self.layout.set_border_width(20)
        card.add(self.layout)
        self.header=Gtk.Box(spacing=10)
        self.layout.pack_start(self.header,False,False,0)
        self.back=make_icon_button('go-previous-symbolic','Back',self.history)
        self.header.pack_start(self.back,False,False,0)
        self.heading=make_label('','title')
        self.header.pack_start(self.heading,True,True,0)
        self.header.pack_start(make_icon_button('window-close-symbolic','Close',self.destroy),False,False,0)
        self.feedback=make_label('','feedback')
        self.feedback.set_line_wrap(True)
        self.layout.pack_start(self.feedback,False,False,0)
        self.scroller=Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_propagate_natural_height(True)
        monitor=self.get_display().get_primary_monitor() or self.get_display().get_monitor(0)
        self.scroller.set_min_content_height(240)
        self.scroller.set_max_content_height(max(240,min(640,monitor.get_geometry().height-200)))
        self.layout.pack_start(self.scroller,True,True,0)
        self.body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.scroller.add(self.body)
        self.footer=make_label('Esc to close','footer')
        self.layout.pack_start(self.footer,False,False,0)
        self.show_all()
        self.feedback.hide()
        self.back.hide()
        if sha:self.detail(sha)
        else:self.history()

    def key(self,widget,event):
        if event.keyval==Gdk.KEY_Escape:
            self.destroy();return True
        if event.keyval==Gdk.KEY_Left and event.state & Gdk.ModifierType.MOD1_MASK:
            if self.back.get_visible():self.history()
            return True
        return False

    def reset(self):
        for child in self.body.get_children():child.destroy()
        self.feedback.hide()

    def history(self):
        """Every known update, newest first, with its (optional)/(recommended) tag."""
        self.reset()
        self.scroller.set_min_content_height(400)
        self.heading.set_text('Update history')
        self.back.hide()
        state=update_check.status()
        entries=sorted(state['updates'].items(),key=lambda item:item[1].get('when') or 0,reverse=True)
        if not entries:
            self.body.pack_start(make_label('No updates recorded yet','subtitle'),False,False,0)
        for sha,entry in entries:
            tag='(optional)' if entry.get('kind')=='optional' else '(recommended)'
            if entry.get('applied'):status='applied '+update_check.ago(entry['applied'])
            elif entry.get('new'):status='new · waiting under Download update'
            else:status='ignored · still downloadable'
            make_row(self.body,entry.get('summary') or 'Rice update',f'{tag} · {status}',
                     'software-update-available-symbolic',lambda s=sha:self.detail(s),wrap_title=True,
                     subtitle_emphasis='ignored' if not entry.get('applied') and not entry.get('new') else None)
        self.body.show_all()
        self.footer.set_text(f'{len(entries)} update{"s" if len(entries)!=1 else ""} · Esc to close')

    def detail(self,sha):
        """One update: summary, the long description and the download action."""
        self.reset()
        self.scroller.set_min_content_height(260)
        state=update_check.status()
        entry=dict(state['updates'].get(sha) or {})
        summary=(entry.get('summary') or (state.get('subject') or '').strip() or 'Rice update')
        tag='(optional)' if entry.get('kind')=='optional' else '(recommended)'
        self.heading.set_text('Update details')
        self.back.show()
        meta=tag+(f' · {sha}' if sha else '')
        if entry.get('when'):meta+=f' · published {update_check.ago(entry["when"])}'
        self.body.pack_start(make_label(meta,'subtitle'),False,False,0)
        self.body.pack_start(make_wrap_label(summary,'row-title'),False,False,0)
        self.body.pack_start(make_wrap_label(entry.get('detail') or summary),False,False,0)
        if entry.get('applied'):
            self.body.pack_start(make_label('Applied '+update_check.ago(entry['applied']),'subtitle'),False,False,0)
        elif not entry.get('new'):
            self.body.pack_start(make_label('Ignored · not offered at the top of Settings','subtitle'),False,False,0)
        actions=Gtk.Box(spacing=10)
        actions.set_homogeneous(True)
        self.body.pack_start(actions,False,False,0)
        if not entry.get('applied'):
            make_action_button(actions,'Download',self.download,primary=True)
        make_action_button(actions,'Close',self.destroy)
        self.body.show_all()
        self.footer.set_text('Esc to close')

    def download(self):
        # The installer restarts rice-controls, so the pull runs in its own
        # on-demand service instead of inside this window.
        try:
            backend.run('systemctl','--user','start','--no-block','rice-update.service',check=True)
        except Exception as exc:
            self.feedback.set_text(str(exc).splitlines()[0][:160])
            self.feedback.show()
            return
        self.destroy()


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.nestea.DesktopControls',flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.panel=None
        self.overlay=None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        for page in ('audio','network','bluetooth','display','settings','power','code','media','updates'):
            action=Gio.SimpleAction.new(page,None)
            action.connect('activate',lambda _a,_p,p=page:self.show(p))
            self.add_action(action)
        Gtk.Settings.get_default().set_property('gtk-icon-theme-name','Adwaita')
        Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',True)
        css=Gtk.CssProvider();css.load_from_path(str(ROOT/'panels.css'))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def show(self,page):
        if page=='updates':
            self.open_updates();return
        # Panel and overlay never share the screen: one surface owns the keyboard.
        self.close_overlay()
        if self.panel and not self.panel.closed:
            if self.panel.page==page:self.panel.close_panel()
            else:
                self.panel.history=[];self.panel.anchor_left=page=='audio';self.panel.load(page,remember=False)
        else:
            self.hold()
            self.panel=Panel(self,page)
            self.panel.connect('destroy',lambda *_:self.release())
            self.panel.present()

    def open_updates(self,sha=None):
        """Centered overlay: the full update history, or one update's detail.

        Closing Settings (and any open updates window) first is the point:
        clicking Download update swaps one surface for the other.
        """
        if self.panel and not self.panel.closed:self.panel.close_panel()
        self.close_overlay()
        self.hold()
        self.overlay=UpdatesOverlay(self,sha)
        self.overlay.connect('destroy',self._overlay_closed)
        self.overlay.present()

    def close_overlay(self,*_):
        if self.overlay is not None:self.overlay.destroy()
        return False

    def _overlay_closed(self,*_):
        self.overlay=None
        self.release()

    def do_command_line(self,cmd):
        args=cmd.get_arguments();page=args[1] if len(args)>1 else 'settings'
        if page=='--daemon':
            self.hold()
            return 0
        if page not in ('audio','network','bluetooth','display','settings','power','code','media','updates'):return 1
        self.show(page)
        return 0

if __name__=='__main__':
    app=App()
    app.run(sys.argv)
    POOL.shutdown(wait=True)
