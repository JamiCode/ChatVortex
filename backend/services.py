from database import db
from models import User,Conversation, Message, ConversationParticipant, Group, GroupMessage
import models
import email_validator as _email_checker
import sys
import schemas as _schemas
import fastapi
import passlib.hash as _hash
from jose import JWTError, jwt
import secrets
from database import db_state_default
from fastapi import Depends, FastAPI, HTTPException, WebSocket, Request
from fastapi.exceptions import WebSocketException
from fastapi import security
from typing import Dict
import jose
import peewee
import json
import base64
from datetime import datetime


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)




JWT_SECRET = '72YRvjqvXkSApDRkDaJxYBzOUnsvDvCKZAl2hMRsyrw'
oauth2schema = security.OAuth2PasswordBearer("/api/token") # we are telling fast api to expect a valid access token in order to access the endpoint

def create_db():
    db.connect()
    db.create_tables([User, Conversation, ConversationParticipant, Message, Group, GroupMessage])
    db.close()
async def reset_db_state():
    db._state._state.set(db_state_default.copy()) # type: ignore
    db._state.reset() # type: ignore



def check_who_none(value, value2):
    if value is None:
        return "Sender"
    elif value2 is None:
        return "recipient"

def get_db(db_state=Depends(reset_db_state)):
    try:
        db.connect()
        yield
    finally:
        if not db.is_closed():
            db.close()


async def get_user_by_email(email:str):
    """ This gets the user by his email"""
    return User.filter(User.email == email).first()

async def get_user_by_username(username:str):
    return User.filter(User.username == username).first()
   

async def create_user(user:_schemas.UserCreate):
    #before we create the user we want to check if the email is valid
    #if it is not valid, raise HttpException
    try:
        valid = _email_checker.validate_email(email=user.email)
        email = valid.email
    except _email_checker.EmailNotValidError:
        raise fastapi.HTTPException(
            status_code=404, 
            detail="Invalid Email"
        )
    #if everything is working fine create the user in the database,
    password_hashed = _hash.bcrypt.hash(user.password)

    user_obj = User.create(email=user.email, username=user.username, hashed_password=password_hashed, is_active=True, is_admin=False)
    return user_obj
     



# so keep in mind each token is tied with an information, one must have this token in other to get access to the information
async def create_token(user:models.User):
    #creates the pydantic schema, fom he user objec
    user_schema_obj =_schemas.User.from_orm(user)
    user_dict = user_schema_obj.dict() #serializes, puts in dictinary format   
    print(user_dict)
    user_dict["date_created"] = user_dict['date_created'].strftime('%Y-%m-%d %H:%M:%S')
    created_token = jwt.encode(user_dict, JWT_SECRET, algorithm='HS256') #token is created by hiding user_dict information. under the oken

    #so whenever someone provides the right token, he would have access to what is tied to this token

    return dict(access_token=created_token, token_type="bearer")



async def authenticate_user(email:str, password:str)->bool:
    user = await get_user_by_email(email=email)
    
    if not user: #if not user
        return False
    if not user.verify_password(password=password):
        return False
    return user



async def authenticate_token(token:str = Depends(oauth2schema)):
    """ This is the custom dependency that checks for token"""
    payload = jwt.decode(token, JWT_SECRET, algorithms="HS256")
    user = User.get_or_none(User.user_id == payload['user_id'])
    if not user:
        raise fastapi.HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    return token


async def get_current_user(token:str = Depends(oauth2schema)):
    
    try:
        #this decodes the jwt token, to get access to the data attached to it (this is called the payload)
        payload = jwt.decode(token, JWT_SECRET, algorithms="HS256")
        user = User.get(payload["user_id"]) 
    except Exception as e:
        raise fastapi.HTTPException(
                    status_code=401,
                    detail="Invalid email or password"
        )
    return _schemas.User.from_orm(user) # returns the pydantic serialize form 


async def update_user(user_id:int, new_username:str):
    user = User.get(User.user_id == user_id)
    try:
        user.username = new_username
        user.save()
        return True
    except:
        return False

async def update_password(user_id:int, new_password:str):
    hashed_new_password = _hash.bcrypt.hash(new_password)
    user = User.get(User.user_id == user_id)
    try:
        user.hashed_password = hashed_new_password
        user.save()
        return True
    except:
        return False 



async def verify_socket_connection(token):
    #getting informatino from token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms="HS256")
        user = User.get_or_none(User.user_id == payload["user_id"])
        username = User.get_or_none(User.username == payload['username'])
        if user and username:
            return user
        else:
            raise WebSocketException(code=fastapi.status.WS_1008_POLICY_VIOLATION, reason="Token information not found")

    except jose.exceptions.JWTError:
        raise WebSocketException(code=fastapi.status.WS_1008_POLICY_VIOLATION, reason="Invalid token")


async def get_token(websocket:WebSocket):
    token_1 = websocket.headers.get("Authorization")
    if token_1 is None:
        #if token is None
        raise WebSocketException(code=fastapi.status.WS_1008_POLICY_VIOLATION, reason="Token not found in header")
    token = token = token_1.split("Bearer ")[-1]
    #return the token
    return token

async def get_token_http(request:Request):
    headers = dict(request.headers.items())
    token = headers['authorization'][7:]
    return token

async def get_token_from_id():
    """ This functions gets jwt token from the id, and returns the jwt"""
    pass

async def conversation_exist(user1_id, user2_id):

    def filter_dm(conversation):
        return conversation.conversation_type == "DM"

    #Keep in mind this codes search for conversation in general(meanin all)
    # Find all conversations that include user1
    user1_conversations = set(cp.conversation_id for cp in ConversationParticipant.select().where(ConversationParticipant.participant_id == user1_id))

    # Find all conversations that include user2
    user2_conversations = set(cp.conversation_id for cp in ConversationParticipant.select().where(ConversationParticipant.participant_id == user2_id))

    # Find the intersection of the two sets of conversations
    common_conversations = user1_conversations.intersection(user2_conversations)
    # Return True if there is at least one common conversation

    if not len(common_conversations) > 0:
        return None

    dm_conversation = tuple(filter(filter_dm, common_conversations))

    if not len(dm_conversation) > 0:
        return None
    return tuple(filter(filter_dm, common_conversations))[0]

    # dont forget to add modification to check for common convsrvatin for dm and return that


async def check_for_conversation(sender_id, recipient_id):
    conversation = models.Conversation.select().join(models.ConversationParticipant).where(
    (models.ConversationParticipant.participant_id == sender_id) |
    (models.ConversationParticipant.participant_id == recipient_id)
    ).group_by(models.Conversation.conversation_id).having(
    peewee.fn.COUNT(models.ConversationParticipant.participant_id) == 2
    ).first()
    return conversation

async def get_recent_chat_list_dm(conversation_id):
  conversation_obj = models.Conversation.get_or_none(models.Conversation.conversation_id == conversation_id) 
  if conversation_obj is None or not len(conversation_obj.messages) > 0:
    return None
  return conversation_obj.messages[-1].message_text


async def get_recent_chat_list_group(conversation_id):
  conversation_obj = models.Conversation.get_or_none(models.Conversation.conversation_id == conversation_id) 
  if conversation_obj is None or not len(conversation_obj.group_messages) > 0 :
    return None
  return conversation_obj.group_messages[-1].message_text


   

async def get_conversations(user_id):
    conversations = []
    conversation_participants = models.ConversationParticipant.select().where(models.ConversationParticipant.participant_id == user_id)

    for conversation_participant in conversation_participants:
        # Extracting the conversation
        conversation = conversation_participant.conversation_id
        if conversation.conversation_type == 'Group': # check if conversation is a group conversation
            # get all participants in the group
            group_participants = models.ConversationParticipant.select().where(
                models.ConversationParticipant.conversation_id == conversation.conversation_id
            ).join(models.User)

            participant_data = []
            group = models.Group.get(models.Group.conversation_id == conversation.conversation_id)
            for participant in group_participants:
                participant_data.append({
                    "user_id": participant.participant_id.user_id,
                    "username": participant.participant_id.username
                })

            last_message_time = conversation.last_message_sent.strftime('%Y-%m-%d %H:%M:%S') if conversation.last_message_sent else None
            last_message_sent = await get_recent_chat_list_group(conversation.conversation_id)
            conversation_data = {
                "conversation_id":conversation.conversation_id,
                "conversation_type":conversation.conversation_type,
                "last_message_sent_time":last_message_time,
                "last_message_sent":last_message_sent,
                "participants": participant_data,
                "group_name":group.group_name,
                "group_id":group.group_id,
                "group_length":group.members_length
            }
            conversations.append(conversation_data)
        else: # personal dm conversation
            # Finding the other participant in the conversation
            other_participant = models.User.select().join(models.ConversationParticipant).where(
                (models.ConversationParticipant.conversation_id == conversation.conversation_id) &
                (models.User.user_id != user_id)
            ).get()
            last_message_time = conversation.last_message_sent.strftime('%Y-%m-%d %H:%M:%S') if conversation.last_message_sent else None
            last_message = await get_recent_chat_list_dm(conversation.conversation_id)
            conversation_data = {
                "conversation_id":conversation.conversation_id,
                "conversation_type":conversation.conversation_type,
                "last_message_sent_time":last_message_time,
                "last_message_sent":last_message,
                "other_participant": {
                    "user_id": other_participant.user_id,
                    "username": other_participant.username,
                    "activity":other_participant.is_active
                },
                'profile_picture' :base64.b64encode(other_participant.profile_picture).decode() if other_participant.profile_picture else None

            }
            conversations.append(conversation_data)
    return conversations



        
async def check_update_conversation(conversations, user):
    new_converstions = await get_conversations(user)
    if conversations != new_converstions:
        #if the value are not the same
        return (True, new_converstions)
    return False


async def get_chat_history(conversation_id:int, onInitial=None, group=False):
    conversation =  models.Conversation.get_or_none(Conversation.conversation_id == conversation_id)

    if not group:
        messages = (
            models.Message
            .select(models.Message.message_id, models.Message.conversation_id, models.Message.sender_id, models.Message.recipient_id, models.Message.message_text, models.Message.timestamp, models.Message.is_read, models.User.username.alias('sender_username'))
            .join(models.User, on=(models.Message.sender_id == models.User.user_id))
            .where(models.Message.conversation_id == conversation_id)
            .dicts()
        )
        if onInitial:
            return {"action":"initial_chat_history", "data":
            list(messages)}
        return {"action":"update_chat_history", "data":list(messages)}
    else:
        messages = (
            models.GroupMessage.select(models.GroupMessage.group_message_id, models.GroupMessage.group_conversation_id, models.GroupMessage.sender_id, models.GroupMessage.message_text, models.GroupMessage.timestamp, models.GroupMessage.is_read, models.User.username.alias('sender_username')).join(models.User, on=(models.GroupMessage.sender_id == models.User.user_id))
            .where(models.GroupMessage.group_conversation_id == conversation_id)
            .dicts()
            )
        if onInitial:
            return {"action":"initial_chat_history", "data":
            list(messages)}
        return {"action":"update_chat_history", "data":list(messages)}


async def leave_group(group_id:int, user_id):
    try:
        group = models.Group.get_or_none(Group.group_id == group_id)
        user = models.User.get_or_none(User.user_id == user_id)

        if group.admin_id == user.user_id:
            return (False,"owner")
        
        # Check if the user is a member of the group
        if models.ConversationParticipant.select().where(
            models.ConversationParticipant.conversation_id == group.conversation_id,
            models.ConversationParticipant.participant_id == user_id
        ).exists():
            # Remove the user from the group
            models.ConversationParticipant.delete().where(
                models.ConversationParticipant.conversation_id == group.conversation_id,
                models.ConversationParticipant.participant_id == user_id
            ).execute()
            #Update the length
            group.members_length = group.members_length - 1
            group.save()
            return (True, "success")
        else:
            return (False, "User is not a member of the group.")
    except DoesNotExist:
        return (False, "Group or User does not exist") 

async def add_members_to_group(request):
    try:
        #Getting the group
        group = models.Group.get_or_none(models.Group.group_id == request.group_id)
        #getting the new member user
        new_member_user = models.User.get_or_none(models.User.user_id == request.new_user_id)

        
        # Check if the user is already a member of the group
        if models.ConversationParticipant.select().where(
            models.ConversationParticipant.conversation_id == group.conversation_id,
            models.ConversationParticipant.participant_id == new_member_user.user_id
        ).exists():
            return {'error':'User already a member of the group'}

        # Add the ConversationParticipant record
        models.ConversationParticipant.create(
            conversation_id=group.conversation_id,
            participant_id=new_member_user.user_id
        )

        #increase the group_length
        group.members_length = group.members_length + 1
        group.save()

        return {"message": "Member added successfully"}

    except models.Group.DoesNotExist:
        return {"error":'group not found'}
        # raise HTTPException(status_code=404, detail="Group not found")

    except models.User.DoesNotExist:
        return {'error': 'user not found'}
        # raise HTTPException(status_code=404, detail="User not found")


accepted_arguments_mapping = {
    "create_db":create_db(),
    "get_db": get_db(),
}

if __name__ == "__main__":
    #create the database if havent yet
    create_db()
