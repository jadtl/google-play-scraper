import random
import requests
import time
from typing import Union
from google_play_scraper.exceptions import ExtraHTTPError, NotFoundError


MAX_RETRIES = 3
RATE_LIMIT_DELAY = 5

import random
import functools
from urllib.request import ProxyHandler, build_opener
import requests

# Ask Mullvad for its relays
answer = requests.get("https://api.mullvad.net/www/relays/all/")
relays = answer.json()
# Only keep the ones that work over SOCKS
proxies = [
    f"socks5h://{relay['socks_name']}:{relay['socks_port']}"
    for relay in relays
    if relay.get('socks_name') and relay.get('socks_port') and relay.get('active')
]

print(f"Loaded {len(proxies)} SOCKS5 proxies from Mullvad.")


session = requests.Session()

def _request(method: str, url: str, **kwargs) -> str:
    last_exception = None
    rate_exceeded_count = 0

    for _ in range(MAX_RETRIES):
        proxy = random.choice(proxies)
        #print(f"Using proxy: {proxy}")
        try:
            response = session.request(
                method,
                url,
                proxies={"http": proxy, "https": proxy},
                timeout=10,
                **kwargs
            )
            if response.status_code == 404:
                raise NotFoundError("App not found (404).")
            if not response.ok:
                raise ExtraHTTPError(f"Status code {response.status_code} returned.")
            if "com.google.play.gateway.proto.PlayGatewayError" in response.text:
                raise Exception("PlayGatewayError")
            return response.text
        except NotFoundError as e:
            # Just forward the not found exception for better logging
            raise e
        except Exception as e:
            last_exception = e
            rate_exceeded_count += 1
            delay = RATE_LIMIT_DELAY * rate_exceeded_count + random.uniform(0.5, 1.5)
            #print(f"Retrying in {delay:.1f}s due to: {e}")
            time.sleep(delay)

    raise last_exception


def get(url: str) -> str:
    return _request("GET", url)


def post(url: str, data: Union[str, bytes], headers: dict) -> str:
    return _request("POST", url, data=data, headers=headers)
