import sys
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Please install boto3")
    sys.exit(1)
from . import minilog
from datetime import datetime
import csv
from filelock import FileLock
import os

def aws_init_key(region=None, profile=None, log=None):
    if log is None:
        log = minilog.minilog()
    default_regions = ['us-west-2', 'cn-northwest-1', 'us-gov-west-1']
    if region is None:
        default_regions = ['us-west-2', 'cn-northwest-1', 'us-gov-west-1']
    else:
        default_regions = [region]
    if profile is None:
        profile = 'default'
    log.info("Use profile:{} in region {}".format(profile,default_regions))
    ec2_resource = None
    ec2_client = None
    for region in default_regions:
        try:
            session = boto3.session.Session(profile_name=profile, region_name=region)
            ec2_resource = session.resource('ec2', region_name=region)
            ec2_client = session.client('ec2', region_name=region)
            region_list = ec2_client.describe_regions()['Regions']
            log.info("Init key in region {} successfully".format(region))
            break
        except Exception as error:
            log.info("Try to init in region:{} result:{}".format(region,str(error)))
    if ec2_resource is None:
        log.error('Unable to init {} in any region'.format(profile))
        sys.exit(1)
    return ec2_resource, ec2_client

def reource_delete(resource_id=None, resource_type=None, region=None, profile=None, log=None):
    """
    resource_type is instance|volume
    """
    if log is None:
        log = minilog.minilog()
    ec2, _ = aws_init_key(region=region,profile=profile,log=log)
    try:
        if 'instance' in resource_type:
            vm = ec2.Instance(resource_id)
            vm.terminate()
        elif 'volume' in resource_type:
            volume = ec2.Volume(resource_id)
            volume.delete()
        else:
            return False
    except Exception as exc:
        log.error("delete {} in {} got error {}".format(resource_id, region, exc))
        return False
    log.info('{} terminated in {}'.format(resource_id, region))
    return True

def init_csv_header(csv_file=None, header_list=None, log=None):
    if log is None:
        log = minilog.minilog()
    if os.path.exists(csv_file):
        os.unlink(csv_file)
    with FileLock(csv_file + '.lock'):
        with open(csv_file,'w+',newline='') as fh:
            csv_operator =csv.writer(fh)
            csv_operator.writerow(header_list)
    log.info('init {} header done!'.format(csv_file))
    return True

def print_volume(volume=None, days_over=0, csv_file=None, log=None):
    if log is None:
        log = minilog.minilog()
    today = datetime.today()
    live_days = today - volume['CreateTime'].replace(tzinfo=None)
    live_days = live_days.days
    if int(live_days) < int(days_over):
        return
    volume_id = volume['VolumeId']
    if 'Tags' in volume.keys():
        tag = volume['Tags'][0]['Value']
    else:
        tag = 'N/A'
    zone = volume['AvailabilityZone']

    log.info('id:{}, Tag:{}, CreateTime:{}, state:{}, live:{} days, zone:{}'.format(
            volume_id, tag, volume['CreateTime'], volume['State'],live_days, zone))
    if csv_file is None:
        return True
    with FileLock(csv_file + '.lock'):
        with open(csv_file,'a+',newline='') as fh:
            csv_operator =csv.writer(fh)
            csv_operator.writerow([volume_id,
                tag, volume['CreateTime'], 
                volume['State'],live_days, zone])

def print_instance(instance=None, days_over=0, csv_file=None, log=None):
    if log is None:
        log = minilog.minilog()
    today = datetime.today()
    live_days = today - instance['LaunchTime'].replace(tzinfo=None)
    live_days = live_days.days
    if int(live_days) < int(days_over):
        return
    instance_id = instance['InstanceId']
    if 'Tags' in instance.keys():
        tag = instance['Tags'][0]['Value']
    else:
        tag = 'N/A'
    zone = instance['Placement']['AvailabilityZone']

    log.info('Key:{}, Tag:{}, LaunchTime:{}, id:{}, state:{}, live:{} days, zone:{}'.format(instance['KeyName'],
            tag, instance['LaunchTime'], 
            instance_id,instance['State']['Name'],live_days, zone))
    if csv_file is None:
        return True
    with FileLock(csv_file + '.lock'):
        with open(csv_file,'a+',newline='') as fh:
            csv_operator =csv.writer(fh)
            csv_operator.writerow([instance['KeyName'],
                tag, instance['LaunchTime'], 
                instance_id,instance['State']['Name'],live_days,zone])

def search_volumes(region=None, profile=None,notused=False, tags=None, is_delete=False, days_over=0, csv_file=None, log=None):
    if log is None:
        log = minilog.minilog()
    _, client = aws_init_key(profile=profile, region=region, log=log)
    volumes_dict = {"Volumes":[]}
    tmp_dict_all = client.describe_volumes()
    loop = 0
    while True:
        log.info('Get all volumes loop {}'.format(loop))
        loop = loop + 1
        volumes_dict['Volumes'].extend(tmp_dict_all['Volumes'])
        try:
            nexttoken = tmp_dict_all['NextToken']
        except KeyError as err:
            log.info("Get all volumes done, length {}".format(len(volumes_dict["Volumes"])))
            break
        if nexttoken == None:
            log.info("Get all volumes done, length {}".format(len(volumes_dict["Volumes"])))
            break
        tmp_dict_all = client.describe_volumes(NextToken=nexttoken)

    tmp_volume = []

    for volume in volumes_dict['Volumes']:
        try:
            if notused:
                if 'available' in volume['State']:
                    tmp_volume.append(volume)
                    continue
            elif tags is not None:
                for tag in tags.split(','):
                    if 'Tags' in volume.keys():
                        for val  in volume['Tags'][0].values():
                            if tag in val:
                                tmp_volume.append(volume)
            else:
                tmp_volume.append(volume)
        except KeyError as err:
            log.info("No such words found {}".format(err))
    tmp_volume.sort(key=lambda k: k['AvailabilityZone'])

    for volume in tmp_volume:
        print_volume(volume=volume, days_over=days_over, csv_file=csv_file)
        if is_delete:
            volume_id = volume['VolumeId']
            reource_delete(resource_id=volume_id, resource_type='volume', region=region, profile=profile)

def search_instances(region=None, profile=None,key_name=None, tags=None, is_delete=False, days_over=0, csv_file=None, log=None):
    if log is None:
        log = minilog.minilog()
    _, client = aws_init_key(profile=profile, region=region, log=log)
    instances_dict = {"Instances":[]}
    tmp_dict_all = client.describe_instances()
    loop = 0
    while True:
        log.info('Get all instances loop {}'.format(loop))
        loop = loop + 1
        for i in tmp_dict_all['Reservations']:
            instances_dict["Instances"].extend(i['Instances'])
        try:
            nexttoken = tmp_dict_all['NextToken']
        except KeyError as err:
            log.info("Get all instances done, length {}".format(len(instances_dict["Instances"])))
            break
        if nexttoken == None:
            log.info("Get all instances done, length {}".format(len(instances_dict["Instances"])))
            break
        tmp_dict_all = client.describe_instances(NextToken=nexttoken)

    tmp_instance = []
    for instance in instances_dict['Instances']:
        try:
            if key_name is not None:
                for key_name in key_name.split(','):
                    if 'KeyName' in instance.keys():
                        if key_name in instance['KeyName']:
                            tmp_instance.append(instance)
            elif tags is not None:
                for tag in tags.split(','):
                    if 'Tags' in instance.keys():
                        for val  in instance['Tags'][0].values():
                            if tag in val:
                                tmp_instance.append(instance)
            else:
                tmp_instance.append(instance)
        except KeyError as err:
            log.info("No such words found {}".format(err))
    for instance in tmp_instance:
        if 'KeyName' not in instance.keys():
            instance['KeyName'] = '-'
    tmp_instance.sort(key=lambda k: k['KeyName'])
    for instance in tmp_instance:
        print_instance(instance=instance,days_over=days_over, csv_file=csv_file)
        if is_delete:
            instance_id = instance['InstanceId']
            reource_delete(resource_id=instance_id, resource_type='instance', region=region, profile=profile)