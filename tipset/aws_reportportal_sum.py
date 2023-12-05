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

def query_bugzilla(bugzilla_url=None, names=None, start_date=None, end_date=None, bugzilla_token=None, bugzilla_limit=1000):
    # ref docs: 
    # https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug.html#search-bugs
    # https://github.com/python-bugzilla/python-bugzilla/blob/main/examples/query.py
    print("#"*20)
    print("Query data from bugzilla")
    try:
        import bugzilla
    except Exception:
        print("please install python-bugzilla")
        return False
    if not bugzilla_url:
        print("no bugzilla_url specified")
        return False
    if not names:
        print("no names specified")
        return False
    URL = bugzilla_url
    bzapi = bugzilla.Bugzilla(URL,api_key=bugzilla_token)
    start_date = datetime.datetime.fromisoformat(start_date)
    end_date = datetime.datetime.fromisoformat(end_date)
    for name in names:
        if not name:
            continue
        query = bzapi.build_query(reporter=name,limit=bugzilla_limit)
        bugs = bzapi.query(query)
        tmp_bugs = []
        if bugs:
            for bug in bugs:
                if bug.creation_time >= start_date and bug.creation_time <= end_date:
                    tmp_bugs.append(bug)
        print("-"*20)
        print("name: {} reported: {}".format(name, len(tmp_bugs)))
        for bug in tmp_bugs:
            print("id:{}, title:{}, component:{}, link:{}".format(bug.id, bug.summary, bug.component, bug.weburl))

def query_rp(rp_url=None, rp_token=None, rp_project=None, start_date=None, end_date=None, rp_page_size=300):

    print("#"*20)
    print("Query data from report portal")
    start_time = datetime.datetime.fromisoformat(start_date) - datetime.timedelta(days=1)
    start_time = int(start_time.timestamp()*1000)
    end_time = datetime.datetime.fromisoformat(end_date) + datetime.timedelta(days=1)
    end_time = int(end_time.timestamp()*1000)
    
    base_url = "{}/api/v1/{}/launch?filter.gt.startTime={}&filter.lt.endTime={}&page.size={}".format(rp_url,rp_project,start_time, end_time,rp_page_size)
    rp_rq = Request(base_url)
    rp_rq.add_header("accept", "*/*")
    rp_rq.add_header("Authorization","bearer {}".format(rp_token))

    records = []
    print('Getting pages in {} page size.'.format(rp_page_size),sep=' ', end =" ")
    page_num = 1
    while True:
        print(page_num,sep=' ', end =" ")
        base_url = "{}/api/v1/{}/launch?filter.gt.startTime={}&filter.lt.endTime={}&page.size={}&page.page={}".format(rp_url,rp_project,start_time, end_time,rp_page_size,page_num)
        rp_rq = Request(base_url)
        rp_rq.add_header("accept", "*/*")
        rp_rq.add_header("Authorization","bearer {}".format(rp_token))
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
            if x.get('key') == 'release' and x.get('value').startswith(('RHEL','CentOS')) and 'CCSP' not in x.get('value'):
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
    print("\n---------- Test sum during {}~{} ----------".format(start_date,end_date))
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

def query_github(gh_url=None, names=None, start_date=None, end_date=None, gh_project=None):
    # ref docs: 
    # https://docs.github.com/en/search-github/getting-started-with-searching-on-github/understanding-the-search-syntax
    print("#"*20)
    print("Query data from github")
    try:
        from tipset.html_parser import paser_html_data
    except Exception:
        print("please install bs4")
        return False
    if not gh_url:
        print("no gh_url specified")
        return False
    if not gh_project:
        print("no gh_project specified")
        return False
    #start_date = datetime.datetime.fromisoformat(start_date)
    #end_date = datetime.datetime.fromisoformat(end_date)
    
    for name in names.split(','):
        if not name:
            continue
        print("-"*20)
        print("name:{}".format(name))
        query_url = "https://github.com/{}/pulls?q=is%3Apr+is%3Aclosed+author%3A{}+merged%3A{}..{}".format(gh_project, name, start_date, end_date)
        paser_html_data(url=query_url,keywords="pull/")

def query_jira(jira_url=None, names=None, start_date=None, end_date=None, jira_projects=None,jira_exclude_projects=None,jira_token=None):
    # ref docs: 
    # https://docs.github.com/en/search-github/getting-started-with-searching-on-github/understanding-the-search-syntax
    try:
        from jira import JIRA
    except ImportError:
        print("please install jira module")
        return False
    print("#"*20)
    jira_session = JIRA(token_auth=jira_token,server=jira_url)

    print("Query data from jira")
    jql_str = ''
    if jira_projects:
        converted = tuple(jira_projects.split(','))
        if jql_str:
            jql_str = jql_str + " and project in {}".format(converted)
        else:
            jql_str = "project in {}".format( converted)
            
        if len(converted) == 1:
            jql_str = jql_str.replace(',','')
    if jira_exclude_projects:
        converted = tuple(jira_exclude_projects.split(','))
        if jql_str:
            jql_str = jql_str + " and project not in ({})".format(converted)
        else:
            jql_str = "project not in {}".format(converted)
        if len(converted) == 1:
            jql_str = jql_str.replace(',','')
    if names:
        converted = tuple(names.split(','))
        if jql_str:
            jql_str = jql_str + " and reporter in {}".format(converted)
        else:
            jql_str = "reporter in {}".format(converted)
        if len(converted) == 1:
            jql_str = jql_str.replace(',','')
    jql_str = '{} and createdDate >= {} and createdDate <= {} ORDER BY  created DESC'.format(jql_str, start_date, end_date)
    print("jql_str:{}".format(jql_str))
    issues = jira_session.search_issues(jql_str)
    for issue in issues:
        if 'MigratedToJIRA' not in issue.fields.labels:
            components = []
            if  issue.fields.components:
                components = [i.name for i in issue.fields.components]
            print("{} - {}, {}, {}".format(issue.key, issue.fields.summary,components , issue.fields.reporter))
        
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

    query_rp(rp_url=cfg_data.get('rp_url'), rp_token=cfg_data.get('rp_token'), rp_project=cfg_data.get('rp_project'), 
        start_date=cfg_data.get('start_date'), end_date=cfg_data.get('end_date'), rp_page_size=cfg_data.get('rp_page_size'))
    if cfg_data.get('bugzilla_names'):
        query_bugzilla(bugzilla_url=cfg_data.get('bugzilla_url'), names=cfg_data.get('bugzilla_names').split(','), start_date=cfg_data.get('start_date'), 
            end_date=cfg_data.get('end_date'), bugzilla_token=cfg_data.get('bugzilla_token'),bugzilla_limit=cfg_data.get('bugzilla_limit'))
    if cfg_data.get('gh_names'):
        query_github(gh_url=cfg_data.get('gh_url'), names=cfg_data.get('gh_names'), start_date=cfg_data.get('start_date'), end_date=cfg_data.get('end_date'), gh_project=cfg_data.get('gh_project'))
    if cfg_data.get('jira_url'):
        query_jira(jira_url=cfg_data.get('jira_url'), names=cfg_data.get('jira_names'), start_date=cfg_data.get('start_date'), end_date=cfg_data.get('end_date'), 
        jira_projects=cfg_data.get('jira_project'),jira_exclude_projects=cfg_data.get('jira_exclude_projects'),jira_token=cfg_data.get('jira_token'))

if __name__ == "__main__":
    main()    