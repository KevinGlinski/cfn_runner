import boto3
import yaml
import json
import argparse
import os
import time
import sys
import traceback 

def main():
    
    def merge_dicts(x, y):
        """Given two dicts, merge them into a new dict as a shallow copy."""
        z = x.copy()
        z.update(y)
        return z

    def get_stack_status(stackname, stack_properties):
        stackstatus = cloudformation.describe_stacks(
            StackName=stack_properties['stackname']
        )
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

    try:
        args = parser.parse_args()

        stack_properties = None
        stack_tags = {}

        if not args.properties_filename:
            print("properties filename not defined")
            sys.exit(1)

        with open(args.properties_filename, 'r') as stream:
            try:
                stack_properties = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        if args.tags_filename:
            with open(args.tags_filename, 'r') as stream:
                try:
                    stack_tags = yaml.load(stream)
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
        print(stack_properties)

        cloudformation = boto3.client('cloudformation', region_name=stack_properties['region'])

        for propkey in stack_properties['parameters']:
            value = stack_properties['parameters'][propkey]
            print(value)
            if type(value) is str and value[0] is "$":
                value = os.environ[value[1:]]

            prop = {
                "ParameterKey": propkey,
                "ParameterValue": str(value).lower() if type(value) is bool else value
            }

            parameter_list.append(prop)    

        resources = {}
        for file in os.listdir(args.resources_directory):
            with open(args.resources_directory + "/" + file, 'r') as stream:

                file_resources = yaml.load(stream)
                print('-----')
                print(file_resources)
                resources = merge_dicts(resources, file_resources)

        print(resources)

        response = {}

        if has_stack(stack_properties['stackname']):
            try:

                response = cloudformation.update_stack(
                    StackName=stack_properties['stackname'],
                    TemplateBody=json.dumps(resources),
                    Tags=taglist,
                    Capabilities=[
                        'CAPABILITY_IAM',
                    ],
                    Parameters=parameter_list
                )
            except Exception as e:
                if 'No updates are to be performed' not in str(e) :
                    print ('not in e')
                    raise e
        else:
            response = cloudformation.create_stack(
                StackName=stack_properties['stackname'],
                TemplateBody=json.dumps(resources),
                Tags=taglist,
                Capabilities=[
                    'CAPABILITY_IAM',
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
                raise "Stack not updated properly"
        #     UPDATE_IN_PROGRESS
        else:
            print ("nothing to do")
    except Exception as ex:
        print(ex)
        print(traceback.format_exc())
        sys.exit(1)     
if __name__ == '__main__':
    main()