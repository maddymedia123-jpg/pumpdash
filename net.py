import time

import requests


def get_json(url, params=None, tries=3, timeout=10):
    """GET with retry + backoff on 429/5xx/network errors. 4xx (except 429) raise immediately."""
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(response=r)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if (code < 500 and code != 429 and code != 0) or i == tries - 1:
                raise
        except requests.RequestException:
            if i == tries - 1:
                raise
        time.sleep(1.5 ** i)