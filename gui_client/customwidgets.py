from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.button import  MDFlatButton
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from util import get_group, leave_group
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList,OneLineAvatarIconListItem
from kivy.properties import StringProperty


class ListItemWithCheckbox(OneLineAvatarIconListItem):
    '''Custom list item.'''
    checked_options = set()
    icon = StringProperty("account")

    def on_checkbox_active(self, checkbox, value, text):
        if value:
            self.__class__.checked_options.add(text)
        else:
            self.__class__.checked_options.remove(text)



class GroupLayout(MDBoxLayout):
    def __init__(self,conversation_id=None, **kwargs):
        super().__init__(**kwargs)
        if conversation_id is not None:
            self.backend_group_response = get_group(conversation_id)
        self.orientation = "vertical"
        self.group_name = MDLabel(text=f"Group Name: {self.backend_group_response.get('group_name')}")
        self.group_id = self.backend_group_response.get('group_id')
        self.members_label = MDLabel(text=f"Member Length: {self.backend_group_response.get('members_length')}")
        self.owner = MDLabel(text=f"Owner:{self.backend_group_response.get('admin').get('__data__').get('username')}")
        self.leave_button = MDFlatButton(text="Click to leave group", on_release=self.on_leave_group)
        self.add_button = MDFlatButton(text="Click to add members")
        self.add_widget(self.group_name)
        self.add_widget(self.members_label)
        self.add_widget(self.owner)
        self.add_widget(self.leave_button)
        self.add_widget(self.add_button)

    def on_leave_group(self, instance):
        leaving_group_process = leave_group(self.group_id)

class ParticipantChooseLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.scrollview  = MDScrollView()
        self.list = MDList()
        for convo in App.get_running_app().convos:
            self.list.add_widget(ListItemWithCheckbox(text=convo))
        self.scrollview.add_widget(self.list)
        self.add_widget(self.scrollview)

