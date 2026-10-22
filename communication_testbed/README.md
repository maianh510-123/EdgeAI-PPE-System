# Testbed truyền thông - code bổ sung theo mô tả Week 4–5

Đây là implementation mới dựa trên mô tả DACN, **không phải source gốc của các tuần
trước**. Không chứa benchmark cũ hoặc khẳng định tái tạo được số đo trong báo cáo.
Input cố định `no_helmet`, confidence=1.0 là giả lập; `is_demo=true` trong mọi event.
Không thực hiện AI inference hoặc chọn giao thức cuối cùng.

## Chạy nhanh HTTP localhost (không cần cài thêm)
Mở hai terminal tại thư mục gốc project trong VS Code.
Terminal 1 - receiver:
```sh
python scripts/benchmark.py receiver --protocol http
```
Chờ `READY`, rồi terminal 2 - sender:
```sh
python scripts/benchmark.py send --protocol http --messages 100 --measurement rtt --note "localhost HTTP smoke"
```
Mỗi lần chạy tạo thư mục riêng `outputs/communication/<run_id>/`, gồm:
- `raw.csv`: từng event, sequence, UUID, thời điểm, trạng thái, latency và lỗi.
- `summary.json`: số lượng, ACK rate, mean/median/P95/min/max/jitter và môi trường.

Đo một chiều **chỉ khi cả receiver và sender cùng hệ điều hành trên cùng máy**:
```sh
python scripts/benchmark.py send --protocol http --messages 100 --measurement local-e2e
```
Không dùng chế độ này qua VM/container khác clock hoặc qua hai máy.
`local-e2e` vẫn cần ACK để lấy timestamp receiver; event đến nhưng ACK thất lạc sẽ
không có latency và không được tính vào ACK rate. Chưa có receiver log để đếm độc lập.
Ctrl+C dừng receiver. Sender tuần tự, không có warmup, không tự retry ở tầng ứng dụng.

## MQTT và CoAP (tùy chọn)
Dùng Python **3.11+** và cài trong môi trường ảo:
```sh
python -m pip install -r communication_testbed/requirements.txt
```
MQTT cần broker riêng. Với Mosquitto đã cài trên máy, chế độ local có thể chạy
`mosquitto -v` ở terminal riêng. Sau đó mở receiver/subscriber:
```sh
python scripts/benchmark.py receiver --protocol mqtt --host 127.0.0.1
```
Chờ `READY`, rồi chạy sender ở terminal khác:
```sh
python scripts/benchmark.py send --protocol mqtt --messages 100 --qos 1
```
Cả hai dùng cùng host broker, port, QoS và topic-prefix; mặc định port 1883,
topic-prefix `ppe/benchmark`. ACK ứng dụng được subscriber publish trên topic
`ppe/benchmark/ack/<message_id>`. Không dùng PUBACK làm bằng chứng subscriber nhận.
Chỉ chạy một receiver trên mỗi topic-prefix để tránh ACK trùng.

CoAP - terminal receiver:
```sh
python scripts/benchmark.py receiver --protocol coap --host 127.0.0.1
```
Terminal sender:
```sh
python scripts/benchmark.py send --protocol coap --messages 100
```
CoAP dùng POST `/ppe`, JSON và context UDP dùng lại; mặc định port 5683.
Receiver dùng portable `simplesocketserver`; phải bind địa chỉ cụ thể (không dùng
0.0.0.0). Trên Wi-Fi hãy dùng địa chỉ LAN thật của máy receiver.

## Hai máy trên cùng Wi-Fi
Chạy HTTP receiver trên máy nhận:
```sh
python scripts/benchmark.py receiver --protocol http --host 0.0.0.0
```
Ví dụ máy nhận có IP 192.168.1.183, trên máy gửi chạy (thay IP theo mạng hiện tại):
```sh
python scripts/benchmark.py send --protocol http --host 192.168.1.183 --measurement rtt --messages 100 --note "Windows sender; macOS receiver; same Wi-Fi"
```
Với CoAP, receiver dùng `--host <IP-LAN-cua-receiver>` và sender dùng cùng IP đó.
Với MQTT, host của cả hai là IP broker; broker phải được cấu hình listener/ACL cho
LAN. Không tự đổi firewall hoặc cấu hình broker. Bản testbed chưa có TLS/auth;
chỉ dùng trong môi trường thử nghiệm tin cậy, chưa phải backend production.

## Mô phỏng mất sự kiện ở sender (gợi ý Week 4)
Ví dụ PowerShell, trong khi receiver đang chạy:
```powershell
foreach ($rate in @(0, 0.1, 0.25, 0.5)) {
    python scripts/benchmark.py send --protocol http --messages 100 --loss-rate $rate --seed 42
}
```
Các mức trên là ví dụ để chạy lại, không phải cấu hình gốc được khẳng định của nhóm.
Đây là bỏ event trước khi gửi bằng RNG có seed; **không mô phỏng packet loss trên
mạng hoặc kiểm tra retransmission của giao thức**. Số bỏ thực tế có thể khác tỷ lệ
kỳ vọng khi N nhỏ. Không tự đổi sự kiện bỏ thành timeout.

## Cách đọc số liệu
- `application_ack_rate_planned_pct`: ACK hợp lệ / số event dự kiến.
- `application_ack_rate_sent_pct`: ACK hợp lệ / số lần thực sự thử gửi; null nếu 0.
- Không gọi các tỷ lệ này là delivery rate độc lập: receiver có thể đã nhận nhưng
  ACK mất hoặc về muộn. Sender chỉ xác nhận ACK khớp UUID trước timeout.
- `measurement=rtt`: trước exchange đến sau đọc/validate ACK, dùng clock sender.
- `measurement=local-e2e`: trước exchange đến handler receiver sau khi có payload.
- P95 dùng nội suy tuyến tính rank 0.95*(N-1). Jitter là trung bình hiệu tuyệt đối
  giữa các mẫu thành công liên tiếp; bỏ qua các mẫu failed/drop.
- Không có mẫu hợp lệ: latency null, không tự ghi 0. Một mẫu: jitter null.
- HTTP mở TCP mới mỗi event và tính connect vào timer; MQTT connect + subscribe
  trước timer; CoAP tạo context trước timer. Đây là so sánh implementation có session
  khác nhau, chưa phải kết luận giao thức nào tốt hơn.
- Timeout/read timeout và DNS tùy thư viện không phải hard deadline chính xác.
- CSV raw được flush từng dòng. Nếu Ctrl+C khi đang chạy sender, có thể chỉ có raw
  một phần và chưa có summary. Không dùng run thiếu summary như một run hoàn chỉnh.

Xem [progress.md](../docs/progress.md) để phân biệt phần đã có với TODO.
