"""
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Copyright Kristian Vestermark, all rights reserved.

File: fb_client.py
Version: 0.1
Author: Kristian V., kristian@vestermark.me

Created: 15-11-2019
"""
import json
import os

from dotenv import load_dotenv
from fbchat import Client
from fbchat.models import *
from rx.subject import Subject
from message import Message as InternalMessage

load_dotenv()


class FBClient(Client):
    def __init__(self, email, password, subject: Subject, session_cookies=None):
        super().__init__(email, password, session_cookies=session_cookies)
        self.subject = subject

    # Event called when message is received on Messenger.
    def onMessage(
            self,
            mid=None,
            author_id=None,
            message=None,
            message_object=None,
            thread_id=None,
            thread_type=ThreadType.USER,
            ts=None,
            metadata=None,
            msg=None,
    ):
        # Only react to messages from a specific thread.
        if thread_id == os.getenv("THREAD_ID"):
            # Dump session cookies and stop thread on !stop.
            if message_object.text == "!stop":
                with open('secrets/session.json', 'w') as f:
                    json.dump(self.getSession(), f)
                    exit(0)
            # Ignore messages from self. Only relevant if sending messages to self.
            if author_id == self.uid:
                return

            # Fetch user, needed to pass username through to Discord Bot.
            user = self.fetchUserInfo(message_object.author).get(message_object.author)

            # Push message to observable.

            self.subject.on_next(InternalMessage(content=f"{message_object.text}", author=f"{user.name}", attachments=message_object.attachments))
