#!/usr/bin/env python
'''
github : https://github.com/liangxiao1/tipset

This tool is for getting element value from html.

Use examples:

$ python html_parser.py --url 'https://xxxxxx/buildinfo?buildID=1612972' --dir /tmp --keyword 'Tags' --element tr --field text --outputfield text -r
INFO:Not found in self content, try to look for child......
INFO:Got ['rhel-9.0.0-beta-candidate', 'rhel-9.0.0-beta-devtest-test']

Get kernel-debug url from brew build page.
$ python html_parser.py --url 'https://xxxxxx/buildinfo?buildID=1612972' --dir /tmp --keyword 'kernel-debug' --excludekeys "src,devel,internal,debuginfo,extra" --andkeys "x86" --element a --field href
INFO:found href http://download.xxxxxx/x86_64/kernel-debug-5.13.0-0.rc3.25.el9.x86_64.rpm for target download
INFO:found href http://download.xxxxxx/x86_64/kernel-debug-core-5.13.0-0.rc3.25.el9.x86_64.rpm for target download
INFO:found href http://download.xxxxxx/x86_64/kernel-debug-modules-5.13.0-0.rc3.25.el9.x86_64.rpm for target download

Get kernel source rpm from build page.
$ python html_parser.py --url 'https://xxxxxx/buildinfo?buildID=1612972'  --dir /tmp --keyword 'src'  --andkeys "rpm" --element a --field href
INFO:found href http://download.xxxxxx/src/kernel-5.13.0-0.rc3.25.el9.src.rpm for target download

$ tail -2 /tmp/job_env.txt
JOB_PKGURL='download' (this is when "--outputfield href" )
JOB_PKGURL='http://download.eng.bos.redhat.com/brewroot/vol/rhel-9/packages/kernel/5.13.0/0.rc3.25.el9/src/kernel-5.13.0-0.rc3.25.el9.src.rpm'
'''
import json
from bs4 import BeautifulSoup
import bs4
import os
import sys
try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen
import logging
import argparse
import string
import re

def walk_child(elements, key, is_found=False, results=[]):
    if hasattr(elements, 'children'):
        for child in elements.children:
            if not hasattr(child, 'children'):
                if len(child)>1 and is_found and key not in child:
                    results.append(child)
            if key in child:
                is_found = True
            walk_child(child, key, is_found=is_found,results=results)
    return is_found, results

def filter_key(src_content, keywords, filed, match_any=True):
    if keywords is None:
        return False
    ret = False
    for keyword in keywords.split(','):
        if filed == 'href' and src_content.get('href') and re.match('.*'+keyword+'.*', src_content.get('href')):
            ret = True
        elif re.match('.*'+keyword+'.*', src_content.get_text()):
            ret = True
        else:
            if match_any and ret:
                break
    return ret

def main():
    parser = argparse.ArgumentParser('Script for get info from html')
    parser.add_argument('--url',dest='url',action='store',help='specify url',default=None,required=True)
    parser.add_argument('--keyword',dest='keyword',action='store',help='specify keyword you are looking for, regex accepted',default=None,required=True)
    parser.add_argument('--andkeys',dest='andkeys',action='store',help='must have keys in and',default=None,required=False)
    parser.add_argument('--orkeys',dest='orkeys',action='store',help='must have keys in or',default=None,required=False)
    parser.add_argument('--excludekeys',dest='excludekeys',action='store',help='specify keyword you are not looking for',default=None,required=False)
    parser.add_argument('--tag',dest='tag',action='store',help='optional specify prefix tag, default is JOB_',default='JOB_',required=False)
    parser.add_argument('--name',dest='name',action='store',help='optional specify suffix name, default is PKGURL',default='PKGURL',required=False)
    parser.add_argument('--field',dest='check_field',action='store',help='href|text, default is href',default='href',required=False)
    parser.add_argument('--outputfield',dest='output_field',action='store',help='href|text, default is href',default='href',required=False)
    parser.add_argument('--element',dest='check_element',action='store',help='default is "a", you can specify others like "br","tr","div"',default='a',required=False)
    parser.add_argument('-r', dest='is_walk',action='store_true',help='walk the child to find match items, only support when filed is text', required=False,default=False)
    parser.add_argument('--dir', dest='file_dir', action='store', default='/tmp',
                                help='optional, output location, default is /tmp', required=False)
    args=parser.parse_args()
    
    log = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO,format="%(levelname)s:%(message)s")
    url = args.url
    keywords = args.keyword
    andkeys = args.andkeys
    orkeys = args.orkeys
    excludekeys = args.excludekeys
    tag = args.tag
    name = args.name
    url_fh = urlopen(url)
    html_src = url_fh.read()
    with open('arch_taskinfo.txt','w') as fh:
        fh.writelines(str(html_src))
    soup = BeautifulSoup(html_src,'lxml')
    log.info("loading data done")
    JOB_DIR = args.file_dir
    JOB_ENV_YAML = JOB_DIR+"/job_env.yaml"
    JOB_ENV_TXT = JOB_DIR+"/job_env.txt"
    results=[]
    
    s=soup.findAll(args.check_element)
    
    for i in s:
        #log.info("name: %s, url: %s",i.get_text(),  i['href'])
        is_exclude = filter_key(i, excludekeys, args.check_field)
        is_and_key = filter_key(i,andkeys, args.check_field, match_any=False)
        is_or_key = filter_key(i,orkeys, args.check_field)
        if not keywords:
            break
        for keyword in keywords.split(','):
            if is_exclude and excludekeys:
                break
            if not is_and_key and andkeys:
                break
            if not is_or_key and orkeys:
                break
            #breakpoint()
            if args.check_field == 'href' and i.get('href') and re.match('.*'+keyword+'.*', i.get('href')):
                log.info("found href %s for target %s", i.get('href'), i.get_text())
                if args.output_field == 'href':
                    results.append(i.get('href'))
                else:
                    results.append(i.get_text())
            elif re.match('.*'+keyword+'.*', i.get_text()):
                log.info("found %s", i.get_text())
                if args.output_field == 'href':
                    try:
                        results.append(i.get('href'))
                    except:
                        log.info("no href for %s", i.get_text())
                        results.append(i.get_text())
                else:
                    results.append(i.get_text())
        if len(results) == 0 and args.is_walk:
            for keyword in keywords.split(','):
                x, y = walk_child(i, keyword)
                if x:
                    results.extend(y)
            if len(results) > 0:
                log.info("Not found in self content, try to look for child......")
                log.info("Got {}".format(results))
                
    
    if len(results) > 0:
        with open(JOB_ENV_YAML, 'a') as fh:
            fh.write("%s%s: '%s'\n"% (tag, name, ','.join(results)))
            log.info("Write to %s", JOB_ENV_YAML)
        with open(JOB_ENV_TXT, 'a') as fh:
            fh.write("%s%s='%s'\n"% (tag, name,','.join(results)))
            log.info("Write to %s", JOB_ENV_TXT)
    else:
        log.info("Not found any match content!")

if __name__ == "__main__":
    main()