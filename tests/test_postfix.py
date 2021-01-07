import asyncio
import pytest
from bley.postfix import main


@pytest.fixture()
def server(event_loop, unused_tcp_port):
    cancel_handle = asyncio.ensure_future(main(port=unused_tcp_port), loop=event_loop)
    event_loop.run_until_complete(asyncio.sleep(0.01))

    try:
        yield unused_tcp_port
    finally:
        cancel_handle.cancel()


@pytest.mark.asyncio
async def test_something(server):
    message = "Foobar!"
    reader, writer = await asyncio.open_connection('localhost', server)

    writer.write(message.encode())
    await writer.drain()

    data = await reader.read(100)
    assert message == data.decode()
    writer.close()
    await writer.wait_closed()

