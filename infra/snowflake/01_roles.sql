-- Bootstrap-only role creation. Run with ACCOUNTADMIN.
USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS PHARMARETAIL_ADMIN
COMMENT = 'Project administrator for PharmaRetail AI Control Tower';

CREATE ROLE IF NOT EXISTS PHARMARETAIL_ENGINEER
COMMENT = 'Data engineering role for RAW through MARTS development';

CREATE ROLE IF NOT EXISTS PHARMARETAIL_DBT
COMMENT = 'Service role for dbt Cloud transformations in modelling schemas';

CREATE ROLE IF NOT EXISTS PHARMARETAIL_AI_APP
COMMENT = 'Runtime role for governed MARTS reads and controlled AI logging';

CREATE ROLE IF NOT EXISTS PHARMARETAIL_READONLY
COMMENT = 'Read-only consumer role restricted to curated MARTS objects';

CREATE ROLE IF NOT EXISTS PHARMARETAIL_STORE_MANAGER
COMMENT = 'Store manager persona restricted by row access policy to assigned stores';

CREATE ROLE IF NOT EXISTS PHARMARETAIL_AREA_MANAGER
COMMENT = 'Area manager persona restricted by row access policy to assigned regions';

CREATE ROLE IF NOT EXISTS PHARMARETAIL_SUPPLY_CHAIN_ANALYST
COMMENT = 'National operational analyst persona with governed MARTS access';

-- PHARMARETAIL_ADMIN inherits every project workload role, while workload roles
-- remain independent from one another to avoid unintended privilege inheritance.
GRANT ROLE PHARMARETAIL_ENGINEER TO ROLE PHARMARETAIL_ADMIN;
GRANT ROLE PHARMARETAIL_DBT TO ROLE PHARMARETAIL_ADMIN;
GRANT ROLE PHARMARETAIL_AI_APP TO ROLE PHARMARETAIL_ADMIN;
GRANT ROLE PHARMARETAIL_READONLY TO ROLE PHARMARETAIL_ADMIN;
GRANT ROLE PHARMARETAIL_STORE_MANAGER TO ROLE PHARMARETAIL_ADMIN;
GRANT ROLE PHARMARETAIL_AREA_MANAGER TO ROLE PHARMARETAIL_ADMIN;
GRANT ROLE PHARMARETAIL_SUPPLY_CHAIN_ANALYST TO ROLE PHARMARETAIL_ADMIN;

-- Integrate the project hierarchy with Snowflake's standard system-role model.
GRANT ROLE PHARMARETAIL_ADMIN TO ROLE SYSADMIN;

-- Explicitly allow the bootstrap user to switch to the daily project admin role.
GRANT ROLE PHARMARETAIL_ADMIN TO USER OMRUM;
