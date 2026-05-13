[app]
title = FlowDo
package.name = flowdo
package.domain = org.flowdo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 4.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,plyer

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.ndk = 27.3.13750724
android.ndk_path = /usr/local/lib/android/sdk/ndk/27.3.13750724
android.sdk_path = /usr/local/lib/android/sdk
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a
android.build_tools_version = 34.0.0
[buildozer]
log_level = 2
warn_on_root = 1
