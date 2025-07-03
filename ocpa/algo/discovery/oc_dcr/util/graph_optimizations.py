
from typing import Dict, Set, Tuple
from ocpa.objects.oc_dcr_graph import OCDCRGraph,DCRGraph,OCDCRObject,DCRRelation, RelationTyps,IN_TOP_GRAPH

from collections import defaultdict
import networkx as nx
import ocpa.algo.discovery.oc_dcr.discover.extentions.nested as ns
from ocpa.util.dcr.converter import DCRConverter

from ocpa.algo.discovery.oc_dcr.util import DiscoverData


class GraphOptimizations:
    """
    Utility class for optimizing and simplifying DCR and OC-DCR graphs.

    Provides:
    - Structural nesting via group identification.
    - Filtering redundant constraints.

    Used after discovery process to reduce complexity.
    """

    @staticmethod
    def optimize_relations(ocdcr: OCDCRGraph) -> OCDCRGraph:
        """
        Optimizes an OCDCR graph by applying transitive reduction to:
        - The main graph relations
        - All object subgraphs
        - Synchronization relations

        Preserves include/exclude relations unchanged.

        Args:
            ocdcr: The OCDCRGraph to optimize

        Returns:
            The optimized OCDCRGraph with minimal relations
        """
        # Optimize main graph
        GraphOptimizations._optimize_main_graph(ocdcr)

        # Optimize all object subgraphs
        GraphOptimizations._optimize_object_subgraphs(ocdcr)

        # Optimize sync relations
        GraphOptimizations._optimize_sync_relations(ocdcr)

        return ocdcr

    @staticmethod
    def _optimize_main_graph(graph: DCRGraph) -> None:
        """
        Optimizes the main graph relations of an OCDCR graph.

        Args:
            graph: The DCRGraph or OCDCRGraph to optimize
        """
        type_to_relations = GraphOptimizations._group_relations_by_type(graph.relations)

        optimized_cond = GraphOptimizations._get_transitive_optimization(type_to_relations.get(RelationTyps.C, set()))
        optimized_resp = GraphOptimizations._get_transitive_optimization(type_to_relations.get(RelationTyps.R, set()))

        optimized_cond = GraphOptimizations._filter_excluded_relations(optimized_cond,type_to_relations.get(RelationTyps.E, set()))
        optimized_resp = GraphOptimizations._filter_excluded_relations(optimized_resp
                                                                       ,type_to_relations.get(RelationTyps.E, set()))

        graph.relations = optimized_cond.union(optimized_resp).union(type_to_relations.get(RelationTyps.I, set())
                                                                     ,type_to_relations.get(RelationTyps.E, set()))

    @staticmethod
    def _optimize_object_subgraphs(ocdcr: OCDCRGraph) -> None:
        """
        Optimizes all object subgraphs in an OCDCR graph.

        Args:
            ocdcr: The OCDCRGraph containing objects to optimize
        """
        for obj in ocdcr.objects.values():
            GraphOptimizations._optimize_main_graph(obj)

    @staticmethod
    def _optimize_sync_relations(ocdcr: OCDCRGraph) -> None:
        """
        Optimizes synchronization relations between objects.

        Args:
            ocdcr: The OCDCRGraph with sync relations to optimize
        """
        type_to_relations = GraphOptimizations._group_relations_by_type(ocdcr.sync_relations)

        optimized_cond = GraphOptimizations._get_transitive_optimization(type_to_relations.get(RelationTyps.C, set()))
        optimized_resp = GraphOptimizations._get_transitive_optimization(type_to_relations.get(RelationTyps.R, set()))

        optimized_cond = GraphOptimizations._filter_excluded_relations( optimized_cond, type_to_relations.get(RelationTyps.E, set()))
        optimized_resp = GraphOptimizations._filter_excluded_relations( optimized_resp
                                                                       ,type_to_relations.get(RelationTyps.E, set()))

        ocdcr.sync_relations = optimized_cond.union(optimized_resp).union(type_to_relations.get(RelationTyps.I, set())
                                                                          ,type_to_relations.get(RelationTyps.E, set()))

    @staticmethod
    def _group_relations_by_type(relations: Set[DCRRelation]) -> Dict[RelationTyps, Set[DCRRelation]]:
        """
        Groups relations by their type for efficient processing.

        Args:
            relations: Set of relations to group

        Returns:
            Dictionary mapping relation types to sets of relations
        """
        type_to_relations = defaultdict(set)
        for relation in relations:
            type_to_relations[relation.type].add(relation)
        return type_to_relations

    @staticmethod
    def _get_transitive_optimization(relations: Set[DCRRelation]) -> Set[DCRRelation]:
        """
        Performs transitive reduction on a set of relations while handling cycles.

        Args:
            relations: Set of relations to optimize

        Returns:
            Optimized set of relations with transitive dependencies removed
        """
        if not relations:
            return set()

        G = nx.DiGraph()
        relation_map = {}

        # Build graph and relation map
        for rel in relations:
            edge = (rel.start_event.activity, rel.target_event.activity)
            G.add_edge(*edge)
            relation_map[edge] = rel

        # Handle cycles -> should not appear usually, this is just for safety
        cycle_edges = set()
        # error if there is no cycle
        while not nx.is_directed_acyclic_graph(G):
            try:
                cycle = nx.find_cycle(G)
                # Store the first edge of the detected cycle
                edge_to_remove = (cycle[0][0], cycle[0][1])
                cycle_edges.add(edge_to_remove)
                G.remove_edge(*edge_to_remove)
            except nx.NetworkXNoCycle:
                break

        # Perform transitive reduction
        TR = nx.transitive_reduction(G)
        reduced_edges = set(TR.edges()).union(cycle_edges)

        return {relation_map[edge] for edge in reduced_edges if edge in relation_map}

    @staticmethod
    def _filter_excluded_relations(relations: Set[DCRRelation], excludes: Set[DCRRelation]) -> Set[DCRRelation]:
        """
        Filters out relations that have parallel exclude edges.

        Args:
            relations: Set of relations to filter
            excludes: Set of exclude relations to check against

        Returns:
            Filtered set of relations without excluded edges
        """
        if not relations or not excludes:
            return relations

        # Create set of exclude edges for fast lookup
        exclude_edges = {(rel.start_event.activity, rel.target_event.activity) for rel in excludes}

        return { rel for rel in relations if (rel.start_event.activity, rel.target_event.activity) not in exclude_edges}

    @staticmethod
    def filter_for_derived_entitiy(data: DiscoverData, oc_dcr: OCDCRGraph) -> OCDCRGraph:
        """
        Filters the OC-DCR graph to remove synchronization relations that do not occur between derived entities. If no derived entities are defined,
        it will be treated as if all entities have interesting interplay and no filtering will be applied.

        Args:
            data (DiscoverData): The data object containing mapping and configuration, including derived entities.
            oc_dcr (OCDCRGraph): The object-centric DCR graph to be filtered.

        Returns:
            OCDCRGraph: The filtered OC-DCR graph where sync relations only exist between derived entity types.
        """
        # If no derived entities are defined, skip filtering and return
        if data.derived_entities is None:
            return oc_dcr

        to_filter = set() # Will collect sync relations that should be removed

        # Iterate over all synchronization relations in the OC-DCR model
        for relation in oc_dcr.sync_relations:
            if oc_dcr.corr(relation.start_event) == IN_TOP_GRAPH or oc_dcr.corr(relation.target_event) == IN_TOP_GRAPH:
                continue
            # Get the object types associated with the start and target events of the relation
            correlated_obj_star = oc_dcr.corr(relation.start_event).type
            correlated_obj_targ = oc_dcr.corr(relation.target_event).type
            # If the two object types are not declared as derived entities, it can be removed
            if not data.are_derived_entities(correlated_obj_star ,correlated_obj_targ):
                to_filter.add(relation)
        # Remove all relations that don't connect derived entities
        oc_dcr.sync_relations.difference_update(to_filter)
        return oc_dcr

    @staticmethod
    def apply_nested(dcr_graph: DCRGraph) -> dict:
        """
        Applies nested group detection to a DCR graph.

        This transformation identifies sets of events that can be grouped based on structural patterns, reducing visual complexity and improving interpretability of large models.

        Args:
            dcr_graph (DCRGraph): A DCR graph 

        Returns:
            dict: A DCR graph template with nested event groups, if any were identified.
        """
        ## nested takes template as input
        template = DCRConverter.to_string_representation(dcr_graph)
        return ns.apply(template)


    def filter_template_relations(template: dict) -> dict:
        """
        Filters out redundant child/group-level relations in a DCR graph template where equivalent group-level relations exist, including nested groups.

        Args:
            template (dict): The template dictionary with events, nestedgroups, and relation dictionaries.

        Returns:
            dict: The template with redundant relations removed.
        """
        nested_map = template.get("nestedgroupsMap", {})
        nestedgroups = template.get("nestedgroups", {})

        # Build mapping: group → all descendants including nested levels
        group_descendants = GraphOptimizations.build_group_descendants(nestedgroups)

        # Build transitive mapping: event/group → all ancestor groups 
        reverse_ancestors = GraphOptimizations.build_reverse_ancestors(nested_map)

        # List of DCR relation types
        relation_keys = ['excludesTo', 'conditionsFor', 'responseTo', 'includesTo']

        for rel_type in relation_keys:
            # Replace each relation set with a filtered version
            template[rel_type] = GraphOptimizations.filter_relation_type(
                rel_dict=template.get(rel_type, {}),
                reverse_ancestors=reverse_ancestors,
                group_descendants=group_descendants
            )

        return template


    def build_group_descendants(nestedgroups: dict) -> dict:
        """
        Computes all descendants for each group recursively.

        Args:
            nestedgroups (dict): Maps group → direct children, can be events or subgroups

        Returns:
            dict: group → set of all transitive descendants
        """
        def get_all_descendants(group):
            visited = set()
            stack = [group]

            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                # Add direct children 
                children = nestedgroups.get(current, set())
                stack.extend(children)

            visited.remove(group)  # Exclude the group itself
            return visited

        return {group: get_all_descendants(group) for group in nestedgroups}


    def build_reverse_ancestors(nested_map: dict) -> dict:
        """
        Builds a reverse mapping of each element to its transitive group ancestors.

        Args:
            nested_map (dict): Maps element → immediate parent group

        Returns:
            dict: element → set of all ancestor groups
        """
        reverse_ancestors = defaultdict(set)

        for child, parent in nested_map.items():
            current = parent
            while current:
                reverse_ancestors[child].add(current)
                current = nested_map.get(current)  # next parent

        return reverse_ancestors


    def filter_relation_type(rel_dict: dict, reverse_ancestors: dict, group_descendants: dict) -> dict:
        """
        Removes redundant relations from a single relation dictionary by checking for implied group-level relations.

        Args:
            rel_dict (dict): relation dictionary (source → set of targets)
            reverse_ancestors (dict): Maps element → ancestor groups
            group_descendants (dict): Maps group → all descendants

        Returns:
            dict: filtered relation dictionary with redundancies removed
        """
        new_rel_dict = {}

        for source, targets in rel_dict.items():
            new_targets = set()

            for target in targets:
                # Check if this relation is redundant
                if GraphOptimizations.is_redundant_relation(source, target, rel_dict, reverse_ancestors, group_descendants):
                    continue  # Skip if redundant
                new_targets.add(target)

            if new_targets:
                new_rel_dict[source] = new_targets

        return new_rel_dict


    def is_redundant_relation(source: str,target: str,rel_dict: Dict[str, Set[str]],reverse_ancestors: Dict[str, Set[str]],group_descendants: Dict[str, Set[str]]) -> bool:
        """
        Checks whether a given relation (source → target) is redundant due to existing group-level relations.

        Redundancy is true if:
        - A parent of the source already has a relation to the target
        - The source already has a relation to a parent of the target
        - A group→group relation exists between source's and target's groups

        Args:
            source (str): The source activity
            target (str): The target activity
            rel_dict (Dict[str, Set[str]]): Dictionary representing direct relations (source → targets)
            reverse_ancestors (Dict[str, Set[str]]): Map from element to all its transitive parent groups
            group_descendants (Dict[str, Set[str]]): Map from group to all transitive descendant elements

        Returns:
            bool: True if the relation is redundant and should be removed
        """

        # Case 1: A parent of the source has a relation to the target
        for ancestor in reverse_ancestors.get(source, []):
            if ancestor in rel_dict and target in rel_dict[ancestor]:
                return True

        # Case 2: The source has a relation to a parent of the target
        for ancestor in reverse_ancestors.get(target, []):
            if source in rel_dict and ancestor in rel_dict[source]:
                return True

        # Case 3: Group-to-group relation exists, and this is a descendant-to-descendant duplicate
        for source_group, source_descs in group_descendants.items():
            if source in source_descs:
                for target_group, target_descs in group_descendants.items():
                    if target in target_descs:
                        if source_group in rel_dict and target_group in rel_dict[source_group]:
                            return True
        return False
    
    def get_relation_partition(relations: Set[DCRRelation]) -> Tuple[Set[DCRRelation], Set[DCRRelation]]:
        """
        Partitions a set of DCR relations into two categories:
        - sync: syncronizing relations (one to many or many to many)
        - one: relations without quantifiers (one to one)

        Args:
            relations (Set[DCRRelation]): A set of DCRRelation objects to be partitioned.

        Returns:
            Tuple[Set[DCRRelation], Set[DCRRelation]]:
                - First set contains relations with quantifiers (sync)
                - Second set contains relations without quantifiers (one)
        """
        # Initialize two sets for different types of relations
        sync = set()  # synchronizing constraints 
        one = set()   # relations without quantifiers 

        for rel in relations:
            # Check the quantifiers
            if rel.get_quantifiers() == (False, False):
                one.add(rel)
            else:
                sync.add(rel)
        return sync, one

    @staticmethod
    def create_nestings_for_subgraphs(oc_dcr: OCDCRGraph) -> OCDCRGraph:
        """
        Applies nesting activities to each subgraph in the OC-DCR model. For nesting, only the one to one relations are considered and all other relations added afterwards.
        
        1. Filter out all syncronizing relations to only apply nested with one to one relations
        2. Applies the nesting algorithm to derive a new nested DCR graph template.
        3. Filters out redundant relations caused by nesting from template.
        4. Converts template to ocdcr object.
        5. Renames group activities to include the object type (to ensure uniqueness).
        6. Preserves and reassigns relations and quantifiers from the original.
        7. Reconstructs the object in the ocdcr graph with the new nested DCR.
        
        Args:
            oc_dcr (OCDCRGraph): The OC-DCR graph containing subgraphs to be nested.

        Returns:
            OCDCRGraph: The updated OC-DCR graph with nested subgraphs.
        """
        for obj_id, dcr_obj in oc_dcr.objects.items():
            ## filter between sync relations and one to one relations
            many,one = GraphOptimizations.get_relation_partition(dcr_obj.relations)

            # apply nested only for one to one relations
            dcr_obj.relations = one

            # get the template after applying nested and filter out redundant relations
            new_dcr_template = GraphOptimizations.filter_template_relations(GraphOptimizations.apply_nested(dcr_obj.to_dcr()))

            #  Create a new OCDCRObject using the nested DCR structure
            new_obj = OCDCRObject(dcr_obj.spawn, dcr_obj.type, new_dcr_template)
            
            # Give unique group names by appending the object ID
            for group in new_obj.nested_events:
                group.activity = f"{group.activity}_{obj_id}"

            # Add relations from the existing graph if still in nested to preserve quantifiers
            for rel in list(dcr_obj.relations):  # Copy to avoid modifying while iterating
                if new_obj.get_relation(rel.start_event,rel.target_event,rel.type) is not None:
                    q_head, q_tail = rel.get_quantifiers()
                    new_obj.add_relation(rel.start_event, rel.target_event, rel.type, q_head, q_tail)

            ## add sync relations again
            for rel in many:
                q_head, q_tail = rel.get_quantifiers()
                new_obj.add_relation(rel.start_event, rel.target_event, rel.type, q_head, q_tail)
            # replace with new object
            oc_dcr.objects[obj_id] = new_obj
            oc_dcr.update_activities()

        return oc_dcr
