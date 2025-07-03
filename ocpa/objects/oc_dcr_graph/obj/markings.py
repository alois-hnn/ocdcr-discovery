from enum import Enum
from typing import Set

from .event import Event

class MarkingTyps(Enum):
	"""
	Enumeration of possible marking types for events in DCR graphs.

	Attributes:
		E: Executed - event has been executed
		I: Included - event is included in the process
		P: Pending - event is pending execution
	"""
	E = 'executed'
	I = 'included'
	P = 'pending'

class DCRMarking:
	"""
	Represents the marking (state) of a DCR graph
	"""

	def __init__(self) -> None:
		"""Initialize empty sets for executed, pending, and included events."""
		self.executed: Set[Event] = set()
		self.pending: Set[Event] = set()
		self.included: Set[Event] = set()

	def get_set(self, marking: MarkingTyps) -> Set[Event]:
		"""
		Get the set of events for a specific marking type.

		Args:
			marking: The marking type to retrieve (E, I, P)

		Returns:
			The set of events with the specified marking
		"""
		return {
			MarkingTyps.E: self.executed,
			MarkingTyps.P: self.pending,
			MarkingTyps.I: self.included
		}[marking]

	def add_event(self, event: Event, marking: MarkingTyps) -> None:
		"""
		Add an event with a specific marking.

		Args:
			event: The event to add to the marking set
			marking: The marking type to assign to the event
		"""
		self.get_set(marking).add(event)

	def get_event_marking(self, event: Event) -> Set[MarkingTyps]:
		"""
		Get the marking type of a specific event.

		Args:
			event: The event to check

		Returns:
			The marking types of the event or empty set if not found
		"""
		mark = set()
		for marking in MarkingTyps:
			if event in self.get_set(marking):
				mark.add(marking)
		return mark

	def remove_event(self, event: Event) -> None:
		for marking in MarkingTyps:
			if event in self.get_set(marking):
				self.get_set(marking).remove(event)

	# Property getters and setters
	@property
	def executed(self):
		return self.__executed

	@executed.setter
	def executed(self, executed):
		self.__executed = executed

	@property
	def pending(self):
		return self.__pending

	@pending.setter
	def pending(self, pending):
		self.__pending = pending

	@property
	def included(self):
		return self.__included

	@included.setter
	def included(self, included):
		self.__included = included