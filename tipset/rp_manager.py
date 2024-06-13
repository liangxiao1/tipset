
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
from tipset.libs.generic_libs import url_opt,find_file
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
from xml.etree.ElementTree import parse
import logging

import datetime
LOG_FORMAT = '%(asctime)s:PID[%(process)d]:%(levelname)s:%(message)s'
LOG = logging.getLogger(__name__)

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
        self.default_headers = {'Authorization': 'Bearer {}'.format(self.rp_token),
                  'content-type': 'application/json',
                  'Accept': '*/*'}
        self.headers = self.default_headers.copy()

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
        LOG.info("Create new launch from {}".format(self.launch_logdir))
        result_xml = None
        for file in os.listdir(self.launch_logdir):
            if file.endswith('.xml'):
                result_xml = file
                break
        #print("{} found in {}".format(result_xml, self.launch_logdir))
        #headers = {'content-type': 'multipart/form-data',
        self.headers['content-type'] = 'application/x-www-form-urlencoded'
        
        tmp_dir = tempfile.mkdtemp(prefix='rp_manager_',dir='/tmp')
        zip_file = "{}/{}.zip".format(tmp_dir,self.launch_name)

        working_dir = os.getcwd()
        os.chdir(tmp_dir)
        shutil.make_archive(self.launch_name, 'zip', self.launch_logdir)
        os.chdir(working_dir)
        
        #f_hand = open("{}/{}".format(self.launch_logdir,result_xml), 'rb')

        f_hand = open(zip_file, 'rb')
        # depends on different reportportal versions, not all support this parameter in api
        # we will update the skipped items to not a bug.
        param_data = {
            "skippedIsNotIssue": "true",
            "notIssue": "true"
            
        }
        data = {
                  "name": self.params.get('launch_name'),
                  #'file': (result_xml, f_hand.read(), "text/xml"),
                  'file': (zip_file, f_hand.read(), "application/x-zip-compressed"),
                }
       
        post_data, h = encode_multipart_formdata(data)
    
        self.headers['content-type'] = h
        req_url = "{}/api/v1/{}/launch/import?".format(self.rp_url,self.rp_project,urlencode(param_data))
        ret = url_opt(req_url, data=post_data, headers=self.headers, method='POST', print_ret=False)
        self.uuid = re.findall('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', ret.get('message'),re.I)[0]
        if self.uuid:
            print(self.uuid)
        self.load()
        self.update(print_ret=False)
        shutil.rmtree(tmp_dir)
        LOG.info("New launch:{}".format(self.uuid))
        if self.params.get('attachment'):
            self.upload_attachment()

    def list(self,print_ret=True):
        '''
        query launch info by launch id or uuid.
        '''
        self.headers = self.default_headers.copy()
        self.headers.pop('content-type')
        if self.id:
            req_url = "{}/api/v1/{}/launch/{}".format(self.rp_url,self.rp_project,self.id)
        elif self.uuid:
            req_url = "{}/api/v1/{}/launch/uuid/{}".format(self.rp_url,self.rp_project,self.uuid)
        
        if self.id or self.uuid:
            LOG.info("Query launch:{}".format(self.id or self.uuid))
            self.metadata = url_opt(req_url,headers=self.headers,print_ret=print_ret)
            LOG.info("Ret:{}".format(self.metadata))
        else:
            start_date = self.params.get('launch_start_date') or datetime.datetime.today().__str__()
            end_date = self.params.get('launch_end_date') or datetime.datetime.today().__str__()

            start_time = datetime.datetime.fromisoformat(start_date) - datetime.timedelta(days=1)
            start_time = int(start_time.timestamp()*1000)
            end_time = datetime.datetime.fromisoformat(end_date) + datetime.timedelta(days=1)
            end_time = int(end_time.timestamp()*1000)
            LOG.info("Query project {} launches in {}~{}".format(self.rp_project,start_date, end_date))
            param_data = {
                'page.size': self.params.get('rp_page_size'),
                'filter.gt.startTime': start_time,
                'filter.lt.endTime': end_time,
            }
            records = []
            page_num = 1
            while True:
                LOG.info("get page {}".format(page_num))
                param_data['page.page'] = page_num
                req_url = "{}/api/v1/{}/launch?{}".format(self.rp_url,self.rp_project,urlencode(param_data))
                tmp_data = url_opt(req_url, headers=self.headers, method='GET', print_ret=False)
                if tmp_data.get("page").get('totalPages') > page_num:
                    records.extend(tmp_data.get('content'))
                    page_num += 1
                else:
                    records.extend(tmp_data.get('content'))
                    break
            print(records)
        return True

    def analyze(self):
        '''
        trigger build in analyze launch id.
        '''
        self.headers = self.default_headers
        self.headers['content-type'] = 'application/json'
        req_url = "{}/api/v1/{}/launch/analyze ".format(self.rp_url,self.rp_project)
        data = {
              "analyzeItemsMode": [
                "TO_INVESTIGATE"
              ],
              "analyzerMode": "ALL",
              "analyzerTypeName": "autoAnalyzer",
              "launchId": self.id
            }
        LOG.info("launch {}: start analyze.".format(self.id))
        post_data = json.dumps(data)
        post_data = post_data.encode()
        url_opt(req_url, headers=self.headers, data=post_data, method='POST')
        return True

    def load(self):
        '''
        init launch property by its return.
        '''
        self.headers = self.default_headers.copy()
        self.headers.pop('content-type')
        self.headers.pop('Accept')
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
        self.headers = self.default_headers
        req_url = "{}/api/v1/{}/launch ".format(self.rp_url,self.rp_project)
        data = {
                  "ids": [
                    self.id
                  ]
                }
        post_data = json.dumps(data)
        post_data = post_data.encode()
        LOG.info("Delete:{}".format(self.id))
        url_opt(req_url, headers=self.headers, data=post_data, method='DELETE')
        return True

    def update(self, print_ret=True):
        '''
        delete launch by id or uuid.
        '''
        self.headers = self.default_headers
        req_url = "{}/api/v1/{}/launch/{}/update ".format(self.rp_url,self.rp_project,self.id)
        data = {
                  "attributes": self.params.get('launch_attributes'),
                  "description": self.params.get('launch_description'),
                  "mode": "DEFAULT"
                }

        LOG.info("update launch's attributes and description:{}".format(self.id))
        post_data = json.dumps(data)
        post_data = post_data.encode()
        #print(post_data)
        url_opt(req_url, headers=self.headers, data=post_data, method='PUT',print_ret=print_ret)
        return True

    def report(self,print_ret=False):
        '''
        download launch report in pdf format.
        '''
        self.headers = self.default_headers.copy()
        self.headers.pop('content-type')
        self.load()
        req_url = "{}/api/v1/{}/launch/{}/report".format(self.rp_url,self.rp_project,self.id)
        data = url_opt(req_url,headers=headers,print_ret=print_ret, ret_format='binary')
        pdf_report = "/tmp/rp_manager_{}.pdf".format(self.id)
        with open(pdf_report, 'wb') as fh:
            fh.write(data)
            print("Report: {}".format(pdf_report))
        return True

    def query_item(self, casename):
        self.headers = self.default_headers
        # get item uuid
        LOG.info("query {} in launch {}.".format(casename, self.id))

        req_url = "{}/api/v1/{}/item".format(self.rp_url,self.rp_project)
        data ={
            'filter.eq.launchId':self.id,
            'filter.eq.name': casename,
            'isLatest':'true',
            'launchesLimit':'0'
        }
        params = urlencode(data)
        req_url = req_url+'?'+params
        return url_opt(req_url, headers=self.headers, method='GET', print_ret=False)

    def update_item(self, case_name=None, attach_file=None):
        # upload log and attachment to the item
        self.headers = self.default_headers
        item_out = self.query_item(case_name)
        LOG.debug(item_out)
        item_uuid = item_out['content'][0].get('uuid')
        item_starttime = item_out['content'][0].get('startTime')
        f_name = '{}/{}'.format(self.launch_logdir, attach_file)
        mime_type = 'text/plain'
        o_mode = 'r'
        if f_name.endswith('png'):
            o_mode = 'rb'
            mime_type = 'image/png'
        elif f_name.endswith('jpeg'):
            o_mode = 'rb'
            mime_type = 'image/jpeg'
        f_hand = open(f_name, o_mode)
        
        payload = [{"itemUuid":item_uuid,"launchUuid":self.uuid,"time":item_starttime,"message":"debug_log","level": "info","file":{"name":case_name}}]
        
        data = {
        'json_request_part': (None, json.dumps(payload), 'application/json'),
        'file': (case_name, f_hand.read(), mime_type), 
        }
        post_data, h = encode_multipart_formdata(data)
        self.headers['content-type'] = h
        req_url="https://reportportal-virtcloud.apps.ocp-c1.prod.psi.redhat.com/api/v1/xiliang_personal/log"
        url_opt(req_url, data=post_data, headers=self.headers, method='POST', print_ret=False)
        LOG.info("{} uploaded.".format(attach_file))

    def upload_attachment(self):
        '''
        upload attachment to test cases
        There are two options we can find the attachment.
        1st is recommended  and add attachment property in your junit file, the tool will upload all named attachment to the test items.
        This allows you have different dir layout and file name.
        <testcase classname="TestCloudInit" name="os_tests.tests.test_cloud_init.TestCloudInit.test_cloud_init_lineoverwrite" time="35.464">
            <properties>
                <property name="attachment" value="attachments/TestCloudInit.os_tests.tests.test_cloud_init.TestCloudInit.test_cloud_init_lineoverwrite/os_tests.tests.test_cloud_init.TestCloudInit.test_cloud_init_lineoverwrite.debug"/>
            </properties>
            <skipped>not supported from cloudinit 22.1, render profile changed to networkmanager</skipped>
            <time>35.464</time>
        </testcase>
        2nd is attachment filename with test case name, the tool will walk the current dir and find all file contains testcase name and upload it.
        '''
        xml_files = find_file(dir_name=self.launch_logdir, f_format='*.xml')
        LOG.info('Try to upload attachment!')
        LOG.debug('{} found in {}'.format(xml_files,self.launch_logdir))
        for xml_file in xml_files:
        # get attachment path from junit file
            attach_found = False
            doc = parse(xml_file)
            for i in doc.iterfind('testsuite/testcase'):
                case_name = i.get('name')
                LOG.info("case_name: {}".format(case_name))
                dup_element = []
                tags = [i.tag for i in i.iter()]
                launch_attachment_include = self.params.get('launch_attachment_include')
                if launch_attachment_include:
                    upload_list = launch_attachment_include.split(',')
                    dup_element = [ x for x in upload_list if x in tags]
                if not dup_element:
                    LOG.debug("do not upload attachment: launch_attachment_include set - {} current case set - {}".format(launch_attachment_include,tags)) 
                    continue

                for x in i.iterfind('properties/property'):
                    if x.get('name') == 'attachment':
                        attach_found = True
                        attachment_file = x.get('value')
                        LOG.info("attachment_file: {}".format(attachment_file))
                        self.update_item(case_name=case_name, attach_file=attachment_file)
                if not attach_found:
                    LOG.debug("No attachment property found, try to search case_name under the log dir")
                    # try to find files named as case_name and uplod it
                    attachment_files = find_file(dir_name=self.launch_logdir, f_format='*.{}.*'.format(case_name))
                    if attachment_files:
                        for attachment in attachment_files:
                            LOG.info("attachment_file: {}".format(attachment))
                            self.update_item(case_name=case_name, attach_file=attachment)
        return True

class User():
    def __init__(self, params):
        self.params = params
        self.rp_url = self.params.get('rp_url')
        self.rp_token = self.params.get('rp_token')
        self.rp_page_size = self.params.get('rp_page_size')
        self.rp_project = self.params.get('rp_project')
        self.metadata = None
        self.default_headers = {'Authorization': 'Bearer {}'.format(self.rp_token),
                  'content-type': 'application/json',
                  'Accept': '*/*'}
        self.headers = self.default_headers.copy()

    def list(self,print_ret=True,all_user=False):
        '''
        query user info
        '''
        self.headers = self.default_headers.copy()
        self.headers.pop('content-type')
        if all_user:
            req_url = "{}/api/v1/user/all".format(self.rp_url)
        else:
            req_url = "{}/api/v1/user".format(self.rp_url)
 
        self.metadata = url_opt(req_url,headers=self.headers,print_ret=print_ret)
        return True

class Project():
    def __init__(self, params):
        self.params = params
        self.rp_url = self.params.get('rp_url')
        self.rp_token = self.params.get('rp_token')
        self.rp_page_size = self.params.get('rp_page_size')
        self.rp_project = self.params.get('rp_project')
        self.id = self.params.get('id')
        self.name = self.params.get('name')
        self.metadata = None
        self.default_headers = {'Authorization': 'Bearer {}'.format(self.rp_token),
                  'content-type': 'application/json',
                  'Accept': '*/*'}
        self.headers = self.default_headers.copy()

    def list(self,print_ret=True,all_user=False):
        '''
        query project info
        '''
        self.headers = self.default_headers.copy()
        self.headers.pop('content-type')
        if not self.id and not self.name:
            req_url = "{}/api/v1/project/names".format(self.rp_url)
        elif self.id is not None:
            param_data = {
                'filter.eq.id' : self.id
            }
            req_url = "{}/api/v1/project/list?{}".format(self.rp_url,urlencode(param_data))
        elif self.name is not None:
            req_url = "{}/api/v1/project/list/{}".format(self.rp_url,self.name)
 
        self.metadata = url_opt(req_url,headers=self.headers,print_ret=print_ret)
        return True

def main():
    
    parser = argparse.ArgumentParser(description='This tool is for managering reportportal in cli.')
    subparsers = parser.add_subparsers(help='supported sub tasks, run log is aved in /tmp/rp_manager_debug.log', required=True)
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
    parser_cert.add_argument('--attachment', dest='attachment', action='store_true',help='upload attachment when create new launch', required=False)
    parser_cert.set_defaults(which='launch')

    parser_cert = subparsers.add_parser('project', help='project managerment')
    parser_cert.add_argument('--cfg', dest='cfg', default='~/rp_manager.yaml', action='store',help='specify configuration file, default is "~/rp_manager.yaml"', required=False)
    parser_cert.add_argument('--id', dest='id', default=None, action='store',help='specify project id, admin role required', required=False)
    parser_cert.add_argument('--name', dest='name', default=None, action='store',help='specify project name', required=False)
    parser_cert.add_argument('--list', dest='list', action='store_true',help='default list all projects names(admin role required), you can specify name to access one', required=False)
    parser_cert.set_defaults(which='project')

    parser_cert = subparsers.add_parser('user', help='user managerment')
    parser_cert.add_argument('--cfg', dest='cfg', default='~/rp_manager.yaml', action='store',help='specify configuration file, default is "~/rp_manager.yaml"', required=False)
    parser_cert.add_argument('--list', dest='list', action='store_true',help='list user information', required=False)
    parser_cert.add_argument('--list_all', dest='list_all', action='store_true',help='list all user information', required=False)
    parser_cert.set_defaults(which='user')

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, filename='/tmp/rp_manager_debug.log')

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
            launch.list()
        elif args.analyze:
            launch.load()
            launch.analyze()
        elif args.delete:
            launch.delete()
        elif args.report:
            launch.report()
        else:
            supported_actions = ['--new','--update','--list','--analyze','--delete','--report']
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

    if args.which == "project":
        project = Project(cfg_data)
        if args.list:
            project.list()
        else:
            supported_actions = ['--list']
            print("Please specify actions in {}".format(supported_actions))


if __name__ == "__main__":
    main()