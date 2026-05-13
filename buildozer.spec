[app]
title = FlowDo
package.name = flowdo
package.domain = org.flowdo
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0
requirements = python3,kivy==2.2.1,kivymd==1.1.1,pillow,plyer
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,RECORD_AUDIO,VIBRATE,RECEIVE_BOOT_COMPLETED
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
