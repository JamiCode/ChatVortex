import asyncio
import websockets
from credentials import HOST
from kivy.event import EventDispatcher
from util import *
from kivy.clock import Clock
from kivy.app import App
from kivymd.uix.snackbar import Snackbar
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
import json
import time


DISCONNECTED = True
class WebSocketClient(EventDispatcher):
	"""This class helps to us to integrate websocket with kivy and to track down the necessary informationassociated with websocket, it comes with some instance variable, attirbues"""
	conversation_connect_object = None
	chat_history_connect_obj = None

	def __init__(self, token=None, main_area_layout=None):
		super().__init__()
		if token is None:
			token = get_user_token()
		self.main_area_layout = main_area_layout
		self.token = token
		self.initial_conversations = [] # list that contains the initial conversation

		#registering events
		self.register_event_type('on_initial_conversation')
		self.register_event_type('on_conversations_updated')
		self.register_event_type('on_personal_dm_receieved')
		self.register_event_type('on_initial_chat_history')
		self.register_event_type("on_update_chat_history")
		self.register_event_type("on_initial_group_chat_history")
		self.register_event_type("on_update_group_chat_history")
	#this courotine method is responsible for connecting our server. accepts token

	#this courotine is responsible for handling connecting to the convo endpoint	
	async def handle_convos_connect(self):
		#conect to the server in token
		try:
			WebSocketClient.conversation_connect_object = await websockets.connect(
				f'ws://{HOST}:8000/socket/convos',
				extra_headers={"Authorization":f"Bearer {self.token}"})

			async for message in WebSocketClient.conversation_connect_object:
				if message == "ping":
					pass
				else:
					response_data = json.loads(message)
					if response_data['action'] == 'initial':
						self.initial_conversations = response_data['convo_data']
						self.dispatch('on_initial_conversation')
						await asyncio.sleep(2)

					if response_data['action'] == 'update':
						self.initial_conversations = response_data["convo_data"]
						self.dispatch('on_conversations_updated')
						await asyncio.sleep(2)
					if response_data['action'] == 'user_info':
						if response_data['detail'] == 'offline':
							print(response_data['user_id'], "Is offline")
					if response_data['action'] == 'broadcast_dm':
						message =str(response_data['message']['message_text'])
						self.dispatch('on_personal_dm_receieved', message)


		
		except websockets.exceptions.ConnectionClosedError:	
			"""Any abruptly closure from the server side """
			print("[INFO] convos Websocket was closed abruptly by the server")
		except websockets.exceptions.ConnectionClosedOK:
			print("[Info] convos Websocket was closed properly by the server")
		except asyncio.exceptions.CancelledError:
			pass
		finally:
			if WebSocketClient.conversation_connect_object is not None:
				await WebSocketClient.conversation_connect_object.close()


	async def handle_chat_history_connect(self, conversation_id):
		try:
			if WebSocketClient.chat_history_connect_obj is not None:
				await WebSocketClient.chat_history_connect_obj.close()
			WebSocketClient.chat_history_connect_obj = await websockets.connect(f"ws://{HOST}:8000/socket/api/chat-history/{conversation_id}",
				extra_headers={"Authorization":f"Bearer {self.token}"}
				)
			async for message in WebSocketClient.chat_history_connect_obj:
				response_data = json.loads(message)
				if response_data['action'] == "initial_chat_history":
							res_chat_list = response_data['data']
							self.dispatch('on_initial_chat_history',res_chat_list)
				elif response_data['action'] == "update_chat_history":
					res_chat_list = response_data['data']

					self.dispatch('on_update_chat_history',res_chat_list)
		except asyncio.exceptions.CancelledError:
			pass
		except websockets.exceptions.ConnectionClosedError:
			print("[INFO] chat history connection was closed by server abruptly")
		except websockets.exceptions.ConnectionClosedOK:
			print("[INFO] Chat  history connectin was closed by the server")
		finally:
			if WebSocketClient.chat_history_connect_obj is not None:
				await WebSocketClient.chat_history_connect_obj.close()
	


	async def handle_group_history_connect(self, conversation_id):
		try:
			if WebSocketClient.chat_history_connect_obj is not None:
				await WebSocketClient.chat_history_connect_obj.close()
			WebSocketClient.chat_history_connect_obj = await websockets.connect(f"ws://{HOST}:8000/socket/group-history/{conversation_id}",
				extra_headers={"Authorization":f"Bearer {self.token}"}
				)
			async for message in WebSocketClient.chat_history_connect_obj:
				response_data = json.loads(message)
				if response_data['action'] == "initial_chat_history":
					res_chat_list = response_data['data']
					self.dispatch('on_initial_group_chat_history',res_chat_list)
				elif response_data['action'] == "update_chat_history":
					res_chat_list = response_data['data']
					self.dispatch('on_update_group_chat_history',res_chat_list)
		except asyncio.exceptions.CancelledError:
			pass
		except websockets.exceptions.ConnectionClosedError:
			print("[INFO]: Group History Connection closed by Server abruptly")
		finally:
			if  WebSocketClient.chat_history_connect_obj is not None:
				await WebSocketClient.chat_history_connect_obj.close()

	async def handle_send_functionality(self,**kwargs):
		"""This method simply connects to the websocket server only to send message to the server, the closing of the websocket server is handled by the server. The Server would end the connection"""
		try:
			message_form = {**kwargs}
			conversation_id = kwargs['conversation_id']
			websocket  = await websockets.connect(
					f"ws://{HOST}:8000/socket/convo/{conversation_id}",
					extra_headers={"Authorization":f"Bearer {self.token}"}
					)
			await websocket.send(json.dumps(message_form))
			response = await websocket.recv()
			response_data = json.loads(response)
			if response_data.get("conversation-error"):
				Snackbar(text=f'{response_data["conversation-error"]}. You cannot message this user',snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#ff0000")).open()

		except websockets.exceptions.ConnectionClosedError:
			"""Any abruptly closure from the server side """
			print("[INFO] convos Websocket was closed abruptly by the server")
		except asyncio.exceptions.CancelledError:
			pass

	async def handle_send_functionality_group(self,**kwargs):
		message_form = {**kwargs}
		conversation_id = kwargs['conversation_id']
		async with websockets.connect(
			f"ws://{HOST}:8000/socket/group_convo/{conversation_id}",
			extra_headers={"Authorization":f"Bearer {self.token}"}
			) as websocket:
			await websocket.send(json.dumps(message_form))
	async def handle_create_chat_functionality(self, create_chat_dialog,**kwargs,):
		"""Return true if the creation was successuly"""
		message_form = {**kwargs}
		username = kwargs.get('username')

		async with websockets.connect(f"ws://{HOST}:8000/socket/create-convo", extra_headers={"Authorization":f"Bearer {self.token}"}) as websoc:
			#send data over
			await websoc.send(json.dumps(message_form))
			response = await websoc.recv()
			response_json = json.loads(response)
			if response_json.get('type') == 'redirect':
				Snackbar(text=response_json.get('info'),snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#ff8a80")).open()
				return
			Snackbar(text="Conversation Created with user",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#ff8a80")).open()
			create_chat_dialog.dismiss()



	#change the for loop to better reflect
	def on_initial_conversation(self,**kwargs):
		# print(self.initial_conversations)
		self.initial_conversations = sorted(self.initial_conversations, key=lambda x: x['last_message_sent_time'], reverse=True)
		rv = self.main_area_layout.ids.chat_list
		rv.data = []
		rv.recipientsget_last_message_from_backend= []
		rv.groups=[]
		app = App.get_running_app()

		for convo in self.initial_conversations:

			if convo['conversation_type'] == "Group":
				convo_prop = {'text': f"Group:{convo['group_name']}", 'secondary_text':f'{convo["last_message_sent"]}','ripple_scale': 0}
				rv.groups.append(True)
				rv.data.append(convo_prop)
				rv.groups_id[convo["conversation_id"]] = convo["group_id"]
				app.group_length[convo["conversation_id"]] = convo["group_length"]
			else:
				convo_prop = {'text': convo['other_participant']['username'], 'secondary_text':f'{convo["last_message_sent"]}','ripple_scale': 0, "profile_picture":convo["profile_picture"]}
				rv.data.append(convo_prop)
				rv.groups.append(False)
				app.convos.add(convo_prop['text'])
				if convo["other_participant"]["activity"]:
					app.recipient_is_active[convo['other_participant']['user_id']] = f"active now"
				else:
					app.recipient_is_active[convo["other_participant"]["user_id"]] = f"""last seen {convo["other_participant"]["last_seen"]}"""

		self.conversations_indicator_list = self.initial_conversations
		#create the same copy for comparing purposes, when the list updates
		rv.recipients = [ None if convo['conversation_type'] == "Group" else convo['other_participant']['user_id'] for convo in self.initial_conversations]
		rv.convos = [convo['conversation_id'] for convo in self.initial_conversations]

		


	def on_conversations_updated(self,**kwargs):
		self.initial_conversations = sorted(self.initial_conversations, key=lambda x: x['last_message_sent_time'], reverse=True)
		rv = self.main_area_layout.ids.chat_list
		rv.data = []
		rv.recipients= []
		rv.groups=[]
		app = App.get_running_app()

		for convo in self.initial_conversations:
			if convo['conversation_type'] == "Group":
				convo_prop = {'text': f"Group:{convo['group_name']}", 'secondary_text':f'{convo["last_message_sent"]}','ripple_scale': 0}
				rv.data.append(convo_prop)
				rv.groups.append(True)
				rv.groups_id[convo["conversation_id"]] = convo["group_id"]	
				app.group_length[convo["conversation_id"]] = convo["group_length"]
			else:
				convo_prop = {'text': convo['other_participant']['username'], 'secondary_text':f'{convo["last_message_sent"]}','ripple_scale': 0}
				rv.data.append(convo_prop)
				rv.groups.append(False)
				app.convos.add(convo_prop['text'])
			
				if convo["other_participant"]["activity"]:
					app.recipient_is_active[convo['other_participant']['user_id']] = f"active now"
				else:
					app.recipient_is_active[convo["other_participant"]["user_id"]] = f"""last seen {convo["other_participant"]["last_seen"]}"""





		rv.recipients = [ None if convo['conversation_type'] == "Group" else convo['other_participant']['user_id'] for convo in self.initial_conversations]
		rv.convos = [convo['conversation_id'] for convo in self.initial_conversations]
		view_instance = rv.view_adapter.get_view(data_item=rv.data[0], viewclass=rv.viewclass, index=0)
		#if user sends message, it should be moved at the beginning recycle view indicating the most recent chat, he is chat
		rv_layout = rv.ids.layout
		view_instance.apply_selection(rv, 0, True)
		rv_layout.select_node(view_instance)



	def on_initial_chat_history(self,res_chat_list):
		rv=self.main_area_layout.ids.chat_history
		rv.chat_items=res_chat_list

	def on_initial_group_chat_history(self, res_chat_list):
		rv=self.main_area_layout.ids.chat_history
		rv.chat_items=res_chat_list

	def on_update_chat_history(self, res_chat_list):
		rv = self.main_area_layout.ids.chat_history
		rv.chat_items = res_chat_list

	def on_update_group_chat_history(self, res_chat_list):
		rv = self.main_area_layout.ids.chat_history
		rv.chat_items = res_chat_list

	def on_personal_dm_receieved(self, *args):
		m = args[0]
		self.main_area_layout.add_chat_message(m)

	@classmethod
	async def _d(cls):
		async with websockets.connect(f"ws://{HOST}:8000/socket/disconnect") as websocket:
			await websocket.send("Hello world")
			await websocket.close()	
		 

	@classmethod
	def disconnect(cls):
		asyncio.create_task(cls._d())
		time.sleep(1)

async def handle_create_group_functionality(**kwargs):
		message_form = {**kwargs}
		async with websockets.connect(f"ws://{HOST}:8000/socket/create-group",extra_headers={"Authorization":f"Bearer {get_user_token()}"}) as websocket:
			await websocket.send(json.dumps(message_form))
			response = await websocket.recv()
			response_json = json.loads(response)
			if response_json.get("error"):
				Snackbar(text=response_json.get('error'),snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#ff8a80")).open()
				return
			elif response_json.get('info') == 'done':
				Snackbar(text="Group Created Sucessfuly",snackbar_x="10dp",snackbar_y="10dp",size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=get_color_from_hex("#ff8a80")).open()




async def handle_close_websocket_connections():
	"""Return True if it was able to """

	if WebSocketClient.conversation_connect_object is None and WebSocketClient.chat_history_connect_obj is None:
		return False

	if WebSocketClient.conversation_connect_object is not None:
		await WebSocketClient.conversation_connect_object.close()

	if WebSocketClient.chat_history_connect_obj is not None:
		await WebSocketClient.chat_history_connect_obj.close()
	return True


