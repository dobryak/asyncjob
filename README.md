# asyncjob

**asyncjob** - is just another simple scheduler for asyncio jobs.  


## Install

The package is available on PyPI.  

```console
# python3 -m pip install asyncjob

```

## Very fast usage

```python
import asyncio
import asyncjob

async def coro():
    ...

loop = asyncio.new_event_loop()
scheduler = asyncjob.Scheduler(loop)

job = [
    [
        loop.create_task(asyncio.sleep(2.0))
    ],
    [
        loop.create_task(coro())
    ]
]

scheduler.push_job(job)

try:
    loop.run_until_complete(scheduler.run())
except KeyboardInterrupt as exc:
    scheduler.cancel()
    loop.run_until_complete(scheduler.wait_stopped())

```
