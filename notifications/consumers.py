from channels.generic.websocket import AsyncJsonWebsocketConsumer

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        await self.accept()
        await self.send_json({"debug": f"connected as {user} (id={getattr(user, 'id', None)}"})
        if user.is_anonymous:
            return await self.close()
        self.group_name = f"notifications_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

    async def disconnect(self, code):
        # only discard if we actually joined a group
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification(self, event):
        await self.send_json(event["payload"])

