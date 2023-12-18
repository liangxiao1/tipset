
#!/usr/bin/env python
'''
github : https://github.com/liangxiao1/tipset

This is a tool for interacting with reportportal in cli.
'''
import argparse
from datetime import datetime
import json
import shutil
import os
import re
import ssl
import sys
import time
from tipset.libs.generic_libs import url_opt
from urllib.parse import urlencode
import urllib.request as request
import urllib
import tempfile
try:
   from urllib3 import encode_multipart_formdata
   import urllib3
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

class Launch():
    def __init__(self, params):
        self.params = params
        self.rp_url = self.params.get('rp_url')
        self.rp_token = self.params.get('rp_token')
        self.rp_page_size = self.params.get('rp_page_size')
        self.rp_project = self.params.get('rp_project')
        self.id = self.params.get('id')
        self.uuid = self.params.get('id')
        self.launch_name = self.params.get('launch_name')
        self.launch_description = self.params.get('launch_description')
        self.launch_attributes = self.params.get('launch_attributes')
        self.launch_logdir = self.params.get('launch_logdir')
        self.launch_use_class_name = self.params.get('launch_use_class_name')
        self.launch_merge_launches = self.params.get('launch_merge_launches')
        self.launch_simple_xml = self.params.get('launch_simple_xml')
        self.launch_auto_dashboard = self.params.get('launch_auto_dashboard')
        self.launch_launch_with_class_name = self.params.get('launch_launch_with_class_name')
        self.launch_property_filter = self.params.get('launch_property_filter')
        self.metadata = None

    def create(self):
        '''
        create new launch.
        '''
        if not self.launch_logdir:
            print("No logdir specified!")
            sys.exit(1)
        if not os.path.exists(self.launch_logdir):
            print("{} not found!".format(self.launch_logdir))
            sys.exit(1)
        result_xml = None
        for file in os.listdir(self.launch_logdir):
            if file.endswith('.xml'):
                result_xml = file
                break
        #print("{} found in {}".format(result_xml, self.launch_logdir))
        #headers = {'content-type': 'multipart/form-data',
        headers = {'content-type': 'application/x-www-form-urlencoded',
                   'Authorization': 'Bearer {}'.format(self.rp_token)}
        
        tmp_dir = tempfile.mkdtemp(prefix='rp_manager_',dir='/tmp')
        zip_file = "{}/{}.zip".format(tmp_dir,self.launch_name)

        working_dir = os.getcwd()
        os.chdir(tmp_dir)
        shutil.make_archive(self.launch_name, 'zip', self.launch_logdir)
        os.chdir(working_dir)
        
        #f_hand = open("{}/{}".format(self.launch_logdir,result_xml), 'rb')

        f_hand = open(zip_file, 'rb')
        data = {
                  "description": self.params.get('launch_description'),
                  #"mode": "DEFAULT",
                  "name": self.params.get('launch_name'),
                  #'file': (result_xml, f_hand.read(), "text/xml"),
                  'file': (zip_file, f_hand.read(), "application/x-zip-compressed")
                }
       

        post_data, h = encode_multipart_formdata(data)
    
        #print(post_data)
        headers['content-type'] = h
        req_url = "{}/api/v1/{}/launch/import".format(self.rp_url,self.rp_project)
        ret = url_opt(req_url, data=post_data, headers=headers, method='POST', print_ret=False)
        self.uuid = re.findall('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', ret.get('message'),re.I)[0]
        if self.uuid:
            print(self.uuid)
        self.load()
        self.update(print_ret=False)
        shutil.rmtree(tmp_dir)

    def list(self,print_ret=True):
        '''
        query launch info by launch id or uuid.
        '''
        headers = {'Authorization': 'Bearer {}'.format(self.rp_token),
                  "Accept": "*/*"}
        if self.id:
            req_url = "{}/api/v1/{}/launch/{}".format(self.rp_url,self.rp_project,self.id)
        elif self.uuid:
            req_url = "{}/api/v1/{}/launch/uuid/{}".format(self.rp_url,self.rp_project,self.uuid)
        self.metadata = url_opt(req_url,headers=headers,print_ret=print_ret)
        return True

    def analyze(self):
        '''
        trigger build in analyze launch id.
        '''
        headers = {'Authorization': 'Bearer {}'.format(self.rp_token),
                  'content-type': 'application/json',
                  'Accept': '*/*'}
        req_url = "{}/api/v1/{}/launch/analyze ".format(self.rp_url,self.rp_project)
        data = {
              "analyzeItemsMode": [
                "TO_INVESTIGATE"
              ],
              "analyzerMode": "ALL",
              "analyzerTypeName": "autoAnalyzer",
              "launchId": self.id
            }
        post_data = json.dumps(data)
        post_data = post_data.encode()
        url_opt(req_url, headers=headers, data=post_data, method='POST')
        return True

    def load(self):
        '''
        init launch property by its return.
        '''
        headers = {'Authorization': 'Bearer {}'.format(self.rp_token)}
        if self.id is None and self.uuid is None:
            print("no product id or uuid specified yet")
            return False
        self.list(print_ret=False)
        self.launch_name = self.metadata.get('name')
        self.launch_description = self.metadata.get('description')
        self.launch_attributes = self.metadata.get('attributes')
        self.uuid = self.metadata.get('uuid')
        self.id = self.metadata.get('id')
        return True

    def delete(self):
        '''
        delete launch by id or uuid.
        '''
        headers = {'Authorization': 'Bearer {}'.format(self.rp_token),
                  'content-type': 'application/json',
                  'Accept': '*/*'}
        req_url = "{}/api/v1/{}/launch ".format(self.rp_url,self.rp_project)
        data = {
                  "ids": [
                    self.id
                  ]
                }
        post_data = json.dumps(data)
        post_data = post_data.encode()
        url_opt(req_url, headers=headers, data=post_data, method='DELETE')
        return True

    def update(self, print_ret=True):
        '''
        delete launch by id or uuid.
        '''
        headers = {'Authorization': 'Bearer {}'.format(self.rp_token),
                  'content-type': 'application/json',
                  'Accept': '*/*'}
        req_url = "{}/api/v1/{}/launch/{}/update ".format(self.rp_url,self.rp_project,self.id)
        data = {
                  "attributes": self.params.get('launch_attributes'),
                  "description": self.params.get('launch_description'),
                  "mode": "DEFAULT"
                }

        post_data = json.dumps(data)
        post_data = post_data.encode()
        #print(post_data)
        url_opt(req_url, headers=headers, data=post_data, method='PUT',print_ret=print_ret)
        return True

    def report(self,print_ret=False):
        '''
        download launch report in pdf format.
        '''
        headers = {'Authorization': 'Bearer {}'.format(self.rp_token),
                  "Accept": "*/*"}
        self.load()
        req_url = "{}/api/v1/{}/launch/{}/report".format(self.rp_url,self.rp_project,self.id)
        data = url_opt(req_url,headers=headers,print_ret=print_ret, ret_format='binary')
        pdf_report = "/tmp/rp_manager_{}.pdf".format(self.id)
        with open(pdf_report, 'wb') as fh:
            fh.write(data)
            print("Report: {}".format(pdf_report))
        return True

class User():
    def __init__(self, params):
        self.params = params
        self.rp_url = self.params.get('rp_url')
        self.rp_token = self.params.get('rp_token')
        self.rp_page_size = self.params.get('rp_page_size')
        self.rp_project = self.params.get('rp_project')
        self.metadata = None

    def list(self,print_ret=True,all_user=False):
        '''
        query user info
        '''
        headers = {'Authorization': 'Bearer {}'.format(self.rp_token),
                  "Accept": "*/*"}
        if all_user:
            req_url = "{}/api/v1/user/all".format(self.rp_url)
        else:
            req_url = "{}/api/v1/user".format(self.rp_url)
 
        self.metadata = url_opt(req_url,headers=headers,print_ret=print_ret)
        return True

def main():
    
    parser = argparse.ArgumentParser(description='This tool is for managering reportportal in cli.')
    subparsers = parser.add_subparsers(help='supported sub tasks', required=True)
    parser_cert = subparsers.add_parser('launch', help='launch create, update, list, attachment manage')
    parser_cert.add_argument('--id', dest='id', default=None, action='store',help='specify launch id', required=False)
    parser_cert.add_argument('--uuid', dest='id', default=None, action='store',help='specify launch uuid', required=False)
    parser_cert.add_argument('--project', dest='project', default='aws', action='store',help='specify project name', required=False)
    parser_cert.add_argument('--cfg', dest='cfg', default='~/rp_manager.yaml', action='store',help='specify configuration file, default is "~/rp_manager.yaml"', required=False)
    parser_cert.add_argument('--list', dest='list', action='store_true',help='list launch information', required=False)
    parser_cert.add_argument('--logdir', dest='launch_logdir', default=None, action='store',help='specify log directory', required=False)
    parser_cert.add_argument('--new', dest='new', action='store_true',help='create new launch with logdir', required=False)
    parser_cert.add_argument('--analyze', dest='analyze', action='store_true',help='trigger launch build in analyze', required=False)
    parser_cert.add_argument('--delete', dest='delete', action='store_true',help='delete launch by uuid or id', required=False)
    parser_cert.add_argument('--update', dest='update', action='store_true',help='update launch information', required=False)
    parser_cert.add_argument('--report', dest='report', action='store_true',help='get launch report in pdf format', required=False)
    parser_cert.set_defaults(which='launch')

    parser_cert = subparsers.add_parser('user', help='user managerment')
    parser_cert.add_argument('--cfg', dest='cfg', default='~/rp_manager.yaml', action='store',help='specify configuration file, default is "~/rp_manager.yaml"', required=False)
    parser_cert.add_argument('--list', dest='list', action='store_true',help='list user information', required=False)
    parser_cert.add_argument('--list_all', dest='list_all', action='store_true',help='list all user information', required=False)
    parser_cert.set_defaults(which='user')

    args = parser.parse_args()

    cfg_file = os.path.expanduser(args.cfg)
    if not os.path.exists(cfg_file):
        print("{} not found, exit!".format(cfg_file))
        sys.exit(1)
    
    global cfg_data
    with open(cfg_file,'r') as fh:
        cfg_data = load(fh, Loader=Loader)
    args_dict = vars(args)
    for key in args_dict:
        if args_dict.get(key) is not None:
            cfg_data[key] = args_dict.get(key)
    #print(cfg_data)    
    if args.which == "launch":
        launch = Launch(cfg_data)
        if args.new:
            launch.create()
        elif args.update:
            launch.load()
            launch.update()
        elif args.list:
            if launch.id:
                launch.list()
            else:
                launch.list_all(partner_id=args.partnerProductId)
        elif args.analyze:
            launch.load()
            launch.analyze()
        elif args.delete:
            launch.delete()
        elif args.report:
            launch.report()
        else:
            supported_actions = ['--new','--update','--list','--list_all','--analyze','--delete','--report']
            print("Please specify actions in {}".format(supported_actions))

    if args.which == "user":
        user = User(cfg_data)
        if args.list:
            user.list()
        elif args.list_all:
            user.list(all_user=True)
        else:
            supported_actions = ['--list','--list_all']
            print("Please specify actions in {}".format(supported_actions))


if __name__ == "__main__":
    main()