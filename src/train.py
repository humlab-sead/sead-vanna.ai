import os
import vanna
from vanna.remote import VannaDefault
import pandas as pd

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

def delete_all_training_data():
    print("Deleting all training data")
    training_data = vn.get_training_data()
    df = pd.DataFrame(training_data)
    for index, row in df.iterrows():
        print(row['id'])
        vn.remove_training_data(row['id'])

def train_on_auto_generated_plan():
    print("Training on auto-generated plan")
    # The information schema query may need some tweaking depending on your database. This is a good starting point.
    df_information_schema = vn.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE table_schema='public'")

    # This will break up the information schema into bite-sized chunks that can be referenced by the LLM
    plan = vn.get_training_plan_generic(df_information_schema)
    # Train on database schema
    vn.train(plan=plan)


def train_on_documentation():
    print("Training on documentation")
    vn.train(documentation="""This database belongs to a system called SEAD, which is an acronym for the Strategic Environmental Archaeology Database. 
         The base unit is the archeological site, found in tbl_sites. 
         Each site have sample groups (tbl_sample_groups) associated with it. 
         Each sample group contains one or many samples, here called physical samples (tbl_physical_samples). 
         Each sample may have one or many analysis entities (tbl_analysis_entities) connected to it. 
         Each analysis entity is connected to a dataset (tbl_datasets), which acts as a grouping for analysis entities. 
         Analysis entities are like an abstract form of datapoint which may be connected to actual data in other tables, e.g. tbl_measured_values, among others.

         Column names should always be prefixed with the table name, e.g. tbl_sites.site_id, tbl_sample_groups.sample_group_id, etc. Even in the output of the SQL queries.
         So tbl_sites.site_id should be selected as: SELECT tbl_sites.site_id AS tbl_sites_site_id FROM tbl_sites
             
         NEVER USE SELECT * FROM any table. Always select the columns you need, e.g. SELECT tbl_sites.site_id, tbl_sites.site_name FROM tbl_sites
         """)
    vn.train(documentation="""
        
         """)

### SQL queries

def train_on_sql():
    print("Training on SQL")
    vn.train(
        question="Fetch me a list of the sites in the system", 
        sql="""
        SELECT 
            tbl_sites.site_id, 
            tbl_sites.site_name,
            MAX(tbl_locations.location_name) AS location_name -- This is one way to deal with multiple locations
        FROM tbl_sites 
        JOIN tbl_site_locations ON tbl_site_locations.site_id = tbl_sites.site_id
        LEFT JOIN tbl_locations ON tbl_locations.location_id = tbl_site_locations.location_id 
            AND tbl_locations.location_type_id = 1
        GROUP BY tbl_sites.site_id, tbl_sites.site_name
        ORDER BY site_name;
        """)

    #Select all sites which have at least one dendrochronological dataset
    vn.train(
        question="Which sites have dendrochronological data?", 
        sql="""
        SELECT DISTINCT(tbl_sites.site_id), tbl_sites.site_name, COUNT(tbl_datasets.dataset_id) AS dataset_count FROM
        public.tbl_sites
        JOIN tbl_sample_groups ON tbl_sample_groups.site_id=tbl_sites.site_id
        JOIN tbl_physical_samples ON tbl_physical_samples.sample_group_id=tbl_sample_groups.sample_group_id
        JOIN tbl_analysis_entities ON tbl_analysis_entities.physical_sample_id=tbl_physical_samples.physical_sample_id
        JOIN tbl_datasets ON tbl_datasets.dataset_id=tbl_analysis_entities.dataset_id
        JOIN tbl_methods ON tbl_methods.method_id=tbl_datasets.method_id
        WHERE method_name='Dendrochronology'
		GROUP BY tbl_sites.site_id, tbl_sites.site_name
		ORDER BY site_name
        """)

    #Select all sites in Halmstad kommun, also counts the number of datasets for each site
    vn.train(
        question="Please show me all sites in Halmstad municipality",
        sql="""
        SELECT 
        tbl_sites.site_id, 
        tbl_sites.site_name,
		COUNT(tbl_datasets.dataset_id) AS dataset_count
        FROM tbl_sites
        JOIN tbl_site_locations ON tbl_site_locations.site_id = tbl_sites.site_id
        JOIN tbl_locations ON tbl_locations.location_id = tbl_site_locations.location_id
        JOIN tbl_location_types ON tbl_location_types.location_type_id = tbl_locations.location_type_id
        JOIN tbl_sample_groups ON tbl_sample_groups.site_id = tbl_sites.site_id
        JOIN tbl_physical_samples ON tbl_physical_samples.sample_group_id = tbl_sample_groups.sample_group_id
        JOIN tbl_analysis_entities ON tbl_analysis_entities.physical_sample_id = tbl_physical_samples.physical_sample_id
		JOIN tbl_datasets ON tbl_datasets.dataset_id=tbl_analysis_entities.dataset_id
        WHERE tbl_locations.location_name = 'Halmstads kommun' 
        AND tbl_location_types.location_type = 'Sub-country administrative region'
        GROUP BY tbl_sites.site_id, tbl_sites.site_name
		ORDER BY dataset_count DESC
        """)

    vn.train(
        question="Show me all sites with references to papers from the year 1997", 
        sql="""
        SELECT DISTINCT tbl_sites.site_id, tbl_sites.site_name, tbl_biblio.year AS reference_year, tbl_biblio.title AS reference_title, tbl_biblio.authors AS reference_authors, COUNT(tbl_biblio.biblio_id) AS reference_count
        FROM public.tbl_sites
        JOIN tbl_sample_groups ON tbl_sample_groups.site_id = tbl_sites.site_id
        JOIN tbl_physical_samples ON tbl_physical_samples.sample_group_id = tbl_sample_groups.sample_group_id
        JOIN tbl_analysis_entities ON tbl_analysis_entities.physical_sample_id = tbl_physical_samples.physical_sample_id
        JOIN tbl_datasets ON tbl_datasets.dataset_id = tbl_analysis_entities.dataset_id
        JOIN tbl_biblio ON tbl_biblio.biblio_id = tbl_datasets.biblio_id
        WHERE tbl_biblio.year = '1997'
        GROUP BY tbl_sites.site_id, tbl_sites.site_name, tbl_biblio.year, reference_title, reference_authors
        ORDER BY reference_count DESC
        """)

    vn.train(
        question="What is the highest measured value for the analysis method phosphate degrees?",
        sql="""
        SELECT tbl_measured_values.measured_value, tbl_sites.site_id, tbl_sites.site_name, tbl_datasets.dataset_name FROM
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

    vn.train(
        question="Find sites associated with the bugs ecocode Aquatics",
        sql="""
        SELECT 
            site_id, 
            site_name,
            ecocode_definition_name,
            COUNT(value) AS analysis_entities
        FROM (
            SELECT 
                tbl_sites.site_id AS site_id, 
                tbl_sites.site_name AS site_name,
                tbl_ecocode_definitions.name AS ecocode_definition_name,
                tbl_analysis_entities.analysis_entity_id AS value
            FROM 
                tbl_analysis_entities
                INNER JOIN tbl_abundances ON tbl_abundances."analysis_entity_id" = tbl_analysis_entities."analysis_entity_id"
                INNER JOIN tbl_taxa_tree_master ON tbl_taxa_tree_master."taxon_id" = tbl_abundances."taxon_id"
                INNER JOIN tbl_ecocodes ON tbl_ecocodes."taxon_id" = tbl_taxa_tree_master."taxon_id"
                INNER JOIN tbl_ecocode_definitions ON tbl_ecocode_definitions."ecocode_definition_id" = tbl_ecocodes."ecocode_definition_id"
                INNER JOIN tbl_ecocode_groups ON tbl_ecocode_groups."ecocode_group_id" = tbl_ecocode_definitions."ecocode_group_id"
                INNER JOIN tbl_ecocode_systems ON tbl_ecocode_systems."ecocode_system_id" = tbl_ecocode_groups."ecocode_system_id"
                INNER JOIN tbl_datasets ON tbl_datasets."dataset_id" = tbl_analysis_entities."dataset_id"
                INNER JOIN tbl_physical_samples ON tbl_physical_samples."physical_sample_id" = tbl_analysis_entities."physical_sample_id"
                INNER JOIN tbl_sample_groups ON tbl_sample_groups."sample_group_id" = tbl_physical_samples."sample_group_id"
                INNER JOIN tbl_sites ON tbl_sites."site_id" = tbl_sample_groups."site_id"
            WHERE 
                1 = 1
                AND tbl_ecocode_systems.ecocode_system_id::text IN ('2')
                AND tbl_ecocode_definitions.ecocode_definition_id::text IN ('323')
            GROUP BY 
                tbl_sites.site_id, 
                tbl_sites.site_name,
                tbl_ecocode_definitions.name,
                tbl_analysis_entities.analysis_entity_id
        ) AS x
        GROUP BY 
            site_id, 
            site_name,
            ecocode_definition_name
        ORDER BY analysis_entities DESC
        """)
    
    vn.train(
        question="Within petrography and thin section analysis (ceramics), show me the sites which have shards taken from a church",
        sql="""
        SELECT DISTINCT 
            tbl_sites.site_id AS site_id, 
            tbl_sites.site_name AS site_name, 
            COALESCE(latitude_dd, 0.0) AS latitude_dd, 
            COALESCE(longitude_dd, 0) AS longitude_dd,
            tbl_methods.method_name
        FROM 
            tbl_sites
            INNER JOIN tbl_sample_groups ON tbl_sample_groups."site_id" = tbl_sites."site_id"
            INNER JOIN tbl_physical_samples ON tbl_physical_samples."sample_group_id" = tbl_sample_groups."sample_group_id"
            INNER JOIN tbl_analysis_entities ON tbl_analysis_entities."physical_sample_id" = tbl_physical_samples."physical_sample_id"
            INNER JOIN tbl_datasets ON tbl_datasets."dataset_id" = tbl_analysis_entities."dataset_id"
            INNER JOIN tbl_physical_sample_features ON tbl_physical_sample_features."physical_sample_id" = tbl_physical_samples."physical_sample_id"
            INNER JOIN tbl_features ON tbl_features."feature_id" = tbl_physical_sample_features."feature_id"
            INNER JOIN tbl_feature_types ON tbl_feature_types."feature_type_id" = tbl_features."feature_type_id"
            JOIN tbl_methods ON tbl_methods.method_id=tbl_datasets.method_id
        WHERE 
            1 = 1
            AND tbl_feature_types.feature_type_id::text IN ('561')
            AND tbl_datasets.method_id IN (172, 171);
        """)
    
    vn.train(
        question="Find all sites with species marked as Notable in the UKRDB system",
        sql="""
        SELECT DISTINCT
            tbl_sites.site_id AS site_id,
            tbl_sites.site_name AS site_name,
            COALESCE(latitude_dd, 0.0) AS latitude_dd,
            COALESCE(longitude_dd, 0) AS longitude_dd
        FROM
            tbl_sites
            INNER JOIN tbl_sample_groups ON tbl_sample_groups."site_id" = tbl_sites."site_id"
            INNER JOIN tbl_physical_samples ON tbl_physical_samples."sample_group_id" = tbl_sample_groups."sample_group_id"
            INNER JOIN tbl_analysis_entities ON tbl_analysis_entities."physical_sample_id" = tbl_physical_samples."physical_sample_id"
            INNER JOIN tbl_abundances ON tbl_abundances."analysis_entity_id" = tbl_analysis_entities."analysis_entity_id"
            INNER JOIN tbl_taxa_tree_master ON tbl_taxa_tree_master."taxon_id" = tbl_abundances."taxon_id"
            INNER JOIN tbl_rdb ON tbl_rdb."taxon_id" = tbl_taxa_tree_master."taxon_id"
            INNER JOIN tbl_rdb_codes ON tbl_rdb_codes."rdb_code_id" = tbl_rdb."rdb_code_id"
            INNER JOIN tbl_rdb_systems ON tbl_rdb_systems."rdb_system_id" = tbl_rdb_codes."rdb_system_id"
        WHERE
            tbl_rdb_systems.rdb_system::text IN ('UKRDB')
            AND tbl_rdb_codes.rdb_definition::text IN ('Notable');
        """)

def train_on_ddl():
    print("Training on DDL")
    #read in the ddl file
    with open('./app/sead_change_control/sead_model/deploy/SEAD_DATABASE_MODEL/tables.sql', 'r') as file:
        ddl = file.read()
        vn.train(sql=ddl)
    with open('./app/sead_change_control/sead_model/deploy/SEAD_DATABASE_MODEL/foreignkeys.sql', 'r') as file:
        ddl = file.read()
        vn.train(sql=ddl)
    with open('./app/sead_change_control/sead_model/deploy/SEAD_DATABASE_MODEL/comments.sql', 'r') as file:
        ddl = file.read()
        vn.train(sql=ddl)


delete_all_training_data()
train_on_auto_generated_plan()
train_on_ddl()
train_on_documentation()
train_on_sql()
