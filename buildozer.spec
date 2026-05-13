[app]
title = FlowDo
package.name = flowdo
package.domain = org.flowdo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 4.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,plyer

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a

# Явно указываем версию build-tools без 37
android.build_tools_version = 34.0.0

[buildozer]
log_level = 2
warn_on_root = 1
