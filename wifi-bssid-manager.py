#!/usr/bin/python3
"""NetworkManager D-Bus tray: pin current BSSID, or clear every saved Wi-Fi pin."""
import math
import os
import re
import struct
import sys
import tempfile
import zlib

import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AyatanaAppIndicator3 as Indicator

NM = 'org.freedesktop.NetworkManager'
ROOT = '/org/freedesktop/NetworkManager'
DEV = NM + '.Device'
WIFI = DEV + '.Wireless'
AP = NM + '.AccessPoint'
ACTIVE = NM + '.Connection.Active'
SETTINGS_ROOT = NM + '.Settings'
CONN = SETTINGS_ROOT + '.Connection'
PROPS = 'org.freedesktop.DBus.Properties'
DBUS = 'org.freedesktop.DBus'
BSSID_PATTERN = re.compile(r'^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$', re.I)


def read_bssid(settings):
    raw = settings.get('802-11-wireless', {}).get('bssid', [])
    try:
        data = bytes(raw)
    except (TypeError, ValueError):
        return ''
    return ':'.join(f'{x:02x}' for x in data) if len(data) == 6 else ''


def bssid_bytes(bssid):
    return dbus.ByteArray(bytes.fromhex(bssid.replace(':', '')))


ICON_NAME = 'wifi-roam-toggle-custom'


def create_tray_icon():
    """Draw a distinct Wi-Fi + orange location pin icon, with no image assets.

    The icon is generated in a private temporary directory for the life of
    the application and registered as an additional AppIndicator icon path.
    """
    size = 64
    scale = 3
    n = size * scale
    pixels = bytearray(size * size * 4)

    def sample(x, y):
        # Transparent outside the dark circular background.
        if (x - 32) ** 2 + (y - 32) ** 2 > 29 ** 2:
            return (0, 0, 0, 0)
        color = (28, 43, 65, 255)

        # Wi-Fi waves: white upper semicircular arcs.
        dx, dy = x - 32, y - 37
        radius = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(dy, dx)) % 360
        if 202 <= angle <= 338 and (abs(radius - 20) < 2.2 or abs(radius - 12) < 2.2):
            color = (246, 249, 255, 255)
        if dx * dx + (y - 34) ** 2 < 2.9 ** 2:
            color = (246, 249, 255, 255)

        # Orange map-pin silhouette, below the Wi-Fi symbol.
        pin_circle = (x - 32) ** 2 + (y - 43) ** 2 < 7.4 ** 2
        pin_tip = 43 <= y <= 56 and abs(x - 32) <= 7.4 * (56 - y) / 13
        if pin_circle or pin_tip:
            color = (255, 177, 49, 255)
        if (x - 32) ** 2 + (y - 42) ** 2 < 3.2 ** 2:
            color = (28, 43, 65, 255)
        return color

    for py in range(size):
        for px in range(size):
            channels = [0, 0, 0, 0]
            for sy in range(scale):
                for sx in range(scale):
                    rgba = sample(px + (sx + .5) / scale, py + (sy + .5) / scale)
                    for k in range(4):
                        channels[k] += rgba[k]
            offset = (py * size + px) * 4
            pixels[offset:offset + 4] = bytes(c // (scale * scale) for c in channels)

    # Encode RGBA PNG with standard library only.
    def chunk(kind, payload):
        return (struct.pack('!I', len(payload)) + kind + payload +
                struct.pack('!I', zlib.crc32(kind + payload) & 0xffffffff))

    scanlines = b''.join(b'\x00' + bytes(pixels[y * size * 4:(y + 1) * size * 4])
                         for y in range(size))
    png = (b'\x89PNG\r\n\x1a\n' +
           chunk(b'IHDR', struct.pack('!2I5B', size, size, 8, 6, 0, 0, 0)) +
           chunk(b'IDAT', zlib.compress(scanlines, 9)) +
           chunk(b'IEND', b''))
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    directory = tempfile.mkdtemp(prefix='wifi-roam-toggle-', dir=runtime if runtime and
                                 os.path.isdir(runtime) else None)
    image_path = os.path.join(directory, ICON_NAME + '.png')
    with open(image_path, 'wb') as file:
        file.write(png)
    return directory


class Tray:
    def __init__(self, ifname=None):
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.ifname = ifname
        self.selected_ifname = ifname
        self.busy = False
        self.pending_refresh = False
        self.current = None
        self.operation = None
        self.check_timer = None
        self.check_attempts = 0

        self.icon_dir = create_tray_icon()
        self.indicator = Indicator.Indicator.new_with_path(
            'wifi-roam-toggle', ICON_NAME,
            Indicator.IndicatorCategory.SYSTEM_SERVICES, self.icon_dir)
        self.indicator.set_icon_full(ICON_NAME, 'Wi-Fi BSSID固定ツール')
        self.indicator.set_status(Indicator.IndicatorStatus.ACTIVE)
        # Indicator label is intentionally unused: some trays concatenate labels
        # on each refresh, creating repeated '固定設定: 1件' text.
        self.menu = Gtk.Menu()
        self.pin_item = Gtk.MenuItem(label='現在の接続先のBSSIDを固定化して，Wi-Fiを再接続する')
        self.pin_item.connect('activate', self.pin_current)
        self.menu.append(self.pin_item)
        self.clear_item = Gtk.MenuItem(label='全ての接続先プロファイルからBSSID設定を削除して，Wi-Fiを再接続する')
        self.clear_item.connect('activate', self.clear_all)
        self.menu.append(self.clear_item)
        self.menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label='終了')
        quit_item.connect('activate', lambda *_: Gtk.main_quit())
        self.menu.append(quit_item)
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        # Signals are debounced. No continuous polling except while reconnecting.
        self.bus.add_signal_receiver(self.on_changed, signal_name='PropertiesChanged',
                                     dbus_interface=PROPS, bus_name=NM)
        for signal in ('Updated', 'Removed'):
            self.bus.add_signal_receiver(self.on_changed, signal_name=signal,
                                         dbus_interface=CONN, bus_name=NM)
        for signal in ('NewConnection', 'ConnectionRemoved'):
            self.bus.add_signal_receiver(self.on_changed, signal_name=signal,
                                         dbus_interface=SETTINGS_ROOT, bus_name=NM)
        self.bus.add_signal_receiver(self.on_changed, signal_name='NameOwnerChanged',
                                     dbus_interface=DBUS, arg0=NM)
        self.refresh()


    def proxy(self, path):
        return self.bus.get_object(NM, str(path))

    def prop(self, path, interface, name):
        return dbus.Interface(self.proxy(path), PROPS).Get(interface, name)

    def on_changed(self, *_):
        if self.busy or self.pending_refresh:
            return
        self.pending_refresh = True
        GLib.timeout_add(200, self.refresh_delayed)

    def refresh_delayed(self):
        self.pending_refresh = False
        if not self.busy:
            self.refresh()
        return False

    def find_device(self):
        mgr = dbus.Interface(self.proxy(ROOT), NM)
        if self.ifname:
            path = str(mgr.GetDeviceByIpIface(self.ifname))
            if int(self.prop(path, DEV, 'DeviceType')) != 2:
                raise RuntimeError(f'{self.ifname} はWi-Fiデバイスではありません')
            return path, self.ifname
        devices = []
        for p in mgr.GetDevices():
            p = str(p)
            if int(self.prop(p, DEV, 'DeviceType')) == 2:
                devices.append((p, str(self.prop(p, DEV, 'Interface')),
                                int(self.prop(p, DEV, 'State'))))
        if not devices:
            return None, None
        connected = sorted((x for x in devices if x[2] == 100), key=lambda x: x[1])
        if connected:
            primary = str(self.prop(ROOT, NM, 'PrimaryConnection'))
            if primary != '/':
                member_devices = {str(p) for p in self.prop(primary, ACTIVE, 'Devices')}
                for device in connected:
                    if device[0] in member_devices:
                        return device[0], device[1]
            return connected[0][0], connected[0][1]
        first = min(devices, key=lambda x: x[1])
        return first[0], first[1]

    def get_current(self):
        device, name = self.find_device()
        self.selected_ifname = name
        if not device:
            return None
        active = str(self.prop(device, DEV, 'ActiveConnection'))
        ap = str(self.prop(device, WIFI, 'ActiveAccessPoint'))
        if active == '/' or ap == '/' or int(self.prop(device, DEV, 'State')) != 100:
            return None
        profile = str(self.prop(active, ACTIVE, 'Connection'))
        ssid = bytes(self.prop(ap, AP, 'Ssid')).decode('utf-8', 'replace')
        bssid = str(self.prop(ap, AP, 'HwAddress')).lower()
        saved = read_bssid(dbus.Interface(self.proxy(profile), CONN).GetSettings())
        return {'device': device, 'name': name, 'active': active,
                'profile': profile, 'ssid': ssid, 'bssid': bssid, 'saved': saved}

    def wifi_profiles(self):
        """Return saved Wi-Fi profiles independently of active connectivity."""
        paths = dbus.Interface(self.proxy('/org/freedesktop/NetworkManager/Settings'),
                               SETTINGS_ROOT).ListConnections()
        found = []
        for p in paths:
            p = str(p)
            settings = dbus.Interface(self.proxy(p), CONN).GetSettings()
            kind = str(settings.get('connection', {}).get('type', ''))
            if kind not in ('802-11-wireless', 'wifi'):
                continue
            found.append((p, settings, read_bssid(settings)))
        return found

    def show_message(self, text):
        # Status is reflected by menu availability; no status rows.
        print(f"wifi-bssid-manager: {text}", file=sys.stderr)

    def refresh(self):
        if self.busy:
            return
        try:
            profiles = self.wifi_profiles()
            pinned = [(p, s, mac) for p, s, mac in profiles if mac]
            self.current = self.get_current()
            state = self.current
            if state:
                same = state['saved'].lower() == state['bssid'].lower()
                self.pin_item.set_label(
                    f"現在の接続先({state['ssid']})のBSSID({state['bssid']})を固定化して，Wi-Fiを再接続する")
                self.pin_item.set_sensitive(not self.busy and not same and
                                            bool(BSSID_PATTERN.fullmatch(state['bssid'])))
            else:
                self.pin_item.set_label('現在の接続先(未接続)のBSSIDを固定化する')
                self.pin_item.set_sensitive(False)
            self.clear_item.set_sensitive(bool(pinned) and not self.busy)
            # Menu labels are derived from current state.
        except Exception as exc:
            self.current = None
            self.pin_item.set_sensitive(False)
            self.clear_item.set_sensitive(False)
            print(f'wifi-bssid-manager: {exc}', file=sys.stderr)

    def set_busy(self, message):
        self.busy = True
        self.pin_item.set_sensitive(False)
        self.clear_item.set_sensitive(False)

    def pin_current(self, *_):
        if self.busy:
            return
        try:
            current = self.get_current()
            if not current or not BSSID_PATTERN.fullmatch(current['bssid']):
                raise RuntimeError('Wi-Fi接続中のみ固定できます')
            if current['saved'] == current['bssid']:
                return
            self.set_busy('現在のAPに固定中…')
            self.operation = {'kind': 'pin', 'current': current, 'failures': []}
            settings = dbus.Interface(self.proxy(current['profile']), CONN).GetSettings()
            settings['802-11-wireless']['bssid'] = bssid_bytes(current['bssid'])
            self.save_profile(current['profile'], settings, self.pin_saved)
        except Exception as exc:
            self.finish_error('BSSID固定を開始できません', exc)

    def clear_all(self, *_):
        if self.busy:
            return
        try:
            profiles = [(p, s) for p, s, mac in self.wifi_profiles() if mac]
            if not profiles:
                self.refresh()
                return
            current = self.get_current()
            # Retain the current active profile for an intentional reconnect.
            reconnect = current if current and any(p == current['profile'] for p, _ in profiles) else None
            self.set_busy(f'BSSID固定を解除中（{len(profiles)}件）…')
            self.operation = {'kind': 'clear', 'remaining': profiles,
                              'cleared': 0, 'failures': [], 'current': reconnect}
            self.clear_next()
        except Exception as exc:
            self.finish_error('固定解除を開始できません', exc)

    def save_profile(self, profile, settings, success):
        # Update2 replaces the settings: GetSettings() is used to preserve all
        # other known properties; disk persistence is requested explicitly.
        conn = dbus.Interface(self.proxy(profile), CONN)
        conn.Update2(settings, dbus.UInt32(1), dbus.Dictionary({}, signature='sv'),
                     reply_handler=lambda result: success(),
                     error_handler=lambda exc: self.save_failed(profile, exc),
                     timeout=25)

    def save_failed(self, profile, error):
        if not self.operation:
            return
        if self.operation['kind'] == 'pin':
            self.finish_error('固定設定の保存に失敗しました', error)
            return
        self.operation['failures'].append(f'{profile}: {error}')
        self.clear_next()

    def pin_saved(self):
        self.reconnect()

    def clear_next(self):
        op = self.operation
        if not op or op['kind'] != 'clear':
            return
        if not op['remaining']:
            if op['current'] and not any(op['current']['profile'] in message for message in op['failures']):
                self.reconnect()
            else:
                # When disconnected, NetworkManager retains control of reconnecting.
                # No active connection is required to clear the saved pin.
                self.finish(op['cleared'], op['failures'])
            return
        path, _old_settings = op['remaining'].pop(0)
        try:
            # Re-read before each write to avoid overwriting external changes.
            settings = dbus.Interface(self.proxy(path), CONN).GetSettings()
            wifi = settings.get('802-11-wireless', {})
            if not read_bssid(settings):
                self.clear_next()
                return
            wifi.pop('bssid', None)
            self.save_profile(path, settings, self.clear_saved)
        except Exception as exc:
            op['failures'].append(f'{path}: {exc}')
            self.clear_next()

    def clear_saved(self):
        self.operation['cleared'] += 1
        self.clear_next()

    def reconnect(self):
        """Reconnect only if the altered profile was active when the action began."""
        op = self.operation
        current = op.get('current') if op else None
        if not current:
            self.finish(op.get('cleared', 0), op.get('failures', []))
            return
        try:
            active = str(self.prop(current['device'], DEV, 'ActiveConnection'))
            if active == '/' or active != current['active']:
                self.activate()
            else:
                dbus.Interface(self.proxy(ROOT), NM).DeactivateConnection(
                    dbus.ObjectPath(active), reply_handler=lambda: self.activate(),
                    error_handler=lambda exc: self.finish_error('切断に失敗しました', exc),
                    timeout=25)
        except Exception as exc:
            self.finish_error('再接続を開始できません', exc)

    def activate(self):
        op = self.operation
        if not op:
            return
        current = op['current']
        try:
            dbus.Interface(self.proxy(ROOT), NM).ActivateConnection(
                dbus.ObjectPath(current['profile']), dbus.ObjectPath(current['device']),
                dbus.ObjectPath('/'), reply_handler=self.activation_started,
                error_handler=lambda exc: self.finish_error('再接続に失敗しました', exc),
                timeout=30)
        except Exception as exc:
            self.finish_error('再接続を要求できません', exc)

    def activation_started(self, *_):
        self.check_attempts = 0
        self.check_timer = GLib.timeout_add(500, self.verify)

    def verify(self):
        op = self.operation
        if not op:
            self.check_timer = None
            return False
        self.check_attempts += 1
        try:
            state = self.get_current()
            if state and state['profile'] == op['current']['profile']:
                # Connection succeeded. Show the saved pin, not a claim about
                # unsupported Reapply() semantics.
                self.check_timer = None
                self.finish(op.get('cleared', 0), op.get('failures', []))
                return False
        except Exception:
            pass
        if self.check_attempts >= 60:
            self.check_timer = None
            self.finish_error('再接続を確認できません', '30秒以内に接続完了を確認できませんでした．設定は保存済みです')
            return False
        return True

    def finish(self, cleared=0, failures=None):
        failures = failures or []
        self.operation = None
        if self.check_timer is not None:
            GLib.source_remove(self.check_timer)
            self.check_timer = None
        self.busy = False
        self.refresh()
        if failures:
            self.error_dialog('一部のプロファイルの変更に失敗しました', '\n'.join(failures[:8]))

    def finish_error(self, title, error):
        self.operation = None
        if self.check_timer is not None:
            GLib.source_remove(self.check_timer)
            self.check_timer = None
        self.busy = False
        self.refresh()
        self.error_dialog(title, error)

    @staticmethod
    def error_dialog(title, message):
        dlg = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR,
                                buttons=Gtk.ButtonsType.CLOSE, text=title)
        dlg.format_secondary_text(str(message))
        dlg.run()
        dlg.destroy()


if __name__ == '__main__':
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] in ('-h', '--help')):
        print('使用方法: wifi-bssid-manager.py [Wi-Fiインターフェース名]')
        sys.exit(0 if len(sys.argv) == 2 else 2)
    Tray(sys.argv[1] if len(sys.argv) == 2 else None)
    Gtk.main()
