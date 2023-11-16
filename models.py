from peewee import *

db = SqliteDatabase('data.sqlite3')


class BaseModel(Model):
    class Meta:
        database = db
        
class User(BaseModel):
    id = BigAutoField(primary_key=True) # Це і є user_id в телеграмі
    full_name = CharField(null=True)
    balance = IntegerField(default=0)
    is_admin = BooleanField(default=False)
    
class Support(BaseModel):
    id = BigAutoField(primary_key=True)
    user = ForeignKeyField(User, backref='supports')
    admin = ForeignKeyField(User, backref='supports_admin')
    text = TextField()
    is_closed = BooleanField(default=False)
    
    
def create_tables():
    with db:
        db.create_tables([User, Support])
        


if __name__ == '__main__':
    create_tables()