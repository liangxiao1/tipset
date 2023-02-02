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
    start_time = datetime.datetime.fromisoformat(cfg_data.get('start_date')) - datetime.timedelta(days=1)
    start_time = int(start_time.timestamp()*1000)
    end_time = datetime.datetime.fromisoformat(cfg_data.get('end_date')) + datetime.timedelta(days=1)
    end_time = int(end_time.timestamp()*1000)
    
    base_url = "{}/api/v1/{}/launch?filter.gt.startTime={}&filter.lt.endTime={}&page.size={}".format(cfg_data.get('rp_url'),cfg_data.get('rp_project'),start_time, end_time,cfg_data.get('page_size'))
    rp_rq = Request(base_url)
    rp_rq.add_header("accept", "*/*")
    rp_rq.add_header("Authorization","bearer {}".format(cfg_data.get('rp_token')))

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
    data_file = '/tmp/rp_data'
    with open(data_file,'w') as f:
        f.write(str(records))
    valid_records = []
    total_cases = 0
    skipped_cases = 0
    run_cases = 0
    passed_cases = 0
    failed_cases = 0
    for i in records:
        is_compose = False
        for x in i.get('attributes'):
            if x.get('key') == 'release' and x.get('value').startswith(('RHEL','CentOS')):
                is_compose = True
                break
        if not is_compose:
            continue
        if i.get('statistics').get('executions').get('passed') and i.get('statistics').get('executions').get('passed') > 0:
            valid_records.append(i)
            total_cases += i.get('statistics').get('executions').get('total')
            skipped_cases += i.get('statistics').get('executions').get('skipped') or 0
            passed_cases += i.get('statistics').get('executions').get('passed')
            failed_cases += i.get('statistics').get('executions').get('failed') or 0
    run_cases = total_cases - skipped_cases
    avg_cases = round(run_cases/len(valid_records))
    avg_pass_cases = round(passed_cases/len(valid_records))
    avg_pass_rate = passed_cases/run_cases*100

    records = valid_records
    data_file = '/tmp/rp_data_new_instances'
    print("\n---------- Test sum during {}~{} ----------".format(cfg_data.get('start_date'),cfg_data.get('end_date')))
    new_instances = []
    new_instances_x86 = 0
    new_instances_arm = 0
    instances = []
    instances_x86 = 0
    instances_arm = 0
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
                if z.get('key') == 'release' and z.get('value'):
                    composes.append(z.get('value'))
    for instance in set(new_instances):
        is_found = False
        for i in records:
            for y in i.get('attributes'):
                if y.get('key') == 'instance' and y.get('value') == instance:
                    is_found = True
                    for z in i.get('attributes'):
                        if z.get('key') == 'arch' and 'x86' in z.get('value'):
                            new_instances_x86 += 1
                        elif z.get('key') == 'arch' and 'aarch' in z.get('value'):
                            new_instances_arm += 1
                if is_found: break
            if is_found: break
    for instance in set(instances):
        is_found = False
        for i in records:
            for y in i.get('attributes'):
                if y.get('key') == 'instance' and y.get('value') == instance:
                    is_found = True
                    for z in i.get('attributes'):
                        if z.get('key') == 'arch' and 'x86' in z.get('value'):
                            instances_x86 += 1
                        elif z.get('key') == 'arch' and 'aarch' in z.get('value'):
                            instances_arm += 1
                if is_found: break
            if is_found: break

    print("launches:{}".format(len(records)))
    print("avg_cases:{}".format(avg_cases))
    print("avg_pass_cases:{}".format(avg_pass_cases))
    print("avg_pass_rate:{:.2f}%".format(avg_pass_rate))
    data_file = '/tmp/rp_data_new_instances'
    with open(data_file,'w') as fh:
        fh.write('\n'.join(set(new_instances)))
    print("new instances:{} x86:{} arm:{}".format(len(set(new_instances)),new_instances_x86, new_instances_arm))

    data_file = '/tmp/rp_data_instances'
    with open(data_file,'w') as fh:
        fh.write('\n'.join(set(instances)))
    print("instances: {} x86:{} arm:{}".format(len(set(instances)),instances_x86,instances_arm))
  
    data_file = '/tmp/rp_data_composes'
    with open(data_file,'w') as fh:
        fh.write('\n'.join(set(composes)))
    rhel_compose = 0
    centos_compose = 0
    for i in set(composes):
        if i.startswith('RHEL'):
            rhel_compose += 1
        elif i.startswith('CentOS'):
            centos_compose += 1
    print("composes:{} RHEL:{} CentOS:{}".format(len(set(composes)),rhel_compose,centos_compose))
    print("data details:{}".format(['/tmp/{}'.format(i) for i in os.listdir('/tmp/') if i.startswith('rp_data')]))

if __name__ == "__main__":
    main()    