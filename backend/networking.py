from typing import List, Dict
from fastapi import WebSocket
from datetime import datetime
import schemas
import models
import json

class ChatHistoryConnectionManager:
    def __init__(self):
        self.connections = set()

    async def connect(self, websocket:WebSocket, user_id):
        await websocket.accept()
        self.connections.add((user_id, websocket))

    def disconnect(self, websocket:WebSocket, user_id):
        self.connections.remove((user_id,websocket))


class ClientConnectionManager:
    """
    The ConnectionManager class keeps track of all active connected clients connections and is used in the websocket endpoint to add and remove connections. This way we can later send messages from the server to specific or all clients if we want to, like sending notifications when an event or data update occurred for example.
    """
    def __init__(self):
        self.active_connections: Dict[int, websocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int, ping_timeout:int =None):
        if not user_id in self.active_connections.keys():
            print("Connected to server", user_id)
            await websocket.accept()
            models.User.update(is_active=True).where(models.User.user_id == user_id).execute()
            self.active_connections[user_id] = websocket
        else:
            #user already connected
            print("User already connected")
            await websocket.accept()

    def disconnect(self, user_id: int):
        current_timestamp = datetime.utcnow()
        models.User.update(last_seen=current_timestamp).where(models.User.user_id == user_id).execute()
        models.User.update(is_active=False).where(models.User.user_id == user_id).execute()
        if self.active_connections.get(user_id):
            del self.active_connections[user_id]
    

   


