import asyncio
import io
import os
import urllib.request

import aiohttp
import discord
from discord import Attachment

from dotenv import load_dotenv
from fbchat import ImageAttachment
from rx import Observable
from fb_client import FBClient, Message, ThreadType
from message import Message as internalMessage

load_dotenv()


class DiscordClient(discord.Client):
    def __init__(self, fb_client: FBClient, observable: Observable, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fb_client = fb_client
        self.observable = observable

    # Event called when Discord Bot is ready.
    async def on_ready(self):
        print("Discord Bot ready.")
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("-------------------")

        # Subscribe to observable. on_next defines function to call when observable emits.
        self.observable.subscribe(on_next=lambda s: self.send_message(s))

    # Event called when message is received through Discord.
    async def on_message(self, message):
        # Make sure message author is not self.
        if message.author != self.user:
            # Check if the message contains attachments.
            if message.attachments:
                # Check if the message has multiple attachments.
                if len(message.attachments) > 1:
                    # If the message contains multiple attachments, raise an exception.
                    raise Exception("More than one attachment received in a single message.")
                else:
                    # Otherwise we assume the attachment is an image and send it to FB. TODO Dont assume this.
                    attachment: Attachment = message.attachments.pop()
                    self.fb_client.sendRemoteImage(attachment.url, message=f"{message.author}:",
                                                   thread_id=os.getenv("THREAD_ID"), thread_type=ThreadType.USER)
            # If the message contains no attachments, just send it.
            else:
                # Create a message string from author name and message content.
                message_str = f"{message.author}: {message.content}"
                # Send message string in messenger using fb_client.send.
                # Env var THREAD_ID must be id of thread to send to.
                # ThreadType is USER for user to user chats, GROUP for group chats.
                self.fb_client.send(Message(text=message_str), thread_id=os.getenv("THREAD_ID"),
                                    thread_type=ThreadType.USER)

    # Coroutine called to send images to Discord channel.
    async def send_image(self, message, attachment, channel):
        # Get image url.
        image_url = self.fb_client.fetchImageUrl(attachment.uid)
        # Attempt to download image.
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                # If unable to download image, raise an exception
                if resp.status != 200:
                    raise Exception("Unable to download picture.")
                data = io.BytesIO(await resp.read())
                # Send image.
                await channel.send(file=discord.File(data, f"{attachment.uid}.jpg"))

    # Synchronous function that adds channel.send to the event loop.
    def send_message(self, message: internalMessage):
        # Get channel from env var CHANNEL_ID
        channel = self.get_channel(int(os.getenv("CHANNEL_ID")))

        # Check if message contains attachments.
        if message.attachments:
            # Check that there is only 1 attachment.
            if len(message.attachments) > 1:
                raise Exception("More than one attachment received in a single message.")

            attachment = message.attachments.pop()
            # Check that the attachment is an Image
            if isinstance(attachment, ImageAttachment):
                # Run the coroutine for sending an image message.
                asyncio.run_coroutine_threadsafe(self.send_image(message, attachment, channel), self.loop)

            # If the attachment is not an image, raise an exception.
            else:
                raise Exception("Attachment is not an image.")
        # If message does not contain attachments, just send the contents.
        else:
            asyncio.run_coroutine_threadsafe(channel.send(message.content), self.loop)
