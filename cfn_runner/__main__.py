import boto3
import yaml
import json
import argparse
import os
import time
import sys
import traceback 
from deepmerge import always_merger

import sys
if sys.version_info[0] >= 3:
    unicode = str

def save_template(s3_url, template):
    s3 = boto3.resource('s3')

    bucket = s3_url.replace("s3:/", )

    s3object = s3.Object('your-bucket-name', 'your_file.json')


def main():
    
    def merge_dicts(x, y):
        """Given two dicts, merge them into a new dict as a shallow copy."""
        result = always_merger.merge(x,y)
        return result

    def get_stack_status(stackname, stack_properties):
        stackstatus = cloudformation.describe_stacks(
            StackName=stack_properties['stackname']
        )
        if "ROLLBACK" in stackstatus:
            print(json.dumps(stackstatus))

        return stackstatus['Stacks'][0]['StackStatus']

    def has_stack(stackname):
        try:

            cloudformation.describe_stacks(
                StackName=stackname
            )
        except :
            return False

        return True

    parser = argparse.ArgumentParser(description='Cloudformation Runner')
    parser.add_argument('--properties', dest='properties_filename',
                    help='Path to the properties file' , required=True)

    parser.add_argument('--tags', dest='tags_filename',
                    help='Path to the tags file')                   

    parser.add_argument('--resources', dest='resources_directory',
                    help='Path to the resources directory', required=True)                   


    parser.add_argument('--dryrun', dest='dry_run', action='store_true',
                    help='show a list of changes from existing stack')                   


    parser.add_argument('--s3Bucket', dest='s3_bucket',
                    help='S3 bucket to save the template, required if template if over 51200 bytes')   

    parser.add_argument('--s3Key', dest='s3_key',
                    help='S3 key to save the template, required if template if over 51200 bytes')   
    try:
        args = parser.parse_args()

        stack_properties = None
        stack_tags = {}

        if not args.properties_filename:
            print("properties filename not defined")
            sys.exit(1)

        with open(args.properties_filename, 'rt') as stream:
            try:
                stack_properties = yaml.load(stream, Loader=yaml.BaseLoader)
            except yaml.YAMLError as exc:
                print(exc)

        if args.tags_filename:
            with open(args.tags_filename, 'rt') as stream:
                try:
                    stack_tags = yaml.load(stream, Loader=yaml.BaseLoader)
                except yaml.YAMLError as exc:
                    print(exc)   
                    sys.exit(1)     


        taglist = []
        for key in stack_tags:
            prop = {
                "Key": key,
                "Value": stack_tags[key]
            }

            taglist.append(prop)

        parameter_list = []
        
        cloudformation = boto3.client('cloudformation', region_name=stack_properties['region'])
        s3 = boto3.resource('s3', region_name=stack_properties['region'])
        
        if 'parameters' in stack_properties:
            for propkey in stack_properties['parameters']:
                value = str(stack_properties['parameters'][propkey])
                print("{} type {}".format(value, type(value)))
               
                if isinstance(value, unicode):
                    value = str(value)

                if isinstance(value, str) and len(value) > 0 and value[0] is "$":
                    print("envar {}= {}", value[1:], os.environ[value[1:]])
                    value = os.environ[value[1:]]


                prop = {
                    "ParameterKey": propkey,
                    "ParameterValue": value if type(value) is str else str(value)
                }

                print("Param Key: {} Value: {}".format(prop["ParameterKey"], prop["ParameterValue"]))

                parameter_list.append(prop)    

        resources = {}
        for file in os.listdir(args.resources_directory):
            print("opening " + file)
            with open(args.resources_directory + "/" + file, 'rt') as stream:
                
                file_resources = yaml.load(stream, Loader=yaml.BaseLoader)
                resources = merge_dicts(resources, file_resources)

        response = {}

        if args.dry_run:

            change_type = "CREATE"

            print(json.dumps(resources))
            if has_stack(stack_properties['stackname']):
                change_type = 'UPDATE'

            try:
                cloudformation.create_change_set(
                        StackName=stack_properties['stackname'],
                        TemplateBody=json.dumps(resources),
                        Tags=taglist,
                        Capabilities=[
                            'CAPABILITY_IAM',
                            'CAPABILITY_NAMED_IAM',
                            'CAPABILITY_AUTO_EXPAND'
                        ],
                        Parameters=parameter_list,
                        ChangeSetName='test',
                        ChangeSetType=change_type
                    )

                
            except Exception as e:
                print (e)
                if 'No updates are to be performed' not in str(e) :
                    print ('not in e')
                    raise e
         
            response = cloudformation.describe_change_set(
                ChangeSetName='test',
                StackName=stack_properties['stackname']
            )

            while "CREATE_IN_PROGRESS" == response["Status"] or "CREATE_PENDING" == response["Status"] :
                print(response["Status"])
                time.sleep(3)

                response = cloudformation.describe_change_set(
                    ChangeSetName='test',
                    StackName=stack_properties['stackname']
                )

        
            # print(response)
            for change in response['Changes']:
                if "Type" in change and change["Type"] == "Resource":
                    print("{} {} {} {}".format(change["ResourceChange"]["Action"], change["ResourceChange"]["ResourceType"], change["ResourceChange"]["LogicalResourceId"], change["ResourceChange"]["PhysicalResourceId"]))

            cloudformation.delete_change_set(
                ChangeSetName='test',
                StackName=stack_properties['stackname']
            )
            
            print("Dry run complete")                    
            return
        else:
            print('not dry run')


        if has_stack(stack_properties['stackname']):
            print(resources)

            try:
                if args.s3_bucket:
                    object = s3.Object(args.s3_bucket, args.s3_key)
                    object.put(Body=json.dumps(resources))
                    response = cloudformation.update_stack(
                        StackName=stack_properties['stackname'],
                        TemplateURL="https://{}.s3.{}.amazonaws.com/{}".format(args.s3_bucket, stack_properties['region'], args.s3_key),
                        Tags=taglist,
                        Capabilities=[
                            'CAPABILITY_IAM',
                            'CAPABILITY_NAMED_IAM',
                            'CAPABILITY_AUTO_EXPAND'
                        ],
                        Parameters=parameter_list
                    )
                else:
                    response = cloudformation.update_stack(
                        StackName=stack_properties['stackname'],
                        TemplateBody=json.dumps(resources),
                        Tags=taglist,
                        Capabilities=[
                            'CAPABILITY_IAM',
                            'CAPABILITY_NAMED_IAM',
                            'CAPABILITY_AUTO_EXPAND'
                        ],
                        Parameters=parameter_list
                    )
            except Exception as e:
                if 'No updates are to be performed' not in str(e) :
                    print ('not in e')
                    raise e
        else:
            if args.s3_bucket:
                object = s3.Object(args.s3_bucket, args.s3_key)
                object.put(Body=json.dumps(resources))

                response = cloudformation.create_stack(
                    StackName=stack_properties['stackname'],
                    TemplateURL="https://{}.s3.{}.amazonaws.com/{}".format(args.s3_bucket, stack_properties['region'], args.s3_key),
                    Tags=taglist,
                    Capabilities=[
                        'CAPABILITY_IAM',
                        'CAPABILITY_NAMED_IAM',
                        'CAPABILITY_AUTO_EXPAND'
                    ],
                    Parameters=parameter_list
                )
            else:
                response = cloudformation.create_stack(
                    StackName=stack_properties['stackname'],
                    TemplateBody=json.dumps(resources),
                    Tags=taglist,
                    Capabilities=[
                        'CAPABILITY_IAM',
                        'CAPABILITY_NAMED_IAM'
                    ],
                    Parameters=parameter_list
                    
                )


        if response:
            print(response)

            stack_status = get_stack_status(stack_properties['stackname'], stack_properties)
            while "COMPLETE" not in stack_status:
                print (stack_status)
                time.sleep(3)
                stack_status = get_stack_status(stack_properties['stackname'], stack_properties)

            print (stack_status)
            if "ROLLBACK" in stack_status:
                raise Exception("Stack not updated properly")
        #     UPDATE_IN_PROGRESS
        else:
            print ("nothing to do")
    except Exception as ex:
        print(ex)
        print(traceback.format_exc())
        sys.exit(1)     
if __name__ == '__main__':
    main()
