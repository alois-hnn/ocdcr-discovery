from ocpa.algo.discovery.oc_dcr.util import DiscoverData, InitialDiscovery, DiscoverLogic, ManyToManyDiscovery, GraphOptimizations, UnspawnedObjHandler

import logging

from ocpa.objects.log.ocel import OCEL
from typing import Dict, List, Set, Tuple

import time

from ocpa.objects.oc_dcr_graph import OCDCRGraph


class Discover:
    """
    Orchestrator for the OC-DCR discovery process.

    Entry point for:
    - Preprocessing input data.
    - Running the discovery pipeline from event logs to an OCDCRGraph.
    - Configuring optional features like nesting or derived entity analysis.

    This class manages logic, validation and optimization components.
    """
    def __init__(self, ocel: OCEL, spawn_mapping: Dict[str, str], activities_mapping: Dict[str, str], apply_nested : bool,
                 derived_entities: List[Tuple[str,str]] = None):
        """
        Initializes the Discover class with the given OCEL event log and activity/object mappings.

        :param ocel: The Object-Centric Event Log.
        :param spawn_mapping: Mapping from object type to the activity that spawns instances of this type.
        :param activities_mapping: Mapping from activity name to object type it belongs to.
        :param derived_entities: list of derived entity tuples, default none -> all entities are conisdered derived
        give empty list in order to mark that there are no derived entities
        """

        self.__data = DiscoverData(ocel, spawn_mapping, activities_mapping,derived_entities)
        self.__logic = DiscoverLogic(self.__data)
        self.__nested = apply_nested

    @property
    def data(self):
        return self.__data

    @property
    def logic(self):
        return self.__logic

    def apply(self) -> OCDCRGraph:
        """
        Executes the full OC-DCR discovery algorithm in three main phases:

        Phase 1 (Initial Discovery):
        - Extract object-specific traces from the OCEL log.
        - Apply the DisCoveR algorithm to derive a base DCR graph.
        - Translate this DCR graph into an Object-Centric DCR structure, including spawning logic
          and per-object subgraphs.

        Phase 2 (Many-to-Many Synchronization Discovery):
        - Identify transitive closures in the object graph to build merged traces across related objects.
        - Discover many-to-many constraints: synchronizing conditions, responses and excludes.

        Phase 3 (Optimization):
        - Optional: create nested subgraphs
        - Optimize the resulting graph
        - Filter the many to many syncs, that are not between derived entities

        :return: An OCDCRGraph representing the discovered object-centric declarative process model.
        """
        logger = logging.getLogger(__name__)

        start_time = time.time()
        logger.info("Starting OC-DCR discovery process.")

        # === HANDLE UNSPAWNED OBJECTS BEFORE DISCOVERY ===
        unspawned_handler = UnspawnedObjHandler(self.data)
        unspawned_handler.create_unspawned_obj_activity_map()
        unspawned_handler.handle_input_mapping()

        first_part = InitialDiscovery(self.data)

        # Step 1
        step_start = time.time()
        logger.info("Step 1: Extracting object-specific traces.")
        log = first_part.extract_object_traces()
        logger.info(f"Step 1 completed in {time.time() - step_start:.2f} seconds.")

        # Step 2
        step_start = time.time()
        logger.info("Step 2: Applying DisCoveR to derive base DCR graph.")
        mined_dcr_graph = first_part.apply_dcr_discover(log)
        logger.info(f"Step 2 completed in {time.time() - step_start:.2f} seconds.")

        # handles edge case when activites aren't included in the abstracted event log
        mined_dcr_graph= first_part.handle_activities_with_zero_constraints(mined_dcr_graph)

        # Step 3
        step_start = time.time()
        logger.info("Step 3: Translating base DCR into OC-DCR structure.")
        oc_dcr = first_part.translate_to_basic_ocgraph_structure(mined_dcr_graph)
        logger.info(f"Step 3 completed in {time.time() - step_start:.2f} seconds.")

        second_part = ManyToManyDiscovery(self.data)

        # Step 4
        step_start = time.time()
        logger.info("Step 4: Identifying transitive closures for many-to-many relationships.")
        log_many_to_many_synchro = second_part.log_from_closures()
        logger.info(f"Step 4 completed in {time.time() - step_start:.2f} seconds.")

        if log_many_to_many_synchro is not None:
            # Step 5a
            step_start = time.time()
            logger.info("Step 5a: Adding many-to-many exclude relations.")
            oc_dcr = second_part.add_many_to_many_excludes(log_many_to_many_synchro, oc_dcr)
            logger.info(f"Step 5a completed in {time.time() - step_start:.2f} seconds.")

            # Step 5b
            step_start = time.time()
            logger.info("Step 5b: Finding synchronizing conditions and responses.")
            oc_dcr = second_part.find_conditions_responses(log_many_to_many_synchro, oc_dcr)
            logger.info(f"Step 5b completed in {time.time() - step_start:.2f} seconds.")

        # handling unspawned objects
        step_start = time.time()
        logger.info("Grouping unspawned objects.")
        # group all unspawned activities belonging to the same object together to ocdcr object
        unspawned_handler.group_unspawned_obj_activities(oc_dcr)
        logger.info(f"Completed in {time.time() - step_start:.2f} seconds.")

        # Nesting Optimization
        if self.__nested:
            step_start = time.time()
            logger.info("Creating nesting for subgraphs.")
            oc_dcr = GraphOptimizations.create_nestings_for_subgraphs(oc_dcr)
            logger.info(f"Nesting completed in {time.time() - step_start:.2f} seconds.")

        # Final Optimizations
        step_start = time.time()
        logger.info("Final Optimization: Optimizing relations.")
        oc_dcr = GraphOptimizations.optimize_relations(oc_dcr)
        logger.info(f"Relation optimization completed in {time.time() - step_start:.2f} seconds.")

        
        step_start = time.time()
        logging.info("Final Optimization: Filtering derived entities.")
        oc_dcr = GraphOptimizations.filter_for_derived_entitiy(self.data, oc_dcr)
        logger.info(f"Entity filtering completed in {time.time() - step_start:.2f} seconds.")

        total_time = time.time() - start_time
        logger.info(f"OC-DCR discovery completed in {total_time:.2f} seconds.")

        return oc_dcr