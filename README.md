# EdgeAI-PPE-System

Bộ khung cho đề tài giám sát trang bị bảo hộ cá nhân (PPE) bằng Edge AI và IoT.
Mục tiêu là tách nhận diện, quy tắc PPE và truyền thông để nhóm phát triển từng phần.
**Đây là skeleton chạy demo, chưa phải hệ thống nhận diện thời gian thực.**

## Trạng thái hiện tại
- Đã có: cấu trúc modular, cấu hình có kiểm tra, 5 class/status, event JSON,
  lọc confidence, demo bằng dữ liệu giả lập, console transport, smoke tests.
- Bổ sung: testbed HTTP/MQTT/CoAP độc lập với AI; localhost one-way, RTT, CSV/JSON,
  thống kê latency và seeded sender event omission. Xem hướng dẫn bên dưới.
- Chưa có trong bản này: model/weights, suy luận ảnh, camera, dataset,
  backend/dashboard, export ONNX, triển khai thiết bị edge.
- Model và giao thức cuối cùng chưa chốt. Thiết kế không phụ thuộc YOLO11n/YOLO26n
  hoặc một giao thức cụ thể. Không cài thư viện AI/giao thức khi chưa cần.
- Thảo luận DACN có nhắc thử nghiệm truyền thông trước đây; source và raw logs chưa
  được cung cấp để đưa vào project này. ZIP không chứa số đo hoặc tuyên bố tái lập chúng.

## Class và status đã chốt
| Class | Status |
|---|---|
| person | detected |
| helmet | compliant |
| safety_vest | compliant |
| no_helmet | violation |
| no_safety_vest | violation |

Mapping theo từng detection, chưa đánh giá tuân thủ của cả người/khung hình.
Không suy ra vi phạm chỉ vì không phát hiện được helmet hoặc safety_vest.

## Kiến trúc high-level
```text
Camera/Input [TODO]
  -> Detector adapter [hiện tại: synthetic DemoDetector]
  -> Confidence filter -> Class/status mapping -> PPEEvent
  -> CommunicationClient [hiện tại: ConsoleClient]
  -> Backend [TODO]
```
Detection không import thư viện truyền thông; transport không phụ thuộc model AI.
Pipeline hiện chạy đồng bộ một batch; chưa có hàng đợi, retry hoặc lưu bền sự kiện.

## Quick start
Giải nén ZIP, mở terminal tại thư mục chứa README này. Cần Python 3.10+.
Chạy ngay, không cần tải dependency:
```sh
python main.py
python main.py --config configs/default.yaml
python -m unittest discover -s tests -v
```
Demo in **2 dòng JSON** cho `person` và `no_helmet`, mỗi event có `is_demo: true`.
UUID và timestamp thay đổi mỗi lần chạy; confidence là số giả lập, không phải kết quả AI.
Log và tổng kết đi ra stderr. Không đọc camera, không gửi mạng.

Khuyến nghị dùng môi trường riêng khi bắt đầu phát triển:
```sh
python -m venv .venv
```
Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```
Nếu máy hạn chế activation, gọi `.\.venv\Scripts\python.exe main.py` trực tiếp.
macOS/Linux: `source .venv/bin/activate`.
Cài package tùy chọn (cần setuptools, có thể cần mạng cho build):
```sh
python -m pip install -r requirements.txt
edgeai-ppe --config configs/default.yaml
python -m edgeai_ppe
```

## Cấu hình
`configs/default.yaml` dùng cú pháp JSON, là một tập con của YAML, để demo không cần
thư viện ngoài. Chưa hỗ trợ cú pháp YAML thông thường hoặc comment trong file config.
Chỉnh device_id, camera_id, confidence_threshold (0..1), log_level.
Chỉ `detector=demo` và `transport=console` được triển khai; tên khác báo lỗi rõ ràng.
Có thể dùng `EDGEAI_DEVICE_ID`, `EDGEAI_CAMERA_ID` trong môi trường để ghi đè ID.
`.env.example` chỉ là mẫu; chương trình chưa tự đọc `.env`.

## Cấu trúc project
```text
main.py                      Entry point từ checkout
pyproject.toml               Package metadata và CLI
configs/default.yaml         Cấu hình demo
src/edgeai_ppe/
  constants.py, config.py     Class/status và cấu hình
  detection/                 Interface, kết quả, detector demo
  compliance/                Mapping class -> status
  communication/             Payload, console, HTTP/MQTT/CoAP adapters
  benchmark/                 Runner, CLI, thống kê và lưu raw data
  pipeline/                  Ghép các module, chạy một batch
  utils/                     Logging
models/                      Chỗ để weights/exports sau này
data/                        Chỗ để ảnh/video/dataset sau này
communication_testbed/       Hướng dẫn thí nghiệm và optional requirements
scripts/                     Run helper, communication benchmark; export là TODO
tests/                       Smoke và kiểm tra hành vi cơ bản
docs/                        Kiến trúc, truyền thông, hướng dẫn phát triển
```
`export_onnx.py` vẫn là TODO và thoát mã 2. `benchmark.py` đã có testbed truyền thông
để chạy lại thí nghiệm và tạo số đo mới. Xem TODO trong code và docs trước khi mở rộng.

## Roadmap
- [x] Chuẩn hóa 5 class, status và event schema ban đầu.
- [x] Chạy pipeline demo và smoke tests.
- [ ] Bổ sung dataset, class-index mapping, weights và thông tin giấy phép.
- [ ] Đánh giá/chọn model và runtime bằng dữ liệu thật.
- [ ] Tích hợp camera, nhận diện và kiểm tra liên kết PPE với từng người.
- [ ] Đưa source và raw logs gốc của các tuần trước vào repo.
- [x] Viết lại testbed HTTP/MQTT/CoAP độc lập và lưu raw CSV/summary JSON.
- [ ] Chạy lại trên mạng/phần cứng của nhóm, đánh giá rồi chọn giao thức.
- [ ] Thêm queue, timeout, ACK, retry, shutdown và chính sách dữ liệu.
- [ ] Tích hợp backend, kiểm thử toàn tuyến và triển khai phần cứng edge.

## Đưa lên GitHub sau khi giải nén
Copy nội dung thư mục này vào clone repository của bạn, rồi xem diff, commit và push.
Nếu repo đã có README/file khác, so sánh trước khi thay thế. Không commit `.env`,
weights hoặc dataset lớn. ZIP không chứa `.git`, secrets hay môi trường ảo.
Nhóm chưa chốt license; hãy chọn license phù hợp trước khi phân phối công khai.

## Code bổ sung theo tiến độ Week 4–5
Đã bổ sung testbed mới theo mô tả trong DACN; đây không phải source gốc đã tạo ra
số liệu báo cáo cũ. Main demo vẫn như trước, không tự gửi mạng.
Mở hai terminal tại thư mục này:
```sh
# Terminal 1
python scripts/benchmark.py receiver --protocol http
```
```sh
# Terminal 2, sau khi receiver báo READY
python scripts/benchmark.py send --protocol http --messages 100 --measurement rtt
```
Kết quả mới nằm trong `outputs/communication/<run_id>/raw.csv` và `summary.json`.
HTTP không cần dependency ngoài. MQTT/CoAP là tùy chọn, cần Python 3.11+ và
`python -m pip install -r communication_testbed/requirements.txt`; MQTT cần broker.
Xem [hướng dẫn chạy localhost/Wi-Fi/loss sweep](communication_testbed/README.md)
và [đối chiếu tiến độ](docs/progress.md). Folder testbed không quyết định giao thức
sản phẩm cuối cùng; không thay thế model AI còn thiếu.
