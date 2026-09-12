[app]
title = Casino Coach Poker
package.name = casinocoach
package.domain = com.casinocoach.training
source.dir = .
source.include_exts = py,kv,png,jpg,atlas,json,ttf
source.exclude_dirs = tests,.git,.venv,bin,tools
version = 0.5.4
requirements = python3==3.12.11,hostpython3==3.12.11,kivy==2.3.1,filetype
orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 36
android.minapi = 24
android.ndk = 28c
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = False
p4a.local_recipes = ./p4a-recipes

[buildozer]
log_level = 2
warn_on_root = 1
