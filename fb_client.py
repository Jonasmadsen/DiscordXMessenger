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
