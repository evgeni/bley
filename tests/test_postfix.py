import asyncio
import pytest
from bley.postfix import PostfixPolicy


@pytest.fixture()
def server(event_loop, unused_tcp_port):
    policy = PostfixPolicy()
    cancel_handle = asyncio.ensure_future(policy.run(port=unused_tcp_port), loop=event_loop)
    event_loop.run_until_complete(asyncio.sleep(0.01))

    try:
        yield unused_tcp_port
    finally:
        cancel_handle.cancel()


@pytest.mark.asyncio
async def test_DUNNO(server):
    reader, writer = await asyncio.open_connection('localhost', server)
    writer.write(b"sender=root@example.com\n")
    writer.write(b"recipient=user@example.com\n")
    writer.write(b"client_address=192.0.2.1\n")
    writer.write(b"\n")
    await writer.drain()
    line_1 = await reader.readline()
    line_2 = await reader.readline()
    assert "action=DUNNO\n" == line_1.decode()
    assert "\n" == line_2.decode()
