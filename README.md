cfn_runner is tool to run cloud formation stacks with properties configured on a yaml file, the properties files can be used to deploy the same stack in multiple environments

** NOTE ** using the yaml shorthand is not supported e.g. ```!Ref logicalName```
## Cloudformation Stack
Stack resources can be broken apart into multiple YAML files which will get merged together. This wouls let you put your EC2 configuration in one file and RDS into another then have them merged into the same stack

## Properties File
The properties yaml file must contain the stack and region and then optional parameters. The value of parameters can also be environment variables if the value begins with a $ an environment variable will be used
```
region: us-east-1
stackname: stackname
parameters:
  foo: bar
  baz: $USER
```

## Install

```pip3 install git+git://github.com/KevinGlinski/cfn_runner```

## Usage

``` cfn_runner --properties example/properties.yml --resources example/resources --tags example/tags.yml ```