prefix=/usr

all:

install:
	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib64/syncupd/plugins"
	cp -r plugins/gentoo.py "$(DESTDIR)/$(prefix)/lib64/syncupd/plugins/gentoo.py"
	chmod 644 "$(DESTDIR)/$(prefix)/lib64/syncupd/plugins/gentoo.py"

uninstall:
	rm -rf "$(DESTDIR)/$(prefix)/lib64/syncupd/plugins/gentoo.py"

.PHONY: all install uninstall
