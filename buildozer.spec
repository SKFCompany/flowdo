[app]
title = МоёМеню
package.name = moemenu
package.domain = org.moemenu
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,ttf
source.exclude_dirs = venv,.git,.buildozer,bin,__pycache__
source.exclude_patterns = venv/*,*.pyc,*.pyo
version = 1.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,requests

# Android
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 26
android.ndk = 25b
android.sdk = 33
android.archs = arm64-v8a, armeabi-v7a

# App icon (place icon.png 512x512 in project root)
icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/splash.png

android.orientation = portrait
android.allow_backup = True

# iOS (not configured)
[buildozer]
log_level = 2
warn_on_root = 1
