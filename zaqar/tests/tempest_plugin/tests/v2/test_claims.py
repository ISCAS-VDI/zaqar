# Copyright (c) 2016 HuaWei, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from six.moves.urllib import parse as urlparse
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators

from zaqar.tests.tempest_plugin.tests import base


CONF = config.CONF


class TestClaims(base.BaseV2MessagingTest):

    @classmethod
    def resource_setup(cls):
        super(TestClaims, cls).resource_setup()
        cls.queue_name = data_utils.rand_name('Queues-Test')
        # Create Queue
        cls.create_queue(cls.queue_name)

    def _post_and_claim_messages(self, queue_name, repeat=1):
        # Post Messages
        message_body = self.generate_message_body(repeat=repeat)
        self.client.post_messages(queue_name=self.queue_name,
                                  rbody=message_body)

        # Post Claim
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        resp, body = self.client.post_claims(queue_name=self.queue_name,
                                             rbody=claim_body)

        return resp, body

    @decorators.idempotent_id('3b839cac-d214-4fca-8c03-b8edbdcecb20')
    def test_post_claim(self):
        _, body = self._post_and_claim_messages(queue_name=self.queue_name)
        claimed_message_uri = body['messages'][0]['href']

        # Delete Claimed message
        self.client.delete_messages(claimed_message_uri)

    @decorators.idempotent_id('e69d047c-b3f4-4216-990e-7953407084b7')
    def test_query_claim(self):
        # Post a Claim
        resp, body = self._post_and_claim_messages(queue_name=self.queue_name)

        # Query Claim
        claim_uri = resp['location'][resp['location'].find('/v2'):]
        self.client.query_claim(claim_uri)

        # Delete Claimed message
        claimed_message_uri = body['messages'][0]['href']
        self.delete_messages(claimed_message_uri)

    @decorators.idempotent_id('5e1e7559-77fc-4ea8-a817-cd43be23d692')
    def test_update_claim(self):
        # Post a Claim
        resp, body = self._post_and_claim_messages(queue_name=self.queue_name)

        claim_uri = resp['location'][resp['location'].find('/v2'):]
        claimed_message_uri = body['messages'][0]['href']

        # Update Claim
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        update_rbody = {"ttl": claim_ttl}

        self.client.update_claim(claim_uri, rbody=update_rbody)

        # Verify claim ttl >= updated ttl value
        _, body = self.client.query_claim(claim_uri)
        updated_claim_ttl = body["ttl"]
        self.assertTrue(updated_claim_ttl >= claim_ttl)

        # Delete Claimed message
        self.client.delete_messages(claimed_message_uri)

    @decorators.idempotent_id('97c1ebcc-9d1e-463a-8673-6ec989ba3be7')
    def test_release_claim(self):
        # Post a Claim
        resp, body = self._post_and_claim_messages(queue_name=self.queue_name)
        claim_uri = resp['location'][resp['location'].find('/v2'):]

        # Release Claim
        self.client.delete_claim(claim_uri)

        # Delete Claimed message
        # This will implicitly verify that the claim is deleted.
        message_uri = urlparse.urlparse(claim_uri).path
        self.client.delete_messages(message_uri)

    @classmethod
    def resource_cleanup(cls):
        cls.delete_queue(cls.queue_name)
        super(TestClaims, cls).resource_cleanup()
