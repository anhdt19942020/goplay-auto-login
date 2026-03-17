import os, sys, shutil
from DrissionPage import ChromiumPage, ChromiumOptions

opts = ChromiumOptions()
profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chrome_test_profile')
opts.set_user_data_path(profile_dir)
opts.set_local_port(9333)
opts.set_argument('--disable-blink-features=AutomationControlled')
opts.remove_argument('--enable-automation')
opts.set_argument('--window-size=1280,720')

# Auto-detect Chrome
if not shutil.which(opts.browser_path or 'chrome'):
    for c in [
        os.path.join(os.environ.get('ProgramFiles', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('LocalAppData', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
    ]:
        if os.path.isfile(c):
            opts.set_browser_path(c)
            print(f"Chrome: {c}")
            break

page = ChromiumPage(opts)
page.get('https://goplay.vn/oauth?redirect_uri=%2F')

import time
time.sleep(3)

webdriver = page.run_js('return navigator.webdriver')
ua = page.run_js('return navigator.userAgent')
chrome_props = page.run_js('''
    return {
        webdriver: navigator.webdriver,
        plugins_count: navigator.plugins.length,
        languages: navigator.languages,
        platform: navigator.platform,
        hardwareConcurrency: navigator.hardwareConcurrency,
        deviceMemory: navigator.deviceMemory || "N/A",
        windowChrome: typeof window.chrome !== "undefined",
        cdc: document.querySelectorAll('[id*="cdc_"]').length
    }
''')

print(f"\n=== Detection Check ===")
print(f"webdriver: {webdriver}")
print(f"UA: {ua}")
print(f"props: {chrome_props}")

# Check Turnstile iframe
turnstile = page.ele('css:iframe[src*="challenges.cloudflare.com"]', timeout=5)
print(f"Turnstile iframe: {'FOUND' if turnstile else 'NOT FOUND'}")

if turnstile:
    response = page.run_js('return document.querySelector("input[name=cf-turnstile-response]")?.value || "EMPTY"')
    print(f"Turnstile token: {response[:50] if response != 'EMPTY' else 'EMPTY'}...")
    
    time.sleep(5)
    response2 = page.run_js('return document.querySelector("input[name=cf-turnstile-response]")?.value || "EMPTY"')
    print(f"Turnstile token (after 5s): {response2[:50] if response2 != 'EMPTY' else 'EMPTY'}...")

page.quit()
import shutil as s
s.rmtree(profile_dir, ignore_errors=True)
