from __future__ import annotations

from typing import Any, Callable

from .job import Job, Task
from .scheduler import Scheduler

__all__ = ["MachineState", "Machine", "MachineStateHandler", "StateTransitionTable"]


MachineStateHandler = Callable[[list[Task]], str | None]


class MachineState:
    def __init__(
        self,
        state_name: Any,
        handler: MachineStateHandler,
    ) -> None:
        self._state_name = state_name
        self._handler = handler

    @property
    def state_name(self) -> Any:
        return self._state_name

    @property
    def handler(self) -> MachineStateHandler:
        return self._handler


EventName = str
StateTransitionTable = tuple[tuple[MachineState, EventName, MachineState], ...]


class Machine(Job):
    """
    A simple implementation of the finity state machine for async jobs.

    """

    def __init__(self, scheduler: Scheduler) -> None:
        super().__init__(scheduler)

        self._state_transition_table = self._get_state_transition_table()

        if not self._state_transition_table:
            raise ValueError("the defined state transition table is empty")

        self._state = self._state_transition_table[0][0]

    def _get_state_transition_table(self) -> StateTransitionTable:
        """
        Return state transition table.

        """
        raise NotImplementedError("state machine must define a state transition table")

    def _spin_machine(self, resolved_tasks: list[Task]) -> None:
        """
        Do one iteration of the machine.

        :param resolved_tasks: A list of tasks has been resolved since previous
        iteration.

        """
        event = self._state.handler(resolved_tasks)
        if event is None:
            # waiting for any resolved task
            return

        current_state = self._state
        for transition in self._state_transition_table:
            if current_state is not transition[0]:
                continue

            if event != transition[1]:
                continue

            self._state = transition[2]
            if current_state is not self._state:
                # spin the machine if the state has been changed
                self._spin_machine([])

            return

        raise ValueError(
            "received unexpected event from the machine state {self._state}"
        )

    def _update(self, resolved_tasks: list[Task]) -> None:
        self._spin_machine(resolved_tasks)
