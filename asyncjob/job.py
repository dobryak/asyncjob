from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Generator
from typing import Any

from .scheduler import Scheduler

__all__ = ["Task", "Job"]


class Task:
    def __init__(
        self,
        job: Job,
        aw: Awaitable[Any],
        name: str | None = None,
        *,
        context: Any = None,
    ) -> None:
        self._aw = aw
        self._name = name
        self._job = job
        self._is_done = False
        self._result: Any = None
        self._context = context

    @property
    def job(self) -> Job:
        """
        The job the task is assigned to.

        """
        return self._job

    @property
    def context(self) -> Any:
        """
        The context of the task.

        """
        return self._context

    def done(self) -> bool:
        return self._is_done

    def get_name(self) -> str | None:
        return self._name

    def get_result(self) -> Any:
        """
        Get a result.

        Event if the result is an exception it is just returned.

        """
        return self._result

    def result(self) -> Any:
        """
        Get a result only if the result is not an exception.

        If the result is exception it is thrown.

        :raises Exception: if the result is an exception

        :returns: a result only if it is not an exception.

        """
        result = self.get_result()

        if isinstance(result, Exception):
            raise result

        return result

    async def wait_done(self) -> Any:
        try:
            result = await self._aw
        except BaseException as exc:
            result = exc

        self._result = result
        self._is_done = True
        self._job.resolve_task(self)

        return result

    def __await__(self) -> Generator[Any, None, Any]:
        return self.wait_done().__await__()


async def _wait_job(job: Job) -> Any:
    try:
        return await job
    except asyncio.CancelledError:
        job.cancel()
        raise


class Job(ABC):
    def __init__(self, scheduler: Scheduler) -> None:
        self._scheduler = scheduler
        self._loop = scheduler.get_event_loop()
        self._task_to_async_task: dict[Task, asyncio.Task[Any]] = dict()
        self._pending_tasks: set[Task] = set()
        self._resolved_tasks: list[Task] = []

        # tasks that was scheduled during the job tick
        self._recent_tasks: set[asyncio.Task[Any]] = set()

        self._is_done = False
        self._is_canceled = False
        self._result: Any = None

        self._done_waiter: asyncio.Future[Any] | None = None

        self._prepare()

    def _prepare(self) -> None:
        """
        Prepare the job.

        """

    @property
    def scheduler(self) -> Scheduler:
        return self._scheduler

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def _clean_up(self) -> None:
        """
        Clean up everytnig.

        Called when the jobs is done.

        """

    def get_result(self) -> Any:
        """
        Get result ob the job.

        Never raises an exception!

        """
        return self._result

    def result(self) -> Any:
        """
        Get a result only if the result is not an exception.

        If the result is exception it is thrown.

        :raises Exception: if the result is an exception

        :returns: a result only if it is not an exception.

        """
        result = self.get_result()

        if isinstance(result, Exception):
            raise result

        return result

    @property
    def pending_tasks_cnt(self) -> int:
        return len(self._pending_tasks)

    def done(self) -> bool:
        """
        Whether the job is done.

        """
        return self._is_done

    def canceled(self) -> bool:
        """
        Whether the job is canceled.

        """
        return self._is_canceled

    def has_pending_tasks(self) -> bool:
        return self.pending_tasks_cnt > 0

    def resolve_task(self, *tasks: Task) -> None:
        """
        Notify about tasks that have been resolved.

        :raises ValueError: if the given task is not in the scheduled list,
        or the given task is not done.

        """
        for task in tasks:
            if task not in self._pending_tasks:
                raise ValueError("the given task is not registered in the job")

            if not task.done():
                raise ValueError("the given task is not done!")

            del self._task_to_async_task[task]
            self._pending_tasks.discard(task)
            self._resolved_tasks.append(task)

    def _resolve(self, result: Any) -> None:
        if self._is_done:
            return

        self._result = result
        self._terminate()

    def _terminate(self) -> None:
        """
        Mark the current job as done and notify everbody about this.

        """
        if self._is_done:
            return

        # self._clean_up()
        self._is_done = True

        if self._done_waiter:
            self._done_waiter.set_result(None)

    def _new_task(
        self,
        aw: Awaitable[Any] | Job,
        *,
        name: str | None = None,
        context: Any = None,
    ) -> Task:
        """
        Create and schedule for execution a new task.

        :param aw: An awaitable object or Job.
        :param name: a name of the task.
        :param context: a context that will be attached to the created task.

        :raises TypeError: if the given awaitable object is not supported.

        """

        if self._loop is None:
            raise RuntimeError(f"event loop is not set for this job {self}")

        if isinstance(aw, Job):
            self._scheduler.push_job(aw)
            if context is None:
                context = aw

            aw = _wait_job(aw)

        task = Task(self, aw, name, context=context)

        self._pending_tasks.add(task)
        atask = self._loop.create_task(task.wait_done())
        self._recent_tasks.add(atask)
        self._task_to_async_task[task] = atask

        return task

    def _sleep(
        self, delay: float, *, name: str | None = "sleep", context: Any = None
    ) -> Task:
        """
        Create a sleep task.

        """

        return self._new_task(asyncio.sleep(delay), name=name, context=context)

    def _cancel_pending_tasks(self, msg: Any = None) -> None:
        if self.canceled():
            return

        for async_task in self._task_to_async_task.values():
            async_task.cancel(msg)

    def cancel(self, msg: Any = None) -> None:
        """
        Cancel all the pending tasks and terminate the job.

        """
        if self._is_done:
            return None

        self._cancel_pending_tasks(msg)
        self._is_canceled = True
        self._resolve(asyncio.CancelledError())

    @abstractmethod
    def _update(self, resolved_tasks: list[Task]) -> None:
        """
        Do one iteration for the internal job.

        This method contains a specific logic of the job, and must not be
        called directly.

        :param resolved_tasks: a list of tasks which was previously raised by
        the job and have finished.

        """

    def do(self) -> set[asyncio.Task[Any]]:
        """
        Iterate the job.

        :returns: a set of tasks that was created during the job iteration.

        """
        if self._is_done:
            return set()

        resolved_tasks = self._resolved_tasks
        self._resolved_tasks = []

        result = None
        try:
            result = self._update(resolved_tasks)
        except Exception as exc:
            self._cancel_pending_tasks(exc)
            self._resolve(exc)

        tasks = self._recent_tasks
        self._recent_tasks = set()

        if not tasks and not self._pending_tasks:
            self._resolve(result)

        return tasks

    def __iter__(self) -> Job:
        return self

    def __next__(self) -> set[asyncio.Task[Any]]:
        while not self.done():
            return self.do()

        raise StopIteration()

    async def wait_done(self) -> Any:
        if self.done():
            return self._result

        if not self._done_waiter:
            self._done_waiter = self._loop.create_future()

        try:
            await self._done_waiter
        finally:
            self._done_waiter = None

        return self._result

    def __await__(self) -> Generator[Any, None, Any]:
        return self.wait_done().__await__()
