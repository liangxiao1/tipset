
#!/usr/bin/env python
'''
github : https://github.com/liangxiao1/tipset

This is a tool for interacting with rhcert web console in cli.
'''
import argparse
import json
import os
import ssl
import sys
import time
from tipset.libs.generic_libs import url_opt
from urllib.parse import urlencode
import urllib.request as request
import urllib
try:
   from urllib3 import encode_multipart_formdata
except ImportError:
    print("please install urllib3")
    sys.exit(1)
from itertools import chain
try:
    from yaml import load, dump
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    try:
        from yaml import Loader, Dumper
    except ImportError:
        print('please install pyyaml')
        sys.exit(1)
import mimetypes

TOKEN_FILE = "/tmp/rhapi_token"

class Product():

    def __init__(self, params):
        self.params = params
        self.id = self.params.get('id')
        self.category = self.params.get('category') #must
        self.name = self.params.get('name') #must
        self.partnerId = self.params.get('partnerId') #must
        self.make = self.params.get('make') #must
        self.model = self.params.get('model') #must
        self.description = self.params.get('description') #must
        self.shortDescription = self.params.get('shortDescription') or self.params.get('description')
        self.productUrl = self.params.get('productUrl') #option
        self.specUrl = self.params.get('specUrl') #option
        self.supportUrl = self.params.get('supportUrl') #option
        self.metadata = {}
        self.base_access_url = check_key(key='access_server')
        self.base_url = "{}/products".format(self.base_access_url)
        self.token = load_token()

    def create(self):
        headers = {'content-type': 'application/json',
                    'Accept': 'application/json',
                   'Authorization': 'Bearer {}'.format(self.token)}
        if len(self.shortDescription) > 200:
            #print("The max length of short description should be less than or equal to 200 characters. Use the first sentence instead.")
            self.shortDescription = self.shortDescription.split('.')[0]
            if len(self.shortDescription) > 200:
                self.shortDescription = self.shortDescription[0:200]

        data = {
           "category": self.category,
           "name": self.name,
           "partnerId": int(self.partnerId),
           "make": self.make,
           "model": self.model,
           "description": self.description,
           "shortDescription": self.shortDescription,
           "productUrl": self.productUrl,
           "specUrl": self.specUrl,
           "supportUrl": self.supportUrl
        }
        post_data = json.dumps(data)
        post_data = post_data.encode()
        url_opt(self.base_url, data=post_data, headers=headers, method='POST')

    def update(self):
        headers = {'content-type': 'application/json',
                   'Authorization': 'Bearer {}'.format(self.token)}
        self.load()
        #for key in chain(self.metadata.keys(), self.params.keys()):
        for key in ["id","category","name","partnerId","make","model","description",'shortDescription',"specUrl",'productUrl', "supportUrl"]:
            print("{} - {} - {}".format(key, self.params.get(key), self.metadata.get(key)))
            if self.params.get(key) is not None and self.params.get(key) != self.metadata.get(key):
                if key == 'id':
                    continue
                option = [{
                    "path": "/{}".format(key),
                    "op": "update",
                    "value": self.params.get(key)
                }]
                print("id: {} updating {} to {}".format(self.id, key,self.params.get(key)))
                post_data = json.dumps(option)
                post_data = post_data.encode()
                url = "{}/{}".format(self.base_url,self.id)
                url_opt(url, data=post_data, headers=headers, method='PATCH')

    def load(self):
        headers = {'Authorization': 'Bearer {}'.format(self.token)}
        if self.id is None:
            print("no product id specified yet")
            return False
        self.product_url = "{}/{}".format(self.base_url, self.id)
        self.metadata = url_opt(self.product_url,headers=headers)
        self.id = self.metadata.get('id')
        self.partnerId = self.metadata.get('partnerId')
        self.make = self.metadata.get('make')
        self.model = self.metadata.get('model')
        self.description = self.metadata.get('description')
        self.productUrl = self.metadata.get('productUrl')
        self.specUrl = self.metadata.get('specUrl')
        self.supportUrl = self.metadata.get('supportUrl')
        return True

    def list_all_products(self):
        headers = {'Authorization': 'Bearer {}'.format(self.token)}
        if self.partnerId is None:
            print("no partnerId specified yet")
            return False
        self.parter_url = "{}/partners/{}/products".format(self.base_access_url, self.partnerId)
        url_opt(self.parter_url,headers=headers)
        return True

    def list_products(self):
        url = "{}/products".format(cfg_data.get("pns_server"))
        url_opt(url)

    def list_product_versions(self):
        url = "{}/versions".format(cfg_data.get("pns_server"))
        url_opt(url)

    def list_product_platforms(self):
        url = "{}/platforms".format(cfg_data.get("pns_server"))
        url_opt(url)

class Certification():
    def __init__(self, params):
        self.params = params
        self.id = self.params.get('id')
        self.caseNumber = self.params.get('caseNumber')
        self.classificationId = self.params.get('classificationId')
        self.certificationTypeId = self.params.get('certificationTypeId')
        self.partnerProductId = self.params.get('partnerProductId')
        self.versionId = self.params.get('versionId')
        self.metadata = {}
        self.attachments = []
        self.base_access_url = check_key(key='access_server')
        self.base_cert_url = "{}/certifications".format(self.base_access_url)
        self.token = load_token()

    def create(self, content):
        headers = {'content-type': 'application/json',
                   'Authorization': 'Bearer {}'.format(self.token)}
        data = {
           "classificationId": int(self.classificationId),
           "certificationTypeId": int(self.certificationTypeId),
           "partnerProductId": int(self.partnerProductId)
        }
        try:
            x = json.loads(content)
            data.update(x) 
        except Exception as err:
            print("content error:{}".format(err))
        #post_data = urllib.parse.urlencode(data)
        post_data = json.dumps(data)
        post_data = post_data.encode()
        url_opt(self.base_cert_url, data=post_data, headers=headers, method='POST')

    def update(self, content):
        headers = {'content-type': 'application/json',
                   'Authorization': 'Bearer {}'.format(self.token)}
        try:
            x = json.loads(content)
        except Exception as err:
            print(err)
            return False
        data = [
                  {
                      "path": "/redHatProductInfo",
                      "op": "update",
                      #"value": {
                      #    #"versionId": self.versionId
                          #"versionId": 2937
                      #    "platformId" : '1'
                      #}
                      "value": x
                  }
               ]
        #post_data = urllib.parse.urlencode(data)
        post_data = json.dumps(data)
        post_data = post_data.encode()
        print(post_data)
        if self.id:
            url = "{}/{}".format(self.base_cert_url, self.id)
        if self.caseNumber:
            url = "{}/cases/{}".format(self.base_access_url, self.caseNumber)
        url_opt(url, data=post_data, headers=headers, method='PATCH')

    def load(self):
        headers = {'Authorization': 'Bearer {}'.format(self.token)}
        if self.id is None and self.caseNumber is None:
            print("any of cert id or casenumber not specified yet")
            return False
        if self.id:
            url = "{}/{}".format(self.base_cert_url, self.id)
        if self.caseNumber:
            url = "{}/cases/{}".format(self.base_access_url, self.caseNumber)
        self.metadata = url_opt(url, headers=headers)
        self.id = self.metadata.get('id')
        self.classificationId = self.metadata.get('classificationId')
        self.certificationTypeId = self.metadata.get('certificationTypeId')
        self.partnerProductId = self.metadata.get('partnerProductId')
        self.versionId = self.metadata.get('versionId')

    def list_all(self, partner_id = None):
        headers = {'Authorization': 'Bearer {}'.format(self.token)}
        
        if partner_id:
            self.partnerProductId = partner_id
            url = "{}/products/{}/certifications".format(self.base_access_url,self.partnerProductId)
        else:
            url = "{}/all".format(self.base_cert_url)
        url_opt(url, headers=headers)
        return True

    def list_cert_types(self):
        url = "{}/certificationTypes".format(cfg_data.get("pns_server"))
        if self.certificationTypeId is not None:
            url = "{}/{}".format(url, self.certificationTypeId)
        url_opt(url)

    def list_comments(self):
        headers = {'Authorization': 'Bearer {}'.format(self.token)}
        if self.id is None:
            print("no cert id specified yet")
            return False
        url = "{}/{}/comments".format(self.base_cert_url, self.id)
        url_opt(url, headers=headers)


    def attachments_list(self):
        headers = {'Authorization': 'Bearer {}'.format(self.token)}
        self.load()
        if self.id is None:
            print("no cert id specified yet")
            return False
        url = "{}/{}/attachments".format(self.base_cert_url, self.id)
        self.attachments = url_opt(url, headers=headers)

    def attachment_upload(self, f_path = None, f_desc = ""):
        #headers = {'content-type': 'application/x-www-form-urlencoded',
        headers = {'content-type': 'multipart/form-data',
                   'Authorization': 'Bearer {}'.format(self.token)}
        #files = {'attachment': open(f_path, 'rb')}
        #headers = {'Authorization': 'Bearer {}'.format(self.token)}
        self.load()
        if not f_path:
            print("No f_path specified")
            return False
        f_path = f_path.replace('\n',' ')
        files_list = f_path.split(' ')
        for f in files_list:
            if not f:
                continue
            if not os.path.exists(f):
                print("{} not found".format(f))
                return False
            f_name = os.path.basename(f)
            if not f_desc:
                print("No file description provided, use file name instead")
                f_desc = f_name
            f_hand = open(f, 'rb')
            data = {
               "certId": str(self.id),
               "description": f_desc,
               #'attachment': (f_name, f_hand, "application/octet-stream")
               'attachment': (f_name, f_hand.read(), "text/xml")
            }
            post_data, h = encode_multipart_formdata(data)
            headers['content-type'] = h
            url = "{}/attachments/upload".format(self.base_access_url)
            print("Uploading {}......".format(f_name))
            loops = 3
            for i in range(loops):
                if i == 2:
                    gen_token_from_username_password()
                    self.token = load_token()
                ret = False
                ret = url_opt(url, data=post_data, headers=headers, method='POST', exit_on_err=False)
                if ret:
                    break
                print("Retry again {}/{}".format(i+1,loops))
                time.sleep(5)

    def attachment_download(self, attachment_id):
        self.attachments_list()
        file_name = attachment_id
        for attach_file in self.attachments:
            if attach_file.get('uuid') == attachment_id:
                file_name = attach_file.get('fileName')
        file_name = os.path.join('/tmp',file_name)
        headers = {'Authorization': 'Bearer {}'.format(self.token)}
        cert_url = "{}/certifications/{}/attachments/{}/download".format(self.base_access_url,self.id, attachment_id)
        data = url_opt(cert_url,print_ret=False, ret_format='xml',headers=headers)
        with open(file_name,'wt') as fh:
            print("Saving to:{}".format(file_name))
            fh.write(data)
        return True


def check_key(key=None):
    if cfg_data.get(key) is None:
        print("{} is not set in cfg file".format(key))
        sys.exit(1)
    return cfg_data.get(key)

def gen_token_from_username_password():
    print("Generating from username and password is deprecated, please use device auth!")
    print("generate new token to {}".format(TOKEN_FILE))
    base_sso_url = check_key(key='sso_server')
    username = check_key(key='username')
    password = check_key(key='password')
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    data = {'username':username,
            'password':password,
            'grant_type':'password',
            'client_id':'rhcert-cwe'}
    post_data = urllib.parse.urlencode(data)
    post_data = post_data.encode()
    if os.path.exists(TOKEN_FILE):
        print("{} found, refresh it".format(TOKEN_FILE))
        os.unlink(TOKEN_FILE)
    with open(TOKEN_FILE,'w+') as fh:
        data = url_opt(url=base_sso_url,data=post_data, headers=headers, method='POST', ret_format='str', print_ret=False)
        fh.write(data)

def gen_token_from_device_auth():
    print("Generating token from device auth!")
    print("generate new token to {}".format(TOKEN_FILE))
    if os.path.exists(TOKEN_FILE) and os.stat(TOKEN_FILE).st_size > 0:
        print("{} exists, please refresh it via --refresh or remove it to generate a new token")
        sys.exit(1)
    device_auth_url = check_key(key='device_auth_url')
    token_url = check_key(key='sso_server')
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    data = {'client_id':'rhcert-cwe',
            'scope':'offline_access'
          }
    post_data = urllib.parse.urlencode(data)
    post_data = post_data.encode()

    response = url_opt(url=device_auth_url,data=post_data, headers=headers, method='POST', ret_format='json', print_ret=False)
    device_code = response.get('device_code')
    #print(response)
    #device_code = 'aIYGos_ku682H0EdBAxOH6XQrXY4qBCW7uXSdZSNBk4'

    verification_uri_complete = response.get('verification_uri_complete')
    input('Please go to {} to complete sign in. Then press ENTER to continue.'.format(verification_uri_complete))
    post_data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
        'client_id': 'rhcert-cwe',
        'device_code': device_code,
    }
    post_data = urllib.parse.urlencode(post_data)
    post_data = post_data.encode()
    #print(post_data)
    with open(TOKEN_FILE,'w+') as fh:
        data = url_opt(url=token_url,data=post_data, headers=headers, method='POST', ret_format='str', print_ret=False)
        fh.write(data)

def refresh_token_from_device_auth():
    token_url = check_key(key='sso_server')
    refresh_token = load_token(key='refresh_token')
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    post_data = {
        'grant_type': 'refresh_token',
        'client_id': 'rhcert-cwe',
        'refresh_token': refresh_token,
        'scope':'offline_access'
    }
    post_data = urllib.parse.urlencode(post_data)
    post_data = post_data.encode()
    #print(post_data)
    if os.path.exists(TOKEN_FILE):
        print("{} found, refresh it".format(TOKEN_FILE))
        if os.stat(TOKEN_FILE).st_size > 0:
            os.rename(TOKEN_FILE, TOKEN_FILE+'.last')
        else:
            os.unlink(TOKEN_FILE)
    with open(TOKEN_FILE,'w+') as fh:
        data = url_opt(url=token_url,data=post_data, headers=headers, method='POST', ret_format='str', print_ret=False)
        fh.write(data)

def refresh_token_on_timer():
    run_venv = '/home/p3_venv/bin/activate'
    if not os.path.exists(run_venv):
        print('please create and install tipset to virtual env /home/p3_venv')
        sys.exit(0)
    if not os.path.exists(TOKEN_FILE):
        print('{} not found, please init token firstly!'.format(TOKEN_FILE))
        sys.exit(0)
    timer_unit_file = """
[Unit]
Description=Refresh rhcert token every 120 mins

[Timer]
OnBootSec=5min
OnUnitActiveSec=120min
Unit=rhcert-manager.service

[Install]
WantedBy=timers.target
    """
    unite_file = """
[Unit]
Description=Refresh rhcert token

[Service]
StandardError=journal
ExecStart=bash -c "/home/p3_venv/bin/python  /home/p3_venv/bin/rhcert_manager token --refresh"

[Install]
WantedBy=multi-user.target

    """
    timer_file = '/usr/lib/systemd/system/rhcert-manager.timer'
    service_file = '/usr/lib/systemd/system/rhcert-manager.service'
    with open(timer_file,'w') as fh:
        fh.write(timer_unit_file)
    with open(service_file, 'w') as fh:
        fh.write(unite_file)
    print('Run "systemctl daemon-reload;systemctl enable --now rhcert-manager.timer" to refesh token every 2 hours')

def load_token(key='access_token'):
    if not os.path.exists(TOKEN_FILE):
        print("{} not found, please init it firstly.".format(TOKEN_FILE))
        sys.exit(1)
    key_value = None
    with open(TOKEN_FILE, 'r') as fh:
        key_value = json.load(fh).get(key)
    return key_value

def query(query_kw=None):
    query_list = ['products', 'versions', 'platforms', 'certificationTypes']
    if query_kw not in query_list:
        print("{} not in supported keys:{}".format(query_kw,query_list))
        sys.exit(1)
    base_query_url = check_key(key='pns_server')
    query_url = "{}/{}".format(base_query_url, query_kw)
    context = ssl._create_unverified_context()
    with request.urlopen(query_url,context=context) as fh:
        print('Got data from %s' % fh.geturl())
        src_data = fh.read().decode('utf-8')
        src_data = src_data.replace('null', 'None')
        src_data = src_data.replace('false', 'False')
        src_data = src_data.replace('true', 'True')
        dest_data = eval(src_data)
        for i in dest_data:
            print("id:{} name:{}".format(i.get('id'), i.get('name')))

def main():
    
    parser = argparse.ArgumentParser(description='This tool is for managering rhcert tasks in cli by calling rest APIs')
    subparsers = parser.add_subparsers(help='certification, partner products, token help', required=True)
    parser_cert = subparsers.add_parser('cert', help='cert ticket create, update, list, attachment manage')
    parser_cert.add_argument('--id', dest='id', default=None, action='store',help='specify certification ticket id', required=False)
    parser_cert.add_argument('--caseNumber', dest='caseNumber', default=None, action='store',help='specify caseNumber', required=False)
    parser_cert.add_argument('--cfg', dest='cfg', default='~/rhcert_manager.yaml', action='store',help='specify configuration file, default is "~/rhcert_manager.yaml"', required=False)
    parser_cert.add_argument('--classificationId', dest='classificationId', default=None, action='store',help='1 for Regular, 4 for Pass-Through, must required when create new certification', required=False)
    parser_cert.add_argument('--certificationTypeId', dest='certificationTypeId', default=None, action='store',help='specify certificationTypeId, must required when create new certification', required=False)
    parser_cert.add_argument('--partnerProductId', dest='partnerProductId', default=None, action='store',help='specify partnerProductId, must required when create new certification', required=False)
    parser_cert.add_argument('--content', dest='content', default=None, action='store',help='update ticket with dict like {"platformId" : "7"} ', required=False)
    parser_cert.add_argument('--new', dest='new', action='store_true',help='create new certification', required=False)
    parser_cert.add_argument('--update', dest='update', action='store_true',help='update certification, cert id is required', required=False)
    parser_cert.add_argument('--list', dest='list', action='store_true',help='list certification, id or partner_id is required', required=False)
    parser_cert.add_argument('--list-cert-types', dest='list_cert_types', action='store_true',help='list all certification types', required=False)
    parser_cert.add_argument('--list-comments', dest='list_comments', action='store_true',help='list comments in a cert ticket', required=False)
    parser_cert.add_argument('--attachment', dest='attachment', default=None, action='store',help='specify attachment file path', required=False)
    parser_cert.add_argument('--attachment_desc', dest='attachment_desc', default=None, action='store',help='specify attachment file description, it is file name by default', required=False)
    parser_cert.add_argument('--attachment_id', dest='attachment_id', default=None, action='store',help='specify attachment id', required=False)
    parser_cert.add_argument('--attachments_list', dest='attachments_list', action='store_true',help='list attachments in a cert ticket', required=False)
    parser_cert.add_argument('--attachment_upload', dest='attachment_upload', action='store_true',help='upload attachment to a specific cert id', required=False)
    parser_cert.add_argument('--attachment_download', dest='attachment_download', action='store_true',help='download attachment with attachment_id specified', required=False)
    parser_cert.set_defaults(which='cert')

    parser_product = subparsers.add_parser('product', help='product add, update or list')
    parser_product.add_argument('--cfg', dest='cfg', default='~/rhcert_manager.yaml', action='store',help='specify configuration file, default is "~/rhcert_manager.yaml"', required=False)
    parser_product.add_argument('--id', dest='id', default=None, action='store',help='specify product id', required=False)
    parser_product.add_argument('--partnerId', dest='partnerId', default=None, action='store',help='specify partner id, must required when create new product', required=False)
    parser_product.add_argument('--category', dest='category', default=None, action='store',help='specify category, must required when create new product', required=False)
    parser_product.add_argument('--name', dest='name', default=None, action='store',help='specify name, must required when create new product', required=False)
    parser_product.add_argument('--make', dest='make', default=None, action='store',help='specify make, must required when create new product', required=False)
    parser_product.add_argument('--model', dest='model', default=None, action='store',help='specify model, must required when create new product', required=False)
    parser_product.add_argument('--description', dest='description', default=None, action='store',help='specify description, must required when create new product', required=False)
    parser_product.add_argument('--shortDescription', dest='shortDescription', default=None, action='store',help='specify short description, default is the same as description', required=False)
    parser_product.add_argument('--productUrl', dest='productUrl', default=None, action='store',help='specify productUrl which is a valid http(s) format', required=False)
    parser_product.add_argument('--specUrl', dest='specUrl', default=None, action='store',help='specify specUrl  which is a valid http(s) format', required=False)
    parser_product.add_argument('--supportUrl', dest='supportUrl', default=None, action='store',help='specify supportUrl  which is a valid http(s) format', required=False)
    parser_product.add_argument('--new', dest='new', action='store_true',help='create new product', required=False)
    parser_product.add_argument('--update', dest='update', action='store_true',help='update product, product id is required', required=False)
    parser_product.add_argument('--list', dest='list', action='store_true',help='list product, id or partner_id is required', required=False)
    parser_product.add_argument('--list-products', dest='list_products', action='store_true',help='list Red Hat products', required=False)
    parser_product.add_argument('--list-product-versions', dest='list_product_versions', action='store_true',help='list Red Hat product versions', required=False)
    parser_product.add_argument('--list-product-platforms', dest='list_product_platforms', action='store_true',help='list Red Hat product platforms', required=False)
    parser_product.set_defaults(which='product')

    parser_token = subparsers.add_parser('token', help='token create or renew')
    parser_token.add_argument('--cfg', dest='cfg', default='~/rhcert_manager.yaml', action='store',help='specify configuration file, default is "~/rhcert_manager.yaml"', required=False)
    parser_token.add_argument('--init', dest='init', action='store_true',help='init token', required=False)
    parser_token.add_argument('--refresh', dest='refresh', action='store_true',help='refresh token', required=False)
    parser_token.add_argument('--refresh_on_timer', dest='refresh_on_timer', action='store_true',help='refresh token on schedule', required=False)
    parser_token.set_defaults(which='token')

    args = parser.parse_args()

    cfg_file = os.path.expanduser(args.cfg)
    if not os.path.exists(cfg_file):
        print("{} not found, exit!".format(cfg_file))
        sys.exit(1)
    
    global cfg_data
    with open(cfg_file,'r') as fh:
        cfg_data = load(fh, Loader=Loader)
    
    if args.which == "cert":
        cert = Certification(vars(args))
        if args.new:
            cert.create(args.content)
        elif args.update:
            cert.update(args.content)
        elif args.list:
            if args.id or args.caseNumber:
                cert.load()
            else:
                cert.list_all(partner_id=args.partnerProductId)
        elif args.list_cert_types:
            cert.list_cert_types()
        elif args.attachments_list:
            cert.attachments_list()
        elif args.list_comments:
            cert.list_comments()
        elif args.attachment_upload:
            cert.attachment_upload(args.attachment, args.attachment_desc)
        elif args.attachment_download:
            if not args.attachment_id:
                print("attachment_id required")
                sys.exit(1)
            cert.attachment_download(args.attachment_id)

    if args.which == "product":
        product = Product(vars(args))
        if args.new:
            product.create()
        elif args.update:
            product.update()
        elif args.list:
            if args.id:
                product.load()
            elif args.partnerId:
                product.list_all_products()
        elif args.list_products:
            product.list_products()
        elif args.list_product_versions:
            product.list_product_versions()
        elif args.list_product_platforms:
            product.list_product_platforms()

    if args.which == 'token':
        if args.init:
            #gen_token_from_username_password()
            gen_token_from_device_auth()
        if args.refresh:
            refresh_token_from_device_auth()
        if args.refresh_on_timer:
            refresh_token_on_timer()

if __name__ == "__main__":
    main()