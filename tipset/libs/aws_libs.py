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
import json
import traceback

def aws_init_key(region=None, profile=None, log=None, client_type='ec2',resource_type='ec2'):
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
            resource = session.resource(resource_type, region_name=region)
            client = session.client(client_type, region_name=region)
            ec2_client = session.client('ec2', region_name=region)
            ec2_resource = session.resource('ec2', region_name=region)
            region_list = ec2_client.describe_regions()['Regions']
            log.info("Init key in region {} successfully".format(region))
            break
        except Exception as error:
            log.info("Try to init in region:{} result:{}".format(region,str(error)))
    if ec2_resource is None:
        log.error('Unable to init {} in any region'.format(profile))
        sys.exit(1)
    return resource, client

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

def search_instances(region=None, profile=None, filters=None, is_delete=False, days_over=0, csv_file=None, csv_header=None, log=None,exclude_tags=None):
    if not log:
        log = minilog.minilog()
    resource, client = aws_init_key(profile=profile, region=region, log=log)
    
    instances_dict = {"Instances":[]}
    #print(json.loads(filters))
    if filters:
        tmp_dict_all = client.describe_instances(Filters=json.loads(filters))
    else:
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

    for instance in instances_dict['Instances']:
        today = datetime.today()
        live_days = today - instance['LaunchTime'].replace(tzinfo=None)
        live_days = live_days.days
        tags = ''
        if 'Tags' in instance.keys():
            for tag in instance['Tags']:
                tags += tag.get('Value')
            is_excluded = False
            if exclude_tags:
                for tag in exclude_tags.split(','):
                    if tag in tags:
                        print("exclude {} as tag {} found".format(instance.get('InstanceId'),tag))
                        is_excluded = True
                        break
            if is_excluded:
                continue
        instance_row_dict = { 'Region':region,
                              'InstanceId':instance.get('InstanceId'),
                              'InstanceType':instance.get('InstanceType'),
                              'KeyName':instance.get('KeyName'),
                              'LaunchTime':instance.get('LaunchTime').isoformat(),
                              'Days':live_days,
                              'Tags':tags,
                              'State':instance['State'].get('Name')
                            }
        if days_over:
            if int(live_days) >= int(days_over):
                save_to_file(resource_file=csv_file,row_dict=instance_row_dict,file_header=csv_header, log=log)
        else:
            save_to_file(resource_file=csv_file,row_dict=instance_row_dict,file_header=csv_header, log=log)
        instance_id = instance['InstanceId']
        if days_over:
            if is_delete and int(live_days) >= int(days_over):
                reource_delete(resource_id=instance_id, resource_type='instance', region=region, profile=profile)
        else:    
            if is_delete:
                reource_delete(resource_id=instance_id, resource_type='instance', region=region, profile=profile)  

#def search_images(region, regionids, result_list, is_check, filter_json, filter,amiids,is_delete, tag_skip, profile, days_over=0):

def search_images(region=None, profile=None, filters=None, is_delete=False, days_over=0, csv_file=None, csv_header=None, log=None, exclude_tags=None):
    if not log:
        log = minilog.minilog()
    _, sts_client = aws_init_key(profile=profile, region=region, client_type='sts', log=log)
    account_id = sts_client.get_caller_identity().get('Account')
    resource, client = aws_init_key(profile=profile, region=region, log=log)

    images_dict = {"Images":[]}
    if filters:
        tmp_dict_all = client.describe_images(
                Filters=json.loads(filters),
                Owners=[account_id]
            )
    else:
        tmp_dict_all = client.describe_images(Owners=[account_id])
    loop = 0
    while True:
        log.info('Get all images loop {}'.format(loop))
        loop = loop + 1
        #for i in tmp_dict_all['Images']:
        images_dict["Images"].extend(tmp_dict_all['Images'])
        try:
            nexttoken = tmp_dict_all['NextToken']
        except KeyError as err:
            log.info("Get all images done, length {}".format(len(images_dict["Images"])))
            break
        if nexttoken == None:
            log.info("Get all images done, length {}".format(len(images_dict["Images"])))
            break
        tmp_dict_all = client.describe_images(NextToken=nexttoken)
#IMAGE_FILE_HEADERS = ['Region', 'ImageId','Name','Description','CreationDate','Days','lastLaunchedTime','Days','Tags','State','SnapshotId','Public','OwnerId']
    for image in images_dict['Images']:
        tags = ''
        if 'Tags' in image.keys():
            #tags = image['Tags'][0]['Value']
            for tag in image['Tags']:
                tags += tag.get('Value')
            is_excluded = False
            if exclude_tags:
                for tag in exclude_tags.split(','):
                    if tag in tags:
                        print("exclude {} as tag {} found".format(image.get('ImageId'),tag))
                        is_excluded = True
                        break
            if is_excluded:
                continue
        
        today = datetime.today()
        create_date = datetime.fromisoformat(image.get('CreationDate'))
        live_days = today - create_date.replace(tzinfo=None)
        live_days = live_days.days

        image_attribute = client.describe_image_attribute(
                Attribute='lastLaunchedTime',
                ImageId=image.get('ImageId')
            )
        last_launch = image_attribute['LastLaunchedTime'].get('Value')
        if last_launch:
            last_days = today - datetime.fromisoformat(last_launch).replace(tzinfo=None)
            last_days = last_days.days
        else:
            last_days = ''
        image_row_dict = { 'Region':region,
                          'ImageId':image.get('ImageId'),
                          'Name':image.get('Name'),
                          'Description':image.get('Description'),
                          'CreationDate':create_date,
                          'LiveDays':live_days,
                          'lastLaunchedTime':last_launch,
                          'LastDays':last_days,
                          'Tags':tags,
                          'State':image.get('State'),
                          'SnapshotId':image['BlockDeviceMappings'][0]['Ebs']['SnapshotId'],
                          'Public':image.get('Public'),
                          'OwnerId':account_id
                        }
        if days_over:
            if int(live_days) >= int(days_over):
                save_to_file(resource_file=csv_file,row_dict=image_row_dict,file_header=csv_header, log=log)
        else:
            save_to_file(resource_file=csv_file,row_dict=image_row_dict,file_header=csv_header, log=log)
        image_id = image['ImageId']
        if days_over:
            if is_delete and int(live_days) >= int(days_over):
                reource_delete(resource_id=image_id, resource_type='ami', region=region, profile=profile)
        else:    
            if is_delete:
                reource_delete(resource_id=image_id, resource_type='ami', region=region, profile=profile)

def search_snapshots(region=None, profile=None, filters=None, is_delete=False, days_over=0, csv_file=None, csv_header=None, log=None, exclude_tags=None):
    if not log:
        log = minilog.minilog()
    _, sts_client = aws_init_key(profile=profile, region=region, client_type='sts', log=log)
    account_id = sts_client.get_caller_identity().get('Account')
    resource, client = aws_init_key(profile=profile, region=region, log=log)

    snapshots_dict = {"Snapshots":[]}
    if filters:
        tmp_dict_all = client.describe_snapshots(
                Filters=json.loads(filters),
                OwnerIds=[account_id]
            )
    else:
        tmp_dict_all = client.describe_snapshots(OwnerIds=[account_id])
    loop = 0
    while True:
        log.info('Get all snapshots loop {}'.format(loop))
        loop = loop + 1
        snapshots_dict["Snapshots"].extend(tmp_dict_all['Snapshots'])
        try:
            nexttoken = tmp_dict_all['NextToken']
        except KeyError as err:
            log.info("Get all snapshots done, length {}".format(len(snapshots_dict["Snapshots"])))
            break
        if nexttoken == None:
            log.info("Get all snapshots done, length {}".format(len(snapshots_dict["Snapshots"])))
            break
        tmp_dict_all = client.describe_snapshots(NextToken=nexttoken)

    for snapshot in snapshots_dict['Snapshots']:
        tags = ''
        if 'Tags' in snapshot.keys():
            for tag in snapshot['Tags']:
                tags += tag.get('Value')
            is_excluded = False
            if exclude_tags:
                for tag in exclude_tags.split(','):
                    if tag in tags:
                        print("exclude {} as tag {} found".format(snapshot.get('SnapshotId'),tag))
                        is_excluded = True
                        break
            if is_excluded:
                continue
        
        today = datetime.today()
        create_date = snapshot.get('StartTime')
        live_days = today - create_date.replace(tzinfo=None)
        live_days = live_days.days
        try:
            vol = resource.Volume(snapshot.get('VolumeId'))
            vol_state = vol.state
        except Exception as exc:
            vol_state = 'N/A'
        
        images = client.describe_images(Owners=[account_id],
            Filters=[
                {
                    'Name': 'block-device-mapping.snapshot-id',
                    'Values': [
                        snapshot.get('SnapshotId'),
                    ]
                },
            ])
        amis = 'Not registered'
        if images.get('Images'):
            amis = ''
            for image in images.get('Images'):
                amis += image.get('ImageId')
#SNAPSHOTS_FILE_HEADERS = ['Region', 'SnapshotId','Description','Tags','StartTime','Days','State','VolumeId','VolumeSize','State','OwnerId']
        snapshot_row_dict = { 'Region':region,
                          'SnapshotId':snapshot.get('SnapshotId'),
                          'Description':snapshot.get('Description'),
                          'Tags':tags,
                          'StartTime':snapshot.get('StartTime').isoformat(),
                          'Days':live_days,
                          'State':tags,
                          'VolumeId':snapshot.get('VolumeId'),
                          'VolumeSize':snapshot.get('VolumeSize'),
                          'State':vol_state,
                          'Images':amis,
                          'OwnerId':account_id
                        }
        if days_over:
            if int(live_days) >= int(days_over):
                save_to_file(resource_file=csv_file,row_dict=snapshot_row_dict,file_header=csv_header, log=log)
        else:
            save_to_file(resource_file=csv_file,row_dict=snapshot_row_dict,file_header=csv_header, log=log)
        snap_id = snapshot['SnapshotId']
        if days_over:
            if is_delete and int(live_days) >= int(days_over):
                reource_delete(resource_id=snap_id, resource_type='snapshot', region=region, profile=profile)
        else:
            if is_delete:
                reource_delete(resource_id=snap_id, resource_type='snapshot', region=region, profile=profile)

def search_volumes(region=None, profile=None, filters=None, is_delete=False, days_over=0, csv_file=None, csv_header=None, log=None, exclude_tags=None):
    if not log:
        log = minilog.minilog()
    _, sts_client = aws_init_key(profile=profile, region=region, client_type='sts', log=log)
    account_id = sts_client.get_caller_identity().get('Account')
    resource, client = aws_init_key(profile=profile, region=region, log=log)

    volumes_dict = {"Volumes":[]}
    if filters:
        tmp_dict_all = client.describe_volumes(
                Filters=json.loads(filters)
            )
    else:
        tmp_dict_all = client.describe_volumes()
    loop = 0
    while True:
        log.info('Get all volumes loop {}'.format(loop))
        loop = loop + 1
        volumes_dict["Volumes"].extend(tmp_dict_all['Volumes'])
        try:
            nexttoken = tmp_dict_all['NextToken']
        except KeyError as err:
            log.info("Get all volumes done, length {}".format(len(volumes_dict["Volumes"])))
            break
        if nexttoken == None:
            log.info("Get all volumes done, length {}".format(len(volumes_dict["Volumes"])))
            break
        tmp_dict_all = client.describe_snapshots(NextToken=nexttoken)

    for volume in volumes_dict['Volumes']:
        tags = ''
        if 'Tags' in volume.keys():
            for tag in volume['Tags']:
                tags += tag.get('Value')
            is_excluded = False
            if exclude_tags:
                for tag in exclude_tags.split(','):
                    if tag in tags:
                        print("exclude {} as tag {} found".format(volume.get('VolumeId'),tag))
                        is_excluded = True
                        break
            if is_excluded:
                continue
        today = datetime.today()
        create_date = volume.get('CreateTime')
        live_days = today - create_date.replace(tzinfo=None)
        live_days = live_days.days
#VOLUMES_FILE_HEADERS = ['Region', 'VolumeId','Size','Tags','CreateTime','Days','State','SnapshotId']
        volume_row_dict = { 'Region':region,
                          'VolumeId':volume.get('VolumeId'),
                          'Size':volume.get('Size'),
                          'Tags':tags,
                          'CreateTime':volume.get('CreateTime').isoformat(),
                          'Days':live_days,
                          'State':volume.get('State'),
                          'SnapshotId':volume.get('SnapshotId'),
                        }
        if days_over:
            if int(live_days) >= int(days_over):
                save_to_file(resource_file=csv_file,row_dict=volume_row_dict,file_header=csv_header, log=log)
        else:
            save_to_file(resource_file=csv_file,row_dict=volume_row_dict,file_header=csv_header, log=log)
        vol_id = volume.get('VolumeId')
        if days_over:
            if is_delete and int(live_days) >= int(days_over):
                reource_delete(resource_id=vol_id, resource_type='volume', region=region, profile=profile)
        else:
            if is_delete:
                reource_delete(resource_id=vol_id, resource_type='volume', region=region, profile=profile)


def save_to_file(resource_file=None,  file_header=None, row_dict=None, log=None):
    if log is None:
        log = minilog.minilog()

    with FileLock(resource_file + '.lock'):
        with open(resource_file,'a+',newline='') as fh:
            csv_operator = csv.DictWriter(fh,file_header)
            csv_operator.writerow(row_dict)

def del_resource_from_file(resource_file=None, resource_type=None, log=None, profile='default', is_delete=False):
    if log is None:
        log = minilog.minilog()
    log.info("load resourcs from file: {} resource_type:{}".format(resource_file,resource_type))
    with FileLock(resource_file + '.lock'):
        with open(resource_file,'r',newline='') as fh:
            csv_data = csv.DictReader(fh)
            for r in csv_data:
                if 'ami' in resource_type:
                    resource_id = r.get("ImageId")
                elif 'instance' in resource_type:
                    resource_id = r.get("InstanceId")
                elif 'snap' in resource_type:
                    resource_id = r.get("SnapshotId")
                elif 'vol' in resource_type:
                    resource_id = r.get("VolumeId")
                region = r.get('Region')
                if is_delete:
                    reource_delete(resource_id=resource_id, resource_type=resource_type, region=region, profile=profile)

def reource_delete(resource_id=None, resource_type=None, region=None, client=None, resource=None, profile=None, log=None):
    """
    resource_type is instance|volume|snapshot|ami
    """
    if log is None:
        log = minilog.minilog()
    if not resource or client:
        resource, client = aws_init_key(region=region,profile=profile,log=log)
    try:
        log.info('try to delete {} from region {}'.format(resource_id,region))
        if 'instance' in resource_type:
            vm = resource.Instance(resource_id)
            try:
                vm.terminate()
            except Exception as exc:
                log.info("cannot delete {} {}".format(resource_id,exc))  
        elif 'volume' in resource_type:
            vol = resource.Volume(resource_id)
            if 'vol-ffffffff' in resource_id:
                return True
            try:
                vol.delete()
            except Exception as exc:
                log.info("cannot delete {} {}".format(resource_id,exc))  
        elif 'ami' in resource_type:
            image = resource.Image(resource_id)
            snapid = image.block_device_mappings[0]['Ebs']['SnapshotId']
            try:
                image.deregister()
            except Exception as exc:
                log.info("cannot delete {} {}".format(resource_id,exc))  
            reource_delete(resource_id=snapid, resource_type='snapshot', region=region,client=client,resource=resource,profile=profile, log=log)   
        elif 'snap' in resource_type:
            snap = resource.Snapshot(resource_id)
            volid = snap.volume_id
            try:
                snap.delete()
            except Exception as exc:
                log.info("cannot delete {} {}".format(resource_id,exc))  
            reource_delete(resource_id=volid, resource_type='volume', region=region,client=client,resource=resource,profile=profile, log=log)   
        else:
            return False
    except Exception as exc:
        log.error("delete {} in {} got error {}".format(resource_id, region, exc))
        traceback.print_exc()
        return False
    #log.info('{} terminated in {}'.format(resource_id, region))
    return True
