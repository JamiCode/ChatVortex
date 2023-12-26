from fastapi import FastAPI, Request, UploadFile, File, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from networking import ClientConnectionManager,ChatHistoryConnectionManager
from fastapi.responses import JSONResponse
from fastapi.exceptions import WebSocketException
from datetime import datetime
from credentials import HOST, PORT
from services import CustomJSONEncoder
import pydantic
import uvicorn
import fastapi.security as fast_security
import schemas
import services
import fastapi as _fastapi
import models
import json
import peewee
import asyncio
import jose
import websockets
import base64
app = FastAPI()

websockets_manager = ClientConnectionManager()
websocket_chat_manager = ChatHistoryConnectionManager()






#------------------- HTTP PROTOCOl
@app.get("/")
async def show_homepage():
    return {"Message": "Welcome to ChatVortexBackend"}


@app.post("/api/create-users/", response_model=schemas.AccessTokenResponse, dependencies=[Depends(services.get_db)])
async def create_user(user: schemas.UserCreate):
    try:
        db_user = await services.get_user_by_email(email=user.email)
        # if user already exists raise something
        # also check if user with username already exists
        if db_user:
            raise _fastapi.HTTPException(
                status_code=400,
                detail="User with that email already exists")

        #creates user   
        user = await services.create_user(user=user)

        #create and return the token
        return await services.create_token(user=user)
    except peewee.IntegrityError as IntegrityError:
        raise _fastapi.HTTPException(
                status_code=400,
                detail="User with username already exists")




#this view is responsible for generating tokens
@app.post("/api/token")
async def generate_token(form_data:fast_security.OAuth2PasswordRequestForm=_fastapi.Depends()):
    user = await services.authenticate_user(email=form_data.username, password=form_data.password)

    if not user:
        # if there s no user, raise http exceptio
        raise _fastapi.HTTPException(status_code=401, detail="Invalid credentials")
    #if there is it would generate token
    return await services.create_token(user=user)



#this view i responsible for getting information of a user. in order to do that we need a token
@app.get("/api/users/me", response_model=schemas.User)
async def get_user(user: schemas.User = Depends(services.get_current_user)):
    return user


#this view egts the profile picture of a user
@app.get("/api/profile_picture/{user_id}", response_model=schemas.UserProfile)
async def get_profile_picture(user_id:int, request:Request, token:schemas.User=Depends(services.authenticate_token)):
    # Check to see if the authenticated user, is the same as the user trying to get his profile picture 
    user_details = await services.get_current_user(token)
    if (user_details.user_id != user_id  ):
        raise _fastapi.HTTPException(status_code=403, detail="Not authorized to get user profile")
    user_profile_picture = None
    user = models.User.get(models.User.user_id == user_id)
    if user.profile_picture:
        user_profile_picture = base64.b64encode(user.profile_picture).decode()

    return JSONResponse({"profile_picture":user_profile_picture})



#This View converts username to user_id
@app.get('/api/user_id/{username}')
async def get_user_id( username:str):
    user = models.User.get_or_none(models.User.username == username)
    if user:
        return {'id':user.user_id}
    return {"error":"User not found"}

#This View converts the userid to username
@app.get('/api/username/{user_id}')
async def get_username(user_id:int):
    user = models.User.get_or_none(models.User.user_id == user_id)
    if user:
        return {'username':user.username}
    return {'error':"User not found"}

@app.get('/api/groups/{conversation_id}')
async def get_group(conversation_id:int):
    """ Get a JSON group based on the object"""
    group = models.Group.get_or_none(models.Group.conversation_id == conversation_id)
    if group:
        group_members = await services.get_group_members(group.group_id)
        admin = group.admin
        del admin.__dict__['__data__']["hashed_password"]
        return {'group_name':group.group_name, 'group_id':group.group_id, 'conversation_id':group.conversation_id, 'admin':admin, 'members_length':group.members_length, 'members':group_members}
    return {"error":"no group with the given conversation"}

@app.get("/api/is_blocked/{conversation_id}")
async def is_blocked(conversation_id, user:schemas.User=Depends(services.get_current_user)):
    conversation = models.Conversation.get_or_none(models.Conversation.conversation_id == conversation_id)
    if conversation:
        return {'is_blocked':conversation.is_blocked, "blocked_user_id":conversation.blocked_user_id}
    else:
        return{"error":"conversation not found"}



@app.get('/api/users/{user_id}')
async def get_user(user_id:int,token:schemas.User=Depends(services.authenticate_token)):
    """ GET JSON user object based on the object"""
    user = models.User.get_or_none(models.User.user_id == user_id)
    if user:
        return {'user_id':user.user_id, 'email':user.email, 'is_active':user.is_active, 'last_seen':user.get_last_seen()}
    return {"error":"no user found"}





@app.put("/api/users/{user_id}/update_username")
async def update_username(user_id:int, username_data: schemas.UserUpdateForm,request:Request,token: str = Depends(services.authenticate_token)):
    #verify if the person making the request is the same person being updated
    token = await services.get_token_http(request)
    user = await services.get_current_user(token)
    if user.user_id != user_id:
        raise _fastapi.HTTPException(status_code=403, detail="Not authorized to update this user's username")

    operation_update = await services.update_user(username_data.user_id, username_data.username)
    if operation_update:
        return {"Info":"Update done"}
    
    return {'error':'return {"Info":"Update done"}'}

@app.put("/api/users/{user_id}/update_password")
async def update_password(
    user_id:int,
    password_data:schemas.UserPasswordUpdateForm,
    request:Request,
    token:str = Depends(services.authenticate_token)):
    token = await services.get_token_http(request)
    user = await services.get_current_user(token)
    if user.user_id != user_id:
        raise _fastapi.HTTPException(status_code=403, detail="Not authorized to update this user's password")
    operation_update = await services.update_password(password_data.user_id, password_data.password)
    if operation_update:
        return {"Info":"Update done"}
    return {'error':'Operaion not sucessful'}


#remeber to error proof this, in case something happens
@app.put("/api/block/{conversation_id}/{user_to_be_blocked_id}")
async def block_user(conversation_id:int, user_to_be_blocked_id:int, request:Request, token:str=Depends(services.authenticate_token)):
    conversation = models.Conversation.get_or_none(models.Conversation.conversation_id == conversation_id)
    conversation.is_blocked = True
    conversation.blocked_user_id = user_to_be_blocked_id
    conversation.save()
    return {"success":"conversation blocked!"}

@app.put("/api/unblock/{conversation_id}")
async def unblock_user(conversation_id:int, request:Request, token:str=Depends(services.authenticate_token)):
    conversation = models.Conversation.get_or_none(models.Conversation.conversation_id == conversation_id)
    conversation.is_blocked = False
    conversation.blocked_user_id = None 
    conversation.save()
    return {"success":"conversation unblocked!"}


@app.put("/api/users/{user_id}/upload_image")
async def update_profile_picture(user_id:int, request:Request, file: UploadFile = File(...), token:str= Depends(services.authenticate_token)):
    # get the user 
    user = models.User.get(models.User.user_id == user_id)
    #read the image bytes
    image_bytes = await file.read()
    user.profile_picture = image_bytes
    user.save()

    # Convert the image bytes to base64 encoding to return in the response
    image_base64 = base64.b64encode(image_bytes).decode()

    # Return a JSON response with the updated profile picture
    return JSONResponse({"profile_picture": image_base64})



@app.delete("/groups/{group_id}/leave/{user_id}")
async def leave_group(group_id: int, user_id: int, request:Request, token:str=Depends(services.authenticate_token)):
    """Given the group_idm and user_id, this would do the operations for leaving group"""
    leave_group_status = await services.leave_group(group_id, user_id)
    if leave_group_status[0]:
        
        return {"message": "Successfully left the group."}
    if leave_group_status[1] == "User is not a member of the group":
        raise _fastapi.HTTPException(status_code=404, detail="User is not a member of the group.")
    if leave_group_status[1] == "Group or User does not exist":
        raise _fastapi.HTTPException(status_code=404, detail="Group or user not found.")
    if leave_group_status[1] == "owner":
         raise _fastapi.HTTPException(status_code=404, detail="Owner cannot leave group only delete.")



@app.post("/groups/add_members")
async def add_members(request:schemas.AddMemberRequest, token:str=Depends(services.authenticate_token)):
    add_members_to_group_process = await services.add_members_to_group(request)
    if add_members_to_group_process.get("error") is None:
        return add_members_to_group_process
    raise _fastapi.HTTPException(status_code=404, detail=add_members_to_group_process.get("error"))





# this endpoint is responsible for starting a communication between. hen user presses on new chat a convsersation is started
@app.websocket("/socket/create-convo")
async def create_convo(websocket:WebSocket, token:str = Depends(services.get_token)):
    #check for exception
    user = await services.verify_socket_connection(token)
    try:
        #continue with the connection
        await websockets_manager.connect(websocket, user.user_id)
        #listens for data exchange
        #json is data from the client
        data =  await websocket.receive_json()
        payload = schemas.MessagePayload(**data)
        sender = models.User.get_or_none(models.User.user_id == payload.sender_id)
        recipient = models.User.get_or_none(models.User.user_id == payload.recipient_id)

        if recipient is None or sender is None:
            # if there is no recipient or sender in the database, do not continue this code further, jump to the next iteration of the loop
            await websocket.send_json({"error":f"{services.check_who_none(value2=recipient, value=sender)} not found"})
            return
        conversation = await services.conversation_exist(sender.user_id, recipient.user_id)

        #check this code out later
        if not conversation or conversation.conversation_type == "Group":
            #if the conversation does not exist create, the conversation and send the url
            conversation = models.Conversation.create(conversation_type="DM", last_message_sent=datetime.utcnow())
            #Update the db ConverSationParticiPant
            models.ConversationParticipant.create(conversation_id=conversation.conversation_id, participant_id=sender.user_id )
            models.ConversationParticipant.create(conversation_id=conversation.conversation_id, participant_id=recipient.user_id)

            #send the url
            response = {"type":'redirect', "info":"new conversation created", "redirect_url":f"ws://{HOST}:{PORT}/socket/convo/{conversation.conversation_id}"}
            await websocket.send_json(response)
        else:
            
            #if the conversation exists
            response = {"type":'redirect', "info":"Conversation already exists between you and the user", "convo_url":f"ws://{HOST}:{PORT}/socket/convo/{conversation.conversation_id}"}
            await websocket.send_json(response)
                    




    except WebSocketDisconnect:
        # if the client disconnects for any reasons
        websockets_manager.disconnect(user.user_id)
        print("{user.user_id} Disconnected from server while creating")
    except json.decoder.JSONDecodeError:
        # if user does not put in the format of json
        raise WebSocketException(code=_fastapi.status.WS_1008_POLICY_VIOLATION, reason="Incorrect format. Format must be in json")
    

@app.websocket("/socket/create-group")
async def create_group(websocket:WebSocket, token:str = Depends(services.get_token)):
    #check for the user if he is valid
    user = await services.verify_socket_connection(token)
    try:
        await websockets_manager.connect(websocket, user.user_id)
        #continue with the connection
        data = await websocket.receive_json()
        payload = schemas.GroupCreatePayload(**data)
        if payload.initial_members is None or len(payload.initial_members) < 2:
            await websocket.send_json({"error":"Must need at least 2 members to start conversation"})
            return
        initiator_id = models.User.get_or_none(models.User.user_id == payload.initiator_id)
        # Retrieving the users with the given IDs
        intial_members_users_id = models.User.select().where(models.User.user_id.in_(payload.initial_members))


        #Now create the group subsequently.

        #Of Course every group is a conversation so lets create the conversation. so start with the conversation

        conversation = models.Conversation.create(conversation_type="Group",last_message_sent=datetime.utcnow())

        models.ConversationParticipant.create(conversation_id=conversation.conversation_id, participant_id=initiator_id)
        #now we create the participants to each conversations
        for member_id in intial_members_users_id:
            models.ConversationParticipant.create(
                conversation_id=conversation.conversation_id,
                participant_id=member_id
            )
        #now create group record object so we can track the groups 

        group = models.Group.create(conversation_id=conversation.conversation_id, admin=initiator_id, members_length=len(conversation.participants), group_name=payload.group_name)
        await websocket.send_json({"info":"done"})
        #and we that we are done with creating our group
    except WebSocketDisconnect:
       print(f"{user.user_id} Disconnected while creating group")
    except json.decoder.JSONDecodeError:
        # if user does not put in the format of json
        raise WebSocketException(code=_fastapi.status.WS_1008_POLICY_VIOLATION, reason="Incorrect format. Format must be in json")




#Remeber to make this connectin shortlived
#this endpoint is responsible for sending and recieving messages from the same convesrsaion
@app.websocket("/socket/convo/{conversation_id}")
async def send_recieve_message_in_conversation(conversation_id:int, websocket:WebSocket, token:str = Depends(services.get_token)):
    user = await services.verify_socket_connection(token)
    try:
        await websocket.accept()
        #listens for data exchange
        data = await websocket.receive_json()
        payload = schemas.SendMessagePayLoad(**data)
        sender = models.User.get_or_none(models.User.user_id == payload.sender_id)
        recipient = models.User.get_or_none(models.User.user_id == payload.recipient_id)
        conversation = models.Conversation.get_or_none(models.Conversation.conversation_id == conversation_id)


        if recipient is None or sender is None:
            # if there is no recipient or sender in the database, do not continue this code further, jump to the next iteration of the loop
            await websocket.send_json({"error":f"{services.check_who_none(value2=recipient, value=sender)} not found"})
            return
        #creat the message to database, and broadcast it
        if conversation:
            #this assumes and takes for granted, conversation exists
            if not await services.conversation_exist(sender.user_id, recipient.user_id) == conversation:
                #check if sendr or user not in this conversation
                await websocket.send_json({"error":'sender or recipient not found in the conversation'})
            elif conversation.is_blocked:
                #this assumed if the conversationed was blocked
                is_blockee = (user.user_id == conversation.blocked_user_id)
                if is_blockee:
                    await websocket.send_json({"conversation-error":"You have been blocked by this user"})
                else:
                    await websocket.send_json({"conversation-error":"You have blocked this user"})
            else:
                current_date = datetime.utcnow()
                message = models.Message.create(
                                conversation_id=conversation.conversation_id,
                                sender_id=sender.user_id,
                                recipient_id=recipient.user_id,
                                message_text=payload.message_text,
                                timestamp=current_date
                )
                conversation.last_message_sent = current_date
                conversation.save()
                message_form = {
                "sender_id":sender.user_id,
                "recipient_id":recipient.user_id,
                "message_text":payload.message_text
                }
                await websocket.send_json({"conversation-success":"Message was sent"})
                #send the message to the other client
                if not recipient.user_id in websockets_manager.active_connections:
                    print("User not online")
        else:
            await websocket.send_json({"conversation-error":"conversation not found"})
                

    except WebSocketDisconnect:
       print(f"{user.user} Disconnected from the server")
    except json.decoder.JSONDecodeError:
        # if user does not put in the format of json
        websockets_manager.disconnect(user.user_id)
        raise WebSocketException(code=_fastapi.status.WS_1008_POLICY_VIOLATION, reason="Unable to parse JSON")
    except pydantic.error_wrappers.ValidationError as error:
        print(error)
        raise WebSocketException(code=_fastapi.status.WS_1008_POLICY_VIOLATION, reason="There is  missing field")

# this endpoint is responsible for sending and recieving messages from the same convesrsaion group
#Group_id here really refers to the conversation_id
@app.websocket("/socket/group_convo/{group_id}")
async def send_recieve_message_in_group(group_id:int, websocket:WebSocket, token:str = Depends(services.get_token)):
    user = await services.verify_socket_connection(token)

    try:
        await websocket.accept()
        #just keeep in mind that would just simly store in the database, does not do broadcasting this is the job of the frontend
        conversation = models.Conversation.get_or_none(models.Conversation.conversation_id == group_id)
        if conversation and conversation.conversation_type == "Group":
            group = conversation.group
            current_date = datetime.utcnow() 
            data = await websocket.receive_json()
            payload = schemas.GroupSendPayload(**data)
            message = models.GroupMessage.create(group_conversation_id=group_id, sender_id=payload.sender_id, message_text=payload.message_text, timestamp=current_date)
            conversation.last_message_sent = current_date
            conversation.save()
        else:
            await websocket.send_json({"error":"Group does not exist"})
    except WebSocketDisconnect:
       print("Something happened with client wifi")
    except json.decoder.JSONDecodeError:
        # if user does not put in the format of json
        raise WebSocketException(code=_fastapi.status.WS_1008_POLICY_VIOLATION, reason="Incorrect format. Format must be in json")

# this endpoint is responsible for streaming over the connection the list of conversation a user has
@app.websocket("/socket/convos")
async def user_conversations(websocket:WebSocket, token: str = Depends(services.get_token)):
    user = await services.verify_socket_connection(token)
    try:
        #continue with the connection
        await websockets_manager.connect(websocket,user.user_id)
        initial_conversations = await services.get_conversations(user.user_id)
        #send the initial of list of conversation user is inss
        await websocket.send_json({"action": "initial", "convo_data": initial_conversations})
        # Listen for new conversations and broadcast updates
        while True:
            new_converstions = await services.get_conversations(user.user_id)
            if new_converstions == initial_conversations:
                #if its the same as initial_conversation we pass
                pass
            else:
                #indicating they are not the same, new changes have been added
                initial_conversations = new_converstions
                await websocket.send_json({"action":"update", "convo_data":initial_conversations})
            #wait for some time
            await asyncio.sleep(0.1)
            await websocket.send_text("ping")# send something to keep the connection going and to know when the connection is closed
    except websockets.exceptions.ConnectionClosedOK as e:
        websockets_manager.disconnect(user.user_id)
        print("[INFO] Connection is closed by the client properly /convos ")
    except websockets.exceptions.ConnectionClosedError as error:
        websockets_manager.disconnect(user.user_id)
        print("[INFO] Connection is closed by the client abruptly /convos ")

        


@app.websocket("/socket/api/chat-history/{conversation_id}")
async def get_chat_history(conversation_id:int, websocket:WebSocket, token:str = Depends(services.get_token)):
    """ This endpoints exists for serving cliens a history of the list of chat history a user has, real time communication"""
    user = await services.verify_socket_connection(token)
    try:
        await websocket_chat_manager.connect(websocket, user.user_id)
        initial_chat_history = await services.get_chat_history(conversation_id, onInitial=True)
        await websocket.send_text(json.dumps(initial_chat_history, cls=CustomJSONEncoder))
        while True:
            new_chat_history = await services.get_chat_history(conversation_id)
            if new_chat_history == initial_chat_history:
                try:
                    await websocket.send_json({'action':'ping'})
                except websockets.exceptions.ConnectionClosedOK as e:
                   websocket_chat_manager.disconnect(websocket, user.user_id)
                   break

            else:
                #indicating they are not the same, new changes have been added
                initial_chat_history = new_chat_history
                await websocket.send_text(json.dumps(initial_chat_history, cls=CustomJSONEncoder))
            #wait for some time
            await asyncio.sleep(0.000000000000001)

            
    except WebSocketDisconnect:
        print(f"chat history {conversation_id}")
        websocket_chat_manager.disconnect(user.user_id, websocket)
    except websockets.exceptions.ConnectionClosedOK:
        print(f"[INFO] /chat-history/{conversation_id}  was closed by the client properly")
    except websockets.exceptions.ConnectionClosedError:
        print(f"[INFO] /chat-history/{conversation_id} was closed abruptly by the client ")
    except json.decoder.JSONDecodeError:
        # if user does not put in the format of json
        websocket_chat_manager.disconnect(user.user_id)
        raise WebSocketException(code=_fastapi.status.WS_1008_POLICY_VIOLATION, reason="Unable to parse JSON")
    except pydantic.error_wrappers.ValidationError as error:
        print(error)
        raise WebSocketException(code=_fastapi.status.WS_1008_POLICY_VIOLATION, reason="There is  missing field")
   


@app.websocket("/socket/group-history/{group_id}")
async def get_group_history(group_id:int, websocket:WebSocket, token:str = Depends(services.get_token)):
    user = await services.verify_socket_connection(token)
    try:
        await websocket_chat_manager.connect(websocket, user.user_id)
        initial_group_history = await services.get_chat_history(group_id, group=True, onInitial=True)
        await websocket.send_text(json.dumps(initial_group_history, cls=CustomJSONEncoder))
        while True:
            new_group_history = await services.get_chat_history(group_id, group=True)
            if new_group_history == initial_group_history:
                try:
                    await websocket.send_json({'action':'ping'})

                except websockets.exceptions.ConnectionClosedOK as e:
                    websocket_chat_manager.disconnect(websocket, user.user_id)
                    break

            else:
                #indicating they are not the same, new changes have been added
                initial_group_history = new_group_history
                await websocket.send_text(json.dumps(initial_group_history, cls=CustomJSONEncoder))
                #wait for some time
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        websocket_chat_manager.disconnect(user.user_id, websocket)
    except websockets.exceptions.ConnectionClosedOK:
        print(f"[INFO] /group-history/{group_id}  was closed by the client properly")
    except websockets.exceptions.ConnectionClosedError:
        print(f"[INFO] /group-history/{group_id} was closed abruptly by the client ")
    except json.decoder.JSONDecodeError:
        # if user does not put in the format of json
        websocket_chat_manager.disconnect(websocket,user.user_id)
        raise WebSocketException(code=_fastapi.status.WS_1008_POLICY_VIOLATION, reason="Unable to parse JSON")
    except pydantic.error_wrappers.ValidationError as error:
        print(error)
        raise WebSocketException(code=_fastapi.status.WS_1008_POLICY_VIOLATION, reason="There is  missing field")


@app.get("/active-connection")
async def disconnect():
    return str(websockets_manager.active_connections)
if __name__ == '__main__':
    uvicorn.run('server:app', host=HOST, port=PORT, reload=True)
