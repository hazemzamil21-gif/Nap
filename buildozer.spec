[app]
title = Napoleon Assistant
package.name = napoleonassistant
package.domain = org.napoleon
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,gif,json
version = 0.1
requirements = python3,kivy,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,SYSTEM_ALERT_WINDOW,QUERY_ALL_PACKAGES,SCHEDULE_EXACT_ALARM,WAKE_LOCK
android.api = 33
android.minapi = 24
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
