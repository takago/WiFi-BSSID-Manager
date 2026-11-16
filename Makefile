# Install the launcher and icon system-wide, and the menu entry per user.
# Run `make install` as the desktop user (not with `sudo make install`).
PREFIX ?= /usr/local
BINDIR = $(PREFIX)/bin
ICONDIR = $(PREFIX)/share/icons/hicolor/64x64/apps
DESKTOPDIR = $(HOME)/.local/share/applications
AUTOSTARTDIR = $(HOME)/.config/autostart
APP = wifi-bssid-manager

.PHONY: all install uninstall autostart no-autostart check
all:
	@echo 'Run make install (or make autostart after installation).'

install: check
	sudo install -D -m 755 $(APP).py $(DESTDIR)$(BINDIR)/$(APP)
	sudo install -D -m 644 $(APP).png $(DESTDIR)$(ICONDIR)/$(APP).png
	install -D -m 644 $(APP).desktop $(DESKTOPDIR)/$(APP).desktop
	@echo 'Installed. Launch from the application menu or run $(APP).'
	@echo 'To start on login: make autostart'

autostart:
	install -D -m 644 $(APP).desktop $(AUTOSTARTDIR)/$(APP).desktop
	@echo 'Automatic login startup enabled.'

no-autostart:
	rm -f $(AUTOSTARTDIR)/$(APP).desktop
	@echo 'Automatic login startup disabled.'

uninstall: no-autostart
	rm -f $(DESKTOPDIR)/$(APP).desktop
	sudo rm -f $(DESTDIR)$(BINDIR)/$(APP) $(DESTDIR)$(ICONDIR)/$(APP).png
	@echo 'Uninstalled (NetworkManager profiles were not modified).'

check:
	/usr/bin/python3 -m py_compile $(APP).py
	@test -f $(APP).desktop && test -f $(APP).png
