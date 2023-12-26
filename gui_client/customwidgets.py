from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.button import  MDFlatButton
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from util import get_group, leave_group, get_username, get_user
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList,OneLineAvatarIconListItem,TwoLineAvatarListItem
from kivy.properties import *
from kivy.uix.image import AsyncImage




class LastSeenLabelDisplay(MDLabel):
    recipient_id = StringProperty("")
    last_seen = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def recipient_id_update(self, value):
        if value is None:
            recipient_id = ""
            return
        self.recipient_id = str(value)
        self.last_seen = get_user(int(self.recipient_id)).get("last_seen")



class ListItemWithCheckbox(OneLineAvatarIconListItem):
    '''Custom list item.'''
    checked_options = set()
    icon = StringProperty("account")

    def on_checkbox_active(self, checkbox, value, text):
        if value:
            self.__class__.checked_options.add(text)
        else:
            self.__class__.checked_options.remove(text)

class MembersShowOneLineAvatarListIconIem(TwoLineAvatarListItem):
    icon = StringProperty("account")




class GroupLayout(MDBoxLayout):
    def __init__(self,conversation_id=None, **kwargs):
        super().__init__(**kwargs)
        self.view_mebers_dialog = None
        if conversation_id is not None:
            self.backend_group_response = get_group(conversation_id)
        self.orientation = "vertical"
        self.group_name = MDLabel(text=f"Group Name: {self.backend_group_response.get('group_name')}")
        self.group_id = self.backend_group_response.get('group_id')
        self.members_label = MDLabel(text=f"Member Length: {self.backend_group_response.get('members_length')}")
        self.owner = MDLabel(text=f"Owner:{self.backend_group_response.get('admin').get('__data__').get('username')}#{self.backend_group_response.get('admin').get('__data__').get('user_id')}")
        self.view_mebers = MDFlatButton(text="View Members", on_press=self.on_view_members)      
       
        self.add_widget(self.group_name)
        self.add_widget(self.members_label)
        self.add_widget(self.owner)
        self.add_widget(self.view_mebers)


    def on_view_members(self, instance):
        if not self.view_mebers_dialog:
            self.view_mebers_dialog = MDDialog(
                        title="Participants",
                        type="custom",
                        content_cls=ViewMemberLayout(members=self.backend_group_response.get("members"),size_hint_y=None,owner=self.owner, height="300dp", spacing="4dp"),
                        buttons=[
                            MDFlatButton(
                                text="Go Back",
                                # text_color=App.get_running_app().THEME['accent_color'],
                                font_name="fonts/Roboto-Bold.ttf",
                                font_size="15sp",
                                on_release=lambda dialog:self.view_mebers_dialog.dismiss()
                            ),
                        ],

                )
        self.view_mebers_dialog.open()

class ViewMemberLayout(MDBoxLayout):
    def __init__(self, members=None,owner=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.scrollview = MDScrollView()
        self.list = MDList()
        if members is not None:
            for i in members:
                string_format = f"{i.get('username')}#{i.get('user_id')}"
                if string_format  == owner:
                     self.list.add_widget(MembersShowOneLineAvatarListIconIem(
                    text=string_format + "[Owner]"
                    ))
                else:
                    self.list.add_widget(MembersShowOneLineAvatarListIconIem(
                        text=string_format
                        ))
            self.scrollview.add_widget(self.list)
            self.add_widget(self.scrollview)

       
class ParticipantChooseLayout(BoxLayout):
    def __init__(self, conversation_id=None,**kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.scrollview  = MDScrollView()
        self.list = MDList()
        self.group_members = [user['username']   for user  in get_group(conversation_id).get('members')]
        for convo in App.get_running_app().convos:
            if not convo in self.group_members:
                self.list.add_widget(ListItemWithCheckbox(text=convo))
        self.scrollview.add_widget(self.list)
        self.add_widget(self.scrollview)
   

class ViewUserProfileLayout(MDBoxLayout):
    view_text = ObjectProperty()
    chat_state = StringProperty()
    def __init__(self, chat_state=None,**kwargs):
        super().__init__(**kwargs)
        self.bind(view_text=self.on_view_text_change)

    def on_view_text_change(self, instance, value):
        print("View Text changed")
        self.ids.show_user_profile_id_text.text = str(value)

    def update_chat_state(self, value):
        self.chat_state = str(value)




class RecipientProfile(AsyncImage):

    source_display = StringProperty("images/dp.png")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_source_display(self, value):
        self.source_display = value

    def reset_default(self):
        self.source_display = "images/dp.png"


