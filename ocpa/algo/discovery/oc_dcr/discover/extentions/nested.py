from copy import deepcopy
from typing import Optional, Dict

from ocpa.objects.oc_dcr_graph.obj import DCRGraph, RelationTyps as Relations

from pm4py.objects.log.obj import EventLog


# TODO mal testweise nicht das wir plagiat machen


"""
This file includes code adapted from:

  Back, C.O., Højen, A.R., & Vestergaard, L.S. (2023).
  "DCR4Py: A PM4Py Library Extension for Declarative Process Mining in Python".
  Published in CEUR Workshop Proceedings, Vol-3783. Available at:
  https://ceur-ws.org/Vol-3783/paper_353.pdf

The original code is licensed under Creative Commons Attribution 4.0 International (CC BY 4.0):
https://creativecommons.org/licenses/by/4.0/

In accordance with this license:
- Original authors are credited.
- The code was modified to integrate with the OCPA framework.
- This code is redistributed under the GPLv3 license as required by the host project.

If you reuse this code, please comply with both CC BY 4.0 and GPLv3 where applicable.
"""


def apply(graph):
    """
    this method calls the nesting miner

    Parameters
    ----------
    log: EventLog | pandas.Dataframe
        Event log to use in the role miner
    graph: DCR_Graph
        Dcr graph to apply additional attributes to
    parameters
        Parameters of the algorithm, including:
            nest_variant : the nesting algorithm to use from the enum above: CHOICE|NEST|CHOICE_NEST
    Returns
    -------
    :class:´GroupSubprocessDcrGraph`
        return a DCR graph, that contains nested groups
    """
    nesting_mine = NestingMining()
    return nesting_mine.mine(graph)


class NestingMining:
    """
    The NestingMining provides a simple algorithm to mine nestings

    After initialization, user can call mine(log, G, parameters), which will return a DCR Graph with nested groups.

    Reference paper:
    Cosma et al. "Improving Simplicity by Discovering Nested Groups in Declarative Models" https://doi.org/10.1007/978-3-031-61057-8_26
    Attributes
    ----------
    graph: Dict[str,Any]
        A template that will be used collecting organizational data

    Methods
    -------
    mine(log, G, parameters)
        calls the main mining function, extract nested groups

    Notes
    ------
    *
    """

    def mine(self, graph : DCRGraph):
        """
        Main nested groups mining algorithm

        Parameters
        ----------
        graph: DCRGraph
            DCR graph to append additional attributes
        parameters: Optional[Dict[str, Any]]
            optional parameters used for role mining
        Returns
        -------
        NestedDCRGraph(G, dcr)
            returns a DCR graph with nested groups
        """

        return self.apply_nest(graph)



    def apply_nest(self, graph):

        existing_nestings = deepcopy(graph['nestedgroups']) if len(graph['nestedgroups'])>0 else None
        nesting = Nesting()
        nesting.create_encoding(graph)
        nesting.nest(graph['events'])
        nesting.remove_redundant_nestings()
        return nesting.get_nested_dcr_graph(graph,existing_nestings)



class Nesting(object):

    def __init__(self):
        self.nesting_template = {"nestedgroups": {}, "nestedgroupsMap": {}, "subprocesses": {}}
        self.nesting_ids = set()
        self.nesting_map = {}
        self.nest_id = 0
        self.enc = None
        self.in_rec_step = 0
        self.out_rec_step = 0
        self.debug = False

    def encode(self, G):
        enc = {}
        for e in G['events']:
            enc[e] = set()
        for e in G['events']:
            for e_prime in G['events']:
                for rel in Relations:
                    if e in G[rel.value] and e_prime in G[rel.value][e]:
                        if rel == Relations.C:
                            enc[e].add((e_prime, rel.value, 'in'))
                        else:
                            enc[e].add((e_prime, rel.value, 'out'))
                    if e_prime in G[rel.value] and e in G[rel.value][e_prime]:
                        if rel == Relations.C:
                            enc[e].add((e_prime, rel.value, 'out'))
                        else:
                            enc[e].add((e_prime, rel.value, 'in'))
        return enc
    def get_opposite_rel_dict_str(self, relStr, direction, event, nestingId):
        relation_dict_str_del = (event, relStr, "out" if direction == "in" else "in")
        relation_dict_str_add = (nestingId, relStr, "out" if direction == "in" else "in")

        return relation_dict_str_del, relation_dict_str_add

    def create_encoding(self, dcr_graph):
        self.enc = self.encode(dcr_graph)

    def find_largest_nesting(self, events_source, parent_nesting=None):
        cands = {}
        events = deepcopy(events_source)
        for e in events:
            for j in events:
                arrow_s = frozenset(self.enc[e].intersection(self.enc[j]))
                if len(arrow_s) > 0:
                    if not arrow_s in cands:
                        cands[arrow_s] = set([])
                    cands[arrow_s] = cands[arrow_s].union(set([e, j]))

        best_score = 0
        best = None
        for arrow_s in cands.keys():
            cand_score = (len(cands[arrow_s]) - 1) * len(arrow_s)
            if cand_score > best_score:
                best_score = cand_score
                best = arrow_s

        if best and len(cands[best]) > 1 and len(best) >= 1:
            if self.debug:
                print(
                    f'[out]:{self.out_rec_step} [in]:{self.in_rec_step} \n'
                    f'     [events] {events} \n'
                    f'[cands[best]] {cands[best]} \n'  # these are the events inside the nesting
                    f'       [best] {best} \n'
                    f'        [enc] {self.enc} \n '
                    f'      [cands] {cands} \n'
                )
            self.nest_id += 1
            nest_event = f'Group{self.nest_id}'

            self.nesting_ids.add(nest_event)
            self.enc[nest_event] = set(best)

            if parent_nesting:
                parent_nesting['events'] = parent_nesting['events'].difference(cands[best])
                parent_nesting['events'].add(nest_event)
                self.nesting_map[nest_event] = parent_nesting['id']

            for e in cands[best]:
                self.nesting_map[e] = nest_event
                self.enc[e] = self.enc[e].difference(best)
                for (e_prime, rel, direction) in best:
                    op_rel_del, op_rel_add = self.get_opposite_rel_dict_str(rel, direction, e, nest_event)
                    # TODO: find out why sometimes it tries to remove non-existing encodings
                    self.enc[e_prime].discard(op_rel_del)  # .remove(op_rel_del)
                    self.enc[e_prime].add(op_rel_add)

            retval = [{'nestingEvents': cands[best], 'sharedRels': best}]
            found = True
            while found:
                temp_retval = self.find_largest_nesting(events_source=cands[best], parent_nesting={'id': f'Group{self.nest_id}', 'events': cands[best]})
                if temp_retval and len(temp_retval) > 0:
                    retval.extend(temp_retval)
                    for tmp in temp_retval:
                        events = events.difference(tmp['nestingEvents'])
                else:
                    found = False
                self.in_rec_step += 1
            return retval

    def nest(self, events_source):
        nestings_arr = [{'nestingEvents': set(), 'sharedRels': set()}]
        events = deepcopy(events_source)

        while True:
            temp_retval = self.find_largest_nesting(events)
            if temp_retval and len(temp_retval) > 0:
                nestings_arr.extend(temp_retval)
                for tmp in temp_retval:
                    events = events.difference(tmp['nestingEvents'])
            else:
                break
            self.out_rec_step += 1

        return self.nesting_map, self.nesting_ids

    def remove_redundant_nestings(self):
        nestings = {}
        for n in self.nesting_ids:
            nestings[n] = set()
        for k, v in self.nesting_map.items():
            nestings[v].add(k)

        # Removing redundant nestings
        nests_to_remove = set([])
        for key in nestings:
            val = nestings[key]
            if len(val) == 1:
                nests_to_remove.add(list(val)[0])

        for nest_to_remove in nests_to_remove:
            parent = self.nesting_map[nest_to_remove]
            for k, v in list(self.nesting_map.items()):
                if v == nest_to_remove:
                    self.nesting_map[k] = parent
            print("Deleting: ", nest_to_remove)
            del self.nesting_map[nest_to_remove]
            self.nesting_ids.remove(nest_to_remove)

            for e, v in deepcopy(list(self.enc.items())):
                for r in v:  #I get a set changed error here
                    (e_prime, rel, direction) = r
                    if e_prime == nest_to_remove:
                        self.enc[e].remove(r)
                        self.enc[e].add((parent, rel, direction))
                if e == nest_to_remove:
                    self.enc[parent] = self.enc[parent].union(self.enc[e])
                    del self.enc[e]

    def should_add(self, rel, direction):
        return direction == 'in' if rel == Relations.C.value else direction == 'out'

    def get_nested_dcr_graph(self, graph, existing_nestings=None):
        events = set(self.enc.keys())
        graph['events'] = events
        graph['marking']['included'] = events

        for n in self.nesting_ids:
            graph['nestedgroups'][n] = set()
            ################
        for k, v in self.nesting_map.items():
            graph['nestedgroups'][v].add(k)

        for e, v in self.enc.items():
            for e_prime, rel, direction in v:
                if self.should_add(rel, direction):
                    if e not in graph[rel]:
                        graph[rel][e] = set()
                    graph[rel][e].add(e_prime)

        if existing_nestings:
            for me, me_events in existing_nestings.items():
                if me not in graph['nestedgroups']:
                    graph['nestedgroups'][me] = set()
                for me_event in me_events:
                    if me_event in self.nesting_map:
                        highest_nesting = self.nesting_map[me_event]
                        while True:
                            if highest_nesting in self.nesting_map:
                                highest_nesting = self.nesting_map[highest_nesting]
                            else:
                                break
                        if highest_nesting not in graph['nestedgroups'][me]:
                            graph['nestedgroups'][me].add(highest_nesting)
                    else:
                        graph['nestedgroups'][me].add(me_event)
                    self.nesting_map[me_event] = me
                if self.debug:
                    print(self.nesting_map[me])
                    print(self.nesting_map)
                    print(graph['nestedgroups'])

        graph['nestedgroupsMap'] = deepcopy(self.nesting_map)

        return graph
        # return res_dcr