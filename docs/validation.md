# Kiểm tra bản 0.2.0

Kiểm tra ngày 2026-10-22 trên Windows, Python 3.12.10.
Optional packages: paho-mqtt 2.1.0, aiocoap 0.4.17.
Broker MQTT dùng riêng cho kiểm thử: amqtt 0.11.4, chỉ bind 127.0.0.1.
Broker kiểm thử và thư viện tải về không được đóng gói vào ZIP.

19 test cases đều đạt, không skip trong lần kiểm tra đủ dependency và broker:
- 6 test core: class/status, payload, demo/filter, send failure, config, CLI.
- 10 test benchmark/HTTP: thống kê, ACK, sender omission, timeout, seed, clock guard,
  HTTP request/response thật, local-e2e/RTT và raw CSV/summary JSON.
- 1 test CoAP qua UDP thật, gồm benchmark RTT và local-e2e.
- 2 test MQTT qua broker thật: application ACK + benchmark và thiếu subscriber.

Lệnh cơ bản từ project root:
```sh
python -m unittest discover -s tests -v
```
Nếu chưa cài aiocoap, CoAP test sẽ skip. MQTT tests skip trừ khi biến môi trường
EDGEAI_MQTT_TEST_PORT trỏ đến port của broker local riêng dùng kiểm thử. Ví dụ
PowerShell nếu broker test đã chạy ở 1883:
```powershell
$env:EDGEAI_MQTT_TEST_PORT = '1883'
python -m unittest discover -s tests -v
```
Không dùng broker production để kiểm thử. Tests tạo topic-prefix riêng theo UUID.
Test files ghi tạm bên trong project rồi tự dọn. Network tests cần kết nối localhost
được môi trường cho phép. Không cần sửa firewall khi chỉ chạy trên localhost.

Đây là kết quả kiểm tra tính đúng của code, không phải benchmark hiệu năng của nhóm.
Chưa kiểm tra hai thiết bị Wi-Fi, Linux/macOS, model AI, camera, backend hoặc phần cứng
edge. Không sao chép các giá trị latency từ báo cáo Week 4/5 vào repo.
