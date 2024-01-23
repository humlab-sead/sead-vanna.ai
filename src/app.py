import os
import vanna
from vanna.remote import VannaDefault
from vanna.flask import VannaFlaskApp

api_key = os.environ['VANNA_API_KEY']

vanna_model_name = os.environ['VANNA_MODEL']
vn = VannaDefault(model=vanna_model_name, api_key=api_key)

vn.connect_to_postgres(
    host=os.environ['POSTGRES_HOST'], 
    dbname=os.environ['POSTGRES_DBNAME'], 
    user=os.environ['POSTGRES_USER'], 
    password=os.environ['POSTGRES_PASSWORD'], 
    port=os.environ['POSTGRES_PORT']
)

#print(vn.ask(question="What is the name of the site with id 1?"))

app = VannaFlaskApp(vn)
app.run()