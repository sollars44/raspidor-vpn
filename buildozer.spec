[app]
title = RASPIDOR
package.name = raspidor
package.domain = org.raspidor.bypass
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,java
source.include_patterns = assets/*,images/*.png,ciadpi
version = 1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 1
android.archs = arm64-v8a
android.minapi = 21
android.ndk = 26b
android.permissions = INTERNET, ACCESS_NETWORK_STATE, CHANGE_NETWORK_STATE
android.manifest.services = org.raspidor.bypass.BypassVpnService
