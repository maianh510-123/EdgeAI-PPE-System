# Đối chiếu tiến độ và code có thể đưa vào repository

Nguồn đối chiếu: cuộc trò chuyện DACN được cung cấp, phần Week 4/5 và mapping PPE.
Không có source, weights, ảnh hay raw logs từ các tuần trước được đính kèm.

| Nội dung đã được mô tả | Code có trong bản cập nhật | Giới hạn |
|---|---|---|
| 5 class và status | constants, evaluator, payload | Theo detection; chưa person association |
| Test giao tiếp độc lập AI với no_helmet | benchmark runner tạo synthetic event | Không inference |
| HTTP request/response | HTTPClient + HTTP receiver | Stdlib server, không phải Flask gốc |
| MQTT publisher/subscriber + ACK cùng message_id | MQTTClient + receiver qua broker | Cần broker và paho-mqtt |
| CoAP request/response | CoAPClient + resource /ppe | Cần aiocoap |
| Localhost unified send-to-receive | local-e2e, timestamp receiver trong ACK | Cùng OS/clock; chỉ đếm ACK thành công |
| Hai thiết bị, đo RTT trên clock sender | rtt dùng perf_counter_ns | Chưa được thử trên thiết bị/Wi-Fi của nhóm |
| Loss sweep Week 4 | seeded sender event omission | Không tương đương packet loss trên mạng |
| Mean, median, P95, jitter | metrics + raw.csv + summary.json | Đo mới khi chạy; không nhúng số liệu cũ |
| Model evaluation / export ONNX | Chưa bổ sung | Thiếu weights, dataset, runtime và class IDs |
| Dashboard, triển khai edge | Chưa bổ sung | Thiếu yêu cầu backend và cấu hình phần cứng |

## Có thể bổ sung sau khi nhóm cung cấp file gốc
- Source testbed Week 4/5, manifest môi trường và raw CSV gốc.
- Script train/evaluate, dataset YAML/class names, weights, export và log thực nghiệm.
- Ảnh kết quả, report và mô tả phần cứng để liên kết đúng evidence với experiment.

Không gán các kết quả trong báo cáo cũ cho implementation mới này. Không đánh dấu
AI hoặc triển khai edge là hoàn thành chỉ vì đã có folder/interface.
