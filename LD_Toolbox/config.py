'''
Configured values to use the script outside the Pro toolbox
environment
'''
#<<<<<<<<<<<<<<< Environment specific required values  >>>>>>>>>>>>>>>
# Enter the full path to the PLSS feature class being used.
PLSS = r'D:\ArcGIS_Projects\CSLB-LegalDesc\BLM_CO_PLSS_Intersected_Survey_Grid.gdb\BLM_Colorado_PLSS_Intersected___Survey_Grid'

# Setup for the log file and audit file
# Original - LOG_FILE_FOLDER = r'D:\Projects\CSLB\logs'
LOG_FILE_FOLDER = r'C:\Users\logans1\Legal_Description_to_Feature\logs'
LOG_FILE_NAME = 'Lease_Updates'
AUDIT_FILE_NAME = 'PLSS_Audit_Records'


#<<<<<<<<<<<<<<< Following items are not environment specific and usually do not need updates >>>>>>>>>>>>>>>

# Field to use to match and dissolve the PLSS polygons. This should match the column name in the Excel file.
DISSOLVE_FIELD = 'Transaction Number'
ACRES_FIELD = 'Acreage'

# Mapping of the Excel column headings to the attribute names in the GIS layer
# WARNING: Some of these keys are hard coded in the script. Check before updating.
FIELD_MAPPING = {
    'Lease Type': 'Lease_Type',
    'Lease Subtype': 'Lease_Subt',
    'Transaction Number': 'Transact_1',
    'Lessee(s)': 'Lessee_Nam',
    'Legacy Lease Number': 'Legacy_Lea',
    'Start Date (Letter Merge)': 'Lease_Star',
    'End Date (Letter Merge)': 'Lease_End_',
    'Internal ID': 'ns_int_id',
    'Lease Terms (Years)': 'Lease_Term',
    'Administrator': 'Administra',
    'District': 'District',
    'Lease Status': 'Lease_Stat',
    'Meridian': 'Meridian',
    'Township': 'Township',
    'Range': 'Range',
    'Section#': 'Section',
    'Legal Description': 'GIS_Legal',
    'Acreage': 'Acreage'
    }

# Required for the data import. Update if the Excel columns change (name or mix)
# Only needed for exceptions, not every field. Use 'Timestamp' for date and/or
# time fields, panda data types for others.
EXCEL_DATATYPES = {
    # 'Section#': "Int64",
    'Start Date (Letter Merge)': 'Timestamp',
    'End Date (Letter Merge)': 'Timestamp',
}

UPDATE_FIELDS = [
    'Lease Type',
    'Lease Subtype',
    'Lessee(s)',
    'Legacy Lease Number',
    'Start Date (Letter Merge)',
    'End Date (Letter Merge)',
    'Internal ID',
    'Lease Terms (Years)',
    'Administrator',
    'District'
    ]




#<<<<<<<<<<<<<<<     >>>>>>>>>>>>>>>
# Possible PLSS source if needed
# https://gis.blm.gov/coarcgis/rest/services/cadastral/BLM_CO_PLSS/MapServer
# https://gbp-blm-egis.hub.arcgis.com/search?categories=cadastral&groupIds=97bb25da078444d4a04669405f77643b

# Cadastral
# https://data.colorado.gov/Local-Aggregation/Statewide-Aggregate-Parcels-in-Colorado-2022-Publi/izys-vycy
