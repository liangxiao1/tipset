import json
import sys
from urllib.parse import urlencode
import urllib.request as request
import urllib

def url_opt(url=None, data=None, timeout=1800, headers=None, method='GET', ret_format = 'json', print_ret=True, exit_on_err=True):
    # post or get data from url, the response is default to json format
    if not url:
        print("No url specified!")
        return None
    req = request.Request(url, method=method)
    if headers:
        for k in headers:
            req.add_header(k, headers.get(k))
    if data:
        req.data = data
    try:
        ret = None
        with request.urlopen(req, timeout=timeout ) as fh:
            #print('Got response from {}'.format(fh.geturl()))
            if ret_format == 'json':
                data = json.loads(fh.read().decode('utf-8'))
                if print_ret: print(json.dumps(data, indent=4))
            elif ret_format == 'binary':
                data = fh.read()
                if print_ret: print(data)
            else:
                data = fh.read().decode('utf-8')
                if print_ret: print(data)
            return data
    except Exception as exc:
        print("exception:{} during process url:{}, return: {}".format(exc,url,exc.read().decode()))
        if 'Unauthorized' in str(exc):
            print("Try to refresh or init new token again and make sure your account have permission to the page!")
        if exit_on_err:
            sys.exit(1)
        return False
    return True