import os
import time

from DrissionPage import ChromiumOptions, ChromiumPage


workspace_dir = os.path.dirname(os.path.abspath(__file__))
chrome_profile_dir = os.path.join(workspace_dir, 'chrome_profile_vlcm')
os.makedirs(chrome_profile_dir, exist_ok=True)

browser_options = ChromiumOptions()
browser_options.set_user_data_path(chrome_profile_dir)
browser_options.set_pref('credentials_enable_service', False)
browser_options.set_pref('profile.password_manager_enabled', False)
browser_options.set_pref('profile.password_manager_leak_detection', False)
browser_options.set_pref('profile.default_content_setting_values.notifications', 2)
browser_options.set_argument('--disable-notifications')
browser_options.set_argument('--disable-features=PasswordLeakDetection,PasswordCheck')

page = ChromiumPage(browser_options)

page.get('https://goplay.vn/')

# Click Tài khoản
page.ele('css:.btn-auth.box-login').click()

time.sleep(1)

# Click đăng nhập
page.ele('css:a.btn-auth.btn-login').click()

# Chờ ô nhập username
page.wait.ele_displayed('css:.vtc-user-login')

# Nhập username
page.ele('css:.vtc-user-login').input('anhcamyt')

# Chuyển sang bước nhập mật khẩu
page.ele('#btn-submit-username').click()

# Chờ ô nhập password
page.wait.ele_displayed('#password')

# Nhập password
page.ele('#password').input('Tinhem13')

# Click đăng nhập
page.ele('#btn-login-pass').click()

page.wait.ele_displayed('#btn-header-shop')
page.ele('#btn-header-shop').click()

print("Login done and opened Nap Game")
