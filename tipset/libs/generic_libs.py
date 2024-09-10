import json
import sys
from urllib.parse import urlencode
import urllib.request as request
from requests_kerberos import HTTPKerberosAuth
from urllib.parse import urlencode, urlparse
import urllib
import os
import fnmatch
import requests
import ssl

def url_opt(url=None, data=None, timeout=1800, headers=None, method='GET', ret_format = 'json', print_ret=True, exit_on_err=True, auth=None):
    # post or get data from url, the response is default to json format
    if not url:
        print("No url specified!")
        return None
    req = request.Request(url, method=method)
    if headers:
        for k in headers:
            req.add_header(k, headers.get(k))
    if auth:
        auth_lists = [HTTPKerberosAuth]
        if type(auth) not in auth_lists:
            print("auth method {} not in supported list {}".format(auth, auth_lists))
            return False
        if isinstance(auth, HTTPKerberosAuth):
            response = requests.Response()
            response.url = url
            host = urlparse(response.url).hostname
            h = auth.generate_request_header(response, host)
            req.add_header('Authorization',h)
    if data:
        req.data = data
    try:
        ret = None
        #context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
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

def find_file(dir_name=None, f_format=None):
    # walk the directly and find the file follow f_format
    f_list = []
    if not os.path.exists(dir_name):
        print("{} not found!".format(dir_name))
        return f_list
    try:
        files_list = os.listdir(dir_name)
    except Exception as exc:
        return f_list
    for f in files_list:
        tmp_path = "{}/{}".format(dir_name,f)
        if os.path.isdir(tmp_path):
            f_list.extend(find_file(dir_name=tmp_path, f_format=f_format))
        if os.path.isfile(tmp_path):
            if fnmatch.fnmatch(f, f_format):
                x = "{}/{}".format(dir_name,f)
                f_list.append(x)
    return f_list
