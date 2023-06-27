import asyncio
import secrets
import os
import concurrent.futures
import threading
from kivy.app import App
from kivy.lang import Builder
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDFillRoundFlatIconButton,MDFillRoundFlatButton, MDFlatButton, MDIconButton
from kivy.metrics import dp
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.textfield import MDTextField
from util import password_is_same, register_user_to_backend, store_token_locally, check_if_authenticated, get_user_token, get_user_details, logout, log_in_user_to_backend, update_cache, get_userid, update_user_name, update_password,get_profile_picture, store_profile_picture_locally, update_profile_picture,get_selected_image
from kivy.config import Config
from kivymd.uix.bottomsheet import MDCustomBottomSheet
from chat_gui import DashBoardScreen
from credentials import HOST
from websocket_kivy import WebSocketClient
from kivymd.toast import toast
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.relativelayout import RelativeLayout
from kivymd.uix.button import MDFloatingActionButton
from kivymd.uix.gridlayout import MDGridLayout
from kivy.factory import Factory
import websockets
from kivy.uix.boxlayout import BoxLayout
from kivy import utils
from kivymd.uix.textfield import MDTextFieldRect
from kivymd.uix.list import IRightBodyTouch, OneLineAvatarIconListItem
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.icon_definitions import md_icons
from kivy.properties import StringProperty, NumericProperty
from websocket_kivy import handle_create_group_functionality    
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.spinner import MDSpinner
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivymd.uix.filemanager import MDFileManager
from src.profile_image_cropper import CircularProfileImageCropper
from websocket_kivy import WebSocketClient, handle_close_websocket_connections
import time
import threading
import setproctitle


setproctitle.setproctitle("PDD")
Builder.load_file('style.kv')


Window.size = (800, 600)
Window.clearcolor = (1,0,0,1)
Window.minimum_width = dp(720)
Window.minimum_height = dp(472)

class ListItemWithCheckbox(OneLineAvatarIconListItem):
    '''Custom list item.'''
    checked_options = set()
    icon = StringProperty("account")

    def on_checkbox_active(self, checkbox, value, text):
        if value:
            self.__class__.checked_options.add(text)
        else:
            self.__class__.checked_options.remove(text)

class RightCheckbox(IRightBodyTouch, MDCheckbox):
    '''Custom right container.'''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_color = (1,1,1,1)

#remeber to edit this using local storage
class ConversationBottomSheetContent(BoxLayout):

    def __init__(self, widget, **kwargs):
        super().__init__(**kwargs)
        self.widget = widget #widget here stands for the create-group-screen
        for convo in App.get_running_app().convos:
            self.ids.convo_members.add_widget(ListItemWithCheckbox(text=convo))
    def create_group(self):

        if self.widget.ids.group_name.text == '':
            Snackbar(text="Enter a Group name ",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=utils.get_color_from_hex("#ff8a80")).open()
        elif len(self.widget.ids.group_name.text) < 3 :
            Snackbar(text="Group Must not be less than 3 characters",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=utils.get_color_from_hex("#ff8a80")).open()
        elif len(self.widget.ids.group_name.text)> 15:
            Snackbar(text="Group Name should not be more than 15 characters",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=utils.get_color_from_hex("#ff8a80")).open()
        else:
            if not len(ListItemWithCheckbox.checked_options) > 0:
                return  
            initiator_id = App.get_running_app().chat_state['sender_id']
            initial_members = [get_userid(name)['id'] for name in ListItemWithCheckbox.checked_options]
            print(initiator_id)
            print(initial_members)
            asyncio.create_task(handle_create_group_functionality(initiator_id=initiator_id, initial_members=initial_members, group_name=self.widget.ids.group_name.text))

class MyTextField(MDTextField):
    def __init__(self, **kwargs):
        kwargs.pop("cursor_height", None)
        super().__init__(**kwargs)

class ChangePasswordLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = "Change Password"
        self.font_size = "24sp"
        self.bold = True
        self.size_hint_y = None
        self.height = dp(48)

class PasswordTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = "password_input"
        self.multiline = False
        self.hint_text = "Enter new password"
        self.password = True
        self.size_hint_y = None
        self.height = dp(48)
        self.background_color = utils.get_color_from_hex("#ffffff")
        self.foreground_color = utils.get_color_from_hex("#000000")
        self.padding = dp(8), dp(16), dp(8), dp(16)

class UserNameTextInput(MDTextFieldRect):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = "username_input"
        self.multiline = False
        self.hint_text = "Enter new username"
        self.size_hint_y = None
        self.height = dp(48)
        self.background_color = utils.get_color_from_hex("#ffffff")
        self.foreground_color = utils.get_color_from_hex("#000000")
        self.padding = dp(8), dp(16), dp(8), dp(16)

class UserNameSettingsLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = "Change Username"
        self.font_size = "24sp"
        self.bold = True
        self.size_hint_y = None
        self.height = dp(48)


class CreateNewGroupScreen(Screen):
    def callback_for_menu_items(self, *args):
        toast(args[0])            
    def show_bottom_sheet(self, widget):
        self.custom_sheet = MDCustomBottomSheet(screen=ConversationBottomSheetContent(widget=widget))
        self.custom_sheet.radius = ('40','40')
        self.custom_sheet.open()
      
class SettingsScreen(Screen):
    def __init__(self, name, sm, **kwargs):
        super().__init__(name=name, **kwargs)
        self.sm = sm
        self.setting = None
        self.manager_open = False
        self.relative_layout = MDRelativeLayout()
        self.image_cropper_layout = MDRelativeLayout(md_bg_color=(1,0,0,1))
        self.circular_profile_image_cropper = CircularProfileImageCropper(size_hint=(None, 0.6), width=self.height)
        self.image_cropper_layout.add_widget(self.circular_profile_image_cropper)
        self.image_widget = MDBoxLayout(orientation="vertical", padding=(10,10), md_bg_color=App.get_running_app().THEME['dark_bg'], spacing=dp(5), radius=dp(10))
        self.image_source = get_profile_picture()
        self.user_image = AsyncImage(source=self.image_source)
        self.user_image.ratio = True
        self.user_image.allow_stretch = True
        self.size_hint_min = (dp(200), dp(200))
        self.edit_image_button = MDIconButton(icon="pencil")
        self.save_button = MDFillRoundFlatButton(text="Save",size_hint=(0.2, None), pos_hint={'x':0, 'top':0.95})
        self.discard_button = MDFlatButton(text="Discard", size_hint=(0.2, None), pos_hint={'x':0.3, 'top':0.95})
        self.file_manager = MDFileManager(exit_manager=self.on_file_manager_close, select_path=self.on_select_path)
        self.save_button.bind(on_release=self.on_save)
        self.discard_button.bind(on_release=self.on_discard)
        self.edit_image_button.bind(on_release=self.on_choose_image)
        self.relative_layout.add_widget(self.save_button)
        self.relative_layout.add_widget(self.discard_button)
        self.image_widget.add_widget(self.user_image)
        self.image_widget.add_widget(self.edit_image_button)

    def on_save(self, instance):
        possible_setting = ["password", "username", "image"]
        if self.setting and self.setting in possible_setting:
        # if there is any valye in self.settin and self.seting in possible setting.
            if self.setting == "username":
                username_name_text_input = self.ids.settings_layout.children[1].text
                if username_name_text_input == "":
                    Snackbar(text="Please enter your new username",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=utils.get_color_from_hex("#ff0000")).open()
                    return
                user_name_update = update_user_name(username_name_text_input)
                if user_name_update:
                    Snackbar(text="Username Successfully, Login Back to see change",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=utils.get_color_from_hex("#00ff00")).open()
                    logout()
                    asyncio.create_task(handle_close_websocket_connections())
                    app.state["on_first_boot"] = False
                    self.sm.current = "splash"
            elif self.setting == "password":
                password_text_input = self.ids.settings_layout.children[1].text
                if password_text_input == "":
                    Snackbar(text="Please enter your new password",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=utils.get_color_from_hex("#ff0000")).open()
                    return
                password_update = update_password(password_text_input)
                Snackbar(text="Password Successfully, Login Back to see change",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=utils.get_color_from_hex("#00ff00")).open()
                logout()
                asyncio.create_task(handle_close_websocket_connections())
                app.state["on_first_boot"] = False
                self.sm.current = 'splash'



    def on_choose_image(self, instance):
        self.file_manager_open =  True
        self.file_manager.show(os.path.expanduser("~"))

    def on_select_path(self, path:str):
        self.user_image.source = path
        self.circular_profile_image_cropper.reset()
        self.circular_profile_image_cropper.source = path
        self.file_manager.close()
    def on_file_manager_close(self, *args):
        self.manager_open = False
        self.file_manager.close()
    
    def on_discard(self, instance):
        if not self.setting == "password" or self.setting == "username":
            self.user_image.source = get_profile_picture()
            return
        self.ids.settings_layout.children[1].text = ""


    def go_back(self):
        self.sm.current = "dashboard"
    def setEdit(self, type_):
        possible_types = ['username', 'password']
        if type_ in possible_types:
            if type_ == possible_types[0]:
                self.setting = "username"
                if len(self.ids.settings_layout.children) > 0:
                    self.ids.settings_layout.clear_widgets()
                    self.ids.settings_layout.add_widget(UserNameSettingsLabel())
                    self.ids.settings_layout.add_widget(UserNameTextInput())
                    self.ids.settings_layout.add_widget(self.relative_layout)
                else:
                    self.ids.settings_layout.add_widget(UserNameSettingsLabel())
                    self.ids.settings_layout.add_widget(UserNameTextInput())
                    self.ids.settings_layout.add_widget(self.relative_layout)

            elif type_ == possible_types[-1]:
                self.setting = "password"
                if len(self.ids.settings_layout.children) > 0:
                    self.ids.settings_layout.clear_widgets()
                    self.ids.settings_layout.add_widget(ChangePasswordLabel())
                    self.ids.settings_layout.add_widget(PasswordTextInput())
                    self.ids.settings_layout.add_widget(self.relative_layout)
                else:
                    self.ids.settings_layout.add_widget(ChangePasswordLabel())
                    self.ids.settings_layout.add_widget(PasswordTextInput())
                    self.ids.settings_layout.add_widget(self.relative_layout)





class ImageScreen(Screen):
    """docstring for ClassName"""
    def __init__(self, name, sm, **kwargs):
        super().__init__(name=name, **kwargs)
        self.sm = sm
        

class SplashScreen(Screen):
    def __init__(self, name,**kwargs):
        super().__init__(name=name, **kwargs)
        self.email = None
        self.password = None

class LoginScreen(Screen):
    login_dialog = None
    error_message = None 
    def __init__(self, name,**kwargs):
        super().__init__(name=name, **kwargs)

    def handle_login(self):

        """ We want to show a Spinner that loads, while we log the user to the backend"""

        self.email = self.ids.login_email.text
        self.password = self.ids.login_password.text
        if self.email == '' or secrets.compare_digest(self.password, ''):
            self.ids.error_label.text = "Enter Your details"
            return

        if not self.login_dialog:
            self.login_dialog = MDDialog(
                    text="Logging You in",
                    content_cls=MDSpinner(),
                    size_hint=(None, None),
                    size=(dp(400), dp(400))

                )
            self.login_dialog.add_widget(MDSpinner(size_hint=(None, None), size=(dp(46), dp(46))))
        self.login_dialog.open()
        self.thread = threading.Thread(target=self.login_user)
        self.thread.start()
    def login_user(self):
        backend_message = log_in_user_to_backend(self.email, self.password)
        if not backend_message[0]:
            #if the server gave us an error 
            self.error_message = backend_message[1]
            Clock.schedule_once(lambda dt:self.show_error(backend_message), 0)
        else:
            #if everything went as successfully planned
            Clock.schedule_once(lambda dt:self.login_complete(backend_message), 0)

    def login_complete(self, backend_message):
            app = App.get_running_app()
            access_token = backend_message[1]
            store_token_locally(access_token)
            App.get_running_app().state['is_authenticated'] = True
            App.get_running_app().state["token"] = access_token
            update_cache(username=get_user_details(access_token))
            store_profile_picture_locally() # get user profile picture and store locally on the client
            self.login_dialog.dismiss()
            sm = app.root.children[0]
            sm.current = "dashboard"
    def show_error(self, backend_message):
        self.ids.error_label.text = self.error_message
        self.login_dialog.dismiss()



class SignUpScreen(Screen):

    username_dialog = None
    sign_up_dialog = None 
    def __init__(self, name,**kwargs):
        super().__init__(name=name, **kwargs)

       
    def showDialog(self):
        if not self.username_dialog:
            self.username_dialog =MDDialog(
                title="What Shold People Know you By?",
                type="custom",
                background_color=App.get_running_app().THEME['bg'], # set background color here
                content_cls=MyTextField(
                    hint_text="Username",
                    required=True,
                    mode="fill",
                    color_mode="custom",
                    line_anim=False,
                    cursor_color=App.get_running_app().THEME["accent_color"],
                    cursor_width="1sp",
                    cursor_height="30dp",
                    cursor_blink=True,
                    font_name="fonts/Roboto-Bold.ttf",
                    font_size="20sp",
                    size_hint_x=1
        ),
            buttons=[
                MDFlatButton(
                    text="Go Back",
                    text_color=App.get_running_app().THEME['accent_color'],
                    font_name="fonts/Roboto-Bold.ttf",
                    font_size="15sp",
                    on_release=lambda dialog: self.username_dialog.dismiss()
                ),
                MDFillRoundFlatIconButton(
                    text="Proceed",
                    icon="check",
                    text_color=App.get_running_app().THEME['font_colors']['primary'],
                    md_bg_color=App.get_running_app().THEME['accent_color'],
                    font_name="fonts/Roboto-Bold.ttf",
                    font_size="15sp",
                    on_release=lambda dialog: self.signup(dialog)
                ),
            ],
        )

        self.username_dialog.open()

    
    def signup(self, dialog):
        """ We want to show a Spinner that loads, while we log the user to the backend"""
        self.password2 = self.ids.password_two.text
        user_information = {
                "email":self.ids.email.text,
                "username":self.username_dialog.content_cls.text,
                "password":self.ids.password_one.text,
            }
        if user_information["email"] == "" or secrets.compare_digest(user_information["password"], "") or secrets.compare_digest(self.password2, ""):
            self.ids.error_label.text = "Please fill in the credentials below"

        if not self.sign_up_dialog:
            self.sign_up_dialog = MDDialog(
                    text="Regesting you account",
                    content_cls=MDSpinner(),
                    size_hint=(None, None),
                    size=(dp(400), dp(400))

                )
            self.sign_up_dialog.add_widget(MDSpinner(size_hint=(None, None), size=(dp(20), dp(20))))
        self.sign_up_dialog.open()
        self.thread = threading.Thread(target=self.sign_up_user, args=(user_information,))
        self.thread.start()

    def sign_up_user(self, user_information):
        if password_is_same(user_information["password"], self.password2):
            backend_message = register_user_to_backend(
                f'http://{HOST}:8000/api/create-users/', user_information)
            if not backend_message[0]: # if server gave us an error on our request
                Clock.schedule_once(lambda dt:self.show_error(backend_message[1]), 0)
            else:
                Clock.schedule_once(lambda dt:self.signup_complete(backend_message), 0)


        else:
            Clock.schedule_once(lambda dt:self.show_error("Password not the same"), 0)

        

    def signup_complete(self, backend_message):
        app = App.get_running_app()
        sm = app.root.children[0]
        sm.current = 'login'
        toast("Try out your new login credentials")
        self.sign_up_dialog.dismiss()
        self.username_dialog.dismiss()

    def show_error(self, backend_message):
        self.ids.error_label.text = backend_message
        self.sign_up_dialog.dismiss()
        self.username_dialog.dismiss()

class ChatVortex(MDApp):
    def __init__(self):
        super().__init__()
        self.started = asyncio.Event()
    state = {
            "token":None,
            "is_authenticated":False,
            "on_first_boot":True
        }
    #storing chat state across all components of the app. this helps the keep track which is the curret chat, sender and recipient 

    # initializing chat_state variale   
    chat_state:dict[str, int | None] = {'conversation_id':None, 'recipient_profile_picture_source':None, "is_group":False}
    convos = set()
    group_length:dict[int:int] = {}
    recipient_is_active = {}
    websocket_connections = dict()

    THEME = {
    'bg': (44/255, 47/255, 63/255),
    'dark_bg':     (28/255, 30/255, 41/255),
    'primary': (0.54, 0.17, 0.89, 1),
    'accent_color':( 0.54, 0.17, 0.89, 1),
    'font_colors': {
        'primary': (0.97, 0.97, 0.97, 1),
        'secondary': (0.38, 0.48, 0.54, 1),
        'tertiary': (1.0, 0.75, 0.0, 1),
    },
    'user_widget_bg': (27/255, 30/255, 43/255, 1), # Dark shade of purple for user widget background
    'divider_color': (0.74, 0.74, 0.74, 1), # Medium shade of grey for divider line
    }
    on_clicked = {"index":'Default'}

    def build(self):
        # Set the window color
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'DeepPurple'

        root_widget = MDBoxLayout(md_bg_color=self.THEME['bg'])

        #if he user is authenticated take us directly to he dashboard
        if check_if_authenticated():
            self.state["is_authenticated"] = True
            self.state["token"] = get_user_token()
            screen_manager = ScreenManager()
            dashboard = DashBoardScreen(name="dashboard", sm=screen_manager)
            screen_manager.add_widget(dashboard)
            screen_manager.add_widget(SplashScreen(name='splash'))
            screen_manager.add_widget(LoginScreen(name='login'))
            screen_manager.add_widget(SignUpScreen(name="sign-up"))
            screen_manager.add_widget(CreateNewGroupScreen(name='create-group'), sm=screen_manager)
            screen_manager.add_widget(SettingsScreen(name='settings', sm=screen_manager))
            root_widget.add_widget(screen_manager)
        else:
            self.state["is_authenticated"] = False
            screen_manager = ScreenManager()
            screen_manager.add_widget(SplashScreen(name='splash'))
            screen_manager.add_widget(LoginScreen(name='login'))
            screen_manager.add_widget(SignUpScreen(name="sign-up"))
            dashboard = DashBoardScreen(name="dashboard", sm=screen_manager)
            screen_manager.add_widget(dashboard)
            screen_manager.add_widget(SettingsScreen(name='settings', sm=screen_manager))
            screen_manager.add_widget(CreateNewGroupScreen(name='create-group'), sm=screen_manager)
            root_widget.add_widget(screen_manager)
        return root_widget

    def on_stop(self):
        Window.close()


async def main():
    try:
        await ChatVortex().async_run('asyncio')
    except asyncio.exceptions.CancelledError:
        pass

if __name__ == "__main__":
   asyncio.run(main())
