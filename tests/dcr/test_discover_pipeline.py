from test_setup import SetUpOCDCRTest, RESULTS_DIR

import os

from ocpa.objects.log.importer.ocel import factory as ocel_import_factory

from ocpa.algo.discovery.oc_dcr.util import DiscoverData

from ocpa.objects.oc_dcr_graph import OCDCRGraph, OCDCRRelation

from ocpa.algo.discovery.oc_dcr import apply as discover_apply


class TestDiscoverPipeline(SetUpOCDCRTest):

    def test_pipeline_runs_and_returns_ocdcr(self):
        data = DiscoverData(
            ocel=self.ocel,
            spawn_mapping=self.spawn_mapping,
            activities_mapping=self.activities_mapping,
            derived_entities=self.derived_entities
        )

        try:
            result = discover_apply(
                ocel=data.ocel,
                spawn_mapping=data.spawn_mapping,
                activities_mapping=data.activities_mapping,
                derived_entities=data.derived_entities
            )
            self.assertIsInstance(result, OCDCRGraph)

            # Basic checks
            activities = [e.activity for e in result.get_events()]
            self.assertGreaterEqual(len(activities), 5)
            self.assertIn("Create Order", activities)
            self.assertIn("Link Item to Order", activities)
            self.assertIn("Ship Order", activities)
            self.assertIn("Accept", activities)

            import ocpa.visualization.oc_dcr_vis as dcr_viz

            viz = dcr_viz.apply(result)
            dcr_viz.save(viz, "testtttt.png")

            # Sync relation presence
            self.assertGreater(len(result.sync_relations), 0)

            # Validate one-to-many quantifiers on sync relations
            for rel in result.sync_relations:
                self.assertIsInstance(rel, OCDCRRelation)
                quant_head, quant_tail = rel.get_quantifiers()
                self.assertTrue(
                    quant_head or quant_tail,
                    f"Expected at least one quantifier in relation: {rel}"
                )

        except Exception as e:
            self.fail(f"discover.apply pipeline raised an exception: {e}")

    def test_discover_apply_pipeline_runs_on_empty_closures(self):

        self.data.ocel = ocel_import_factory.apply(
            os.path.join(RESULTS_DIR, "jsonocel/test_log_edge_case_no_closures.jsonocel")
        )
        data = DiscoverData(
            ocel=self.data.ocel,
            spawn_mapping=self.data.spawn_mapping,
            activities_mapping=self.data.activities_mapping,
            derived_entities=self.data.derived_entities
        )

        try:
            graph = discover_apply(
                ocel=data.ocel,
                spawn_mapping=data.spawn_mapping,
                activities_mapping=data.activities_mapping,
                derived_entities=data.derived_entities
            )
            self.assertIsInstance(graph, OCDCRGraph)
        except Exception as e:
            self.fail(f"discover.apply raised an exception on empty closures: '{e}'")