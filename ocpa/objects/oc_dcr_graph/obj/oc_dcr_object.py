from typing import Dict

from .dcr_graph import DCRGraph
from .relations import DCRRelation, RelationTyps, OCDCRRelation
from .event import Event

class OCDCRObject(DCRGraph):
	"""
	Represents an object in an Object-Centric DCR (OCDCR) graph.

	Extends DCRGraph with:
	- Spawn event: The event that creates instances of this object type, None if not spawned
	- type: Identifier for the object type
	- Support for quantified relations

	Each object maintains its own DCR subgraph that defines its behavior.
	"""

	def __init__(self, spawn: Event | None, type: str, dcr: Dict | DCRGraph = None):
		"""
		Initialize an OCDCR object. It can be initialized with either a DCRGraph or a dcr template:
		dcr_template = {
			'events': set(),
			'marking': {'executed': set(), 'pending': set(),
						'included': set()},
			'includesTo': {},                                   ## {'event1': {'event2', 'event3'}} means that event2 and event3 will be included when event1 executes
			'excludesTo': {},                                   ## {'event1': {'event2', 'event3'}} means that event2 and event3 will be excluded when event1 executes
			'responseTo': {},                                   ## {'event1': {'event2', 'event3'}} means that event2 and event3 are responses to event1
			'conditionsFor': {},                                ## {'event1': {'event2', 'event3'}} means that event2 and event3 are conditions for event1
			'nestedgroups': {},                                 ## {'event1': {'event2', 'event3'}} means that event1 is a nested group including event2 and event3
		}

		Args:
			spawn: The spawn event that creates this object
			type: The type identifier of the object
			dcr: Optional template to initialize from or alternatively a DCRGraph
		"""
		self.__spawn = spawn
		self.__type = type
		if isinstance(dcr, DCRGraph):
			# Initialize from existing DCRGraph
			self.marking = dcr.marking
			self.relations = dcr.relations
			self.events = dcr.events
			self.nestedgroups = dcr.nestedgroups
			self.nested_events = dcr.nested_events

		else:
			# Initialize normally with optional template
			super().__init__(dcr)

	@property
	def spawn(self) -> Event:
		return self.__spawn

	@property
	def type(self) -> str:
		return self.__type

	@type.setter
	def type(self, type: str) -> None:
		self.__type = type

	def add_relation(self, start_event: str | Event, target_event: str | Event,
					 relation_type: RelationTyps, quantifier_head: bool = False,
					 quantifier_tail: bool = False) -> None:
		"""
		Add a relation with quantifiers between two events. If the relation already exists, updates its quantifiers instead of creating a new one.

		Args:
			start_event: Source event or its activity name
			target_event: Target event or its activity name
			relation_type: Type of relation
			quantifier_head: Whether there is a universal quantifier to target event, always False if not spawned (default: False)
			quantifier_tail: Whether there is a universal quantifier from start event, always False if not spawned (default: False)

		Raises:
			TypeError: If events are of invalid types
		"""
		# Convert string activity names to Event objects if strings
		if isinstance(start_event, str) and isinstance(target_event, str):
			start_event = self.get_event(start_event)
			target_event = self.get_event(target_event)

		if start_event is None or target_event is None:
			raise ValueError("Event not found")

		if not (isinstance(start_event, Event) and isinstance(target_event, Event)):
			raise TypeError("Events must be both strings or both Event objects")
		
        # Check if relation already exists
		e = self.get_relation(start_event, target_event, relation_type)
		if e is not None:
			# Update quantifiers if relation exists
			e.quantifier_head = quantifier_head
			e.quantifier_tail = quantifier_tail
			return

		if self.__spawn is None:
			# No many to many if object is not spawned
			self.relations.add(OCDCRRelation(start_event, target_event, relation_type,False, False))
		else:	
			self.relations.add(OCDCRRelation(start_event, target_event, relation_type,quantifier_head, quantifier_tail))


	def to_dcr(self) -> DCRGraph:
		"""
		Convert this OCDCR object to a standard DCRGraph.

		Returns:
			A DCRGraph containing all events and relations without quantifiers
		"""

		# ensures that there are no OCDCRRelation in the set
		dcr_relations = {
			DCRRelation(rel.start_event, rel.target_event, rel.type)
			for rel in self.relations
		}
		return DCRGraph.from_attributes(
			events=self.events,
			relations=dcr_relations,
			marking=self.marking,
			nested_groups=self.nestedgroups,
			nested_events=self.nested_events
		)
