#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import shutil
import requests
import multiprocessing
from gi.repository import Gio
from gi.repository import GLib


class PluginObject:

    def __init__(self, param, api):
        self.param = param
        self.api = api
        self.resolvConfFile = os.path.join(self.api.getRootDir(), "etc/resolv.conf")
        self.makeConfFile = os.path.join(self.api.getRootDir(), "etc/portage/make.conf")
        self.mirrorsFile = os.path.join(self.api.getRootDir(), "etc/portage/mirrors")
        self.oriMakeConfContent = None
        self.oriMirrorsFileContent = None

    def stage_working_start_handler(self, requestObj):
        self._prepare_root()
        return {}

    def stage_working_end_handler(self):
        self._unprepare_root()

    def _prepare_root(self):
        shutil.copyfile("/etc/resolv.conf", self.resolvConfFile)
        if True:
            with open(self.makeConfFile, "r") as f:
                self.oriMakeConfContent = f.read()
            if os.path.exists(self.mirrorsFile):
                with open(self.mirrorsFile, "r") as f:
                    self.oriMirrorsFileContent = f.read()
            self._updateMirrors()
            self._updateParallelism()

    def _unprepare_root(self):
        if self.oriMirrorsFileContent is not None:
            with open(self.mirrorsFile, "w") as f:
                f.write(self.oriMirrorsFileContent)
                self.oriMirrorsFileContent = None
        else:
            _Util.forceDelete(self.mirrorsFile)

        if self.oriMakeConfContent is not None:
            with open(self.makeConfFile, "w") as f:
                f.write(self.oriMakeConfContent)
                self.oriMakeConfContent = None

        if os.path.exists(self.resolvConfFile):
            os.unlink(self.resolvConfFile)

    def _updateMirrors(self):
        # local mirrors
        localGentooMirror = ""
        localRsyncMirror = ""
        localKernelMirror = ""
        localArchMirror = ""
        localPortageMirrorDict = dict()
        if True:
            gentooMirrors = []
            rsyncMirrors = []
            kernelMirrors = []
            archMirrors = []

            browser = _AvahiServiceBrowser("_mirrors._tcp")
            browser.run()
            for name, addr, port in browser.get_result_list():
                for key, value in requests.get("http://%s:%d/api/mirrors" % (addr, port)).json().items():
                    if not value.get("available", False):
                        continue

                    if key == "gentoo":
                        if "http" in value["interface-file"]:
                            s = value["interface-file"]["http"]["url"]
                            s = s.replace("{IP}", addr)
                            gentooMirrors.append(s)
                        elif "ftp" in value["interface-file"]:
                            s = value["interface-file"]["ftp"]["url"]
                            s = s.replace("{IP}", addr)
                            gentooMirrors.append(s)

                    if key == "gentoo-portage":
                        if "rsync" in value["interface-file"]:
                            s = value["interface-file"]["rsync"]["url"]
                            s = s.replace("{IP}", addr)
                            rsyncMirrors.append(s)

                    if key == "kernel":
                        if "http" in value["interface-file"]:
                            s = value["interface-file"]["http"]["url"]
                            s = s.replace("{IP}", addr)
                            kernelMirrors.append(s)
                        elif "ftp" in value["interface-file"]:
                            s = value["interface-file"]["ftp"]["url"]
                            s = s.replace("{IP}", addr)
                            kernelMirrors.append(s)

                    if key == "archlinux":
                        if "http" in value["interface-file"]:
                            s = value["interface-file"]["http"]["url"]
                            s = s.replace("{IP}", addr)
                            archMirrors.append(s)

                    if "interface-file" in value:
                        if "http" in value["interface-file"]:
                            s = value["interface-file"]["http"]["url"]
                            s = s.replace("{IP}", addr)
                            if key not in localPortageMirrorDict:
                                localPortageMirrorDict[key] = []
                            localPortageMirrorDict[key].append(s)
                        elif "ftp" in value["interface-file"]:
                            s = value["interface-file"]["ftp"]["url"]
                            s = s.replace("{IP}", addr)
                            if key not in localPortageMirrorDict:
                                localPortageMirrorDict[key] = []
                            localPortageMirrorDict[key].append(s)

            localGentooMirror = " ".join(gentooMirrors)
            localRsyncMirror = " ".join(rsyncMirrors)
            localKernelMirror = " ".join(kernelMirrors)
            localArchMirror = " ".join(archMirrors)

        # regional public mirrors
        publicGentooMirror = ""
        publicRsyncMirror = ""
        publicKernelMirror = ""
        publicArchMirror = ""
        if True:
            gentooMirrors = []
            rsyncMirrors = []
            kernelMirrors = []
            archMirrors = []

            # countryCode, countryName = self.__geoGetCountry()
            countryCode = "CN"

            if countryCode == "CN":
                gentooMirrors = [
                    "http://mirrors.163.com/gentoo",
                    "https://mirrors.tuna.tsinghua.edu.cn/gentoo",
                ]
                rsyncMirrors = [
                    "rsync://rsync.cn.gentoo.org/gentoo-portage",
                    "rsync://rsync1.cn.gentoo.org/gentoo-portage",
                ]
                kernelMirrors = [
                    "https://mirrors.tuna.tsinghua.edu.cn/kernel",
                ]
                archMirrors = [
                    "http://mirrors.neusoft.edu.cn/archlinux",
                    "http://mirrors.tuna.tsinghua.edu.cn/archlinux",
                    "http://mirrors.ustc.edu.cn/archlinux",
                ]

            publicGentooMirror = " ".join(gentooMirrors)
            publicRsyncMirror = " ".join(rsyncMirrors)
            publicKernelMirror = " ".join(kernelMirrors)
            publicArchMirror = " ".join(archMirrors)

        # modify make.conf
        self.__setMakeConfVar("GENTOO_MIRRORS", "%s %s ${GENTOO_DEFAULT_MIRROR}" % (localGentooMirror, publicGentooMirror))
        self.__setMakeConfVar("RSYNC_MIRRORS", "%s %s ${RSYNC_DEFAULT_MIRROR}" % (localRsyncMirror, publicRsyncMirror))
        self.__setMakeConfVar("KERNEL_MIRRORS", "%s %s ${KERNEL_DEFAULT_MIRROR}" % (localKernelMirror, publicKernelMirror))
        self.__setMakeConfVar("ARCHLINUX_MIRRORS", "%s %s" % (localArchMirror, publicArchMirror))

        # write to /etc/portage/mirrors
        with open(self.mirrorsFile, "w") as f:
            for name, mlist in localPortageMirrorDict.items():
                f.write(name + "\t" + " ".join(mlist) + "\n")

    def _updateParallelism(self):
        # gather system information
        cpuNum = multiprocessing.cpu_count()                   # cpu core number
        memSize = _Util.getPhysicalMemorySize()               # memory size in GiB

        # determine parallelism parameters
        buildInMemory = (memSize >= 24)
        if buildInMemory:
            jobcountMake = cpuNum + 2
            jobcountEmerge = cpuNum
            loadavg = cpuNum
        else:
            jobcountMake = cpuNum
            jobcountEmerge = cpuNum
            loadavg = max(1, cpuNum - 1)

        # check/fix MAKEOPTS variable
        # for bug 559064 and 592660, we need to add -j and -l, it sucks
        value = self.__getMakeConfVar("MAKEOPTS")
        if True:
            m = re.search("\\B--jobs(=([0-9]+))?\\b", value)
            if m is None:
                value += " --jobs=%d" % (jobcountMake)
                self.__setMakeConfVar("MAKEOPTS", value.lstrip())
            elif m.group(2) is None or int(m.group(2)) != jobcountMake:
                value = value.replace(m.group(0), "--jobs=%d" % (jobcountMake))
                self.__setMakeConfVar("MAKEOPTS", value.lstrip())
        value = self.__getMakeConfVar("MAKEOPTS")
        if True:
            m = re.search("\\B--load-average(=([0-9\\.]+))?\\b", value)
            if m is None:
                value += " --load-average=%d" % (loadavg)
                self.__setMakeConfVar("MAKEOPTS", value.lstrip())
            elif m.group(2) is None or int(m.group(2)) != loadavg:
                value = value.replace(m.group(0), "--load-average=%d" % (loadavg))
                self.__setMakeConfVar("MAKEOPTS", value.lstrip())
        value = self.__getMakeConfVar("MAKEOPTS")
        if True:
            m = re.search("\\B-j([0-9]+)?\\b", value)
            if m is None:
                value += " -j%d" % (jobcountMake)
                self.__setMakeConfVar("MAKEOPTS", value.lstrip())
            elif m.group(1) is None or int(m.group(1)) != jobcountMake:
                value = value.replace(m.group(0), "-j%d" % (jobcountMake))
                self.__setMakeConfVar("MAKEOPTS", value.lstrip())
        value = self.__getMakeConfVar("MAKEOPTS")
        if True:
            m = re.search("\\B-l([0-9]+)?\\b", value)
            if m is None:
                value += " -l%d" % (loadavg)
                self.__setMakeConfVar("MAKEOPTS", value.lstrip())
            elif m.group(1) is None or int(m.group(1)) != loadavg:
                value = value.replace(m.group(0), "-l%d" % (loadavg))
                self.__setMakeConfVar("MAKEOPTS", value.lstrip())

        # check/fix EMERGE_DEFAULT_OPTS variable
        value = self.__getMakeConfVar("EMERGE_DEFAULT_OPTS")
        if True:
            m = re.search("\\B--jobs(=([0-9]+))?\\b", value)
            if m is None:
                value += " --jobs=%d" % (jobcountEmerge)
                self.__setMakeConfVar("EMERGE_DEFAULT_OPTS", value.lstrip())
            elif m.group(2) is None or int(m.group(2)) != jobcountEmerge:
                value = value.replace(m.group(0), "--jobs=%d" % (jobcountEmerge))
                self.__setMakeConfVar("EMERGE_DEFAULT_OPTS", value.lstrip())
        value = self.__getMakeConfVar("EMERGE_DEFAULT_OPTS")
        if True:
            m = re.search("\\B--load-average(=([0-9\\.]+))?\\b", value)
            if m is None:
                value += " --load-average=%d" % (loadavg)
                self.__setMakeConfVar("EMERGE_DEFAULT_OPTS", value.lstrip())
            elif m.group(2) is None or int(m.group(2)) != loadavg:
                value = value.replace(m.group(0), "--load-average=%d" % (loadavg))
                self.__setMakeConfVar("EMERGE_DEFAULT_OPTS", value.lstrip())

        # check/fix PORTAGE_TMPDIR variable
        value = self.__getMakeConfVar("PORTAGE_TMPDIR")
        if True:
            if buildInMemory:
                tdir = "/tmp"
            else:
                tdir = "/var/tmp"
            if value != tdir:
                self.__setMakeConfVar("PORTAGE_TMPDIR", tdir)

    def __getMakeConfVar(self, varName):
        """Returns variable value, returns "" when not found
           Multiline variable definition is not supported yet"""

        buf = ""
        with open(self.makeConfFile, 'r') as f:
            buf = f.read()

        m = re.search("^%s=\"(.*)\"$" % (varName), buf, re.MULTILINE)
        if m is None:
            return ""
        varVal = m.group(1)

        while True:
            m = re.search("\\${(\\S+)?}", varVal)
            if m is None:
                break
            varName2 = m.group(1)
            varVal2 = self.__getMakeConfVar(self.makeConfFile, varName2)
            if varVal2 is None:
                varVal2 = ""

            varVal = varVal.replace(m.group(0), varVal2)

        return varVal

    def __setMakeConfVar(self, varName, varValue):
        """Create or set variable in make.conf
           Multiline variable definition is not supported yet"""

        endEnter = False
        buf = ""
        with open(self.makeConfFile, 'r') as f:
            buf = f.read()
            if buf[-1] == "\n":
                endEnter = True

        m = re.search("^%s=\"(.*)\"$" % (varName), buf, re.MULTILINE)
        if m is not None:
            newLine = "%s=\"%s\"" % (varName, varValue)
            buf = buf.replace(m.group(0), newLine)
            with open(self.makeConfFile, 'w') as f:
                f.write(buf)
        else:
            with open(self.makeConfFile, 'a') as f:
                if not endEnter:
                    f.write("\n")
                f.write("%s=\"%s\"\n" % (varName, varValue))


class _Util:

    @staticmethod
    def getPhysicalMemorySize():
        with open("/proc/meminfo", "r") as f:
            # We return memory size in GB.
            # Since the memory size shown in /proc/meminfo is always a
            # little less than the real size because various sort of
            # reservation, so we do a "+1"
            m = re.search("^MemTotal:\\s+(\\d+)", f.read())
            return int(m.group(1)) / 1024 / 1024 + 1

    @staticmethod
    def forceDelete(filename):
        if os.path.islink(filename):
            os.remove(filename)
        elif os.path.isfile(filename):
            os.remove(filename)
        elif os.path.isdir(filename):
            shutil.rmtree(filename)


class _AvahiServiceBrowser:

    """
    Exampe:
        obj = _AvahiServiceBrowser("_http._tcp")
        obj.run()
        obj.get_result_list()
    """

    def __init__(self, service):
        self.service = service

    def run(self):
        self._result_dict = dict()

        self._server = None
        self._browser = None
        self._error_message = None
        try:
            self._server = Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SYSTEM,
                                                          Gio.DBusProxyFlags.NONE,
                                                          None,
                                                          "org.freedesktop.Avahi",
                                                          "/",
                                                          "org.freedesktop.Avahi.Server")

            path = self._server.ServiceBrowserNew("(iissu)",
                                                  -1,                                   # interface = IF_UNSPEC
                                                  0,                                    # protocol = PROTO_INET
                                                  self.service,                         # type
                                                  "",                                   # domain
                                                  0)                                    # flags
            self._browser = Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SYSTEM,
                                                           Gio.DBusProxyFlags.NONE,
                                                           None,
                                                           "org.freedesktop.Avahi",
                                                           path,
                                                           "org.freedesktop.Avahi.ServiceBrowser")
            self._browser.connect("g-signal", self._signal_handler)

            self._mainloop = GLib.MainLoop()
            self._mainloop.run()
            if self._error_message is not None:
                raise Exception(self._error_message)
        except GLib.Error as e:
            # treat dbus as success but no result
            if e.domain != "g-dbus-error-quark":    # FIXME: more eligant way?
                raise
        finally:
            self._error_message = None
            if self._browser is not None:
                self._browser.Free()
                self._browser = None
            self._server = None

    def get_result_list(self):
        return self._result_dict.values()

    def _signal_handler(self, proxy, sender, signal, param):
        if signal == "ItemNew":
            interface, protocol, name, stype, domain, flags = param.unpack()
            self._server.ResolveService("(iisssiu)",
                                        interface,
                                        protocol,
                                        name,
                                        stype,
                                        domain,
                                        -1,                                     # interface = IF_UNSPEC
                                        0,                                      # protocol = PROTO_INET
                                        result_handler=self._service_resolved,
                                        error_handler=self._failure_handler)

        if signal == "ItemRemove":
            interface, protocol, name, stype, domain, flags = param.unpack()
            key = (interface, protocol, name, stype, domain)
            if key in self._result_dict:
                del self._result_dict[key]

        if signal == "AllForNow":
            self._mainloop.quit()

        if signal == "Failure":
            self._failure_handler(param)

        return True

    def _service_resolved(self, proxy, result, user_data):
        interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags = result
        key = (interface, protocol, name, stype, domain)
        self._result_dict[key] = (name, address, int(port))

    def _failure_handler(self, error):
        self._error_message = error
        self._mainloop.quit()
