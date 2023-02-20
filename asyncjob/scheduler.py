import asyncio
from collections.abc import Iterable
from typing import Any, Optional

__all__ = ["Scheduler", "TaskProvider"]


TaskProvider = Iterable[set[asyncio.Task[Any]]]


class Scheduler:
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._loop = loop if loop else asyncio.get_event_loop()
        self._pending_jobs: list[TaskProvider] = []
        self._job_tasks: list[asyncio.Task[Any]] = []
        self._terminated = True
        self._stop_waiter: asyncio.Future[Any] | None = None
        self._stop_future: asyncio.Future[Any] | None = None

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    @property
    def is_running(self) -> bool:
        return bool(not self._terminated and self._stop_future)

    @property
    def jobs_count(self) -> int:
        return len(self._job_tasks)

    async def wait_stopped(self) -> None:
        if not self._stop_waiter:
            return

        await self._stop_waiter

    def _stop(self) -> None:
        """
        Stop processing jobs.

        Called every time the last job resolves.

        """
        if not self._stop_future or self._stop_future.done():
            return

        self._stop_future.set_result(None)

    async def _process_job(self, job: TaskProvider) -> Any:
        """
        Process the given job while it fires tasks.

        """
        pending_tasks: set[asyncio.Task[Any]] = set()

        try:
            for tasks in job:
                for task in tasks:
                    pending_tasks.add(task)

                if not pending_tasks:
                    break

                _, pending_tasks = await asyncio.wait(
                    pending_tasks, return_when=asyncio.FIRST_COMPLETED
                )

        except asyncio.CancelledError:
            for task in pending_tasks:
                task.cancel()
            raise

        finally:
            if pending_tasks:
                await asyncio.wait(pending_tasks, return_when=asyncio.ALL_COMPLETED)

                for tasks in job:
                    ...

    async def _schedule_job(self, job: TaskProvider) -> None:
        """
        Create a new task for processing the given job.

        The newly created task is awaited until it is resolved.

        """
        task = self._loop.create_task(self._process_job(job))
        self._job_tasks.append(task)

        try:
            await task
        finally:
            self._job_tasks.remove(task)
            if not self._job_tasks:
                self._stop()

    def _run_job(self, job: TaskProvider) -> None:
        """
        Start processing of the given job.

        """
        self._loop.create_task(self._schedule_job(job))

    def push_job(self, job: TaskProvider) -> None:
        """
        Push a new job to the scheduler.

        If the scheduler is running the job is scheduled immediately, otherwise
        it is added to the pending list.

        """
        if not self._terminated and self._stop_future and not self._stop_future.done():
            self._run_job(job)
        else:
            self._pending_jobs.append(job)

    def _schedule_pending_jobs(self) -> None:
        for job in self._pending_jobs:
            self._run_job(job)

        self._pending_jobs = []

    def _notify_stop_waitier(self) -> None:
        if not self._stop_waiter:
            return

        self._stop_waiter.set_result(None)
        self._stop_waiter = None

    def terminate(self) -> None:
        """
        Terminate procesing of new jobs.

        This will not stop the scheduler immediately, the scheduler will be
        running until the last job is resolved.

        All jobs which are added after call this this method are added to the
        pending list.

        """
        self._terminated = True

    def cancel(self) -> None:
        """
        Terminate the scheduler and cancel all the scheduled jobs.

        """
        self.terminate()

        if not self._job_tasks:
            self._stop()
            return

        for job_task in self._job_tasks:
            job_task.cancel()

    async def run(self) -> None:
        """
        Run scheduler while there are not resolved jobs.

        """
        if self._stop_future:
            raise RuntimeError("Scheduler is already running")

        self._terminated = False
        self._stop_waiter = self._loop.create_future()
        self._stop_future = self._loop.create_future()

        self._schedule_pending_jobs()

        await self._stop_future

        self._stop_future = None
        self.terminate()
        self._notify_stop_waitier()

    async def run_forever(self) -> None:
        """
        Run scheduler forever.

        To stop the scheduler use the :meth:`terminate` method.

        """
        if self._stop_future:
            raise RuntimeError("Scheduler is already running")

        self._terminated = False
        self._stop_waiter = self._loop.create_future()

        while True:
            if self._terminated:
                break

            self._stop_future = self._loop.create_future()
            self._schedule_pending_jobs()

            await self._stop_future

        self._notify_stop_waitier()
