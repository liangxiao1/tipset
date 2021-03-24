#!/usr/bin/env python
'''
github : https://github.com/liangxiao1/tipset

This tool parses ci event message which is json format to yaml and bash format
for easy access. The only input is ci mesage and the output is job_env.yaml
and job_env.txt file.

For example:
Below is ci message:
{
    "status": "FINISHED",
    "label": "aaa",
    "respin": 0,
    "date": "20191229",
    "version": "8.1.0",
    "options": {"option1":"ccc","option2":"ddd"},
    "params": ["param1","param2"]
}

To avoid conflicating with existing variables, the tool add 'JOB_' ahead of original fileds.
Below is job_env.yaml content:
"JOB_STATUS": "FINISHED"
"JOB_LABLE": "aaa"
"JOB_RESPIN": 0
"JOB_DATE": "20191229"
"JOB_VERSION": "8.1.0"
"JOB_OPTIONS_OPTION1": "ccc"
"JOB_OPTIONS_OPTION2": "ddd"
"JOB_PARAMS_1": "param1"
"JOB_PARAMS_2": "param2"

Below is job_env.txt content, you can source it directly for sh script using.
JOB_STATUS="FINISHED"
JOB_LABLE="aaa"
JOB_RESPIN=0
JOB_DATE="20191229"
JOB_VERSION="8.1.0"
JOB_OPTIONS_OPTION1="ccc"
JOB_OPTIONS_OPTION2="ddd"
JOB_PARAMS_1="param1"
JOB_PARAMS_2="param2"

$mkdir /tmp/2
$ s='{"a":"aaa","b":5,"c":["cc","ccc"],"dd":{"dd1":"dd1d","dd2":["dd2_list1","dd2_list2"]}}'
$ python json_parser.py -c $s --dir /tmp/2 --tag XX

'''

from __future__ import print_function
import logging
import argparse
import os
import json
from collections import OrderedDict

LOG = logging.getLogger(__name__)
LOG_FORMAT = "%(levelname)s:FUNC-%(funcName)s:%(message)s"
ARG_PARSER = argparse.ArgumentParser(
    description="dump json each items. \
        eg.  python json_parser.py -c $json_message --dir /tmp")
JOB_ENV_YAML = "job_env.yaml"
JOB_ENV_TXT = "job_env.txt"
FINAL_DICT = OrderedDict()

def is_dict(item):
    '''
    check item is a dict or not
    '''
    if  item.__class__ is dict:
        LOG.debug("It is a dict")
    else:
        LOG.debug("It is not a dict")
        return False
    return True

def is_list(item):
    '''
    check item is a list or not
    '''
    if item.__class__ is list:
        LOG.debug("It is a list")
    else:
        LOG.debug("It is not a list")
        return False
    return True

def walk_list(list_items, key_name):
    '''
    walk through a list
    '''

    for item in list_items:
        key = key_name + "_" + str(list_items.index(item))
        if not is_list(item) and not is_dict(item):
            LOG.info('%s, %s', key.upper(), item)
            FINAL_DICT[key.upper()] = item
        elif is_list(item):
            walk_list(item, key)
        elif is_dict(item):
            walk_dict(item, key)

def walk_dict(dict_items, key_name_org):
    '''
    walk through a dict
    '''
    for key in dict_items:
        key_name = key_name_org + "_" + str(key)
        if not is_list(dict_items[key]) and not is_dict(dict_items[key]):
            LOG.info('%s, %s, %s', key_name.upper(), key, dict_items[key])
            FINAL_DICT[key_name.upper()] = dict_items[key]
        elif is_list(dict_items[key]):
            walk_list(dict_items[key], key_name)
        elif is_dict(dict_items[key]):
            walk_dict(dict_items[key], key_name)

def json_parser(json_message):
    '''
    walk through json_message
    '''
    LOG.debug("The original message:\n%s", json_message)
    for key in json_message:
        key_name = PREFIX_TAG + "_" + str(key)
        if not is_dict(json_message[key]) and not is_list(json_message[key]):
            LOG.info('%s: %s', key.upper(), json_message[key])
            FINAL_DICT[key_name.upper()] = json_message[key]
        elif is_list(json_message[key]):
            walk_list(json_message[key], key_name)
        elif is_dict(json_message[key]):
            walk_dict(json_message[key], key_name)
    LOG.info(FINAL_DICT)

def write_env_txt():
    '''
    write to env txt file.
    '''
    with open(os.path.join(ARGS.file_dir, JOB_ENV_TXT), 'wt') as file_hanle:
        for key in FINAL_DICT:
            #LOG.debug(type(FINAL_DICT[key]))
            if not isinstance(FINAL_DICT[key], int) and not isinstance(FINAL_DICT[key], float):
                file_hanle.write('%s="%s"\n' % (key, FINAL_DICT[key]))
                LOG.debug('Write %s="%s"', key, FINAL_DICT[key])
            else:
                file_hanle.write('%s=%s\n' % (key, FINAL_DICT[key]))
                LOG.debug("Write %s=%s", key, FINAL_DICT[key])
    LOG.info("Write to %s", os.path.join(ARGS.file_dir, JOB_ENV_TXT))

def write_env_yaml():
    '''
    write to env json file.
    '''
    with open(os.path.join(ARGS.file_dir, JOB_ENV_YAML), 'wt') as file_hanle:
        for key in FINAL_DICT:
            if not isinstance(FINAL_DICT[key], int) and not isinstance(FINAL_DICT[key], float):
                file_hanle.write('%s: "%s"\n' % (key, FINAL_DICT[key]))
                LOG.debug('Write %s: "%s"', key, FINAL_DICT[key])
            else:
                file_hanle.write("%s: %s\n" % (key, FINAL_DICT[key]))
                LOG.debug("Write %s: %s", key, FINAL_DICT[key])
    LOG.info("Write to %s", os.path.join(ARGS.file_dir, JOB_ENV_YAML))

def main():
    global PREFIX_TAG
    global ARGS
    ARG_PARSER.add_argument('-d', dest='is_debug', action='store_true',
                            help='run in debug mode', required=False)
    ARG_PARSER.add_argument('-c', dest='json_message', action='store', default=None,
                            help='required, json like message', required=True)
    ARG_PARSER.add_argument('--dir', dest='file_dir', action='store', default='/tmp',
                            help='optional, output location, default is /tmp', required=False)
    ARG_PARSER.add_argument('--tag', dest='tag', action='store', default='JOB',
                            help='optional, the prefix tag added to each field, default is "JOB"',
                            required=False)

    ARGS = ARG_PARSER.parse_args()
    PREFIX_TAG = ARGS.tag

    if ARGS.is_debug:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    json_parser(json.loads(ARGS.json_message))
    write_env_txt()
    write_env_yaml()

if __name__ == '__main__':
    main()

    
