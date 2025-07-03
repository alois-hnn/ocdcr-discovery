"""
Basic DCR graph visualizer.
"""
from graphviz import Digraph
from typing import Set,Dict
from ocpa.objects.oc_dcr_graph import DCRRelation, DCRGraph, Event
from ocpa.visualization.oc_dcr_vis.variants.utils_viz import cluster_to_same_cluster, is_ancestor_or_self, get_edge_attrs, initialize_graph, add_events

def add_edgeDCR(relation: DCRRelation, graph: Digraph, 
                groupRelation: Dict[Event, Set[Event]]) -> None:
    """
    Add a DCR relation edge to the graph.
    
    Args:
        relation: The DCR relation to visualize
        graph: The Digraph to add to
        groupRelation: Dictionary of group memberships
    """
    source = relation.start_event
    target = relation.target_event
    
    # Get edge attributes based on relation type
    edge_attrs = get_edge_attrs(relation.type)

    # Handle edges from/to groups
    if source.isGroup and source in groupRelation and groupRelation[source]:
        edge_attrs["ltail"] = f"cluster_{source.activity}"  # Edge from group

    if target.isGroup and target in groupRelation and groupRelation[target]:
        edge_attrs["lhead"] = f"cluster_{target.activity}"  # Edge to group

    graph.edge(source.activity, target.activity, **edge_attrs)

def apply(dcr: DCRGraph, parameters: Dict = None) -> Digraph:
    """
    Main function to visualize a DCR graph.
    
    Args:
        dcr: The DCR graph to visualize
        parameters: Visualization parameters
        
    Returns:
        The generated Digraph visualization
    """
    # Initialize graph with parameters
    graph, image_format = initialize_graph(parameters)
    
    add_events(dcr.events, graph, dcr.nestedgroups, dcr.nestedgroups, dcr.marking, parameters)

    # Add all relations between events
    for relation in dcr.relations:
        source = relation.start_event
        target = relation.target_event
        
        # Special handling for relations within same group/hierarchy
        if (source.isGroup or target.isGroup) and (
            source == target or 
            is_ancestor_or_self(source, target) or 
            is_ancestor_or_self(target, source)
        ):
            cluster_to_same_cluster(graph, relation, dcr.nestedgroups)
        else:
            add_edgeDCR(relation, graph, dcr.nestedgroups)

    # Final graph formatting
    graph.attr(overlap='false') 
    graph.format = image_format.replace("html", "plain-text")
    return graph