"""Optional CoAP/UDP experiment; one reusable context per sequential run."""
import asyncio
import time

from edgeai_ppe.communication.ack import make_ack, read_ack


def _library():
    try:
        import aiocoap
        import aiocoap.resource
        return aiocoap
    except ImportError as exc:
        raise RuntimeError("Install communication_testbed/requirements.txt for CoAP") from exc


class CoAPClient:
    def __init__(self, host="127.0.0.1", port=5683, timeout=5.0):
        self.lib = _library()
        self.timeout = timeout
        self.uri = f"coap://{host}:{port}/ppe"
        self.loop = asyncio.new_event_loop()
        try:
            self.context = self.loop.run_until_complete(
                self.lib.Context.create_client_context(transports=["simple6"]))
        except BaseException:
            self.loop.close()
            raise

    async def _exchange(self, event):
        request = self.lib.Message(code=self.lib.POST, uri=self.uri,
                                   payload=event.to_json().encode("utf-8"), content_format=50)
        response = await asyncio.wait_for(self.context.request(request).response, self.timeout)
        if not response.code.is_successful():
            raise OSError(f"CoAP status {response.code}")
        return read_ack(response.payload, event.message_id)

    def exchange(self, event):
        try:
            return self.loop.run_until_complete(self._exchange(event))
        except (self.lib.error.Error, ValueError) as exc:
            raise OSError(str(exc)) from exc

    def send(self, event):
        self.exchange(event)

    def close(self):
        try:
            self.loop.run_until_complete(self.context.shutdown())
        finally:
            self.loop.close()


async def create_coap_server(host="127.0.0.1", port=5683):
    lib = _library()

    class PPEResource(lib.resource.Resource):
        async def render_post(self, request):
            received_ns = time.perf_counter_ns()
            try:
                ack = make_ack(request.payload, received_ns)
            except (ValueError, TypeError, KeyError):
                return lib.Message(code=lib.BAD_REQUEST, payload=b"Invalid PPE event")
            return lib.Message(code=lib.CHANGED, payload=ack, content_format=50)

    site = lib.resource.Site()
    site.add_resource(["ppe"], PPEResource())
    # Explicit interface address is required by the portable server transport.
    return await lib.Context.create_server_context(
        site, bind=(host, port), transports=["simplesocketserver"])
