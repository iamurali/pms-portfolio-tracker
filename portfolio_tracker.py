import requests
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from cryptography.fernet import Fernet, InvalidToken
import base64
from telethon.tl.types import MessageMediaPoll

class MyAlternatesAutomation:
    def __init__(self, username, password, login_url, session_api_url, investor_api_url, headless=True):
        self.username = username
        self.password = password
        self.login_url = login_url
        self.session_api_url = session_api_url
        self.investor_api_url = investor_api_url
        self.session = requests.Session()
        self.driver = None
        self.headless = headless
        self.data_file = "portfolio_data.json"

    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Add user agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)

    def login(self):
        """Perform login on the MyAlternates platform"""
        try:
            print("Navigating to login page...")
            self.driver.get(self.login_url)

            # Wait for page to load
            time.sleep(3)

            # Try different possible selectors for username field
            username_selectors = [
                "input[name='username']",
                "input[type='email']",
                "input[id='username']",
                "input[id='email']",
                "input[placeholder*='username' i]",
                "input[placeholder*='email' i]"
            ]

            username_field = None
            for selector in username_selectors:
                try:
                    username_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"Found username field with selector: {selector}")
                    break
                except TimeoutException:
                    continue

            if not username_field:
                # Fallback: try to find any input field
                input_fields = self.driver.find_elements(By.TAG_NAME, "input")
                if len(input_fields) >= 2:
                    username_field = input_fields[0]
                    print("Using first input field as username")
                else:
                    raise Exception("Could not find username field")

            # Try different possible selectors for password field
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "input[id='password']"
            ]

            password_field = None
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"Found password field with selector: {selector}")
                    break
                except NoSuchElementException:
                    continue

            if not password_field:
                # Fallback: use second input field if available
                input_fields = self.driver.find_elements(By.TAG_NAME, "input")
                if len(input_fields) >= 2:
                    password_field = input_fields[1]
                    print("Using second input field as password")
                else:
                    raise Exception("Could not find password field")

            # Clear and fill the form
            print("Filling login credentials...")
            username_field.clear()
            username_field.send_keys(self.username)

            password_field.clear()
            password_field.send_keys(self.password)

            # Find and click submit button
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Sign in')",
                "button:contains('Login')",
                ".btn-primary",
                ".login-btn",
                "form button"
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    if ":contains" in selector:
                        # Handle text-based selectors
                        buttons = self.driver.find_elements(By.TAG_NAME, "button")
                        for btn in buttons:
                            if "sign in" in btn.text.lower() or "login" in btn.text.lower():
                                submit_button = btn
                                break
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)

                    if submit_button:
                        print(f"Found submit button with selector: {selector}")
                        break
                except NoSuchElementException:
                    continue

            if not submit_button:
                # Fallback: try any button
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                if buttons:
                    submit_button = buttons[0]
                    print("Using first available button as submit")
                else:
                    raise Exception("Could not find submit button")

            print("Clicking sign in button...")
            submit_button.click()

            # Wait for redirect to dashboard
            print("Waiting for redirect to dashboard...")
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda driver: "dashboard" in driver.current_url.lower()
                )
                # print(f"Successfully redirected to: {self.driver.current_url}")
            except TimeoutException:
                print(f"Timeout waiting for redirect. Current URL: {self.driver.current_url}")
                # Continue anyway as login might still be successful

            return True

        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False

    def extract_cookies(self):
        """Extract cookies from browser session"""
        cookies = {}
        for cookie in self.driver.get_cookies():
            cookies[cookie['name']] = cookie['value']
        return cookies

    def call_session_api(self):
        """Call the session API with extracted cookies"""
        print("Extracting cookies from browser...")
        cookies = self.extract_cookies()

        print("Calling session API...")
        try:
            response = self.session.get(
                self.session_api_url,
                cookies=cookies,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json',
                    'Referer': self.login_url.replace('/login', '/dashboard')
                },
                timeout=30
            )

            print(f"Session API Response Status: {response.status_code}")
            print("Session API Response Headers:")

            print("Session API Response Body: [REDACTED]")
            try:
                json_response = response.json()
                return json_response
            except:
                return response.text

        except Exception as e:
            print(f"Session API call failed: {str(e)}")
            return None

    def call_investor_api(self, session_response):
        """Call the investor API with extracted cookies"""
        print("Calling investor API...")
        cookies = self.extract_cookies()
        try:
            response = self.session.get(
                self.investor_api_url,
                cookies=cookies,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json',
                    'authorization': session_response['accessToken'],
                    'Referer': self.login_url.replace('/login', '/dashboard')
                },
                timeout=30
            )

            print(f"Investor API Response Status: {response.status_code}")
            print("Investor API Response Body: [REDACTED]")
            try:
                json_response = response.json()
                return json_response
            except:
                return response.text

        except Exception as e:
            print(f"Investor API call failed: {str(e)}")
            return None

    def run_full_automation(self):
        """Run the complete automation flow"""
        try:
            # Setup browser
            print("Setting up Chrome WebDriver...")
            self.setup_driver()

            # Perform login
            if self.login():
                print("Login successful!")

                # Wait a moment for session to be established
                time.sleep(2)

                # Call session API
                session_response = self.call_session_api()

                # Call investor API
                investor_response = self.call_investor_api(session_response)

                return {
                    'session_api': session_response,
                    'investor_api': investor_response
                }
            else:
                print("Login failed!")
                return None

        except Exception as e:
            print(f"Automation failed: {str(e)}")
            return None
        finally:
            if self.driver:
                print("Closing browser...")
                self.driver.quit()

    def get_fernet_key(self):
        """
        Return a Fernet key (bytes). Read from environment variable FERNET_KEY.
        The key should be a URL-safe base64-encoded 32-byte key (Fernet standard).
        """
        key = os.environ.get("FERNET_KEY")  # set this in GitHub Secrets or env locally
        if not key:
            return None
        # If someone stored it with literal \n or whitespace, strip it
        key = key.strip()
        try:
            # validate base64 by converting to bytes and back
            kbytes = key.encode("utf-8")
            # Fernet will validate the key when used; just return bytes
            return kbytes
        except Exception:
            return None

    def make_fernet(self):
        """
        Create Fernet instance from env key. Returns Fernet or None.
        """
        k = self.get_fernet_key()
        if not k:
            return None
        try:
            return Fernet(k)
        except Exception as e:
            print("Invalid FERNET_KEY:", e)
            return None

    def load_previous_data(self):
        """Load previous portfolio data from encrypted file (portfolio_data.enc)."""
        enc_path = "portfolio_data.enc"
        if not os.path.exists(enc_path):
            # fallback to old unencrypted file for compatibility
            plain_path = self.data_file
            if os.path.exists(plain_path):
                try:
                    with open(plain_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Error loading plain data file: {e}")
            return None
        fernet = self.make_fernet()
        if not fernet:
            print("FERNET_KEY not configured or invalid - cannot decrypt stored portfolio_data.enc")
            return None
        try:
            with open(enc_path, "rb") as fh:
                token = fh.read()
            plaintext = fernet.decrypt(token)
            data = json.loads(plaintext.decode("utf-8"))
            return data
        except InvalidToken:
            print("Decryption failed: Invalid Fernet token (wrong key or corrupted file).")
            return None
        except Exception as e:
            print(f"Error reading/decrypting {enc_path}: {e}")
            return None

    def save_current_data(self, data):
        """
        Save current portfolio data encrypted to portfolio_data.enc using FERNET_KEY.
        Also keep a plaintext backup if FERNET_KEY not configured (optional).
        """
        enc_path = "portfolio_data.enc"
        plain_path = self.data_file

        fernet = self.make_fernet()
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

        if fernet:
            try:
                token = fernet.encrypt(payload)
                with open(enc_path, "wb") as fh:
                    fh.write(token)
                # optional: remove plaintext file if exists (safer)
                if os.path.exists(plain_path):
                    try:
                        os.remove(plain_path)
                    except Exception:
                        pass
                print(f"Encrypted data saved to {enc_path}")
                return
            except Exception as e:
                print(f"Failed to encrypt and save data: {e}")
                # fallthrough to save plaintext below

        # If no key or encryption failed, save plaintext as fallback (less secure)
        try:
            with open(plain_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"FERNET_KEY not available — saved plaintext to {plain_path}")
        except Exception as e:
            print(f"Error saving plaintext data: {e}")

    def analyze_changes(self, previous_data, current_data):
        """Analyze portfolio changes with enhanced detail"""
        if not previous_data:
            # Get all equity holdings with their details
            equity_holdings = []
            for holding in current_data['Profile']['Holdings']:
                if holding['SecurityType'] == 'Equity':
                    equity_holdings.append({
                        'company': holding['CompanyName'],
                        'sector': holding['Sector'],
                        'category': holding['Category'],
                        'weightage': holding['PortfolioWeightage'],
                        'value': holding['PortfolioValue']
                    })

            # Sort by weightage (highest first)
            equity_holdings.sort(key=lambda x: x['weightage'], reverse=True)

            return {
                'is_first_run': True,
                'current_value': current_data['Profile']['Networth']['CurrentNetworth'],
                'current_return': current_data['Profile']['Networth']['Return'] * 100,
                'total_holdings': len(equity_holdings),
                'holdings_list': equity_holdings
            }

        prev_networth = previous_data['Profile']['Networth']
        curr_networth = current_data['Profile']['Networth']

        # Portfolio changes
        value_change = curr_networth['CurrentNetworth'] - prev_networth['CurrentNetworth']
        value_change_pct = (value_change / prev_networth['CurrentNetworth']) * 100
        return_change = (curr_networth['Return'] - prev_networth['Return']) * 100

        # Holdings analysis
        prev_holdings = {h['ISIN']: h for h in previous_data['Profile']['Holdings'] if h['SecurityType'] == 'Equity'}
        curr_holdings = {h['ISIN']: h for h in current_data['Profile']['Holdings'] if h['SecurityType'] == 'Equity'}

        # Current holdings with change data for display
        current_holdings_display = []
        for isin, curr_holding in curr_holdings.items():
            change_pct = 0
            if isin in prev_holdings:
                prev_holding = prev_holdings[isin]
                weight_change = curr_holding['PortfolioWeightage'] - prev_holding['PortfolioWeightage']
                value_change_pct = ((curr_holding['PortfolioValue'] - prev_holding['PortfolioValue']) / prev_holding['PortfolioValue']) * 100
                change_pct = value_change_pct

            current_holdings_display.append({
                'company': curr_holding['CompanyName'],
                'sector': curr_holding['Sector'],
                'category': curr_holding['Category'],
                'weightage': curr_holding['PortfolioWeightage'],
                'value': curr_holding['PortfolioValue'],
                'change_pct': change_pct,
                'is_new': isin not in prev_holdings
            })

        # Sort by weightage (highest first)
        current_holdings_display.sort(key=lambda x: x['weightage'], reverse=True)

        # New stocks
        new_stocks = []
        for isin, holding in curr_holdings.items():
            if isin not in prev_holdings:
                new_stocks.append({
                    'company': holding['CompanyName'],
                    'weightage': holding['PortfolioWeightage'],
                    'value': holding['PortfolioValue'],
                    'sector': holding['Sector']
                })

        # Removed stocks
        removed_stocks = []
        for isin, holding in prev_holdings.items():
            if isin not in curr_holdings:
                removed_stocks.append({
                    'company': holding['CompanyName'],
                    'weightage': holding['PortfolioWeightage'],
                    'value': holding['PortfolioValue'],
                    'sector': holding['Sector']
                })

        # Top changes
        stock_changes = []
        for isin, curr_holding in curr_holdings.items():
            if isin in prev_holdings:
                prev_holding = prev_holdings[isin]
                value_change = curr_holding['PortfolioValue'] - prev_holding['PortfolioValue']
                value_change_pct = (value_change / prev_holding['PortfolioValue']) * 100
                weight_change = curr_holding['PortfolioWeightage'] - prev_holding['PortfolioWeightage']

                if abs(value_change_pct) > 0.01:
                    stock_changes.append({
                        'company': curr_holding['CompanyName'],
                        'value_change_pct': value_change_pct,
                        'weight_change': weight_change,
                        'current_weight': curr_holding['PortfolioWeightage']
                    })

        # Sort by change percentage
        gainers = sorted([s for s in stock_changes if s['value_change_pct'] > 0],
                         key=lambda x: x['value_change_pct'], reverse=True)[:5]
        losers = sorted([s for s in stock_changes if s['value_change_pct'] < 0],
                        key=lambda x: x['value_change_pct'])[:5]

        return {
            'is_first_run': False,
            'portfolio': {
                'previous_value': prev_networth['CurrentNetworth'],
                'current_value': curr_networth['CurrentNetworth'],
                'value_change': value_change,
                'value_change_pct': value_change_pct,
                'return_change': return_change,
                'current_return': curr_networth['Return'] * 100
            },
            'new_stocks': sorted(new_stocks, key=lambda x: x['weightage'], reverse=True),
            'removed_stocks': sorted(removed_stocks, key=lambda x: x['weightage'], reverse=True),
            'top_gainers': gainers,
            'top_losers': losers,
            'total_holdings': len(curr_holdings),
            'current_holdings': current_holdings_display
        }

    def generate_telegram_message(self, analysis, history=None):
        """
        Enhanced Telegram message:
        - Adds 1-line sparkline for Networth trend (last N values from history)
        - Shows ALL holdings expanded with proportional bars
        """

        # === helper: sparkline ===
        def sparkline(values, blocks="▁▂▃▄▅▆▇█"):
            if not values:
                return ""
            mn, mx = min(values), max(values)
            if mx == mn:
                return blocks[0] * len(values)
            step = (mx - mn) / (len(blocks) - 1)
            return "".join(blocks[int((v - mn) / step)] for v in values)

        # === helper: proportional bar ===
        def proportional_bar(value, max_value, length=20):
            if max_value <= 0:
                return "░" * length
            filled = int(round((value / max_value) * length))
            if filled > length:
                filled = length
            return "█" * filled + "░" * (length - filled)

        # === helper: Rs format ===
        def fmt_rs(x):
            try:
                return f"₹{int(round(x)): ,d}"
            except Exception:
                return str(x)

        # === HEADER ===
        now = datetime.now().strftime('%d-%b-%Y | %I:%M %p IST')
        header = f"📊💼 ABAKKUS PMS DAILY PORTFOLIO SNAPSHOT\n🗓️ {now}\n" + "━" * 50 + "\n\n"

        # === NETWORTH TREND (if history provided) ===
        sparkline_block = ""
        if history:
            last_vals = [h['portfolio']['current_value'] for h in history[-7:] if 'portfolio' in h]
            if last_vals:
                sparkline_block = f"📈 Networth Trend (7d): {sparkline(last_vals)}\n\n"

        # === PERFORMANCE ===
        if analysis.get('is_first_run', False):
            summary = (
                f"💰 INITIAL RUN\n"
                f"• Current Value: ₹{analysis.get('current_value', 0):,.2f}\n"
                f"• Total Return: {analysis.get('current_return', 0):+.2f}%\n"
                f"• Holdings: {analysis.get('total_holdings', 0)}\n\n"
            )
        else:
            portfolio = analysis.get('portfolio', {})
            value = portfolio.get('current_value', 0)
            day_change = portfolio.get('current_value', 0) - portfolio.get('previous_value', 0)
            day_pct = portfolio.get('value_change_pct', 0)
            total_return = portfolio.get('current_return', 0)
            return_change = portfolio.get('return_change', 0)

            change_emoji = "📈" if day_change >= 0 else "📉"
            summary = (
                f"💰 PERFORMANCE\n"
                f"• Current Value: ₹{value:,.2f}\n"
                f"• Day Change: {change_emoji} ₹{abs(day_change):,.0f} ({day_pct:+.2f}%)\n"
                f"• Total Return: {total_return:+.2f}%\n"
                f"• Return Change: {return_change:+.2f}%\n\n"
            )

        # === HOLDINGS (all expanded) ===
        holdings = analysis.get('current_holdings') or analysis.get('holdings_list') or []
        if not holdings:
            return header + summary + "⚠️ No holdings found.\n"

        max_weight = max((h.get('weightage', 0) for h in holdings), default=0.0)
        holdings_lines = []
        for i, h in enumerate(holdings, start=1):
            company = h.get('company') or h.get('CompanyName') or "Unknown"
            pct = h.get('weightage', 0.0)
            value_num = h.get('value', 0.0)
            bar = proportional_bar(pct, max_weight, length=20)
            company_display = company if len(company) <= 36 else company[:33] + "..."
            holdings_lines.append(
                f"{i:2}. {company_display}\n"
                f"    {bar} {pct:5.2f}%  • {fmt_rs(value_num)}"
            )
        holdings_block = "📋 FULL PORTFOLIO ALLOCATION\n" + "\n".join(holdings_lines) + "\n\n"

        # === MOVERS ===
        movers_block = ""
        if not analysis.get('is_first_run', False):
            gainers = analysis.get('top_gainers', [])[:5]
            losers = analysis.get('top_losers', [])[:5]
            if gainers:
                movers_block += "🚀 TOP GAINERS\n"
                for g in gainers:
                    movers_block += f"• {g.get('company')[:36]} +{g.get('value_change_pct', 0):.2f}%\n"
                movers_block += "\n"
            if losers:
                movers_block += "⚠️ TOP LOSERS\n"
                for l in losers:
                    movers_block += f"• {l.get('company')[:36]} {l.get('value_change_pct', 0):.2f}%\n"
                movers_block += "\n"

        exits_block = ""
        if not analysis.get('is_first_run', False):
            exits = analysis.get('removed_stocks', [])
            if exits:
                exits_block = "🗑️ COMPLETELY EXITED STOCKS\n"
                for e in exits:
                    exits_block += (
                        f"• {e.get('company')[:36]} "
                        f"(was {e.get('weightage', 0):.2f}% • {fmt_rs(e.get('value', 0))})\n"
                    )
                exits_block += "\n"

        # === FOOTER ===
        footer = (
            f"📱 Total Holdings: {len(holdings)}\n"
            f"🔔 Next Update: Tomorrow 9 PM IST\n"
        )

        return header + sparkline_block + summary + holdings_block + movers_block + exits_block + footer

def send_message(api_id, api_hash, recipient, session_string, msg):
    # Connect to Telegram
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    client.connect()
    client.send_message(recipient, msg)
    client.disconnect()
    print("Telegram message sent!")

def get_session(api_id, api_hash):
    client = TelegramClient('telegram_session', api_id, api_hash)
    client.start()

    if client.is_user_authorized():
        # Convert to string session
        string_session = StringSession.save(client.session)
        print("Session string: [REDACTED]")
        return string_session
    else:
        print("Session file not authorized. Use the first method.")

def main(user_name_cred, pwd_cred, api_id, api_hash, session_string, recipients, login_url, session_api_url, investor_api_url):
    # Configuration
    # Create automation instance
    automation = MyAlternatesAutomation(
        username=user_name_cred,
        password=pwd_cred,
        login_url=login_url,
        session_api_url=session_api_url,
        investor_api_url=investor_api_url,
        headless=True
    )
    # Run the complete flow
    results = automation.run_full_automation()
    if results:
        print("\n" + "="*50)
        print("AUTOMATION COMPLETED SUCCESSFULLY")
        print("="*50)

        # Session API response redacted for security
        if results['investor_api']:
            # Investor API response redacted for security
            previous_data = automation.load_previous_data()
            analysis = automation.analyze_changes(previous_data, results['investor_api'])
            message = automation.generate_telegram_message(analysis)
            # Message content redacted for security
            for recipient in recipients:
                send_message(api_id, api_hash, recipient, session_string, message)
            automation.save_current_data(results['investor_api'])
    else:
        print("Automation failed!")

if __name__ == "__main__":
    api_id_cred = int(os.environ.get('API_ID', 0))
    api_hash_cred = os.environ.get('API_HASH', '')
    session = os.environ.get('SESSION_STRING', '')
    recipients_str = os.environ.get('RECIPIENT_IDS', '')
    recipients = [int(r.strip()) for r in recipients_str.split(',') if r.strip()]
    user_name = os.environ.get('PMS_USERNAME', '')
    pwd = os.environ.get('PMS_PWD', '')
    
    # URL configuration from environment variables
    login_url = os.environ.get('LOGIN_URL', '')
    session_api_url = os.environ.get('SESSION_API_URL', '')
    investor_api_url = os.environ.get('INVESTOR_API_URL', '')

    # Credentials and session data redacted for security
    main(user_name, pwd, api_id_cred, api_hash_cred, session, recipients, login_url, session_api_url, investor_api_url)
