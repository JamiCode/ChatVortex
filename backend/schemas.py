import pydantic
from datetime import datetime
from pydantic.utils import GetterDict
from typing import Any, List, Union
import peewee


class PeeweeGetterDict(GetterDict):
    def get(self, key: Any, default: Any = None):
        res = getattr(self._obj, key, default)
        if isinstance(res, peewee.ModelSelect):
            return list(res)
        return res



class AccessTokenResponse(pydantic.BaseModel):
    access_token:str
    token_type:str



class UserBase(pydantic.BaseModel):
    email:str
    username:str

class UserCreate(UserBase):
    password:str

class UserProfile(pydantic.BaseModel):
    profile_picture:Union[str, None]



class User(UserBase):
    user_id:int
    date_created:datetime

    class Config:
        orm_mode = True

class UserUpdateForm(pydantic.BaseModel):
    user_id:int
    username:str

class UserPasswordUpdateForm(pydantic.BaseModel):
    user_id:int
    password:str



# for the use of sockets
class UserSocketDisplay:
    user_id:int

    class Config:
        orm_mode = True



class GroupCreatePayload(pydantic.BaseModel):
    initiator_id:int
    initial_members:Union[List[int], None]
    group_name:str

class GroupSendPayload(pydantic.BaseModel):
    sender_id:int
    message_text:str

class MessagePayload(pydantic.BaseModel):
    sender_id:int
    recipient_id:int
class SendMessagePayLoad(MessagePayload):
    message_text:str


class ConversationPayload(pydantic.BaseModel):
    user_id:int
    recipient_id:int


class ChatHistoryRequest(pydantic.BaseModel):
    conversation_id:int

