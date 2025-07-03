from ocpa.objects.log.variants.table import Table
from ocpa.objects.log.variants.graph import EventGraph
import ocpa.objects.log.converter.versions.df_to_ocel as obj_converter
import ocpa.objects.log.variants.util.table as table_utils

import pandas as pd
import math
from typing import Dict
from ast import literal_eval

import warnings

warnings.filterwarnings("ignore", message="The argument 'infer_datetime_format' is deprecated")

"""
    This file is basically just a copy of the import functions implemented in OCPA with minor changes in order
    to avoid dependency conflicts
"""

# Original function in ocpa importer for csv
def to_df(filepath, parameters=None):
    if parameters is None:
        raise ValueError("Specify parsing parameters")
    df = pd.read_csv(filepath, sep=parameters["sep"])
    obj_cols = parameters['obj_names']

    def _eval(x):
        if x == 'set()':
            return []
        elif type(x) == float and math.isnan(x):
            return []
        else:
            return literal_eval(x)

    df_ocel = pd.DataFrame()

    if obj_cols:
        for c in obj_cols:
            df_ocel[c] = df[c].apply(_eval)

    df_ocel["event_id"] = [str(i) for i in range(len(df))]
    df_ocel['event_activity'] = df[parameters['act_name']]
    df_ocel['event_timestamp'] = pd.to_datetime(df[parameters['time_name']])

    df_ocel.sort_values(by='event_timestamp', inplace=True)

    if "start_timestamp" in parameters:
        df_ocel['event_start_timestamp'] = pd.to_datetime(
            df[parameters['start_timestamp']])
    else:
        df_ocel['event_start_timestamp'] = pd.to_datetime(
            df[parameters['time_name']])

    for val_name in parameters['val_names']:
        df_ocel[('event_' + val_name)] = df[parameters[val_name]]

    if 'obj_val_names' in parameters:
        for obj_val_name in parameters['val_names']:
            df_ocel[obj_val_name] = df[parameters[obj_val_name]]
    return df_ocel

def csv_to_ocel(filepath, parameters: Dict, file_path_object_attribute_table=None):
    from ocpa.objects.log.ocel import OCEL
    df = to_df(filepath, parameters)
    obj_df = None
    if file_path_object_attribute_table:
        obj_df = pd.read_csv(file_path_object_attribute_table)
    log = Table(df, parameters=parameters, object_attributes=obj_df)
    print("Table Format Successfully Imported")
    obj = obj_converter.apply(df)
    print("Object Format Successfully Imported")
    graph = EventGraph(table_utils.eog_from_log(log))
    print("Graph Format Successfully Imported")
    ocel = OCEL(log, obj, graph, parameters)
    return ocel