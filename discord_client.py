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

File: discord_client.py
Version: 0.1
Author: Kristian V., kristian@vestermark.me

Created: 15-11-2019
"""
import asyncio
import io
import os
from asyncio import coroutine

import aiohttp
import discord
from discord import Attachment

from dotenv import load_dotenv
from fbchat import ImageAttachment
from rx import Observable

from exceptions.unrecognized_attachment_exception import UnrecognizedAttachmentException
from fb_client import FBClient, Message, ThreadType
from message import Message as InternalMessage

load_dotenv()


class DiscordClient(discord.Client):
    def __init__(self, fb_client: FBClient, observable: Observable, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fb_client = fb_client
        self.observable = observable
        self.channel: discord.TextChannel = None
        self.thread_type = ThreadType.USER if os.getenv("THREAD_TYPE") == "USER" else ThreadType.GROUP
        self.thread_id = os.getenv("THREAD_ID")

    # Event called when Discord Bot is ready.
    async def on_ready(self):
        self.channel = self.get_channel(int(os.getenv("CHANNEL_ID")))

        print("Discord Bot ready.")
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("Operating on channel")
        print(f"Server name: {self.channel.guild}")
        print(f"Channel name: {self.channel.name}")
        print("-------------------")

        # Subscribe to observable. on_next defines function to call when observable emits.
        self.observable.subscribe(on_next=lambda s: self.send_message(s))

    async def on_message(self, message: discord.Message):
        if message.author != self.user:
            if message.attachments:
                attachment: Attachment = message.attachments.pop()  # TODO Check attachment type somehow
                self.fb_client.sendRemoteFiles(file_urls=attachment.url, message=f"{message.author}:", thread_id=self.thread_id, thread_type=self.thread_type)
            else:
                self.fb_client.send(Message(text=f"{message.author}: {message.content}"), thread_id=self.thread_id, thread_type=self.thread_type)

    # Coroutine called to send images to Discord channel.
    async def send_image(self, message: InternalMessage, attachment: ImageAttachment):
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
                await self.channel.send(content=f"{message.author}:", file=discord.File(data, f"{attachment.uid}.{attachment.original_extension}"))

    def send_message(self, message: InternalMessage):
        try:
            # Check if message contains attachments.
            if message.attachments:
                attachment_type_dict = {ImageAttachment: self.send_image}
                for attachment in message.attachments:
                    if type(attachment) in attachment_type_dict:
                        attachment_func: coroutine = attachment_type_dict.get(type(attachment))
                        asyncio.run_coroutine_threadsafe(attachment_func(message, attachment), self.loop)
                    else:
                        raise UnrecognizedAttachmentException(f"Message contained unrecognized attachment type. Message: \"{message.author}: {message.content}\". Attachment type: {type(attachment)}")
            else:
                asyncio.run_coroutine_threadsafe(self.channel.send(content=f"{message.author}: {message.content}"), self.loop)
        except UnrecognizedAttachmentException as exception:
            print(exception)
            asyncio.run_coroutine_threadsafe(self.channel.send(content=exception), self.loop)
