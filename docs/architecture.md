# Architecture and boundaries
Planned: Input -> Detector -> class/status mapping -> PPEEvent -> transport -> backend.
Implemented: synthetic DemoDetector -> threshold filter -> PPEEvent -> ConsoleClient.
Detector and CommunicationClient are structural Protocol interfaces, injected into
PPEPipeline. A real detector can accept a frame object; the eventual adapter defines
its supported input type. No camera loop or image decoding is implemented.

A detection is a class plus confidence. The evaluator maps exactly one class at a
time. It does not associate equipment with a person, resolve conflicting detections,
or infer a violation from missing detections. A compliant equipment event is not a
claim that a whole person or frame is compliant.

Events carry UUID message_id, timezone-aware UTC timestamp, device_id, camera_id,
detection_class, status, confidence, is_demo and schema_version. Event time is not
a latency measurement. Demo records always have is_demo=true.

Pipeline is one synchronous batch. OSError from a sender is logged and counted;
later events are still attempted. Failed events are not persisted or retried.
Programming errors propagate. A future asynchronous bounded queue is required to
isolate inference from slow network I/O. Adapter resource cleanup is also TODO.

A separate reconstructed benchmark CLI exercises HTTP/MQTT/CoAP adapters with
synthetic no_helmet events. These are not yet wired into the core demo CLI. See
../communication_testbed/README.md for clock boundaries and known limitations.
