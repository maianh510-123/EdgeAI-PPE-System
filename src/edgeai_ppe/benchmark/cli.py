import argparse
import asyncio
import json
import math
import threading

from edgeai_ppe.benchmark.runner import run_benchmark


def positive_float(text):
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("Must be finite and > 0")
    return value


def parser():
    cli = argparse.ArgumentParser(description="Reconstructed PPE communication testbed; synthetic input")
    cli.add_argument("role", choices=("receiver", "send"))
    cli.add_argument("--protocol", choices=("http", "mqtt", "coap"), default="http")
    cli.add_argument("--host", default="127.0.0.1", help="Receiver bind address or destination/broker host")
    cli.add_argument("--port", type=int, help="Default: HTTP 8080, MQTT 1883, CoAP 5683")
    cli.add_argument("--timeout", type=positive_float, default=5.0)
    cli.add_argument("--topic-prefix", default="ppe/benchmark")
    cli.add_argument("--qos", type=int, choices=(0, 1, 2), default=1)
    cli.add_argument("--messages", type=int, default=100)
    cli.add_argument("--loss-rate", type=float, default=0.0, help="Sender omission probability, e.g. 0.25")
    cli.add_argument("--seed", type=int, default=42)
    cli.add_argument("--interval", type=float, default=.01, help="Seconds after each completed exchange")
    cli.add_argument("--measurement", choices=("rtt", "local-e2e"), default="rtt")
    cli.add_argument("--output", default="outputs/communication")
    cli.add_argument("--note", default="", help="Record topology/device/network description")
    return cli


async def _serve_coap(args):
    from edgeai_ppe.communication.coap import create_coap_server
    context = await create_coap_server(args.host, args.port)
    try:
        print(f"READY coap {args.host}:{args.port}", flush=True)
        await asyncio.Future()
    finally:
        await context.shutdown()


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    args.port = args.port if args.port is not None else {"http": 8080, "mqtt": 1883, "coap": 5683}[args.protocol]
    if not 1 <= args.port <= 65535:
        cli.error("port must be between 1 and 65535")
    if args.messages < 1 or not math.isfinite(args.loss_rate) or not 0 <= args.loss_rate <= 1:
        cli.error("messages must be positive and loss-rate must be in [0,1]")
    if not math.isfinite(args.interval) or args.interval < 0:
        cli.error("interval must be finite and nonnegative")
    if args.measurement == "local-e2e" and args.host not in ("localhost", "127.0.0.1"):
        cli.error("local-e2e requires localhost on the same operating system; use RTT for Wi-Fi")
    if not args.topic_prefix.strip("/") or any(c in args.topic_prefix for c in ("+", "#", "\x00")):
        cli.error("topic-prefix must be nonempty and contain no wildcards")
    try:
        if args.role == "receiver":
            if args.protocol == "http":
                from edgeai_ppe.communication.http import create_http_server
                with create_http_server(args.host, args.port) as server:
                    print(f"READY http {args.host}:{args.port}", flush=True)
                    server.serve_forever()
            elif args.protocol == "mqtt":
                from edgeai_ppe.communication.mqtt import create_mqtt_receiver
                session = create_mqtt_receiver(args.host, args.port, args.timeout, args.topic_prefix, args.qos)
                try:
                    print(f"READY mqtt broker={args.host}:{args.port}", flush=True)
                    threading.Event().wait()
                finally:
                    session.close()
            else:
                asyncio.run(_serve_coap(args))
            return 0
        if args.protocol == "http":
            from edgeai_ppe.communication.http import HTTPClient
            client = HTTPClient(args.host, args.port, args.timeout)
        elif args.protocol == "mqtt":
            from edgeai_ppe.communication.mqtt import MQTTClient
            client = MQTTClient(args.host, args.port, args.timeout, args.topic_prefix, args.qos)
        else:
            from edgeai_ppe.communication.coap import CoAPClient
            client = CoAPClient(args.host, args.port, args.timeout)
        try:
            directory, summary = run_benchmark(
                client, protocol=args.protocol, host=args.host, port=args.port,
                output=args.output, messages=args.messages, loss_rate=args.loss_rate,
                seed=args.seed, interval=args.interval, measurement=args.measurement,
                timeout=args.timeout, note=args.note, qos=args.qos, topic_prefix=args.topic_prefix)
            print(json.dumps({"output": str(directory), "summary": summary}, indent=2, ensure_ascii=False))
            return 1 if summary["failed"] else 0
        finally:
            client.close()
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, RuntimeError) as exc:
        cli.exit(2, f"Testbed error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
