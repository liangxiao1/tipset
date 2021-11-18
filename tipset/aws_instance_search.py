#!/usr/bin/env python
'''
github : https://github.com/liangxiao1/tipset

This tool is for find or clean up instances in all supported regions by keyname/tag
'''
from datetime import datetime, timezone
import argparse
import logging
import concurrent.futures
import sys
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Please install boto3")
    sys.exit(1)
from tipset.libs import aws_libs
from tipset.libs import minilog
def main():
    parser = argparse.ArgumentParser('To list/clean up instances cross regions')
    parser.add_argument('--key_name', dest='key_name', action='store',\
        help='specify for instance, seperated by ","', required=False)
    parser.add_argument('--tags', dest='tags', action='store',\
        help='specify for tags, seperated by ","', required=False)
    parser.add_argument('--delete', dest='delete', action='store_true',\
        help='optional, specify for delete instances, otherwise list only', required=False)
    parser.add_argument('-d', dest='is_debug', action='store_true',\
        help='optional, run in debug mode', required=False, default=False)
    parser.add_argument('--force', dest='is_force', action='store_true',\
        help='optional, force delete', required=False, default=False)
    parser.add_argument('--skip_region', dest='skip_region', action='store',\
        help='optional skip regions, seperated by ","', required=False, default=None)
    parser.add_argument('--region', dest='only_region', action='store',\
        help='optional only regions for checking, seperated by ","', required=False, default=None)
    parser.add_argument('--profile', dest='profile', default='default', action='store',
        help='option, profile name in aws credential config file, default is default', required=False)
    parser.add_argument('--days', dest='days_over', default='0', action='store',
        help='option, resource exists over days, default is 0', required=False)
    args = parser.parse_args()

    log = minilog.minilog()
    if args.is_debug:
        log.show_debug = True
    _, client = aws_libs.aws_init_key(profile=args.profile, log=log)
    region_list = client.describe_regions()
    if args.delete and not args.is_force:
        delete_confirm = input("Are you sure want to delete instances found?(yes/no)")
        if 'yes' not in delete_confirm:
            log.info("Please remove --delete if you do not want to delete")
            sys.exit(0)
    elif args.delete and args.is_force:
        log.info("Will force delete found instances")
    instance_csv = '/tmp/exists_instances.csv'
    instance_csv_header = ['Key', 'Tag', 'LaunchTime', 'Instance Id', 'State', 'Live Days', 'Zone']
    aws_libs.init_csv_header(csv_file=instance_csv, header_list=instance_csv_header)
    for region in region_list['Regions']:
        region_name = region['RegionName']
        if args.skip_region is not None and region_name in args.skip_region:
            log.info('Skip {}'.format(region_name))
            continue
        if args.only_region is not None and region_name not in args.only_region:
            log.info('Skip {}'.format(region_name))
            continue
        log.info("Check {} ".format(region_name))
        aws_libs.search_instances(region=region_name, profile=args.profile, key_name=args.key_name, 
            tags=args.tags, is_delete=args.delete, days_over=args.days_over, csv_file=instance_csv,log=log)
    log.info("instances saved to {}".format(instance_csv))
if __name__ == '__main__':
    main()
