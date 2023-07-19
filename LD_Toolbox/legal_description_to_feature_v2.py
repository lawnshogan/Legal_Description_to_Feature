'''
Module to support toolbox

Code assumes Python >=v3.6 and that it is an ArcGIS Pro environment
'''
import os
import csv
from datetime import datetime as dt
import logging
import numpy as np
import pandas as pd
import string
from typing import List, Union, Tuple

import arcpy

import config as cfg
import ld_parser

#<<<<<<<<<<<<<<<     >>>>>>>>>>>>>>>

IS_GCS_DEV = True

if IS_GCS_DEV:
    # Original - EXCEL_INPUT = r'D:\Projects\CSLB\data\GIS_Lease_Update_big_test.xlsx'
    # Original - WORKING_GDB = r'D:\ArcGIS_Projects\CSLB-LegalDesc\CSLB-LegalDesc.gdb'
    # Original - GIS_LAYER = r'D:\ArcGIS_Projects\CSLB-LegalDesc\CSLB-LegalDesc.gdb\SLB_Lease_SchemaFC'
    # Original - REPORT_FOLDER = r'D:\Projects\CSLB\temp'
    EXCEL_INPUT = r'C:\Users\logans1\Legal_Description_to_Feature\Netsuite_Active_Leases'
    WORKING_GDB = r'C:\Users\logans1\Legal_Description_to_Feature\Monthly Lease Update.gdb'
    GIS_LAYER = r'C:\Users\logans1\Legal_Description_to_Feature\Monthly Lease Update.gdb\Sample_Test_7_3_2023'
    REPORT_FOLDER = r'C:\Users\logans1\Legal_Description_to_Feature\temp'

FIRST_DIV = 'First_Div'
SECOND_DIV = 'Second_Div'

#<<<<<<<<<<<<<<<     >>>>>>>>>>>>>>>
class DualLogger:
    '''
    Logs to both arcpy and to python log file, using the
    three levels arcpy allows (vs five for python logging)
    '''
    def __init__(self, out_folder:str, log_name:str, log_level:str='INFO', plain_format:bool = False, arcpy_msg:bool = True):
        self.out_folder = out_folder
        self.log_name = log_name
        self.log_level = log_level
        self.plain_format = plain_format
        self.arcpy_msg = arcpy_msg

        if self.log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError(f'Unknown log level entered: {self.log_level}')

        self._log = self._get_logger(self.log_name, self.out_folder, self.log_level, self.plain_format)

    def __str__(self):
        return f'out_folder: {self.out_folder}; log_name: {self.log_name}; log_level: {self.log_level}'

    def _get_logger(self, log_name:str, folder:str, log_level:str, plain_format:bool) -> logging.Logger:
        ''' Setup for logging across modules and functions '''
        logger = logging.getLogger(log_name)
        logger.setLevel('DEBUG') # Setting baseline level of the overall logger

        time_stamp = dt.now().strftime('%Y%m%d_%H%M')
        log_file = os.path.join(folder, f"{time_stamp}_{log_name}.log")

        file_handler = logging.FileHandler(filename=log_file)
        if plain_format:
            file_format = logging.Formatter('%(message)s')
        else:
            file_format = logging.Formatter('%(asctime)s [%(levelname)s] %(filename)s.%(funcName)s(%(lineno)d) : %(message)s')
        file_handler.setFormatter(file_format)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)

        return logger

    def debug(self, msg:str) -> None:
        ''' Log debug message, log file only'''
        self._log.debug(msg)

    def info(self, msg:str) -> None:
        ''' Log info message'''
        self._log.info(msg)
        if self.arcpy_msg:
            arcpy.AddMessage(msg)

    def warning(self, msg:str) -> None:
        ''' Log warning message'''
        self._log.warning(msg)
        if self.arcpy_msg:
            arcpy.AddWarning(msg)

    def error(self, msg:str) -> None:
        ''' Log a error message'''
        self._log.error(msg)
        if self.arcpy_msg:
            arcpy.AddError(msg)

    def critcal(self, msg:str) -> None:
        ''' Log a critical message; error level in arcpy'''
        self._log.critical(msg)
        if self.arcpy_msg:
            arcpy.AddError(msg)


def get_excel_data(excel_file:str) -> pd.DataFrame:
    '''
    Get the lease data from the Excel file
    '''
    if os.path.exists(excel_file):
        excel_data = pd.read_excel(excel_file)
    else:
        raise FileNotFoundError('Unable to find lease data Excel file')

    for field_name, data_type in cfg.EXCEL_DATATYPES.items():
        if data_type == 'Timestamp':
            excel_data[field_name] = excel_data[field_name].apply(lambda x: x.date())
        else:
            excel_data[field_name] = excel_data[field_name].astype(data_type)

    excel_data = excel_data.replace({np.nan:None})

    return excel_data


def _check_lease_update_data(data_df:pd.DataFrame) -> Tuple[pd.DataFrame, List[list]]:
    '''
    Check the data file records to make sure each transaction
    has consistent data. Send mismatches to the error output.
    '''
    error_records = []
    excel_keys = list(data_df[cfg.DISSOLVE_FIELD].unique())

    for key in excel_keys:
        records_to_check = data_df.loc[data_df[cfg.DISSOLVE_FIELD] == key]

        valid_update = True
        mismatched_fields = []
        for field in cfg.UPDATE_FIELDS:
            field_values = list(records_to_check[field].unique())
            if len(field_values) > 1:
                valid_update = False
                mismatched_fields.append(field)

        if not valid_update:
            record_list = records_to_check.values
            record_list = record_list.tolist()
            for record in record_list:
                record.append(f'Fields mismatch: {mismatched_fields}')
                error_records.append(record)
                error_log.info(record)
            data_df = data_df.loc[data_df[cfg.DISSOLVE_FIELD] != key]

    return (data_df, error_records)


def get_table_field_objects(tbl_name:str) -> List[arcpy.Field]:
    '''
    Provides a list of field objects for the table, less geometry/gdb
    related fields. Table name needs to be either full path or
    name within context of the workspace.
    '''
    field_list = arcpy.ListFields(tbl_name)
    field_list = [field_obj for field_obj in field_list if field_obj.type not in ['Geometry','GlobalID', 'OID', 'Guid']]
    field_list = [field_obj for field_obj in field_list if field_obj.name.lower() not in ['shape_length','shape_area', 'shape']]

    return field_list


def insert_new_data(target_lyr:str, source_feature_lyr:str, source_data:dict) -> None:
    '''
    Merges the data from the PLSS dissolve layer current gis layer data
    '''
    # Hard setting the Transactio field in the gis layer
    insert_fields = [] #['Transactio'] #<< Dropping the field
    insert_fields.extend(list(cfg.FIELD_MAPPING.values()))
    insert_fields.append('SHAPE@')

    with arcpy.da.InsertCursor(target_lyr, insert_fields) as insert_cursor:
        for key, data_values in source_data.items():
            # Hard setting the Transactio field in the gis layer
            insert_row = [] # ['Lease'] #<< Dropping the default value
            insert_row.extend(data_values[:])
            query = f"{cfg.FIELD_MAPPING[cfg.DISSOLVE_FIELD]} = '{key}'"
            with arcpy.da.SearchCursor(source_feature_lyr, 'SHAPE@', query) as source_cursor:
                for source_row in source_cursor:
                    insert_row.append(source_row[0])
                    insert_cursor.insertRow(insert_row)


def get_meridian(meridian_num:Union[int, str]) -> str:
    '''
    Normalize the meridian number.
    '''
    if meridian_num is None:
        raise ValueError('Empty value value in meridian number')

    meridian = str(meridian_num)

    if not meridian.isdigit():
        raise ValueError('Improper value in meridian number')
    elif len(meridian) > 2:
        raise ValueError('Meridian greater than two digits presented. Unable to process.')

    if len(meridian) == 1:
        meridian = "0" + meridian

    return meridian


def get_township(township_field:str) -> str:
    '''
    Normalize the township number
    '''
    if township_field is None or not isinstance(township_field, str):
        raise ValueError('Non-string value presented in township data')
    elif len(township_field) == 0:
        raise ValueError('Empty string presented in township data')

    test_string = township_field.lower()
    test_string = test_string.replace(' ', '')

    if 'n' not in test_string and 's' not in test_string:
        raise ValueError('No directional value provided in township data')

    if 'n' in test_string:
        township_direction = 'N'
        test_string = test_string.replace('n', '')
    else:
        township_direction = 'S'
        test_string = test_string.replace('s', '')

    if '.5' in test_string:
        township_fraction = '2'
        test_string = test_string.replace('.5', '')
    else:
        township_fraction = '0'

    if not test_string.isdigit():
        raise ValueError('Unknown characters in township data')

    padding = 3 - len(test_string)
    township_num = '0' * padding
    township_num = township_num + test_string

    # format of ID: NNNFD
        # NNN 3 digits, starting with zero
        # F fractional - either 0, 2
        # D directional - either N or S

    township_id = township_num + township_fraction + township_direction

    return township_id


def get_range(range_field:str) -> str:
    '''
    Normalize the range number
    '''
    if range_field is None or not isinstance(range_field, str):
        raise ValueError('Non-string value presented in range data')
    elif len(range_field) == 0:
        raise ValueError('Empty string presented in reange data')

    test_string = range_field.lower()
    test_string = test_string.replace(' ', '')

    if 'e' not in test_string and 'w' not in test_string:
        raise ValueError('No directional value provided in range data')

    if 'e' in test_string:
        range_direction = 'E'
        test_string = test_string.replace('e', '')
    else:
        range_direction = 'W'
        test_string = test_string.replace('w', '')

    if '.5' in test_string:
        range_fraction = '2'
        test_string = test_string.replace('.5', '')
    else:
        range_fraction = '0'

    if not test_string.isdigit():
        raise ValueError('Unknown characters in range data')

    padding = 3 - len(test_string)
    range_num = '0' * padding
    range_num = range_num + test_string

    # format of ID: NNNFD
        # NNN 3 digits, starting with zero
        # F fractional - either 0, 2
        # D directional - either N or S

    range_id = range_num + range_fraction + range_direction

    return range_id


def get_section(section_num:Union[int, str]) -> str:
    '''
    Normalize the section number. Can accept either
    string or integer input
    '''
    if section_num is None:
        raise ValueError('Empty value value in section number')

    section = str(section_num)

    if not section.isdigit():
        raise ValueError('Unable to resolve section number to a digit')
    elif len(section) > 2:
        raise ValueError('Section greater than two digits presented. Unable to process.')

    if len(section) == 1:
        section = "0" + section

    return section


def write_error_file(error_records:List[list], field_names:list, output_folder:str) -> None:
    '''
    Write the error records out to a csv file
    '''
    time_stamp = dt.now().strftime('%Y%m%d_%H%M')
    audit_file_name = f'{cfg.AUDIT_FILE_NAME}_{time_stamp}.csv'
    audit_file = os.path.join(output_folder, audit_file_name)

    with open(audit_file, 'w', encoding='UTF-8', newline ='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(field_names)
        writer.writerows(error_records)


def check_first_div(data_to_check:pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    '''
    Parse the PLSS first div entry out of the data in the dataframe.
    Return an updated data frame with a First_Div column added. Post
    any records that will not parse to the error log. Also return a
    list of these error records.
    '''
    error_records = []
    index_to_drop = []
    updated_df = data_to_check.assign(First_Div = None, ErrorMsg = '')

    for index, data_row in updated_df.iterrows():
        error_msg = ''
        try:
            meridian_num = get_meridian(data_row['Meridian'])
        except ValueError as err:
            error_msg = f'{error_msg}; {str(err)}'

        try:
            township_num = get_township(data_row['Township'])
        except ValueError as err:
            error_msg = f'{error_msg}; {str(err)}'

        try:
            range_num = get_range(data_row['Range'])
        except ValueError as err:
            error_msg = f'{error_msg}; {str(err)}'

        try:
            section_num = get_section(data_row['Section#'])
        except ValueError as err:
            error_msg = f'{error_msg}; {str(err)}'

        if len(error_msg) > 0:
            error_msg = error_msg[2:] # remove leading '; '
            updated_df.at[index, ['ErrorMsg']] = (error_msg)
            index_to_drop.append(index)

        else:
            first_div = f'CO{meridian_num}{township_num}{range_num}0SN{section_num}0'
            updated_df.at[index, [FIRST_DIV]] = (first_div)

    if len(index_to_drop) > 0:
        error_df = updated_df.loc[updated_df['ErrorMsg'] != '']
        # error_df.drop(columns=FIRST_DIV, inplace=True)
        error_df = error_df.drop(columns=FIRST_DIV)
        error_records = error_df.values.tolist()

        updated_df.drop(index_to_drop, inplace=True)

    updated_df.drop(columns='ErrorMsg', inplace=True)

    return updated_df, error_records


def check_second_div(data_to_check:pd.DataFrame) -> Tuple[dict, list, list]:
    '''
    Check the second div entries and compile list for PLSS check and audit
    report
    '''
    index_to_drop = []
    index_of_warnings = []

    data_records = data_to_check.to_dict('index')

    for index, data_record in data_records.items():
        if data_record['Legal Description'] is None or len(data_record['Legal Description']) == 0:
            data_record[SECOND_DIV] = ['ALL']
        else:
            try:
                results_2nd_div = ld_parser.get_2nd_div(data_record['Legal Description'])
            except ValueError as results_err:
                data_record['ErrorMsg'] = str(results_err)
                index_to_drop.append(index)
            else:
                data_record[SECOND_DIV] = results_2nd_div['lookups']
                warning_msg = ''
                if len(results_2nd_div['fractionals']) > 0:
                    warning_msg = f"{warning_msg}; Review these fractionals not processed: {results_2nd_div['fractionals']}"
                if len(results_2nd_div['fall_outs']) > 0:
                    warning_msg = f"{warning_msg}; Review these remnants not processed: {results_2nd_div['fall_outs']}"
                if len(warning_msg) > 0:
                    warning_msg = f'AUDIT ONLY: {warning_msg[2:]}' # removed leading '; '
                    warning_msg = f"{warning_msg} >> First_Div value: {data_record[FIRST_DIV]} Second_Div value(s): {results_2nd_div['lookups']}"
                    data_record['WarningMsg'] = warning_msg
                    index_of_warnings.append(index)

    return (data_records, index_to_drop, index_of_warnings)


def get_2nd_div_error_records(err_type:str, records:dict, col_names:list) -> list:
    '''
    Parse out the records that have error or warning messages. Reorder data
    to match original data attribute sequence.
    '''
    if err_type not in ['WarningMsg', 'ErrorMsg']:
        raise KeyError(f'Unknown error type presented: {err_type}')

    records_with_errors = []

    second_div_warnings = {index:value for index, value in records.items() if value.get(err_type)}

    for data_record in second_div_warnings.values():
        error_record = [data_record.get(key, None) for key in col_names]
        error_record.append(data_record[err_type])
        records_with_errors.append(error_record)

    return records_with_errors


def get_plss_features(output_lyr_name:str, output_gdb:str, template_lyr:str, data_records:dict) -> Tuple[str, list]:
    '''
    Get the PLSS features for the given data record
    Return the path to the temp PLSS feature layer and a list
    of error records
    '''
    error_records = []
    reverse_lookup = {value:key for key, value in cfg.FIELD_MAPPING.items()}
    insert_fields = list(cfg.FIELD_MAPPING.values())
    insert_fields.append('SHAPE@')

    temp_plss_lyr = os.path.join(output_gdb, output_lyr_name)

    if arcpy.Exists(temp_plss_lyr):
        arcpy.Delete_management(temp_plss_lyr)

    arcpy.CreateFeatureclass_management(
        out_path=output_gdb,
        out_name=output_lyr_name,
        geometry_type='POLYGON',
        template=template_lyr
        )

    total_records = len(data_records)
    log.info(f'{total_records} to check for PLSS')

    with arcpy.da.InsertCursor(temp_plss_lyr, insert_fields) as plss_insert:
        for record_count, data_record in enumerate(data_records,1):
            insert_count = 0

            first_div_value = data_record[FIRST_DIV]
            if data_record[SECOND_DIV][0] == 'ALL':
                plss_query = f"FRSTDIVID = '{first_div_value}'"
            elif len(data_record[SECOND_DIV]) == 1:
                plss_query = f"FRSTDIVID = '{first_div_value}' AND SECDIVNO = '{data_record[SECOND_DIV][0]}'"
            else:
                second_div_tuple = tuple(data_record[SECOND_DIV])
                plss_query = f"FRSTDIVID = '{first_div_value}' AND SECDIVNO IN {second_div_tuple}"

            try:
                with arcpy.da.SearchCursor(cfg.PLSS, 'SHAPE@', plss_query) as plss_cursor:
                    for plss_row in plss_cursor:
                        new_row = [data_record[reverse_lookup[field]] for field in insert_fields[:-1]] # trap for missing key?
                        new_row.append(plss_row[0])

                        plss_insert.insertRow(new_row)
                        insert_count += 1
            except RuntimeError as run_err:
                err_msg = f"Runtime error. Transaction number: {data_record['Transaction Number']} ERROR: {run_err}"
                log.error(err_msg)
                error_record = [value for key, value in data_record.items() if key not in [FIRST_DIV, SECOND_DIV]]
                error_record.append(err_msg)
                error_records.append(error_record)

                # TODO make that 2nd div list a set somewhere as I am seeing duplicate elements

            if insert_count == 0:
                err_msg = f"No PLSS records found for query: {plss_query}"
                log.error(f"{err_msg} Transaction number: {data_record['Transaction Number']}")
                error_record = [value for key, value in data_record.items() if key not in [FIRST_DIV, SECOND_DIV]]
                error_record.append(err_msg)
                error_records.append(error_record)

            if record_count % 1000 == 0:
                log.info(f'{record_count} of {total_records} processed by PLSS check')

    return temp_plss_lyr, error_records


def get_dissolve_fc(plss_lyr:str, target_gdb:str ) -> str:
    '''
    Dissolve the PLSS features into one record per
    '''
    dissolve_name = "temp_Dissolve_lyr"
    dissolve_fc = os.path.join(target_gdb, dissolve_name)

    if arcpy.Exists(dissolve_fc):
        arcpy.Delete_management(dissolve_fc)

    arcpy.PairwiseDissolve_analysis(
        in_features = plss_lyr,
        out_feature_class = dissolve_fc,
        dissolve_field = cfg.FIELD_MAPPING[cfg.DISSOLVE_FIELD]
    )

    return dissolve_fc


def consolidate_new_data(records_to_check:dict, acres_index:int) -> dict:
    '''
    Consolidate the data down to one record per key, summing the acres
    '''
    #TODO Issue: In test data, potentially different Legal Description, TRS for multiple records. What gets put into GIS Layer?

    keys_to_add = []
    data_to_insert = {}

    for data_record in records_to_check.values():
        key_field_value = data_record[cfg.DISSOLVE_FIELD]
        if key_field_value not in keys_to_add:
            keys_to_add.append(key_field_value)
            insert_data = [data_record[field_name] for field_name in cfg.FIELD_MAPPING]
            data_to_insert[key_field_value] = insert_data
        else:
            data_to_insert[key_field_value][acres_index] = add_acres(data_to_insert[key_field_value][acres_index], data_record[cfg.ACRES_FIELD])

    return data_to_insert


def add_acres(x:Union[float, None], y:Union[float, None]) -> Union[float, None]:
    '''
    Add the acres up, taking into account None values
    '''
    if x is None and y is None:
        return None
    elif x is None:
        return y
    elif y is None:
        return x
    else:
        return float(x) + float(y)


def check_acres(original_data:pd.DataFrame, data_to_insert:dict, new_records:dict, acres_index:int) -> list:
    '''
    Check the consolidated acres after the 2nd Div and PLSS processing against the
    original data import. If any records were dropped due to errors, it will be
    flagged here
    '''
    error_records = []
    col_names = original_data.columns.to_list()
    for key, data_values in data_to_insert.items():
        total_original_acres = original_data.loc[original_data[cfg.DISSOLVE_FIELD] == key, cfg.ACRES_FIELD].sum()
        if total_original_acres != data_values[acres_index]:
            warning_msg = f'WARNING: Acres mismatch on {key}. Original:{total_original_acres} Insert: {data_values[acres_index]}'

            # Need to get the data in a consistent order, so going back to this source
            for data_record in new_records.values():
                if data_record[cfg.DISSOLVE_FIELD] == key:
                    error_record = [data_value for data_key, data_value in data_record.items() if data_key in col_names]
                    break

            error_record.append(warning_msg)
            error_records.append(error_record)

    return error_records


def main(excel_file, output_gdb, gis_layer, output_folder):
    '''
    Create new lease layer combination of Excel data and PLSS
    polygons
    '''
    if not arcpy.Exists(gis_layer):
        log.error(f'Cannot find the target GIS layer {gis_layer}')
        return

    if not os.path.exists(excel_file):
        log.error('Cannot find Excel file for lease input. Correct and rerun script.')
        return

    if not os.path.exists(output_folder):
        log.error(f'Cannot locate report folder for output: {output_folder}')
        return

    if not arcpy.Exists(cfg.PLSS):
        log.error(f'Cannot locate PLSS layer: {cfg.PLSS}')
        return

    if not arcpy.Exists(output_gdb):
        log.error(f'Cannot locate output GDB: {output_gdb}')
        return

    arcpy.env.workspace = output_gdb
    arcpy.overwriteOutputs = True
    arcpy.env.overwriteOutput = True
    spatial_ref = arcpy.Describe(gis_layer).spatialReference
    arcpy.env.outputCoordinateSystem = spatial_ref

    error_file_entries = []

    log.info('Getting excel data')
    lease_data_df = get_excel_data(excel_file)
    excel_col_names = lease_data_df.columns.to_list()

    log.info('Checking the Excel data for errors')
    lease_data_df, error_file_entries = _check_lease_update_data(lease_data_df)
    log.info(f'{len(error_file_entries)} records removed from the Excel data. See error file.')

    log.info('Checking for updates and adds to GIS layer')
    gis_lyr_keys = set(row[0] for row in arcpy.da.SearchCursor(gis_layer, cfg.FIELD_MAPPING[cfg.DISSOLVE_FIELD]))

    records_to_update_df = lease_data_df[lease_data_df[cfg.DISSOLVE_FIELD].isin(gis_lyr_keys)]
    records_to_add_df = lease_data_df[~lease_data_df[cfg.DISSOLVE_FIELD].isin(gis_lyr_keys)]

    log.debug(f'{records_to_update_df.shape[0]} possible update records')
    log.debug(f'{records_to_add_df.shape[0]} possible records to add')

    log.info('Processing updates...')
    records_to_update_df = records_to_update_df.drop_duplicates()
    gis_fields = [cfg.FIELD_MAPPING[field] for field in cfg.FIELD_MAPPING if field in cfg.UPDATE_FIELDS]

    update_fields = [cfg.DISSOLVE_FIELD]
    update_fields.extend(cfg.UPDATE_FIELDS)
    update_values_only_df = records_to_update_df[update_fields]

    log.info('Applying updates against GIS data')
    record_count = 0
    for data_row in update_values_only_df.itertuples(index=False):
        data_to_update = list(data_row)

        query = f"{cfg.FIELD_MAPPING[cfg.DISSOLVE_FIELD]} = '{data_to_update[0]}'"
        with arcpy.da.UpdateCursor(gis_layer, gis_fields, query) as update_cursor:
            for gis_row in update_cursor:
                record_count += 1
                update_cursor.updateRow(data_to_update[1:])

    log.info(f'{record_count} records updated in GIS layer')

    log.info('Processing new additions...')
    new_records_df, error_records = check_first_div(records_to_add_df)
    error_file_entries.extend(error_records)

    log.info(f'{len(error_records)} errors found in First Division check')
    for record in error_records:
        error_log.info(record)

    new_records, index_to_drop, index_of_warnings = check_second_div(new_records_df)

    error_records = []
    if len(index_to_drop) > 0:
        error_records = get_2nd_div_error_records('ErrorMsg', new_records, excel_col_names)
        error_file_entries.extend(error_records)

        # new_records = {index:value for index, value in new_records.items() if value.get('ErrorMsg') is not None}
        new_records = {index:value for index, value in new_records.items() if value.get('ErrorMsg') is None}

    log.info(f'{len(error_records)} errors found in Second Division check')
    for record in error_records:
        error_log.info(record)

    error_records = []
    if len(index_of_warnings) > 0:
        error_records = get_2nd_div_error_records('WarningMsg', new_records, excel_col_names)
        error_file_entries.extend(error_records)

        for index, value in new_records.items():
            new_records[index] = {key:data_record for key, data_record in value.items() if key != 'WarningMsg'}

    log.info(f'{len(error_records)} records with audit data to review in Second Division check')
    for record in error_records:
        error_log.info(record)

    if len(new_records) > 0:
        log.info('Getting PLSS features for the additional records')
        plss_features_lyr_name = 'temp_PLSS_features'

        plss_features_lyr, error_records = get_plss_features(plss_features_lyr_name,
                                                                output_gdb,
                                                                template_lyr=gis_layer,
                                                                data_records=new_records.values())

        log.info(f'{len(error_records)} errors occured in the PLSS lookup')
        error_file_entries.extend(error_records)

        log.info(f'Performing dissolve of PLSS features using {cfg.DISSOLVE_FIELD} field')
        dissolve_fc = get_dissolve_fc(plss_features_lyr, output_gdb)

        acres_index = list(cfg.FIELD_MAPPING.keys()).index(cfg.ACRES_FIELD)

        log.info('Consolidating the attribute data from new records to get total acres')
        data_to_insert = consolidate_new_data(new_records, acres_index)

        error_records = check_acres(lease_data_df, data_to_insert, new_records, acres_index)
        error_file_entries.extend(error_records)
        for error_msg in error_records:
            log.info(error_msg)
            error_log.info(error_msg)

        log.info('Merging data into gis layer')
        insert_new_data(gis_layer, dissolve_fc, data_to_insert)

    else:
        log.info('No new records now available to be added')

    log.info('Creating CSV file of error records')
    field_names = excel_col_names[:]
    field_names.append('Error/Audit Messages')
    write_error_file(error_file_entries, field_names, output_folder)

    log.info('Processing completed')


#<<<<<<<<<<<<<<<     >>>>>>>>>>>>>>>
log = DualLogger(cfg.LOG_FILE_FOLDER, cfg.LOG_FILE_NAME, 'DEBUG')
error_log = DualLogger(cfg.LOG_FILE_FOLDER, cfg.AUDIT_FILE_NAME, 'INFO', plain_format=True, arcpy_msg=False)

if __name__ == '__main__':

    log.info('Starting legal description feature layer script')

    if IS_GCS_DEV:
        main(EXCEL_INPUT, WORKING_GDB, GIS_LAYER, REPORT_FOLDER)
    else:
        raise RuntimeError('Need to either run from toolbox or define dev variables')

    log.info('Script completed')
