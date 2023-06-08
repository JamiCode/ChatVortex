import httpx
import keyring
import json
import re
import datetime
import time
import zoneinfo
import secrets
import os
import glob
import base64
import imghdr
import shutil
import io
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image, AsyncImage
from kivymd.uix.list import ImageLeftWidget
# setting our creentials
service_name = "chat_vortex_service"
username = "user_access_token"
HOST:str = "localhost"




def get_kivy_chat_account_image_texture(filepath):
    """ This gets the default dp.user via texture"""
    data = io.BytesIO(open(filepath, "rb").read())
    cim = CoreImage(data, ext="png")
    return cim.texture

def get_kivy_image_from_bytes_texture(image_byte:str):
    image_type = imghdr.what(None, image_byte)
    buf = io.BytesIO(image_byte)
    cim = CoreImage(buf, ext=image_type)
    return cim.texture

def decode_base64(code:str):
    image_byte = base64.b64decode(code)
    return image_byte



def get_profile_picture():
    folder_path = "images/pfp"
    all_files = glob.glob(os.path.join(folder_path, "*"))
    files_only = [f for f in all_files if os.path.isfile(f)]
    return str(files_only[0])

def delete_profile_picture_locally():
    path = get_profile_picture()
    os.remove(path)




def password_is_same(password_one:str, password_two:str):
    if secrets.compare_digest(password_one, password_two):
        return True
    else:
        return False


#this function registers users to the backend
def register_user_to_backend(backend_endpoint:str, json_data:dict)->tuple:

    header ={
        "Content-Type": "application/json",
    }

    response = httpx.post(backend_endpoint, json=json_data, headers=header)


    try:
         #if the response of the server is not ok
       if not response.status_code == 200:
            detail = response.json()['detail'] #convert to python dict
            return (False, detail)
       else:
            access_token = response.json()['access_token']
            return (True,access_token)
    except Exception as e:
        raise e


def store_token_locally(token:str):
    keyring.set_password(service_name, username, token)

def check_if_authenticated()-> bool:
    if keyring.get_password(service_name, username) == None:
        return False
    return True
def get_user_token():
    return keyring.get_password(service_name, username)


def get_user_details(token:str):
    header = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    response = httpx.get(f"http://{HOST}:8000/api/users/me", headers=header)
    return response.json()

def get_last_message_from_backend(token:str, conversation_id:int):
    header = {"Authorization": f"Bearer {token}", "Content-Type":"application/json"}
    response = httpx.get(f"http://{HOST}:8000/api/convo/{conversation_id}/last_message_sent", headers=header)
    return response.json()


def log_in_user_to_backend(email:str, password:str)->bool:
    """" Sends user form in the form of urlencoded, to the backend and returns a tuple of true/false, and message from the. """
    back_endpoint = f"http://{HOST}:8000/api/token"
    headers = {"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
    body = {"grant_type": "", "username": email, "password": password, "scope": "", "client_id": "", "client_secret": ""}


    response = httpx.post(back_endpoint, data=body)

    if not response.status_code == 200:
        return (False, response.json()['detail'])
    else:
        access_token = response.json()['access_token']
        return (True, access_token)

def get_user_details_from_cache():
    user_info = None
    
    with open('cache.json','r') as file:
        content = file.read()
        json_data = json.loads(content)
        user_info = json_data['username']
    return user_info


def change_profile_picture_locally(base_64_encoded:str):
    """ Take the bae 64 encoded image returned by the server, and save it locally"""
    image_byte = base64.b64decode(base_64_encoded)
    image_type = imghdr.what(None, image_byte)

    if not image_type:
        raise ValueError("Unsupported image type")

    # Delete the old profile picture, if it exists
    delete_profile_picture_locally()

    with open(f"images/pfp/dp_user.{image_type}", "wb") as file:
        file.write(image_byte)


def store_profile_picture_locally():
    user_id = get_user_details_from_cache()["user_id"]
    token = get_user_token()
    backend_endpoint = f"http://{HOST}:8000/api/profile_picture/{user_id}"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    response = httpx.get(backend_endpoint, headers=headers)
    profile_picture = response.json().get('profile_picture')
    if not profile_picture:
        return
    change_profile_picture_locally(profile_picture) #add image to the path

def reset_profile_picture_to_default():
    # this function resets the profile picture back to the default png
    delete_profile_picture_locally() # delete any file in the pfp
    source_dir = 'images/no_pfp'
    destination_dir = 'images/pfp'
    file_name = "dp_user.png"
    source_file = f"{source_dir}/{file_name}"
    destination_file = f"{destination_dir}/{file_name}"
    shutil.copy(source_file, destination_file)



def logout():
    if keyring.get_password(service_name, username) is None:
        return 0
    keyring.delete_password(service_name, username)
    reset_profile_picture_to_default()



def update_user_name(username:str):
    user_id = None
    with open('cache.json', 'r') as file:
        content = file.read()
        json_data = json.loads(content)
        user_id = json_data['username']['user_id']
    user_update_body = {"user_id":user_id, "username":username}
    token = get_user_token()
    back_endpoint = f'http://{HOST}:8000/api/users/{user_id}/update_username'
    headers = { "Content-Type": "application/json","Authorization": f"Bearer {token}"}
    response = httpx.put(back_endpoint, headers=headers, json=user_update_body)
    if response.json().get('error'):
        return False
    return True


def update_password(password:str):
    user_id = None
    with open('cache.json', 'r') as file:
        content = file.read()
        json_data = json.loads(content)
        user_id = json_data['username']['user_id']
    user_update_body = {"user_id":user_id, "password":password}
    token = get_user_token()
    back_endpoint = f'http://{HOST}:8000/api/users/{user_id}/update_password'
    headers = {"Content-Type":"application/json", "Authorization":f"Bearer {token}"}
    response = httpx.put(back_endpoint, headers=headers, json=user_update_body)
    if response.json().get('error'):
        return False
    return True


def update_profile_picture(path_to_image:str) -> bool:
    user_id = get_user_details_from_cache()['user_id']
    token = get_user_token()
    backend_endpoint = f"http://{HOST}:8000/api/users/{user_id}/upload_image"
    headers = {"Authorization":f"Bearer {token}"}
    with open(path_to_image, "rb") as file:
        response = httpx.put(backend_endpoint, headers=headers, files={"file":(path_to_image, file)})

    if not response.status_code == 200:
        # if the status code is not ok, something is wrong with the request
        return False
    change_profile_picture_locally(response.json().get('profile_picture'))
    return True


def get_userid(username:str):
    back_endpoint = f"http://{HOST}:8000/api/user_id/{username}"
    response = httpx.get(back_endpoint)
    return response.json()


def update_cache(username:str=None, email:str=None):
  form  =   {"username":username, "image":None,"email":email}


  json_string = json.dumps(form)

  with open('cache.json', "w") as file:
        file.write(json_string)


def download_image(filepath:str=None, image_byte:str=None):
    if filepath is None or image_byte is None:
        return
    else:
        image_byte = base64.b64decode(image_byte)
        image_type = imghdr.what(None, image_byte)
        if not os.path.exists(filepath + str(image_type)):
            with open(filepath + str(image_type), "wb") as file:
                file.write(image_byte)
            return filepath + str(image_type)
        else:
            return filepath + str(image_type)




def is_valid_username(username):
    pattern = r'^[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, username))

def is_valid_id(id):
    pattern = r'^\d+$'
    return bool(re.match(pattern, id))

def is_valid_username_id_string(string):
    pattern = r'^[a-zA-Z0-9_]+#[0-9]+$'
    return bool(re.match(pattern, string))

def validate_username_id_string(string):
    if not is_valid_username_id_string(string):
        return False
    parts = string.split('#')
    username = parts[0]
    id = parts[1]
    if not is_valid_username(username) or not is_valid_id(id):
        return False
    return True



def get_local_time_zone() -> datetime.timezone:
    local_tz_offset_sec = -time.timezone
    local_tz = datetime.timezone(datetime.timedelta(seconds=local_tz_offset_sec))
    return local_tz

def convert_string_to_date(time_str: str):
    local_tz = get_local_time_zone()
    utc_time_obj = datetime.datetime.fromisoformat(time_str).replace(tzinfo=datetime.timezone.utc)
    local_time = utc_time_obj.astimezone(local_tz)

    time_formatted = local_time.strftime("%I:%M %p")
    day_formatted = local_time.strftime("%d/%m/%Y")

    return (day_formatted, time_formatted)


def get_selected_image(image_widget):
    return image_widget.source
 