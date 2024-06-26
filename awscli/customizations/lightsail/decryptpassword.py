# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import logging
import os
import base64

import jmespath

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from awscli.compat import six

from botocore.model import Shape
from botocore.utils import set_value_from_jmespath

from awscli.arguments import BaseCLIArgument


logger = logging.getLogger(__name__)


HELP = """<p>The file that contains the private key of the keypair
used when the instance created (e.g. windows-keypair.pem).  If this
is supplied, the password ciphertext returned in the response will
be decrypted, and will appear in the password field.</p>"""


class PrivateKeyArgument(BaseCLIArgument):

    def __init__(self, session, operation_model, name):
        self._session = session
        self.argument_model = Shape('PrivateKeyArgument', {'type': 'string'})
        self._operation_model = operation_model
        self._name = name
        self._key_path = None
        self._required = False

    @property
    def cli_type_name(self):
        return 'string'

    @property
    def required(self):
        return self._required

    @required.setter
    def required(self, value):
        self._required = value

    @property
    def documentation(self):
        return HELP

    def add_to_parser(self, parser):
        parser.add_argument(self.cli_name, dest=self.py_name,
                            help='SSH Private Key file')

    def add_to_params(self, parameters, value):
        """
        This gets called with the value of our ``--private-key``
        if it is specified.  It needs to determine if the path
        provided is valid and, if it is, it stores it in the instance
        variable ``_key_path`` for use by the decrypt routine.
        """
        if value:
            path = os.path.expandvars(value)
            path = os.path.expanduser(path)
            if os.path.isfile(path):
                self._key_path = path
                endpoint_prefix = \
                    self._operation_model.service_model.endpoint_prefix
                service_id = self._operation_model.service_model.service_id
                event = 'after-call.%s.%s' % (service_id.hyphenize(),
                                              self._operation_model.name)
                self._session.register(event, self._decrypt_password_data)
            else:
                msg = ('private-key should be a path to the '
                       'local SSH private key file of the keypair '
                       'used to create the instance.')
                raise ValueError(msg)

    def _decrypt_password_data(self, parsed, **kwargs):
        """
        This handler gets called after the GetInstanceAccessDetails command has
        been executed.  It is called with the encrypted password in the
        ``parsed`` data.  It checks to see if a private key was specified on
        the command.  If it was, it tries to use that private key to decrypt
        the password data and put it in the returned data dictionary.
        """
        if self._key_path is not None:
            logger.debug("Decrypting password data using: %s", self._key_path)
            value = jmespath.search(
                'accessDetails.passwordData.ciphertext', parsed)
            if not value:
                return
            try:
                with open(self._key_path, 'rb') as pk_file:
                    pk_bytes = pk_file.read()
                    backend = default_backend()
                    private_key = load_pem_private_key(pk_bytes, None, backend)
                    value = base64.b64decode(value)
                    value = private_key.decrypt(value, PKCS1v15())
                    logger.debug(parsed)
                    set_value_from_jmespath(
                        parsed,
                        'accessDetails.password',
                        value.decode('utf-8'))
                    logger.debug(parsed)
            except Exception:
                logger.debug('Unable to decrypt password', exc_info=True)
                msg = ('Unable to decrypt password ciphertext using '
                       'provided private key file.')
                raise ValueError(msg)