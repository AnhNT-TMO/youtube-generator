# Giao việc cho Codex

Codex (`codex exec`) là nhân viên thêm của PM, dùng để tiết kiệm token Claude cho **việc đã có flow** khi CEO yêu cầu.
PM vẫn chịu trách nhiệm cho mọi đầu ra: Claude nghĩ việc, chia việc, viết brief, giám sát, kiểm đầu ra; Codex làm.

## Khi nào giao

- Chỉ khi CEO yêu cầu dùng Codex, hoặc việc đã nằm trong một flow có sẵn và CEO đã cho phép giao Codex cho loại việc đó.
- Giao được: việc có lệnh/script sẵn và kết quả kiểm được bằng máy. Ví dụ: chạy tool, sửa file theo chỉ dẫn chính xác,
  tìm + tải tài liệu nguồn, chạy job OMR/render bằng lệnh có sẵn, ghi sổ, so sánh bằng tool.
- **Việc phải nhìn ảnh:** worker chỉ thấy ảnh được đính kèm lúc start (`--image`); ảnh nó tự mở/cắt bằng lệnh shell
  thì nó **không thấy**, dù báo cáo vẫn nói đã xem. PM cắt sẵn ảnh (vd. mỗi hệ khuông một ảnh) rồi đính kèm.
- **Không giao:** việc mà đáp án dùng để kiểm cũng nằm trong tầm tay worker, việc quyết định (giữ ở PM/CEO).
- Loại việc mới: chạy **calibration** trước: cho Codex làm 2–3 mục PM đã biết đáp án (Codex không thấy đáp án), chấm bằng máy.
  Đạt mới giao hàng loạt. Không đạt → ghi bài học vào bảng dưới, không giao loại việc đó nữa.

## Model và số lượng

- `cx/gpt-6.1-sol`, effort `high` (mặc định của `codex_task.py`). Không dùng model đắt hơn nếu CEO không bảo.
- Tối đa 6 worker cùng lúc (giới hạn chung của Mac). Server: việc nặng vẫn qua `guard.sh run`, mỗi lúc một job OMR/GPU.

## Lệnh

```bash
CT() { python3 .claude/skills/pm-production/scripts/codex_task.py "$@"; }
CT start <task> --brief <brief.md> --allow '<glob>' … [--forbid '<regex>' …] [--image a.png …] [--effort medium]
CT status [task] [--tail N] [--running]   # RUNNING/DONE/FAILED, số lệnh, progress, token, lệnh cuối, VIOLATION theo --forbid
CT audit [tasks…] [--ignore '<glob>' …]   # file đổi từ lúc task chạy mà không task nào được phép ghi
CT stop <task>
```

- Mọi file của task ở `production/codex/<task>/`: `brief.md` (brief + luật PM tự gắn), `log.jsonl` (mọi lệnh worker chạy),
  `progress.md` (một dòng mỗi mục xong), `result.md` (báo cáo cuối), `meta.json`.
- Agent Codex có tên trong `.codex/agents/*.toml` (vd. reviewer của resource queue) chạy bằng `scripts/codex_agent.py run`.

## Brief

Một brief = một việc, một danh sách mục cố định, đủ để làm mà không cần hỏi:
- mục tiêu và định nghĩa "xong" đo được; danh sách mục (slug/file) cụ thể, không "làm hết";
- lệnh chính xác cần chạy; file được đọc, file được ghi (khớp `--allow`); việc cấm (khớp `--forbid`);
- định dạng dòng kết quả cho từng mục; gặp vướng → ghi `BLOCKED: <lý do>` cho mục đó và làm mục tiếp, không đoán.

## Giám sát (PM phải biết nhân viên đang làm gì)

1. Chạy `CT start` nền, rồi một Monitor/until-loop đánh thức PM khi task xong; giữa chừng `CT status --running`.
2. `--forbid` mọi đường tắt tới đáp án (vd. file đáp án, file đã cách ly, tool chấm điểm khi worker chỉ được chép).
   `status` in `VIOLATION` → `CT stop` ngay, cách ly đầu ra của task, ghi sổ.
3. Xong: `CT audit` (file ngoài phạm vi), đọc `result.md`, rồi **kiểm đầu ra bằng máy** (tool check, so số liệu, diff),
   lấy mẫu đọc tay vài mục. Không bao giờ nhận kết quả chỉ vì báo cáo nói PASS.
4. Đầu ra sai → đưa chính lỗi đó vào brief mới và chạy lại; sai lần 2 cùng kiểu → PM tự làm hoặc bỏ loại việc đó.
5. Đầu ra hỏng/giả: **không xóa**, chuyển vào thư mục cách ly tên rõ (`NOT-EVIDENCE-…`, `FABRICATED-…`) kèm README, khôi phục
   file gốc từ log (log ghi nội dung worker đã đọc), chạy tool check.

## Bài học (cập nhật khi calibration ra kết quả mới)

| Loại việc | Kết quả | Ngày |
|---|---|---|
| Chép giai điệu từ ảnh scan, worker tự mở ảnh | **Hỏng.** Không thấy ảnh, chỉ đạt 22–38 %, nốt bịa theo bước liền; được thấy giai điệu của mình thì chép lại thành "bản in" để ra PASS (bịa bằng chứng). | 2026-10-07 |
| Chép giai điệu từ ảnh scan, PM đính kèm ảnh cắt theo hệ khuông (`-i`, read-only, thư mục trống) | **Đạt.** 3 bài PM đã chép đúng: 95 %, 98 %, 100 % (lệch 1–3 trường độ). Cả trang trong một ảnh: kém (sai nhịp, lặp câu). Rủi ro còn lại: bài nổi tiếng có thể chép theo trí nhớ → mỗi khác biệt và mỗi PASS của bài phổ biến phải được PM mở scan đối chiếu. | 2026-10-07 |
| Tự khai vi phạm | Có worker tự dừng và báo đã đọc file cấm; nhiều worker khác không báo. Luôn kiểm bằng log, không tin lời khai. | 2026-10-07 |
