import kivy
from kivy.utils import get_color_from_hex
from kivy.uix.screenmanager import *
from kivymd.uix.textfield import MDTextField
from util import *
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.list import ThreeLineAvatarIconListItem, OneLineAvatarIconListItem, TwoLineAvatarListItem, OneLineListItem
from kivy.metrics import dp
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivymd.uix.recycleview import MDRecycleView
from kivy.core.window import Window
from kivymd.uix.list import ImageLeftWidget
from kivy.uix.image import AsyncImage, Image
from kivy.uix.textinput import TextInput
from kivy.app import App
from kivy.properties import ColorProperty, BooleanProperty, StringProperty, ListProperty, ObjectProperty, NumericProperty, DictProperty
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from websocket_kivy import WebSocketClient, handle_close_websocket_connections
from kivy.uix.label import Label
from kivymd.uix.label import MDLabel
from kivy.clock import Clock
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import * 
from kivymd.uix.snackbar import Snackbar
from kivymd.toast import toast
from kivy.uix.widget import Widget
import random
import asyncio
import json
import threading
import time
from kivymd.uix.filemanager import MDFileManager
from kivy.uix.image import CoreImage
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Ellipse
from customwidgets import GroupLayout, ParticipantChooseLayout, ListItemWithCheckbox, ViewUserProfileLayout,RecipientProfile



class CustomImageLeftWidget(AsyncImage):
    """This custom class is needed   for my texture rending"""
    pass



class EditableImageWidget(BoxLayout):
    def __init__(self, **kwargs):
        super(EditableImageWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.image = AsyncImage(source="images/dp.png", size_hint=(1, 0.02), allow_stretch=True, keep_ratio=True)
        self.add_widget(self.image)
        self.edit_icon = MDIconButton(icon="pencil", size_hint=(None, None), size=(dp(48), dp(48)))
        self.edit_icon.pos_hint = {'center_x': .5, 'center_y': .5}
        self.add_widget(self.edit_icon)

    def open_file_manager(self, *args):
        # Open the file manager to allow the user to select a new image
        self.file_manager.show("/")

    def exit_file_manager(self, *args):
        # Close the file manager
        self.file_manager.close()

    def select_path(self, path):
        # Set the new image source and reload the circular image
        self.image.source = path
        self.image.reload()

class CustomMDLabel(MDLabel):
    def __init__(self, **kwargs):
        super(CustomMDLabel, self).__init__(**kwargs)
        self.padding = [0, dp(4), 0, dp(4)]



class ChatHistoryItem(MDBoxLayout):
    message = StringProperty('')
    sender_username = StringProperty('')
    message_time = StringProperty('')
    chat_item_background_color = ObjectProperty(get_color_from_hex("#ff0000"))

class ChatHistoryList(MDRecycleView):
    """A widget for displaying a list of chat items"""
    #the chat_items here is based on the {conversation_id}
    chat_items = ListProperty([])
    current_conversation = NumericProperty(0)

    def __init__(self, **kwargs):
        super(ChatHistoryList, self).__init__(**kwargs)
        #add a change to this later
        self.data = []
        self.bind(chat_items=self.on_chat_items_update)


    def decide_hex_color(self, username):
        actual_username = get_user_details_from_cache()["username"]
        if actual_username == username:
            return "#620c8a"
        return "#231a24"

    def on_chat_items_update(self, instance, new_chat_items):
        """ when on_chat_items value changes this fncion gets called"""
        
        self.data = [ {'message':chat['message_text'], 'sender_username':chat['sender_username'], 'message_time':" ".join(convert_string_to_date(chat['timestamp'])),'chat_item_background_color':get_color_from_hex(self.decide_hex_color(chat["sender_username"]))} for chat in new_chat_items]
        self.refresh_from_data()



class UserNameDisplay(Label):

    username_display = StringProperty("James")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_username_display(self, value):
        self.username_display = str(value)

class GroupMemeberLengthDisplay(Label):
    group_length_display = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_group_members_length_display(self, value):
        self.group_length_display = str(value)



class AccountUsernameDisplay(MDLabel):
    username_display = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_account_username_display(self, value):
        self.username_display = str(value)
    

class MyTextInput(TextInput):
    def __init__(self, **kwargs):
        super(MyTextInput, self).__init__(**kwargs)
        Window.bind(mouse_pos=self.on_mouseover)
        app = App.get_running_app()
        self.cursor_color = get_color_from_hex("#03a9f4")
    
    def on_mouseover(self, window, pos):
        if self.collide_point(*pos):
            Window.set_system_cursor('ibeam')
        else:
            Window.set_system_cursor('arrow')

class SelectableRecycleLayout(Widget):
    """Adds selection and focus behavior to the view."""
    owner = ObjectProperty()
    selected = DictProperty()
    selects = ListProperty()
    multiselect = BooleanProperty(False)

    def clear_selects(self):
        self.selects = []

    def refresh_selection(self):
        for node in self.children:
            try:  #possible for nodes to not be synched with data
                data = self.parent.data[node.index]
                node.selected = data['selected']
            except:
                pass

    def deselect_all(self):
        for data in self.parent.data:
            data['selected'] = False
        self.refresh_selection()
        self.selects = []
        self.selected = {}

    def select_all(self):
        self.selects = []
        selects = []
        for data in self.parent.data:
           
            data['selected'] = True
            selects.append(data)
        self.selects = selects
        self.selected = selects[-1]
        self.refresh_selection()

    def select_node(self, node):
        if not self.multiselect:
            self.deselect_all()
        node.selected = True
        self.selects.append(node.data)
        if node.data not in self.parent.data:
            return
        self.parent.data[self.parent.data.index(node.data)]['selected'] = True
        node.data['selected'] = True
        self.selected = node.data

    def deselect_node(self, node):
        if node.data in self.selects:
            self.selects.remove(node.data)
        if self.selected == node.data:
            if self.selects:
                self.selected = self.selects[-1]
            else:
                self.selected = {}
        if node.data in self.parent.data:
            parent_index = self.parent.data.index(node.data)
            parent_data = self.parent.data[parent_index]
            parent_data['selected'] = False
        node.selected = False
        node.data['selected'] = False

    def click_node(self, node):
        #Called by a child widget when it is clicked on
        if node.selected:
            if self.multiselect:
                self.deselect_node(node)
            else:
                pass
                #self.deselect_all()
        else:
            if not self.multiselect:
                self.deselect_all()
            self.select_node(node)
            self.selected = node.data

    def remove_node(self, node):
        self.parent.data.pop(node.index)

    def select_range(self, *_):
        if self.multiselect and self.selected and self.selected['selectable']:
            select_index = self.parent.data.index(self.selected)
            selected_nodes = []
            if self.selects:
                for select in self.selects:
                    if select['selectable']:
                        if select not in self.parent.data:
                            continue
                        index = self.parent.data.index(select)
                        if index != select_index:
                            selected_nodes.append(index)
            else:
                selected_nodes = [0, len(self.parent.data)]
            if not selected_nodes:
                return
            closest_node = min(selected_nodes, key=lambda x: abs(x-select_index))
            for index in range(min(select_index, closest_node), max(select_index, closest_node)):
                selected = self.parent.data[index]
                selected['selected'] = True
                if selected not in self.selects:
                    self.selects.append(selected)
            self.parent.refresh_from_data()

    def toggle_select(self, *_):
        if self.multiselect:
            if self.selects:
                self.deselect_all()
            else:
                self.select_all()
        else:
            if self.selected:
                self.selected = {}
class SelectableRecycleBoxLayout(SelectableRecycleLayout,RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''



class SelectedChatItem(RecycleDataViewBehavior, TwoLineAvatarListItem):
    
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)
    left_image = ObjectProperty()
    clicked = False

    def __init__(self, **kwargs):
        self.left_image = AsyncImage(source="images/dp.png")
        super().__init__(**kwargs)


    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        self.data = data
        if not data.get("profile_picture"):
            self.left_image.source = "images/dp.png"


        return super(SelectedChatItem, self).refresh_view_attrs(
            rv, index, data)
    
    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(SelectedChatItem, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            self.parent.click_node(self)
            self.apply_selection(self.parent.parent,self.index, True)
    
    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        if is_selected:
            self.bg_color = (21/255, 23/255, 31/255, 1)  # Blue color

            app = App.get_running_app()
            #grabbing the  main area and storing in self.root
            self.main_area = app.root.children[0].children[0].children[0]
            # giving the values to the chat_state
            chat_state = {
                'recipient_id':rv.recipients[index],
                'conversation_id':rv.convos[index],
                'is_group': rv.groups[index]
            }
            app.update_chat_state(chat_state)
            self.main_area.view_layout.ids.last_seen_display.recipient_id_update(app.chat_state['recipient_id'])


            app.conversation_blocked_status = check_is_blocked(app.chat_state['conversation_id'])
            if not SelectedChatItem.clicked:
                self.main_area.remove_widget(self.main_area.children[0])
                # print(self.main_area)
                self.main_area.add_widget(self.main_area.sidebar2)
                SelectedChatItem.clicked = True
            if not self.data.get("profile_picture"):
                app.chat_state["recipient_profile_picture_source"] = "images/dp.png"
                # this grabs the RecipientProfile Widget in Sidebar 2, and call the reset_default method
                MainArea.recipient_profile_object.reset_default()
            else:
                image_src = download_image(filepath=f"images/recipients/{rv.recipients[index]}", image_byte=self.data.get("profile_picture"))
                app.chat_state["recipient_profile_picture_source"] = image_src
                MainArea.recipient_profile_object.update_source_display(image_src)


            if app.chat_state['is_group']:
                MainArea.group_memebers_object.update_group_members_length_display(f"{app.group_length[rv.convos[index]]} members")
                asyncio.create_task(client.handle_group_history_connect(app.chat_state['conversation_id']))
            else:
                activity_text = app.recipient_is_active[app.chat_state['recipient_id']]
                MainArea.group_memebers_object.update_group_members_length_display(f"{activity_text}")


                asyncio.create_task(client.handle_chat_history_connect(app.chat_state['conversation_id']))
         
            MainArea.username_label.update_username_display(rv.data[index]['text'])  
            # Find the new index of the selected item after rearranging
        else:
            self.bg_color = App.get_running_app().THEME["bg"]  # Blue color



    def on_kv_post(self, base_widget):
        self.ids._left_container.clear_widgets()
        self.ids._left_container.add_widget(self.left_image)



class ChatRecycleView(MDRecycleView):
    def __init__(self, **kwargs):
        super(ChatRecycleView, self).__init__(**kwargs)
        self.viewclass = SelectedChatItem
        self.is_search_data = False
        self.recipients = []
        self.data = []
        self.in_memory_data = [] # holds memory of data before in search mode
        self.search_data = []
        self.groups = []
        self.groups_id  = {}
        self.bind(data=self.on_data_change)
    def selectItem(self, itemId):
        self.selectedItemId = itemId
        # Update the background color of the selected item

    def set_data(self):
        """ This is for setting the data, if the user is in search mode or not"""
        self.is_search_data = True
        self.data = self.search_data
    def unset_data(self):
        self.is_search_data = False
        self.data = self.in_memory_data

    def on_data_change(self, instance, value):
        if not self.is_search_data:
            self.in_memory_data = self.data


#  Creating a class for custom label that would help in the rerender








class SideBarBoxLayoutOne(BoxLayout):
    pass


class MainArea(BoxLayout):
    create_chat_dialog = None
    # SIDEBAR_2 = None
    recipient_profile_object = None
    group_memebers_object = None
    group_member_length_display  = None
    username_label = None
    view_profile_text = StringProperty('View Profile')
    leave_group_text = StringProperty("Leave Group")
    block_text = StringProperty("")
    def __init__(self, sm, **kwargs):
        self.bind(block_text=self.on_text_variable_change)
        self.sm = sm 
        self.coversation_group_menu  = None
        self.leave_group_confirmation_menu = None
        self.add_members_dialog = None
        self.blocked_dialog_confirmation = None
        self.unblocked_dialog_confirmation = None
        self.sidebar2 = None
        self.on_view_user_show_dialog = None
        self.view_layout = ViewUserProfileLayout()
        super().__init__(**kwargs)
        menu_items = [
            {"text":'Logout', 'viewclass':"OneLineListItem", "on_release":self.logout},
            {"text":"Settings", 'viewclass':"OneLineListItem", "on_release":self.show_settings_screen},
            {'text':'New Group', 'viewclass':'OneLineListItem', 'on_release':self.show_create_group_screen}
        ]

        self.chat_menu_items = [
            {"text":self.block_text, 'viewclass':"OneLineListItem",'on_release':self.block_dialog_show},
            {'text':"View User", "viewclass":"OneLineListItem", "on_release":self.on_view_user_show}
        ]

        group_chat_menu_items = [
            {"text":'View Group', 'viewclass': 'OneLineListItem', 'on_release':self.show_view_conversation},
            {'text':"Leave Group", 'viewclass':'OneLineListItem', "on_release":self.show_leave_group_dialog},
            {'text':"Add Members ", 'viewclass':"OneLineListItem", "on_release":self.show_add_member_dialog}
        ]
        self.menu = MDDropdownMenu(
            items=menu_items,
            caller=self.ids.icon_button,
            width_mult=2,
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        MainArea.chat_menu = MDDropdownMenu(
                items=self.chat_menu_items,
                caller=self.ids.icon_button2,
                width_mult=2,
                pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        MainArea.group_menu = MDDropdownMenu(
                items=group_chat_menu_items,
                caller=self.ids.icon_button2,
                width_mult=2,
                pos_hint={"center_x": 0.5, "center_y": 0.5}
        )


    def on_text_variable_change(self, instance, value):
        # print("changed  ")
        # This method will be called whenever the text_variable changes
        MainArea.chat_menu.items[0]['text'] = value
        if  MainArea.chat_menu.items[0]['text'] == "unblock":
            MainArea.chat_menu.items[0]['on_release'] = self.unblock_dialog_show
        else:
           MainArea.chat_menu.items[0]['on_release'] = self.block_dialog_show



    def menu_open(self, is_group):
        if is_group:
            MainArea.group_menu.open()
        else:
            app = App.get_running_app()
            self.view_layout.view_text = str(get_username(App.get_running_app().chat_state['recipient_id']))
            if app.conversation_blocked_status["is_blocked"] and app.conversation_blocked_status["blocked_user_id"] != get_userid_from_cache():
                #if the conversation is blocked and the user is not the blocked user, he has the option to unblock
                self.block_text = "unblock"
                MainArea.chat_menu.open()
            elif not app.conversation_blocked_status["is_blocked"]:
                self.block_text = "block"
                MainArea.chat_menu.open()




    def unblock_dialog_show(self):
        if not self.unblocked_dialog_confirmation:
            self.unblocked_dialog_confirmation = MDDialog(text="Are you sure you want to unblock this user?", type="custom",buttons=[
                    MDFlatButton(text="Cancel", on_release=lambda dialog:self.unblocked_dialog_confirmation.dismiss()),
                    MDFlatButton(text="Confirm", on_release=self.unblock)
                ] )
        self.unblocked_dialog_confirmation.open()
    def unblock(self, instance):
        conversation_id = App.get_running_app().chat_state["conversation_id"]
        unblocking_process = unblock_util(conversation_id)
        if unblocking_process:
            Snackbar(text="Successfully unblocked this user",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#00ff00")).open()
            self.unblocked_dialog_confirmation.dismiss()


    def block_dialog_show(self):
        if not self.blocked_dialog_confirmation:
            self.blocked_dialog_confirmation = MDDialog(
                text="Do you want to block this user?",
                type="custom",
                buttons=[
                    MDFlatButton(text="Cancel", on_release=lambda dialog:self.blocked_dialog_confirmation.dismiss()),
                    MDFlatButton(text="Confirm", on_release=self.block)
                ] 
                )
        self.blocked_dialog_confirmation.open()
    def block(self, instance):
        conversation_id = App.get_running_app().chat_state["conversation_id"]
        recipient_id = App.get_running_app().chat_state['recipient_id']
        blocking_process = block_util(conversation_id, recipient_id)
        if blocking_process == True:
            Snackbar(text="Successfully Blocked this user",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#00ff00")).open()
            self.blocked_dialog_confirmation.dismiss()

    def on_view_user_show(self):
        if not self.on_view_user_show_dialog:
            self.on_view_user_show_dialog = MDDialog(
                    title="User Profile",
                    type="custom",
                    content_cls=self.view_layout,
                )


        self.on_view_user_show_dialog.open()


    def show_leave_group_dialog(self):
        if not self.leave_group_confirmation_menu:
            self.leave_group_confirmation_menu = MDDialog(
                    text="Are you sure you want to leave this group?",
                    type="custom",
                    buttons=[
                        MDFlatButton(text="Cancel", on_release=lambda dialog: self.leave_group_confirmation_menu.dismiss()), MDFlatButton(text="Leave", text_color=(1,0,0,1), md_bg_color=(1, 0, 0, 1),font_size="15sp", on_release=self.leave_group_dialog)
                    ]
                )

        self.leave_group_confirmation_menu.open()

    def show_add_member_dialog(self):
        if not self.add_members_dialog:
            self.add_members_dialog = MDDialog(title="Choose participants below",type="custom",content_cls=ParticipantChooseLayout(size_hint_y=None, height="300dp", spacing="4dp"), buttons=[MDFlatButton(text="Cancel", on_release=lambda dialog:self.add_members_dialog.dismiss()), MDFlatButton(text="Add", on_release=self.on_add_member)])
        self.add_members_dialog.open()

    def on_add_member(self, instance):
        new_users_ids = [get_userid(name).get('id') for name in ListItemWithCheckbox.checked_options ]
        rv = self.ids.chat_list
        group_id = rv.groups_id[App.get_running_app().chat_state['conversation_id']]
        for new_user_id in new_users_ids:
            add_members_process = add_members( group_id, new_user_id)
            if add_members_process.get("detail"):
                Snackbar(text=f"{add_members_process['detail']}",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#ff0000")).open()
                return
        Snackbar(text=f"{add_members_process['message']}",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#00ff00")).open()

        self.add_members_dialog.dismiss()

    def leave_group_dialog(self, instance):
        conversation_id = App.get_running_app().chat_state['conversation_id']
        rv = self.ids.chat_list
        group_id = rv.groups_id[conversation_id]
        leave_group_process = leave_group(group_id)
        if leave_group_process == True:
            self.leave_group_confirmation_menu.dismiss()
            # self.remove_widget(MainArea.SIDEBAR_2)
            self.remove_widget(self.sidebar2)
            self.add_widget(MDLabel(text="Select a Chat to start Chatting", halign="center"))
            Snackbar(text="Successfully left the group",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#00ff00")).open()
            SelectedChatItem.clicked = False
        else:
             Snackbar(text=f"{leave_group_process}",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#00ff00")).open()



    def show_view_conversation(self):
        app = App.get_running_app()
        if app.chat_state["is_group"]:
            self.coversation_group_menu =  MDDialog(
                title="Group Info",
                type="custom",
                # background_color=app.THEME['bg'], # set background color here
                content_cls=GroupLayout(conversation_id=app.chat_state["conversation_id"],size_hint_y=None, height="300dp", spacing="4dp"),
                buttons=[
                    MDFlatButton(
                        text="Go Back",
                        # text_color=App.get_running_app().THEME['accent_color'],
                        font_name="fonts/Roboto-Bold.ttf",
                        font_size="15sp",
                        on_release=lambda dialog:self.coversation_group_menu.dismiss()
                    ),
                ],

                )

            self.coversation_group_menu.open()
            return


    def on_kv_post(self, base_widget):
        MainArea.recipient_profile_object = self.ids.rp
        MainArea.group_memebers_object  = self.ids.group_member_length_display
        MainArea.username_label = self.ids.username_label
        self.sidebar2 = self.ids.sidebar2
       

    def get_dimension(self):
     print(Window.size)

    def send(self):
        """This simply adds the message to the userbase"""
        message = self.ids.chat_box.text
        if message == '':
            pass
        conversation_id = App.get_running_app().chat_state['conversation_id']
        sender_id = App.get_running_app().chat_state['sender_id']
        recipient_id = App.get_running_app().chat_state['recipient_id']
        is_group = App.get_running_app().chat_state['is_group']

        if not is_group:
            asyncio.gather(client.handle_send_functionality(message_text=message, conversation_id=conversation_id, recipient_id=recipient_id, sender_id=sender_id))
            return
        asyncio.gather(client.handle_send_functionality_group(message_text=message, conversation_id=conversation_id, sender_id=sender_id))
        self.ids.chat_box.text = ''

    def show_create_group_screen(self):
        self.sm.transition = FadeTransition()
        self.sm.current = "create-group"
        self.menu.dismiss()

    def logout(self):
        app =App.get_running_app() 
        app.state['is_authenticated'] = False
        app.state = {}
        app.update_chat_state({})
        app.convos = set()
        asyncio.create_task(handle_close_websocket_connections())
        app.state["on_first_boot"] = False

        logout()
        self.sm.current = "splash"
        self.sm.transition.direction = "left"
        self.menu.dismiss()
       

    def show_settings_screen(self):
        self.sm.current = "settings"
        self.menu.dismiss()

    def search_chat(self):
        text = self.ids.search_chat_input.text.lower()
        if text:
            names_chat = [d for d in self.ids.chat_list.data]
            filtered_data = list(filter(lambda name: text in name['text'].lower(), names_chat))
            self.ids.chat_list.search_data = filtered_data
            self.ids.chat_list.set_data()
        else:
            self.ids.chat_list.unset_data()

    def create_new_chat_dialog(self):
        if not self.create_chat_dialog:
            self.create_chat_dialog=MDDialog(
                    title="Enter username with ID",
                    type="custom",
                    content_cls=MDTextField(
                            hint_text="Example:John#1",
                            mode='rectangle',
                            color_mode="custom",
                            line_anim=False,
                            cursor_color=App.get_running_app().THEME['accent_color'],
                            cursor_width="1sp",
                            cursor_blink=True,
                            font_size="20sp",
                            size_hint_x=1

                        ),
                    buttons=[
                    MDFlatButton(
                        text="Go Back",
                        text_color=App.get_running_app().THEME['accent_color'],
                        font_name="fonts/Roboto-Bold.ttf",
                        font_size="15sp",
                        on_release=lambda dialog: self.create_chat_dialog.dismiss()),
                    MDRectangleFlatIconButton(
                        text="Start Chatting",
                        icon="chat-plus",
                        text_color=App.get_running_app().THEME['font_colors']['primary'],
                        md_bg_color=App.get_running_app().THEME['accent_color'],
                        font_name="fonts/Roboto-Bold.ttf",
                        font_size="15sp",
                        on_release=lambda dialog: self.create_chat()
                        ),
                    ],

                )
        self.create_chat_dialog.open()

        
    def create_chat(self):
        sender_id=App.get_running_app().chat_state['sender_id']
        recipient_text=self.create_chat_dialog.content_cls.text
        recipient_id = get_userid(recipient_text).get('id')
        if not recipient_id:
            Snackbar(text="User Not found",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#ff8a80")).open()
        else:

            task = asyncio.create_task(client.handle_create_chat_functionality(create_chat_dialog=self.create_chat_dialog,sender_id=sender_id, recipient_id=recipient_id))
            



class DashBoardScreen(Screen):

    def __init__(self, name, sm,**kwargs):
        super().__init__(name=name, **kwargs)
        token = get_user_token()
        self.sm = sm
        self.app = App.get_running_app()
        self.main_area_layout = MainArea(sm=self.sm,orientation="horizontal")
        self.add_widget(self.main_area_layout)


        if self.app.state["on_first_boot"]:
            self.app.state['on_first_boot'] = False
            self.main_area_layout.remove_widget(self.main_area_layout.ids.sidebar2)
            self.main_area_layout.add_widget(MDLabel(text="Select a chat to start messaging", halign="center"))


        self.websocket_client = WebSocketClient(token, self.main_area_layout)

    def mount_ui(self):
        self.username = get_user_details_from_cache()["username"]
        self.user_id = get_user_details_from_cache()["user_id"]
        self.main_area_layout.ids.account_username_display.update_account_username_display(f"{self.username}#{self.user_id}")

        App.get_running_app().chat_state['sender_id'] = get_user_details_from_cache()["user_id"]



    async def connect_to_server(self):
        """The first connection is made for long lived streaming connection for conversations"""
        token = get_user_token()
        global client
        client = WebSocketClient(token, self.main_area_layout)
        t = await client.handle_convos_connect()


    async def mount_image(self):
        self.main_area_layout.ids.user_display_profile_picture.reload()
        await asyncio.sleep(0.5)
        self.main_area_layout.ids.user_display_profile_picture.source = get_profile_picture()
    


    def on_enter(self):
        """ We we enter this screen, we establish the websocket connection to fastapi server."""
        asyncio.create_task(self.connect_to_server())
        asyncio.create_task(self.mount_image())
        self.mount_ui()