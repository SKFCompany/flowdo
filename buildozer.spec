[app]
title = FlowDo
package.name = flowdo
package.domain = org.flowdo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 4.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,plyer

# vosk и pyttsx3 УБРАТЬ — они не работают на Android через buildozer
# requirements НЕ добавляй: vosk, pyttsx3, pyaudio

android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

[buildozer]
log_level = 2
