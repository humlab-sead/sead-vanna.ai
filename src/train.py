import os
import vanna
from vanna.remote import VannaDefault

api_key = os.environ['VANNA_API_KEY']
#api_key = vanna.get_api_key('my-email@example.com')

vanna_model_name = os.environ['VANNA_MODEL']
vn = VannaDefault(model=vanna_model_name, api_key=api_key)

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

# Train on database schema
vn.train(plan=plan)


### Free text training/instructions

# Sometimes you may want to add documentation about your business terminology or definitions.
vn.train(documentation="""This database belongs to a system called SEAD, which is an acronym for the Strategic Environmental Archaeology Database. 
         The base unit is the archeological site, found in tbl_sites. 
         Each site have sample groups (tbl_sample_groups) associated with it. 
         Each sample group contains one or many samples, here called physical samples (tbl_physical_samples). 
         Each sample may have one or many analysis entities (tbl_analysis_entities) connected to it. 
         Each analysis entity is connected to a dataset (tbl_datasets), which acts as a grouping for analysis entities. 
         Analysis entities are like an abstract form of datapoint which may be connected to actual data in other tables, e.g. tbl_measured_values, among others.
         """)

### SQL queries

#Select all sites which have at least one dendrochronological dataset
vn.train(
    question="Which sites have dendrochronological data?", 
    sql="""
    SELECT DISTINCT(tbl_sites.site_id) FROM
    public.tbl_sites
    JOIN tbl_sample_groups ON tbl_sample_groups.site_id=tbl_sites.site_id
    JOIN tbl_physical_samples ON tbl_physical_samples.sample_group_id=tbl_sample_groups.sample_group_id
    JOIN tbl_analysis_entities ON tbl_analysis_entities.physical_sample_id=tbl_physical_samples.physical_sample_id
    JOIN tbl_datasets ON tbl_datasets.dataset_id=tbl_analysis_entities.dataset_id
    JOIN tbl_methods ON tbl_methods.method_id=tbl_datasets.method_id
    WHERE method_name='Dendrochronology'
    """)

#Select all sites in Halmstad kommun
vn.train(
    question="Please show me all sites in Halmstad municipality",
    sql="""
    SELECT * FROM tbl_sites
    JOIN tbl_site_locations ON tbl_site_locations.site_id=tbl_sites.site_id
    JOIN tbl_locations ON tbl_locations.location_id=tbl_site_locations.location_id
    JOIN tbl_location_types ON tbl_location_types.location_type_id=tbl_locations.location_type_id
    WHERE tbl_locations.location_name='Halmstads kommun' AND tbl_location_types.location_type='Sub-country administrative region'
    """)

vn.train(
    question="Show me all sites with references to papers from the year 1997", 
    sql="""
    SELECT * FROM
    public.tbl_sites
    JOIN tbl_sample_groups ON tbl_sample_groups.site_id=tbl_sites.site_id
    JOIN tbl_physical_samples ON tbl_physical_samples.sample_group_id=tbl_sample_groups.sample_group_id
    JOIN tbl_analysis_entities ON tbl_analysis_entities.physical_sample_id=tbl_physical_samples.physical_sample_id
    JOIN tbl_datasets ON tbl_datasets.dataset_id=tbl_analysis_entities.dataset_id
    JOIN tbl_biblio ON tbl_biblio.biblio_id=tbl_datasets.biblio_id
    WHERE tbl_biblio.year='1997'
    """)

vn.train(
    question="What is the highest measured value for the analysis method phosphate degrees?",
    sql="""
    SELECT * FROM
    public.tbl_sites
    JOIN tbl_sample_groups ON tbl_sample_groups.site_id=tbl_sites.site_id
    JOIN tbl_physical_samples ON tbl_physical_samples.sample_group_id=tbl_sample_groups.sample_group_id
    JOIN tbl_analysis_entities ON tbl_analysis_entities.physical_sample_id=tbl_physical_samples.physical_sample_id
    JOIN tbl_datasets ON tbl_datasets.dataset_id=tbl_analysis_entities.dataset_id
    JOIN tbl_methods ON tbl_methods.method_id=tbl_datasets.method_id
	JOIN tbl_measured_values ON tbl_measured_values.analysis_entity_id=tbl_analysis_entities.analysis_entity_id
    WHERE method_name='Phosphate degrees'
	ORDER BY tbl_measured_values.measured_value::float DESC
    """)
