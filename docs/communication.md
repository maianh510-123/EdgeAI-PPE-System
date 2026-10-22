# Communication contract

Core demo vẫn dùng ConsoleClient và không gửi mạng. Các experiment adapters HTTP,
MQTT, CoAP được dùng qua scripts/benchmark.py, chưa được chọn làm transport mặc định
của main.py. Chúng cung cấp send(event) và exchange(event)->Receipt, cùng close().
MQTT/CoAP cần đóng tài nguyên; sender CLI luôn close trong finally.

ACK gồm message_id, accepted=true, receiver_perf_ns. Receiver validate event class,
status, confidence, timezone và UUID trước khi ACK. ACK nghĩa là handler đã chấp nhận
payload; chưa có lưu database hay xử lý cảnh báo. Event timestamp không dùng đo RTT.

HTTP: stdlib server + POST /ppe, một connection mới/event. MQTT: paho 2.x callback
API VERSION2, MQTT 3.1.1, chờ SUBACK trước gửi, application ACK từ subscriber, bỏ retained
ACK, đối chiếu UUID, mặc định QoS1. CoAP: aiocoap UDP POST /ppe, dùng lại context.
CoAP/MQTT có thể tự retransmit ở tầng thư viện/giao thức; runner không app-retry.

Đo RTT trên sender; localhost one-way lấy receiver perf_counter_ns cùng OS. Không
trừ monotonic clocks của hai máy. Không so trực tiếp one-way với RTT hoặc gán broker
PUBACK thành subscriber delivery. Nếu chạy khác VM/OS, dùng RTT.

Xem ../communication_testbed/README.md cho lệnh chạy, công thức thống kê và loss model.
Các adapter được viết lại theo mô tả, chưa tái lập benchmark cũ. Không có raw dữ liệu cũ.

TODO: authentication/TLS, backend persistence, schema evolution, ACK log độc lập,
async bounded queue, drop policy, retries và crash recovery cho hệ thống thực.
Pipeline vẫn synchronous; các adapter thử nghiệm không đảm bảo inference không bị
chặn bởi network. Chưa có lựa chọn model hay giao thức cuối cùng.

API references used when implementing (primary documentation):
- https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html
- https://aiocoap.readthedocs.io/en/latest/examples.html
- https://aiocoap.readthedocs.io/en/latest/faq.html
- https://docs.python.org/3/library/time.html#time.perf_counter
