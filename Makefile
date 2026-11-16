# System installation: sudo make install / sudo make uninstall
# Per-user autostart: make autostart / make no-autostart (without sudo)
PREFIX ?= /usr/local
BINDIR = $(PREFIX)/bin
ICONDIR = $(PREFIX)/share/icons/hicolor/64x64/apps
DESKTOPDIR = $(PREFIX)/share/applications
AUTOSTARTDIR = $(HOME)/.config/autostart
APP = wifi-bssid-manager

.PHONY: all check install uninstall autostart no-autostart
all:
	@echo 'Install system-wide: sudo make install'
	@echo 'Enable login startup for this user: make autostart'

check:
	/usr/bin/python3 -c "import ast, pathlib; ast.parse(pathlib.Path('$(APP).py').read_text())"
	@test -f $(APP).desktop && test -f $(APP).png

install: check
	install -D -m 755 $(APP).py $(DESTDIR)$(BINDIR)/$(APP)
	install -D -m 644 $(APP).png $(DESTDIR)$(ICONDIR)/$(APP).png
	install -D -m 644 $(APP).desktop $(DESTDIR)$(DESKTOPDIR)/$(APP).desktop
	@echo 'Installed $(APP) system-wide.'
	@echo 'Optional (as your normal user): make autostart'

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/$(APP)
	rm -f $(DESTDIR)$(ICONDIR)/$(APP).png
	rm -f $(DESTDIR)$(DESKTOPDIR)/$(APP).desktop
	@echo 'Uninstalled system files. To remove per-user startup: make no-autostart'

autostart:
	@test -x $(BINDIR)/$(APP) || { echo 'Please run sudo make install first.' >&2; exit 1; }
	install -D -m 644 $(APP).desktop $(AUTOSTARTDIR)/$(APP).desktop
	@echo 'Autostart enabled for $(USER).'

no-autostart:
	rm -f $(AUTOSTARTDIR)/$(APP).desktop
	@echo 'Autostart disabled for $(USER).'
