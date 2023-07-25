import datetime
import argparse
import requests
import fake_useragent
import concurrent.futures
import os
import easygui


def create_vuln_file():
    with open("SqliVuln.txt", "w"):
        pass


def banner():
    return """
  Simple Script for Scanning The Web for SQLI vulns
  """


def convert_cert(burp_cert, to_pem=True):
    if to_pem:
        os.system(f"openssl x509 -inform der {burp_cert} -out burp.pem")
    else:
        print("Conversion to PEM format not requested.")


def generate_user_agent():
    user_agent = fake_useragent.UserAgent().random
    return user_agent


def test_url(url, payload, use_cookies, proxies, generate_user_agent, cert_path):
    # Add payload to URL
    url_with_payload = f"{url}{payload}"

    # Send the request with the payload
    headers = {'User-Agent': generate_user_agent()} if generate_user_agent else {}
    cookies = {'cookie1': 'value1', 'cookie2': 'value2'} if use_cookies else None

    try:
        response = requests.get(url_with_payload, headers=headers, cookies=cookies, proxies=proxies, verify=cert_path)
        response.raise_for_status()  # Raise an exception for non-200 status codes
        if any(keyword in response.text.lower() for keyword in ['error', 'syntax error', 'mysql', 'postgre',
                                                                'oracle', 'microsoft', 'informix', 'db2', 'sqlite',
                                                                'sybase']):
            return url_with_payload, payload
    except (requests.RequestException, requests.Timeout):
        pass
    return None


def test_urls(urls, payload, use_cookies, num_threads, proxies, generate_user_agent, cert_path):
    vuln_list = []  # List to store the vulnerabilities found
    create_vuln_file()  # Just create the file but don't write to it yet
    start_time = datetime.datetime.now()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(test_url, url, payload, use_cookies, proxies, generate_user_agent, cert_path)
                   for url in urls]

        # Wait for all tasks to complete
        concurrent.futures.wait(futures)

        # Collect the vulnerabilities from completed futures
        for future in futures:
            result = future.result()
            if result is not None:
                vuln_list.append(result)

    # Write all vulnerabilities to the file in a single operation
    now = datetime.datetime.now()
    date_time_string = now.strftime("%Y-%m-%d_%H-%M-%S")
    with open("SqliVuln.txt", 'a') as vuln_file:
        for url, payload in vuln_list:
            vuln_file.write(f"[+] SQL injection vulnerability found at {url} (payload={payload}) Date:{date_time_string}\n")

    elapsed_time = datetime.datetime.now() - start_time
    print(f"Scan completed in {elapsed_time.total_seconds():.2f} seconds.")
    print("All vuln Targets Saved at SqliVuln.txt")


if __name__ == '__main__':
    print(banner())
    parser = argparse.ArgumentParser(description='Test a list of URLs for SQL injection vulnerabilities')
    parser.add_argument("--convert-burpcert", action='store_true',
                        help="Convert Burp Cert to a Format supported for this script")
    parser.add_argument('--url', help='Single URL to test for SQL injection vulnerabilities')
    parser.add_argument('url_file', nargs='?', default=None, help='Path to a file containing a list of URLs')
    parser.add_argument('--payload', help='Payload to be used for testing SQL injection vulnerabilities')
    parser.add_argument('--use-cookies', action='store_true', help='Use cookies in requests')
    parser.add_argument('--num-threads', type=int, default=10, help='Number of threads to use (default: 10)')
    parser.add_argument('--proxy', help='Proxy to use for requests (format: http://proxyserver:port)')
    parser.add_argument('--random-user-agent', action='store_true', help='Generate a random user agent for each request')
    parser.add_argument('--cert-path', help='Path to a certificate file for the proxy')
    args = parser.parse_args()

    if args.convert_burpcert:
        cert_file = easygui.fileopenbox(msg='Select Burp Suite certificate file', title='Select certificate file',
                                        filetypes='*.der')
        if cert_file:
            convert_cert(cert_file, to_pem=True)
            print('Certificate converted to PEM format')
            exit()
        else:
            print('No certificate file selected')
            exit()

    if args.url is not None:
        urls = [args.url]
    elif args.url_file is not None:
        with open(args.url_file) as f:
            urls = f.read().splitlines()
    else:
        parser.error('You must specify either a URL or a URL file.')

    payload = "'" if args.payload is None else args.payload
    use_cookies = args.use_cookies
    num_threads = args.num_threads

    proxies = {'http': args.proxy, 'https': args.proxy} if args.proxy is not None else None

    generate_user_agent = lambda: fake_useragent.UserAgent().random if args.random_user_agent else None

    cert_path = args.cert_path

    test_urls(urls, payload, use_cookies, num_threads, proxies, generate_user_agent, cert_path)
