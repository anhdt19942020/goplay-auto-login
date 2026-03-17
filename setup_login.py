"""
Setup Login Script - Chạy 1 lần trên server RDP.
Mở Chrome cùng profile automation, để user login thủ công.
Sau khi login OK, cookies sẽ được lưu → API tự động sẽ dùng lại.
"""
import os, sys, shutil, time

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(WORKSPACE_DIR, 'chrome_profile_vlcm')

def main():
    from DrissionPage import ChromiumPage, ChromiumOptions

    opts = ChromiumOptions()
    opts.set_user_data_path(PROFILE_DIR)
    opts.set_local_port(9222)
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
                print(f"[OK] Chrome: {c}")
                break

    print("\n=== GoPlay Login Setup ===")
    print(f"Profile: {PROFILE_DIR}")
    print("Dang mo Chrome... Hay dang nhap tai khoan GoPlay thu cong.")
    print("Sau khi login xong, nhan ENTER o day de dong Chrome.\n")

    page = ChromiumPage(opts)
    page.get('https://goplay.vn/oauth?redirect_uri=%2F')

    input(">>> Da login xong? Nhan ENTER de luu va dong Chrome... ")

    # Check login state
    cookies = page.cookies()
    goplay_cookies = [c for c in cookies if 'goplay' in c.get('domain', '')]
    if goplay_cookies:
        print(f"[OK] Da luu {len(goplay_cookies)} cookies GoPlay vao profile.")
    else:
        print("[WARN] Khong tim thay cookies GoPlay. Ban co chac da login?")

    page.quit()
    print("[OK] Chrome da dong. Profile duoc luu.")
    print("Ban co the chay API binh thuong (start_api.bat hoac Task Scheduler).")


if __name__ == '__main__':
    main()
