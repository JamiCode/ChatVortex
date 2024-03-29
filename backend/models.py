import peewee
import datetime
from database import db
import passlib.hash as _hash



# Define the User model
class User(peewee.Model):
    user_id = peewee.PrimaryKeyField()
    email = peewee.CharField(unique=True, index=True)
    username = peewee.CharField(max_length=50, unique=True)
    hashed_password = peewee.CharField()
    is_active = peewee.BooleanField(default=False)
    is_admin = peewee.BooleanField(default=False)
    date_created = peewee.DateTimeField(default=datetime.datetime.now)
    profile_picture = peewee.BlobField(null=True)
    last_seen = peewee.DateTimeField(null=False) 

    class Meta:
        database = db

    
    def __repr__(self) -> str:
        return f"User Record({self.username})"

    def verify_password(self, password:str):
        return _hash.bcrypt.verify(password, self.hashed_password)

    def get_last_seen(self):
        now = datetime.datetime.utcnow()
        time_diff = now - self.last_seen
        # Calculate the time difference in minutes
        minutes = int(time_diff.total_seconds() / 60)

        if not self.is_active:  
            if minutes < 1:
                return "now"
            elif minutes == 1:
                return "1 min ago"
            elif minutes < 60:
                return f"{minutes} mins ago"
            elif minutes < 1440:  # 24 hours
                hours = int(minutes / 60)
                return f"{hours} hours ago"
            else:
                days = int(minutes / 1440)
                return f"{days} days ago"
        return 'online'




# Define the Conversation model
class Conversation(peewee.Model):
    conversation_id = peewee.PrimaryKeyField()
    conversation_type = peewee.CharField(choices=[('DM', 'Direct Message'), ('Group', 'Group')], max_length=10)
    last_message_sent = peewee.DateTimeField(default=datetime.datetime.utcnow())
    is_blocked  = peewee.BooleanField(default=False)
    blocked_user_id = peewee.IntegerField(null=True)

    class Meta:
        database = db


# Define the ConversationParticipant model
class ConversationParticipant(peewee.Model):
    conversation_id = peewee.ForeignKeyField(Conversation, backref='participants')
    participant_id = peewee.ForeignKeyField(User)

    class Meta:
        database = db




# Define the Message model
class Message(peewee.Model):
    message_id = peewee.PrimaryKeyField()
    conversation_id = peewee.ForeignKeyField(Conversation, backref='messages')
    sender_id = peewee.ForeignKeyField(User) #keep track who sent it
    recipient_id = peewee.ForeignKeyField(User) # Keep track who recieved it   
    message_text = peewee.CharField(max_length=255)
    voice_message = peewee.BlobField(null=True)
    timestamp = peewee.DateTimeField(default=datetime.datetime.utcnow)
    is_read  = peewee.BooleanField(default=False)

    class Meta:
        database = db
            
class GroupMessage(peewee.Model):
    group_message_id = peewee.PrimaryKeyField()
    group_conversation_id = peewee.ForeignKeyField(Conversation, backref="group_messages")
    sender_id = peewee.ForeignKeyField(User)
    message_text = peewee.CharField(max_length=255)
    voice_message = peewee.BlobField(null=True)
    timestamp = peewee.DateTimeField()
    is_read  = peewee.BooleanField(default=False)

    class Meta:
        database = db

class Group(peewee.Model):
    group_name = peewee.CharField(max_length="50")
    group_id = peewee.PrimaryKeyField()
    conversation_id = peewee.ForeignKeyField(Conversation, backref='group')
    admin = peewee.ForeignKeyField(User, backref='admin_of')
    members_length = peewee.IntegerField()


    class Meta:
        database = db


#Model defined to know blocked relationship


 
