#!/usr/bin/env python
'''
github : https://github.com/liangxiao1/tipset

This is a tool for monitoring resources on aws.
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
import traceback

LOG = minilog.minilog()
INSTANCE_FILE = '/tmp/aws_instances.csv'
INSTANCE_FILE_HEADERS = ['Region', 'InstanceId','InstanceType', 'KeyName','LaunchTime','Days','Tags','State']

IMAGE_FILE = '/tmp/aws_images.csv'
IMAGE_FILE_HEADERS = ['Region', 'ImageId','Name','Description','CreationDate','LiveDays','lastLaunchedTime','LastDays','Tags','State','SnapshotId','Public','OwnerId']

SNAPSHOTS_FILE = '/tmp/aws_snapshots.csv'
SNAPSHOTS_FILE_HEADERS = ['Region', 'SnapshotId','Description','Tags','StartTime','Days','State','VolumeId','VolumeSize','State','OwnerId','Images']

VOLUMES_FILE = '/tmp/aws_volumes.csv'
VOLUMES_FILE_HEADERS = ['Region', 'VolumeId','Size','Tags','CreateTime','Days','State','SnapshotId']

def monitor_instances(regions=None, profile='default', filters=None, is_delete=False, days_over=0, log=None, exclude_tags=None):
    aws_libs.init_csv_header(csv_file=INSTANCE_FILE, header_list=INSTANCE_FILE_HEADERS)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        all_jobs = {executor.submit(aws_libs.search_instances, region=region, profile=profile, filters=filters, is_delete=is_delete,exclude_tags=exclude_tags, days_over=days_over, csv_file=INSTANCE_FILE,csv_header=INSTANCE_FILE_HEADERS, log=log): region for region in regions}
        for r in concurrent.futures.as_completed(all_jobs, timeout=1800):
            x = all_jobs[r]
            try:
                data = r.result()
            except Exception as exc:
                traceback.print_exc()
                #print('{} generated an exception: {}'.format(r,exc))
            else:
                pass
    #for region in regions:
    #    LOG.info("Check {} ".format(region))
    #    aws_libs.search_instances(region=region, profile=profile, filters=filters, is_delete=False, days_over=0, csv_file=INSTANCE_FILE,csv_header=INSTANCE_FILE_HEADERS, log=log)
    LOG.info("instances saved to {}".format(INSTANCE_FILE))

def monitor_snapshots(regions=None, profile='default', filters=None, is_delete=False, days_over=0, log=None, exclude_tags=None):
    aws_libs.init_csv_header(csv_file=SNAPSHOTS_FILE, header_list=SNAPSHOTS_FILE_HEADERS)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        all_jobs = {executor.submit(aws_libs.search_snapshots, region=region, profile=profile, filters=filters, is_delete=is_delete,exclude_tags=exclude_tags, days_over=days_over, csv_file=SNAPSHOTS_FILE,csv_header=SNAPSHOTS_FILE_HEADERS, log=log): region for region in regions}
        for r in concurrent.futures.as_completed(all_jobs, timeout=1800):
            x = all_jobs[r]
            try:
                data = r.result()
                
            except Exception as exc:
                traceback.print_exc()
                #print('{} generated an exception: {}'.format(r,exc))
            else:
                pass
    LOG.info("snapshots saved to {}".format(SNAPSHOTS_FILE))

def monitor_amis(regions=None, profile='default', filters=None, is_delete=False, days_over=0, log=None, exclude_tags=None):
    aws_libs.init_csv_header(csv_file=IMAGE_FILE, header_list=IMAGE_FILE_HEADERS)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        all_jobs = {executor.submit(aws_libs.search_images, region=region, profile=profile, filters=filters, is_delete=is_delete,exclude_tags=exclude_tags, days_over=days_over, csv_file=IMAGE_FILE,csv_header=IMAGE_FILE_HEADERS, log=log): region for region in regions}
        for r in concurrent.futures.as_completed(all_jobs, timeout=1800):
            x = all_jobs[r]
            try:
                data = r.result()
                
            except Exception as exc:
                traceback.print_exc()
                #print('{} generated an exception: {}'.format(r,exc))
            else:
                pass
    LOG.info("images saved to {}".format(IMAGE_FILE))

def monitor_volumes(regions=None, profile='default', filters=None, is_delete=False, days_over=0, log=None, exclude_tags=None):
    aws_libs.init_csv_header(csv_file=VOLUMES_FILE, header_list=VOLUMES_FILE_HEADERS)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        all_jobs = {executor.submit(aws_libs.search_volumes, region=region, profile=profile, filters=filters, is_delete=is_delete,exclude_tags=exclude_tags, days_over=days_over, csv_file=VOLUMES_FILE,csv_header=VOLUMES_FILE_HEADERS, log=log): region for region in regions}
        for r in concurrent.futures.as_completed(all_jobs, timeout=1800):
            x = all_jobs[r]
            try:
                data = r.result()
                
            except Exception as exc:
                traceback.print_exc()
                #print('{} generated an exception: {}'.format(r,exc))
            else:
                pass
    LOG.info("snapshots saved to {}".format(VOLUMES_FILE))

def main():
    parser = argparse.ArgumentParser('A tool for monitoring resources on aws.')

    parser.add_argument('--days', dest='days_over', default='0', action='store',
        help='option, resource exists over N days, default value is 0', required=False)
    parser.add_argument('--debug', dest='is_debug', action='store_true',
        help='optional, run in debug mode', required=False, default=False)
    parser.add_argument('--delete', dest='delete', action='store_true',
        help='optional, specify for delete operation, otherwise list only', required=False)
    parser.add_argument('--filters', dest='filters', action='store',
        help='optional, json filters like in awscli, eg.  \'[{"Name":"tag:Name","Values":["xiliang*"]}]\'', required=False)
    parser.add_argument('--exclude_tags', dest='exclude_tags', action='store',
        help='optional, exclude resources with tags', required=False)
    parser.add_argument('--force', dest='is_force', action='store_true',
        help='optional, force action without confirmation', required=False, default=False)
    parser.add_argument('--profile', dest='profile', default='default', action='store',
        help='optional, profile name in .aws/credentials, default value is "default"', required=False)
    parser.add_argument('--regions', dest='only_regions', action='store',
        help='optional, specify which region to check, seperated by ",", default is all', required=False, default=None)
    parser.add_argument('--exclude_regions', dest='exclude_regions', action='store',
        help='optional, specify which region to exclude, seperated by ","', required=False, default=None)
    parser.add_argument('--type', dest='resource_type', default='all', action='store',
        help='optional, pick up from instance,volume,ami,snapshot, default show them all', required=False)
    parser.add_argument('--resources', dest='resources', default=None, action='store',
        help='optional, specify a resources csv file to delete them in auto', required=False)

    args = parser.parse_args()

    if args.is_debug:
        LOG.show_debug = True
    
    resource, client = aws_libs.aws_init_key(profile=args.profile, log=LOG)
    global region_list
    regions_all = client.describe_regions()
    region_list = []
    for region in regions_all['Regions']:
        region_list.append(region['RegionName'])
    if args.only_regions:
        region_list = args.only_regions.split(',')
    if args.exclude_regions:
        for region in args.exclude_regions(',').split(','):
            region_list.remove(region)
    
    if args.delete and not args.is_force:
        delete_confirm = input("Are you sure want to delete resources found?(yes/no)")
        if 'yes' not in delete_confirm:
            LOG.info("Please remove --delete if you do not want to remove them!")
            sys.exit(0)
    elif args.delete and args.is_force:
        LOG.info("Will force delete resources found!")

    if args.resources:
        aws_libs.del_resource_from_file(resource_file=args.resources, resource_type=args.resource_type, profile=args.profile, log=LOG, is_delete=args.delete)
        sys.exit()
    if 'all' in args.resource_type or 'instance' in args.resource_type:
        monitor_instances(regions=region_list, profile=args.profile, filters=args.filters, is_delete=args.delete, days_over=args.days_over, log=LOG, exclude_tags=args.exclude_tags)
    if 'all' in args.resource_type or 'ami' in args.resource_type:
        monitor_amis(regions=region_list, profile=args.profile, filters=args.filters, is_delete=args.delete, days_over=args.days_over, log=LOG, exclude_tags=args.exclude_tags)
    if 'all' in args.resource_type or 'snap' in args.resource_type:
        monitor_snapshots(regions=region_list, profile=args.profile, filters=args.filters, is_delete=args.delete, days_over=args.days_over, log=LOG, exclude_tags=args.exclude_tags)
    if 'all' in args.resource_type or 'volume' in args.resource_type:
        monitor_volumes(regions=region_list, profile=args.profile, filters=args.filters, is_delete=args.delete, days_over=args.days_over, log=LOG, exclude_tags=args.exclude_tags)
    
if __name__ == '__main__':
    main()
