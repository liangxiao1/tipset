import logging
import argparse
import copy
import os
import json
import re
import tipset
import sys

log = logging.getLogger(__name__)
FORMAT = "%(levelname)s:%(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)

result_dict = {}
def search_field(tips_data, field, keyword, tipids=None):
    for tipid in tips_data.keys():
        if tipids is not None:
            if tipid not in tipids.split(','):
                continue
        for tip in tips_data[tipid]:
            if isinstance(tips_data[tipid][field], list):
                for i in (tips_data[tipid][field]):
                    for x in i.keys():
                        if keyword.lower() in i[x].lower():
                            result_dict[tipid] = tips_data[tipid]
            elif keyword.lower() in tips_data[tipid][field].lower():
                result_dict[tipid] = tips_data[tipid]
            break

def print_result(tips_data, sum_only=False, fields_only=None, tipids=None):
    for tipid in tips_data.keys():
        if tipids is not None:
            if tipid not in tipids.split(','):
                continue
        for tip in tips_data[tipid]:
            log.info("-"*75)
            log.info("tipid:{} subject:{}".format(tipid, tips_data[tipid]['subject']))
            if sum_only:
                break
            if fields_only is not None:
                pass
            for step in tips_data[tipid]['demo_steps']:
                log.info("step:{}".format(step['step']))
                if len(step['out'])>1:
                    log.info("out:{}".format(step['out']))
            log.info("tags:{}".format(tips_data[tipid]['tags']))
            log.info("comments:{}".format(tips_data[tipid]['comments']))
            log.info("link:{}".format(tips_data[tipid]['link']))
            break

def main():
    parser = argparse.ArgumentParser(
    description="tipsearch is a colletion of tips with demo.")
    parser.add_argument('-k', dest='keywords', default=None, action='store',
                    help='use comma to split multiple keywords', required=False)
    parser.add_argument('-f', dest='fields', default=None, action='store',
                    help='search from specific field, split by comma', required=False)
    parser.add_argument('-i', dest='tipids', default=None, action='store',
                    help='show tips by specific tipid directly', required=False)
    parser.add_argument('-s', dest='sum_only', action='store_true',
                    help='list tipid and subject only', required=False)
    args = parser.parse_args()
    log.info("Run in mode: keywords:{} fields: {} tipids: {} sum_only: {}".format(args.keywords, args.fields, args.tipids, args.sum_only))
    # tips data file
    tips_data_file = os.path.dirname(tipset.__file__) + "/data/tips_data.json"
    # Result dir
    fileds = ['subject', 'demo_steps', 'tags', 'comments', 'link']
    with open(tips_data_file,'r') as fh:
        log.info("Loading baseline data file from {}".format(tips_data_file))
        tips_data = json.load(fh)
    if args.keywords is None:
        log.info("No keyword specified, show all items!")
        print_result(tips_data, sum_only=args.sum_only, tipids=args.tipids)
        sys.exit(0)
    for keyword in args.keywords.split(','):
        if args.fields is not None:
            for field in args.fields.split(','):
                if field not in fileds:
                    log.error("{} not support field {}".format(field, fileds))
                    continue
                search_field(tips_data, field, keyword, tipids=args.tipids)
        else:
            for field in fileds:
                search_field(tips_data, field, keyword, tipids=args.tipids)
    print_result(result_dict, sum_only=args.sum_only,tipids=args.tipids)
    log.info("Total found: {}".format(len(result_dict)))

if __name__ == "__main__":
    main()