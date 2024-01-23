import os
from vanna.openai.openai_chat import OpenAI_Chat
from vanna.marqo.marqo import Marqo_VectorStore
#from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore

class MyVanna(Marqo_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        #ChromaDB_VectorStore.__init__(self, config=config)
        Marqo_VectorStore.__init__(self, config={'marqo_url': 'http://marqo:8882'})
        OpenAI_Chat.__init__(self, config=config)

vn = MyVanna(config={'api_key': os.environ['OPENAI_API_KEY'], 'model': 'gpt-4'})


vn.connect_to_postgres(
    host=os.environ['POSTGRES_HOST'], 
    dbname=os.environ['POSTGRES_DBNAME'], 
    user=os.environ['POSTGRES_USER'], 
    password=os.environ['POSTGRES_PASSWORD'], 
    port=os.environ['POSTGRES_PORT']
)


# The information schema query may need some tweaking depending on your database. This is a good starting point.
df_information_schema = vn.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE table_schema='public'")

# This will break up the information schema into bite-sized chunks that can be referenced by the LLM
plan = vn.get_training_plan_generic(df_information_schema)

#print(plan)

# If you like the plan, then uncomment this and run it to train
vn.train(plan=plan)

# Sometimes you may want to add documentation about your business terminology or definitions.
vn.train(documentation="This database belongs to a system called SEAD, which is an acronym for the Strategic Environmental Archaeology Database. The base unit is the archeological site, found in tbl_sites. Each site have sample groups (tbl_sample_groups) associated with it. Each sample group contains one or many samples, here called physical samples (tbl_physical_samples). Each sample may have one or many analysis entities (tbl_analysis_entities) connected to it. Each analysis entity is connected to a dataset (tbl_datasets), which acts as a grouping for analysis entities. Analysis entities are like an abstract form of datapoint which may be connected to actual data in other tables, e.g. tbl_measured_values, among others.")

# You can also add SQL queries to your training data. This is useful if you have some queries already laying around. You can just copy and paste those from your editor to begin generating new SQL.
#vn.train(sql="SELECT * FROM my-table WHERE name = 'John Doe'")

vn.train(sql="""SELECT * FROM
public.tbl_sites
JOIN tbl_sample_groups ON tbl_sample_groups.site_id=tbl_sites.site_id
JOIN tbl_physical_samples ON tbl_physical_samples.sample_group_id=tbl_sample_groups.sample_group_id
JOIN tbl_analysis_entities ON tbl_analysis_entities.physical_sample_id=tbl_physical_samples.physical_sample_id
JOIN tbl_datasets ON tbl_datasets.dataset_id=tbl_analysis_entities.dataset_id
JOIN tbl_methods ON tbl_methods.method_id=tbl_datasets.method_id
WHERE tbl_sites.site_id=1 AND method_name='Magnetic susceptibility'""")
         

