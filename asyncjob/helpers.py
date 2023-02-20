import asyncio
import logging
from typing import Callable

from .fsm import Machine, MachineState, StateTransitionTable
from .job import Job, Task
from .scheduler import Scheduler

__all__ = ["RetryJobWrapper"]


logger = logging.getLogger(__name__)


class RetryJobWrapper(Machine):
    """
    Job wrapper that executes the given job until it is succeed or the given
    :param:`retry_count` attempts is reached.

    """

    def __init__(
        self,
        scheduler: Scheduler,
        job_factory: Callable[[], Job],
        *,
        delay: float = 30,
        retry_count: int = 10,
    ) -> None:
        super().__init__(scheduler)

        self._job_factory = job_factory
        self._job: Job | None = None
        self._delay = abs(delay)
        self._retry_count = abs(retry_count)
        self._tries = 0

    @property
    def tries(self) -> int:
        return self._tries

    @property
    def job(self) -> Job | None:
        return self._job

    def _get_state_transition_table(self) -> StateTransitionTable:
        exec_job = MachineState("exec_job", self._exec_job)
        wait = MachineState("wait", self._wait)
        retry = MachineState("retry", self._retry)

        return (
            (exec_job, "wait", wait),
            (wait, "retry", retry),
            (retry, "exec_job", exec_job),
        )

    def _exec_job(self, _: list[Task]) -> str:
        self._job = self._job_factory()
        self._new_task(self._job, name="wrapped_job")

        return "wait"

    def _wait(self, resolved_tasks: list[Task]) -> str | None:
        for task in resolved_tasks:
            job = task.context
            if not isinstance(job, Job):
                raise RuntimeError(
                    f"wrong result from task received, expected job, got: {job}"
                )

            if job.canceled():
                self.cancel()
                return None

            try:
                self._resolve(job.result())
            except Exception as exc:
                logger.info(f"job {job} has been failed")
                if self._retry_count > 0 and self._tries >= self._retry_count:
                    self._resolve(exc)
                    return None

                logger.info(f"retry the job {job}")
                self._tries += 1
                return "retry"

        return None

    def _retry(self, resolved_tasks: list[Task]) -> str | None:
        if not resolved_tasks:
            logger.info(f"{self} - wait for {self._delay} seconds")
            self._new_task(asyncio.sleep(self._delay), name="wait_for_retry")
            return None

        return "exec_job"
