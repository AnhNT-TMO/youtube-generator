# Report + state layout

## `reports/YYYY-MM-DD.md` (one per run, Vietnamese, ≤ 1 page)

```markdown
# R&D <channel> · YYYY-MM-DD

Dữ liệu: pulse <n kênh / n video> · discover <có/không> · units <n>. Bảng: topics/YYYY-MM-DD.md.

## Kết luận cho PM
- <1–3 dòng: giữ chủ đề X / đổi sang Y / thử Z, kèm con số quyết định>

## Thay đổi so với lần trước
| Trend | Loại (chủ đề / nhánh nhạc / đóng gói / ngoài hợp đồng) | Trạng thái | Bằng chứng (video, kênh, hit, fresh, % view) |

## Kênh mình
<view, view/ngày các video gần nhất, sub; video nào đang lên>

## Thumbnail (tuần; bảng thumbs/<date>.md)
<mẫu đang thắng / bão hòa / đang mở, kèm hit share và độ tin (weak khi < 5 hit)>

### Ý tưởng thumbnail (3–5, PM chọn)
| # | Cảnh | Chủ thể | Chữ (vai trò, số từ) | Màu + ánh sáng | Nguyên liệu thắng lấy từ trend | Khác ngách / khác 3 album gần nhất ở đâu |

## Shorts (tuần; shorts/<date>.md + sheet)
<loại Short + chủ đề trên Shorts đang thắng; kênh thắng bằng Shorts>

### Ý tưởng Shorts (2–4, PM chọn)
| # | Loại | Chủ đề | Bài của mình (album + slot / library) + đoạn | Góc câu hook 0–3 s | Kiểu ảnh | version | youtube-shorts làm được? (có / cần: …) |

## Deep dive (nếu có)
Chủ đề · reference set (research/<set>) · điều khán giả viết trong comment · điều ngách làm giống nhau / chưa ai làm ·
copy guard (title, chữ thumbnail, tên kênh của họ)
```

## `state.md` (living summary, overwritten each run)

```markdown
# Trạng thái trend <channel> (cập nhật YYYY-MM-DD)

| Trend | Loại | Trạng thái | Từ ngày | Kênh mình đang làm? | Ghi chú |

Chủ đề đang làm: <topic> từ <date> (<n> video của mình) · kết quả kênh mình: <tóm tắt>
Đề xuất tiếp theo: <một dòng>
Báo cáo gần nhất: reports/YYYY-MM-DD.md
```
