# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from awscli.customizations.lightsail.push_container_image \
    import PushContainerImage
from awscli.customizations.lightsail.decryptpassword \
    import PrivateKeyArgument


def initialize(cli):
    """
    The entry point for Lightsail high level commands.
    """
    cli.register('building-command-table.lightsail', inject_commands)
    cli.register(
        'building-argument-table.lightsail.get-instance-access-details',
        giad_add_private_key)


def inject_commands(command_table, session, **kwargs):
    """
    Called when the Lightsail command table is being built.
    Used to inject new high level commands into the command list.
    """
    command_table['push-container-image'] = PushContainerImage(session)


def giad_add_private_key(argument_table, operation_model, session, **kwargs):
    """
    This handler gets called after the argument table for the
    operation has been created.  It's job is to add the
    ``private-key`` parameter.
    """
    argument_table['private-key'] = PrivateKeyArgument(
        session, operation_model, 'private-key')
