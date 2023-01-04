import json
import os
import tipset
from urllib import request
from urllib.request import Request
import argparse
import sys
import datetime
import re
try:
    from yaml import load, dump
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

def main():
    cfg_file_tmpl = os.path.dirname(tipset.__file__) + "/cfg/aws_reportportal_sum.yaml"

    parser = argparse.ArgumentParser(description='The tool simple description')
    parser.add_argument('-f', dest='cfg_file', default=None, action='store',help='specify cfg file', required=True)
    args = parser.parse_args()
    if not os.path.exists(args.cfg_file):
        print("missing cfg file, here is template: {}".format(cfg_file_tmpl))
        sys.exit(1)
    cfg_data = {}
    with open(args.cfg_file,'r') as fh:
        cfg_data = load(fh, Loader=Loader)
    start_time = datetime.datetime.fromisoformat(cfg_data.get('start_date'))
    start_time = int(start_time.timestamp()*1000)
    end_time = datetime.datetime.fromisoformat(cfg_data.get('end_date'))
    end_time = int(end_time.timestamp()*1000)
    
    base_url = "{}/api/v1/{}/launch?filter.gt.startTime={}&filter.lt.endTime={}&page.size={}".format(cfg_data.get('rp_url'),cfg_data.get('rp_project'),start_time, end_time,cfg_data.get('page_size'))
    rp_rq = Request(base_url)
    rp_rq.add_header("accept", "*/*")
    rp_rq.add_header("Authorization","bearer {}".format(cfg_data.get('rp_token')))
    data_file = '/tmp/rp_data'
    with request.urlopen(rp_rq) as fh:
        with open(data_file,'w') as f:
            f.write(fh.read().decode())

    records = []
    print('Getting pages in {} page size.'.format(cfg_data.get('page_size')),sep=' ', end =" ")
    page_num = 1
    while True:
        print(page_num,sep=' ', end =" ")
        base_url = "{}/api/v1/{}/launch?filter.gt.startTime={}&filter.lt.endTime={}&page.size={}&page.page={}".format(cfg_data.get('rp_url'),cfg_data.get('rp_project'),start_time, end_time,cfg_data.get('page_size'),page_num)
        rp_rq = Request(base_url)
        rp_rq.add_header("accept", "*/*")
        rp_rq.add_header("Authorization","bearer {}".format(cfg_data.get('rp_token')))
        with request.urlopen(rp_rq) as fh:
            tmp_data = json.loads(fh.read().decode())
            if tmp_data.get("page").get('totalPages') > page_num:
                records.extend(tmp_data.get('content'))
                page_num += 1
            else:
                records.extend(tmp_data.get('content'))
                break

    data_file = '/tmp/rp_data_new_instances'
    print("\n---------- Test sum during {}~{} ----------".format(cfg_data.get('start_date'),cfg_data.get('end_date')))
    new_instances = []
    instances = []
    composes = []
    for i in records:
        for y in i.get('attributes'):
            if y.get('key') == 'new_instance' and y.get('value') == 'true':
                for z in i.get('attributes'):
                    if z.get('key') == 'instance':
                        new_instances.append(z.get('value'))
            for z in i.get('attributes'):
                if z.get('key') == 'instance':
                    instances.append(z.get('value'))
                if z.get('key') == 'release' and re.match('RHEL-.*\d$', z.get('value')):
                    composes.append(z.get('value'))
    print("total launches: {}".format(len(records)))
    data_file = '/tmp/rp_data_new_instances'
    with open(data_file,'w') as fh:
        fh.write('\n'.join(set(new_instances)))
    print("total new instances: {}".format(len(set(new_instances))))

    data_file = '/tmp/rp_data_instances'
    with open(data_file,'w') as fh:
        fh.write('\n'.join(set(instances)))
    print("total instances: {}".format(len(set(instances))))
  
    data_file = '/tmp/rp_data_composes'
    with open(data_file,'w') as fh:
        fh.write('\n'.join(set(composes)))
    print("total composes: {}".format(len(set(composes))))

if __name__ == "__main__":
    main()    