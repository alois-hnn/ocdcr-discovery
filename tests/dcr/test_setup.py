import os
import warnings
warnings.simplefilter("ignore")

from datetime import datetime
from typing import List, Dict, Union

from ocpa.objects.log.importer.ocel import factory as ocel_import_factory

import unittest
import polars as pl
from ocpa.algo.discovery.oc_dcr.util import DiscoverData
from ocpa.objects.oc_dcr_graph import IN_TOP_GRAPH

RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../sample_logs/'))

class SetUpOCDCRTest(unittest.TestCase):
    def setUp(self):
        self.ocel = ocel_import_factory.apply(os.path.join(RESULTS_DIR, "jsonocel/test_log.jsonocel"))
        self.spawn_mapping = {
            "Order": "Create Order",
            "Item": "Add Item"
        }
        self.activities_mapping = {
            "Link Item to Order": "Item",
            "Ship Order": "Order",
            "Accept": IN_TOP_GRAPH
        }
        self.derived_entities = [("Item", "Order")]

        self.data = DiscoverData(
            ocel=self.ocel,
            spawn_mapping=self.spawn_mapping,
            activities_mapping=self.activities_mapping,
            derived_entities=self.derived_entities
        )

    EventRow = Dict[str, Union[str, datetime]]
    ExpectedRows = List[EventRow]

    def help_test_eventlog(self,expected_rows: ExpectedRows,actual_df: pl.DataFrame):
        expected_df = pl.DataFrame(expected_rows).with_columns([
            pl.col("time:timestamp").cast(pl.Datetime)
        ]).sort(["case:concept:name", "time:timestamp"])

        actual_df = actual_df.with_columns([
            pl.col("time:timestamp").cast(pl.Datetime)
        ]).sort(["case:concept:name", "time:timestamp"])

        self.assertEqual(actual_df.shape, expected_df.shape, "DataFrame shape mismatch")
        self.assertEqual(
            actual_df.shape, expected_df.shape,
            "Mismatch in number of rows/columns"
        )
        for row_actual, row_expected in zip(actual_df.iter_rows(named=True), expected_df.iter_rows(named=True)):
            self.assertEqual(row_actual, row_expected, f"Row mismatch: {row_actual} != {row_expected}")