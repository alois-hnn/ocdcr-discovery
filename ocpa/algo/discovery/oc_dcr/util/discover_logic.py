from pm4py.objects.log.obj import Event
import pandas as pd
from typing import Dict, List, Set, Tuple
import ocpa.algo.discovery.oc_dcr.discover.dcr_discovery as dis

import networkx as nx
import polars as pl
from itertools import combinations
from collections import defaultdict

#from jupyter.oc_dcr_graph_discovery import object_types
from ocpa.objects.oc_dcr_graph import OCDCRGraph, DCRGraph, Event, OCDCRRelation, RelationTyps, DCRRelation, \
    OCDCRObject, IN_TOP_GRAPH
from . import SPAWN
from .graph_optimizations import GraphOptimizations
from .discover_data import DiscoverData

class DiscoverLogic:
    """
    Core logic component providing basic functionalities for the discovery process needed for both the initial discovery and the many to many discovery.
    """
    def __init__(self, data: DiscoverData):
        """
        Initializes discover logic with the provided DiscoverData instance.

        :param data: The DiscoverData object containing mappings and configuration
        """
        self.__data = data
        # cache for correlation
        self._corelation_cache: Dict[str ,Set[str]] = {} # activty : Set[obj_types]

    @property
    def data(self) -> DiscoverData:
        return self.__data

    def get_correlated_obj_types(self, activity: str) -> Set[str]:
        """
        get a list of all object types an activity correlates to
        :param activity: the activity as str
        :return: set of all correlated object types
        """
        if activity in self._corelation_cache.keys():
            return self._corelation_cache[activity]

        ocel = self.data.ocel
        ot_set = set()
        all_types = set(ocel.object_types)

        for eid in ocel.obj.act_events.get(activity, []):
            ot_set.update(ocel.obj.raw.objects[oid].type for oid in ocel.obj.eve_objects[eid])
            if ot_set == all_types:
                break

        self._corelation_cache[activity] = ot_set
        return ot_set

    def are_related_activities(self, activity1: Event |str, activity2: Event |str) -> bool:
        """
        Checks whether the two activties have at least one common element

        :param activity1 (str): the first activity
        :param activity2 (str): the second activity
        :return: True if the two activties have at least one common element, False otherwise
        """
        if isinstance(activity1, Event):
            activity1 = activity1.activity
        if isinstance(activity2, Event):
            activity2 = activity2.activity

        activity1_corr = self.get_correlated_obj_types(activity1)
        activity2_corr = self.get_correlated_obj_types(activity2)
        return not activity1_corr.isdisjoint(activity2_corr)

    def _is_spawned_activity(self, object_id: str, activity: str) -> bool:
        """
        Checks whether the activity is a spawned activity of object type's subgraph

        :param object_id (str):  the object type to check
        :param activity (str): the activity to check
        :return: True if the activity is a spawned activity of object type's subgraph, False otherwise
        """
        object_type = self.data.ocel.obj.raw.objects[object_id].type
        return self.data.is_spawned_obj(object_type) and object_type == self.data.get_activity_mapping(activity)

    @staticmethod
    def apply_dcr_discover(log: pd.DataFrame) -> DCRGraph:
        """
        Applies the DisCoveR miner to generate a DCR graph from the provided event log.

        :param log: A pandas DataFrame representing the event log.
        :return: A mined DCRGraph.
        """
        mined_dcr_graph = dis.apply(log=log.to_pandas())
        return mined_dcr_graph



class InitialDiscovery(DiscoverLogic):
    """
    Implements the initial step of the OCDisCoveR algorithm as described in Definition 8 of the paper
    'Discovery of Object-Centric Declarative Models'. This class is responsible for constructing the basic
    object-centric DCR structure from mined DCR graphs using the following steps:

    1. Extract one-to-many relations with appropriate quantifiers.
    2. Detect and separate spawn-related activities.
    3. Construct subgraphs for each object type based on activity mappings.
    4. Filter and add appropriate relations within each subgraph.
    5. Combine these into an OCDCRGraph that includes both the top-level process and object-specific subgraphs.

    """

    def __init__(self, data: DiscoverData):
        super().__init__(data)
        # space for intermediate values for demonstration purposes

    # For each entity type we extract the directly follows path for that entity into an event log
    def extract_object_traces(self) -> pd.DataFrame:
        """
        For each object type in the OCEL log, this method constructs an event log by collecting the directly-follows
        paths of each object instance (OID) and then unites the per object type logs.

        :return: A combined polars DataFrame representing the flattened event log per object.
        """
        logs_per_obj_type = []
        for object_type in self.data.ocel.object_types:
            data = list()
            # For each object type, iterate over all object instances (OIDs)
            for oid in self.data.ocel.obj.ot_objects[object_type]:
                # Retrieve all events related to this object (already sorted by timestamp)
                for event in self.data.ocel.obj.sequence[oid]:
                    # Build a row for the event log, with object ID as the trace identifier
                    data.append({
                        "case:concept:name": oid,  # trace is just for debugging
                        "concept:name": event.act,
                        "time:timestamp": event.time
                    })
            logs_per_obj_type.append(pl.DataFrame(data))
        return pl.concat(logs_per_obj_type)

    def handle_activities_with_zero_constraints(self,dcr: DCRGraph) -> DCRGraph:
        """
        Ensures that all activities from the input OCEL are present in the mined DCR graph,
        even if they are not associated with any object and thus were excluded from the
        abstracted event log during the extraction process.

        This function adds any missing activities as events to the DCR graph, without
        introducing any constraints. This guarantees that every activity from the input
        mapping is represented in the final DCR model.

        Args:
            dcr (DCRGraph): The dynamic condition response graph to be updated.

        Returns:
            DCRGraph: The updated DCRGraph with all required activities included as events.
        """
        for activity in self.data.get_activities():
            if Event(activity) not in dcr.events:
                dcr.add_event(activity)
        return dcr


    def _indentify_one_to_many_quantifiers(self, relation: DCRRelation) -> OCDCRRelation:
        """
          Adds one-to-many quantifier flags to relations where applicable based on subgraph origin.

        :param relation: The relation to annotate.
        :return: Annotated OCDCRRelation with quantifiers.
        """
        if self.data.is_from_subgraph(relation.start_event):
            relation = OCDCRRelation(relation.start_event, relation.target_event, relation.type, True, False)
        elif self.data.is_from_subgraph(relation.target_event):
            relation = OCDCRRelation(relation.start_event, relation.target_event, relation.type, False, True)
        return relation

    def _create_one_to_many_relation(self, mined_dcr: DCRGraph, oc_dcr: OCDCRGraph) -> Tuple[OCDCRGraph, DCRGraph]:
        """
        Moves non-spawn activities to top-level OC-DCR and annotates related constraints.

        :param mined_dcr: Flat DCRGraph to extract from.
        :param oc_dcr: Partially built OC-DCR graph.
        :return: Tuple with updated OC-DCR graph and reduced mined DCRGraph.
        """
        temp_top_level = [e for e in mined_dcr.events if self.data.is_no_spawn_in_top_level(e)]

        for event in temp_top_level:
            incidental_relations = mined_dcr.get_incidental_relations(event)
            marking = mined_dcr.marking.get_event_marking(event)

            mined_dcr.remove_event(event)
            oc_dcr.add_event(activity=event, marking=marking)


            oc_dcr.relations.update(
                self._indentify_one_to_many_quantifiers(rel) for rel in incidental_relations
            )

        return oc_dcr, mined_dcr

    def _is_relation_between_spawn_spawned(self, relation: DCRRelation) -> bool:
        """
        Determines if a relation connects a spawn activity with its spawned subgraph event.

        :param relation: The relation to check.
        :return: True if relation is between a spawn and its spawned activity.
        """
        # spawn to subgraph
        if self.data.is_spawn_activity(relation.start_event) and self.data.is_from_subgraph(relation.target_event):
            spawn = relation.start_event
            sub = relation.target_event
        # subgraph to spawn
        elif self.data.is_spawn_activity(relation.target_event) and self.data.is_from_subgraph(
                relation.start_event):
            sub = relation.start_event
            spawn = relation.target_event
        else:
            return False
        # checks whether the subgraph activity is a spawned activity of the spawn activity
        return spawn.activity == self.data.get_spawn_mapping(self.data.get_activity_mapping(sub.activity))

    def _get_one_to_many_spawn(self, spawn_events: List[Event], mined_dcr: DCRGraph) -> Set[DCRRelation]:
        """
        Retrieves one-to-many relations for all spawn events, filtering out direct spawn→subgraph links.

        :param spawn_events: List of events that trigger spawning of new objects.
        :param mined_dcr: Original mined DCRGraph before subgraph partitioning.
        :return: A set of relations (as OCDCRRelations) relevant for top-level to subgraph communication.
        """
        return {
            self._indentify_one_to_many_quantifiers(relation)
            for event in spawn_events
            for relation in mined_dcr.get_incidental_relations(event)
            if not self._is_relation_between_spawn_spawned(relation)
        }

    def _build_subgraphs_from_dcr(self, mined_dcr: DCRGraph) -> Dict[str, DCRGraph]:
        """
        Builds separate DCR subgraphs for each object type by partitioning activities and relations
        based on the activity-to-object mapping.

        :param mined_dcr: The input DCRGraph with all discovered activities and relations.
        :return: Dictionary mapping object type → DCRGraph.
        """

        # initialize mapping
        object_type_dcrs: Dict[str, DCRGraph] = {
            object_type: DCRGraph()
            for object_type in self.data.get_spawn_obj_types()
        }

        # adds every event to it's corresponding subgraph
        for event in mined_dcr.events:
            marking = mined_dcr.marking.get_event_marking(event)
            object_type_dcrs[self.data.get_activity_mapping(event.activity)].add_event(event, marking)

        return object_type_dcrs

    def _filter_relations(self, object_type_dcrs: Dict[str, DCRGraph], dcr_graph: DCRGraph) -> Dict[str, DCRGraph]:
        """
        Filters and redistributes relations in a DCRGraph into corresponding subgraphs (object_type_dcrs)
        based on activity mappings. Only includes relations where both the start and target activities
        map to the same object type.

        Args:
            object_type_dcrs (Dict[str, DCRGraph]): Dictionary mapping object types to their respective DCR subgraphs.
            dcr_graph (DCRGraph): The full DCRGraph containing all relations.

        Returns:
            Dict[str, DCRGraph]: Updated dictionary of object-specific DCRGraphs with filtered relations added.
        """
        for relation in dcr_graph.relations:
            # Determine the object types associated with the start and target activities
            start_type = self.data.get_activity_mapping(relation.start_event.activity)
            target_type = self.data.get_activity_mapping(relation.target_event.activity)
            # include the relation if both activities are mapped to the same object type
            if start_type == target_type:
                object_type_dcrs[target_type].add_relation(
                    start_event=relation.start_event,
                    target_event=relation.target_event,
                    relation_type=relation.type
                )
        return object_type_dcrs


    def _add_objects_to_ocdcr(self, object_type_dcrs: Dict[str, DCRGraph], oc_dcr: OCDCRGraph) -> OCDCRGraph:
        """
        Adds each object type subgraph to the OC-DCR structure.

        :param object_type_dcrs: Object-specific DCR subgraphs.
        :param oc_dcr: OC-DCR graph under construction.
        :return: Updated OC-DCR graph with object models.
        """
        for object_type, graph in object_type_dcrs.items():
            spawn_event = Event(self.data.get_spawn_mapping(object_type))
            oc_dcr.add_object(OCDCRObject(
                type=object_type,
                dcr=graph,
                spawn=spawn_event
            ))
        return oc_dcr

    def _filter_top_level_relations_synchros(self, oc_dcr: OCDCRGraph) -> OCDCRGraph:
        """
        Filters top-level relations, keeping only those with shared object type relations

        :param oc_dcr: OC-DCR graph with candidate top-level relations.
        :return: Filtered OC-DCR graph.
        """
        # filters all incidental relations for top level activites if the start/target activities have at least one
        # common related obj type
        oc_dcr.relations = set([
            relation for relation in oc_dcr.relations
            if self.are_related_activities(relation.start_event.activity, relation.target_event.activity)
        ])
        return oc_dcr

    def _get_spawn_events(self, dcr: DCRGraph) -> List[Event]:
        """
        Gets list of all spawn events in the mined dcr graph

        :param dcr: A DCRGraph mined from DisCoveR
        :return: Filtered OC-DCR graph.
        """
        return [e for e in dcr.events if self.data.is_spawn_activity(e)]

    def _add_spawn_events_to_oc_dcr(self, oc_dcr: OCDCRGraph, mined_dcr: DCRGraph, events: List[Event]) -> Tuple[OCDCRGraph,DCRGraph]:
        """
        Adds spawn events to top-level OC-DCR and removes them from mined DCR.

        :param oc_dcr: OC-DCR graph being built.
        :param mined_dcr: Original mined DCR graph.
        :param events: List of spawn events.
        :return: Tuple of updated OC-DCR and reduced DCR graph.
        """
        for e in events:
            oc_dcr.add_event(e, marking=mined_dcr.marking.get_event_marking(e))
            mined_dcr.remove_event(e)
        return oc_dcr,mined_dcr

    # definition 8
    def translate_to_basic_ocgraph_structure(self, mined_dcr_graph: DCRGraph) -> OCDCRGraph:
        """
        Converts the mined DCR graph into a basic OC-DCR structure by adding activities
        and relations into top-level and object-type-specific subgraphs, based on the activity-to-object mapping.

        Steps:
        1. Separate top-level to spawned activities relations and add as one to many.
        2. Identify spawn events and separate one-to-many relations that are not between spawn event and its spawned activities.
        3. Split the remaining graph into subgraphs per object type.
        4. Filter relations within the same object to corresponding subgraphs.
        5. Build the final OC-DCR structure with all discovered objects and their subgraphs.

        :param mined_dcr_graph: A DCRGraph mined from DisCoveR.
        :return: An OCDCRGraph representing the basic object-centric model.
        """
        oc_dcr = OCDCRGraph()

        # extract all one to many realations and add their quantifiers
        oc_dcr, mined_dcr_graph = self._create_one_to_many_relation(mined_dcr_graph, oc_dcr)

        spawn_events = self._get_spawn_events(mined_dcr_graph)

        # extract all one to many constraints incidental with spawn activities
        one_to_many_spawn = self._get_one_to_many_spawn(spawn_events, mined_dcr_graph)

        # remove spawns from dcr and add the spawn activities to the oc dcr
        for event in spawn_events:
            marking = mined_dcr_graph.marking.get_event_marking(event)
            oc_dcr.add_event(event, marking=marking)
            mined_dcr_graph.remove_event(event)

        # add the one to many relations related to spawn events to the ocdcr graph
        oc_dcr.relations.update(one_to_many_spawn)

        # split the mined dcr graph into subgraphs per object type
        object_type_dcrs = self._build_subgraphs_from_dcr(mined_dcr_graph)

        # Filter out cross-object-type relations
        object_type_dcrs = self._filter_relations(object_type_dcrs, mined_dcr_graph)

        # Add each object type and its subgraph into the OC-DCR structure
        oc_dcr = self._add_objects_to_ocdcr(object_type_dcrs, oc_dcr)

        # Remove top-level relations that are not correlated to at least one shared object type
        oc_dcr = self._filter_top_level_relations_synchros(oc_dcr)

        return oc_dcr


class ManyToManyDiscovery(DiscoverLogic):
    """
    Discovers synchronization constraints between different object types -> many-to-many constraints
    """

    def __init__(self, data: DiscoverData):
        super().__init__(data)
        # space for intermediate values for demonstration porposes

    # definition 9
    # adds for all objects that are related according to def 9 a edge between them in a networkx graph
    def compute_transitive_closure(self):
        """
        Computes the transitive closure of the entity graph based on shared event participation.

        Objects are considered connected if they participate in the same event. This function constructs
        an undirected graph where nodes are object IDs and edges indicate co-occurrence in at least one event.
        Then, connected components are identified, each representing a closure of related objects.

        :return: A list of sets, where each set contains object IDs belonging to one transitive closure, is empty if
        there are no closures in the ocel
        """
        graph = nx.Graph()
        events = self.data.ocel.obj.raw.events

        for event in events.values():
            related_objects = set(event.omap)
            if len(related_objects) >= 2:
                graph.add_edges_from(combinations(related_objects, 2))

        return list(nx.connected_components(graph))

    def _resolve_object_id(self, event, activity: str) -> str:
        for object_id in event.omap:
            obj_type = self.data.ocel.obj.raw.objects[object_id].type
            mapping = self.data.get_activity_mapping(activity)
            if mapping == SPAWN and self.data.is_activity_spawn_of_obj(activity, obj_type):
                return object_id
            if obj_type == mapping:
                return object_id
        return event.omap[0] if event.omap else IN_TOP_GRAPH

    # definition 10
    def _flattening_of_ekg(self, transitive_closure: List[Set[str]]) -> pl.DataFrame | None:
        """
        Generates a flattened event log from transitive closures of related objects.
        Each trace is constructed from all events linked to the closure's objects, filtered by spawned activity type.

        This enables mining of synchronizing conditions/responses across related object instances.

        :param transitive_closure: A list of sets, each representing a closure of related objects.
        :return: A pandas DataFrame log where each trace corresponds to one closure.
        """
        # case that the transitive closure is empty --> there are no related objects --> no sync relations
        if not transitive_closure:
            return None

        log_data = []
        get_events = self.data.ocel.obj.raw.events
        get_mapping = self.data.ocel.obj.raw.obj_event_mapping

        for idx, closure in enumerate(transitive_closure):
            seen_eids = set()
            for object_id in closure:
                for eid in get_mapping.get(object_id, []):
                    if eid in seen_eids:
                        continue
                    seen_eids.add(eid)
                    event = get_events[eid]
                    oid = self._resolve_object_id(event, event.act)
                    log_data.append({
                        "case:concept:name": f"closure_{idx}",
                        "concept:name": event.act,
                        "time:timestamp": event.time,
                        "object_id": oid
                    })

        log_df = pl.DataFrame(log_data)
        log_df = log_df.sort(["case:concept:name", "time:timestamp", "object_id"])
        return log_df

    def log_from_closures(self) -> pd.DataFrame:
        """
        Generates traces from transitive object closures to enable detection of many-to-many synchronizations.

        :return: A pandas DataFrame log derived from transitive closures.
        """
        transitive_closure = self.compute_transitive_closure()
        return self._flattening_of_ekg(transitive_closure)

    def get_synchronisation_constraints(self, log: pd.DataFrame, oc_dcr: OCDCRGraph) -> OCDCRGraph:
        """
        Adds many-to-many synchronization constraints to the OC-DCR graph by:
        1. Discovering exclude relations from a log built from object closures.
        2. Discovering synchronizing condition and response relations.

        Args:
            log (pd.DataFrame): Flattened event log where each trace is a transitive closure of related objects.
            oc_dcr (OCDCRGraph): The current OC-DCR graph to add the synchronization constraints to.

        Returns:
            OCDCRGraph: Updated OC-DCR graph including many-to-many exclude, condition, and response constraints.
        """
        # Add exclude constraints
        oc_dcr = self.add_many_to_many_excludes(log, oc_dcr)
        # Add condition and response constraints
        self.find_conditions_responses(log ,oc_dcr)
        return oc_dcr

    def add_many_to_many_excludes(self, log: pl.DataFrame, oc_dcr: OCDCRGraph) -> OCDCRGraph:
        """
        Discovers and adds many-to-many exclude constraints between activities.
        Args:
            log (pl.DataFrame): The transitive closure event log used to mine synchronization constraints.
            oc_dcr (OCDCRGraph): The OC-DCR graph to which the exclude constraints will be added.

        Returns:
            OCDCRGraph: The updated OC-DCR graph with exclude constraints.
        """
        # Mine DCR graph from the closure-based log
        synchronisation_constraints = DiscoverLogic.apply_dcr_discover(log)

        # Get the exclude constraints
        excludes = {k for k in synchronisation_constraints.relations if k.type == RelationTyps.E}

        # Add excludes by applying partition on the ocdcr
        oc_dcr.partition(excludes)

        return oc_dcr

    def _to_relations(self, relations: Dict[str, Set[str]], rel_type: RelationTyps, oc_dcr: OCDCRGraph) -> Set[OCDCRRelation]:
        """
        Converts a dictionary of event relations into OCDCRRelations with quantifiers.

        Handles two cases differently:
        - For conditions (C): Relations are stored as {target: {sources}}
        - For responses (R): Relations are stored as {source: {targets}}

        Args:
            relations: Dictionary mapping:
                    - For conditions: {target_activity: {source_activities}}
                    - For responses: {source_activity: {target_activities}}
            rel_type: The type of relation (Condition or Response)
            oc_dcr: The OCDCR graph to lookup events from

        Returns:
            Set of OCDCRRelation objects with universal quantifiers (True, True)
        """
        if rel_type == RelationTyps.C:
            # Conditions are stored as target → sources
            return {
                OCDCRRelation(
                    oc_dcr.get_event(source) ,oc_dcr.get_event(target) ,rel_type, True ,True)
                for target, sources in relations.items()
                for source in sources
            }
        else:
            # Responses are stored as source → targets
            return {
                OCDCRRelation(oc_dcr.get_event(source) ,oc_dcr.get_event(target) ,rel_type ,True ,True)
                for source, targets in relations.items()
                for target in targets
            }

    def _all_spawned_instances_in_list(self, activity: str, event_list: List[Dict], spawned_objs: Set[str]) -> bool:
        """
        Verifies if all spawned instances of an activity appear in the event list.

        This is used to check if all object instances that have spawned have performed a given activity in the trace.

        Args:
            activity: The activity name to check
            event_list: List of events as dictionaries with 'concept:name' and 'object_id'
            spawned_objs: Set of spawned object IDs

        Returns:
            True if all required (activity, object_id) pairs are present in event_list,
            False otherwise. Returns True if spawned_objs is empty.
        """
        if not spawned_objs:
            return True

        # Create lookup set of (activity, object_id) pairs from event_list
        observed_pairs = {(event["concept:name"], event["object_id"] )for event in event_list}

        # Check if all required combinations exist
        return all((activity, obj_id) in observed_pairs for obj_id in spawned_objs)

    def find_conditions_responses(self, log_many_to_many_synchro: pl.DataFrame, oc_dcr: OCDCRGraph) -> OCDCRGraph:
        """
        Discovers condition and response constraints between spawned activities.

        Processes the flattened event log to identify:
        - Conditions: Activities that must precede others across all related objects
        - Responses: Activities that must follow others across all related objects

        Args:
            log_many_to_many_synchro: Flattened event log containing closure traces
            oc_dcr: The OC-DCR graph to add discovered constraints to

        Returns:
            The updated OC-DCR graph with added condition/response constraints
        """
        # Get all unique activities and filter for spawned ones
        activities = set(log_many_to_many_synchro["concept:name"].unique())
        spawned_activities = {act for act in activities if self.data.is_from_subgraph(act)}

        # Initialize all potential constraints (all combinations of spawned activities without self-loops)
        sync_conditions = {act: spawned_activities - {act} for act in spawned_activities}
        sync_responses = {act: spawned_activities - {act} for act in spawned_activities}

        # Filter constraints by analyzing each trace
        self._process_traces(sync_conditions, sync_responses, activities, log_many_to_many_synchro)

        # Convert to OCDCR relations and filter out redundant relations based on transitivity
        sync_conditions_opt = GraphOptimizations._get_transitive_optimization(self._to_relations(sync_conditions, RelationTyps.C, oc_dcr))
        sync_responses_opt = GraphOptimizations._get_transitive_optimization(self._to_relations(sync_responses, RelationTyps.R, oc_dcr))
        # Add to graph
        oc_dcr.partition(sync_conditions_opt)
        oc_dcr.partition(sync_responses_opt)

        return oc_dcr

    def _process_traces(self ,sync_conditions: Dict[str, Set[str]] ,sync_responses: Dict[str, Set[str]], activities: Set[str] ,log: pl.DataFrame) -> None:
        """
        Processes each trace to filter condition/response constraints.

        For each event in each trace:
        - For spawned activities: Checks which constraints still hold
        - For spawn events: Tracks which objects spawned which activities

        Args:
            sync_conditions: Current potential condition constraints, modified in-place
            sync_responses: Current potential response constraints, modified in-place
            activities: Set of all activities in the log
            log: The event log data as a polars DataFrame
        """
        # Process each trace (closure of related objects)
        for trace in log.group_by("case:concept:name"):
            trace = trace[1]  # Get the DataFrame part
            events = trace.sort("time:timestamp").select(["concept:name", "object_id"]).to_dicts()
            prefix, suffix = [], events.copy()
            # Track spawned object instances per activity
            spawned_objects = {act: set() for act in activities if self.data.is_from_subgraph(act)}

            while suffix:
                event = suffix.pop(0)
                activity = event["concept:name"]

                if self.data.is_from_subgraph(activity):
                    # Filter conditions - keep only those where all instances appear in prefix -> all spawned instances have performed that activity before the current one
                    sync_conditions[activity] = { act for act in sync_conditions[activity] if self._all_spawned_instances_in_list(act, prefix, spawned_objects.get(act, set()))}

                    # Filter responses - keep only those where all instances appear in suffix  -> all spawned instances will performe that activity after the current one
                    sync_responses[activity] = {act for act in sync_responses[activity] if self._all_spawned_instances_in_list( act, suffix, spawned_objects.get(act, set()))}

                elif activity in self.data.spawn_mapping.values():
                    # Track spawned activities for this object instance
                    self._track_spawned_activities(activity, event, spawned_objects)

                prefix.append(event)

    def _track_spawned_activities(self, spawn_activity: str, event: Dict, spawned_objects: Dict[str, Set[str]]) -> None:
        """
        Records which activities are spawned by each object instance.

        Args:
            spawn_activity: The spawning activity name
            event: The event dictionary containing object_id
            spawned_objects: Dictionary tracking spawned activities per object
        """
        # Get object type for this spawn activity
        obj_type = next(obj for obj, act in self.data.spawn_mapping.items() if act == spawn_activity)

        # Verify the event's object matches the spawn type
        if obj_type == self.data.ocel.obj.raw.objects[event["object_id"]].type:
            # Record all activities spawned by this object instance
            for activity in self.data.get_spawned_activities_of_obj(obj_type):
                spawned_objects[activity].add(event["object_id"])

