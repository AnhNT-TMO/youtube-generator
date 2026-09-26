# 09. YouTube Shorts cho kênh nhạc

Nguồn: R&D tra cứu ngày 2026-09-25 (trang Help/Blog/API chính thức của YouTube, điều khoản Suno, dữ liệu creator/analyst, metadata
công khai của các kênh cùng ngách). Nhãn: **[CT]** trang chính thức · **[DL]** dữ liệu lớn của bên thứ ba (tương quan, không phải nhân quả)
· **[CĐ]** lời khuyên cộng đồng, chưa kiểm được. Chính sách Shorts đổi nhanh: kiểm lại link [CT] trước khi ra quyết định.

## 1. Một Short cần gì (thông số)

| Mục | Giá trị | Nguồn |
|---|---|---|
| Phân loại | video **≤ 3 phút** và khung **dọc hoặc vuông** thì tự thành Short. Không cần `#shorts`. Video 16:9 không bao giờ thành Short | [CT] [15424877](https://support.google.com/youtube/answer/15424877) |
| Khung hình | **1080×1920** (9:16). Trang Shorts ghi upload tối đa 1080p; chưa rõ bản 4K dọc có giữ 4K không → render 1080×1920 | [CT] [10059070](https://support.google.com/youtube/answer/10059070) |
| Mã hóa | MP4 faststart, H.264 High, fps gốc; AAC-LC 48 kHz; 1080p SDR **8 Mbps** (24–30 fps) / 12 Mbps (48–60 fps) | [CT] [1722171](https://support.google.com/youtube/answer/1722171) |
| Loudness | không có con số chính thức; giữ −14 LUFS như album | [CĐ] |
| Vùng bị giao diện che | trên ~10 % (thanh tìm kiếm), **dưới ~20–25 %** (tên kênh, title, thanh nhạc), **phải ~10 %** (nút like/comment/share/remix). Vùng an toàn ≈ 900×1160 px ở giữa | [CĐ]; Google Ads chỉ có hình minh họa [9128498](https://support.google.com/google-ads/answer/9128498) |
| Ảnh bìa riêng | Studio desktop, tài khoản đã xác minh, 9:16 (khuyên 2160×3840). Từ 7/2026 mở cho kênh **trong YPP** trước, kênh khác mở dần; mobile chọn được khung bất kỳ | [CT] [72431](https://support.google.com/youtube/answer/72431), [blog 24/7/2026](https://blog.youtube/news-and-events/youtube-studio-custom-thumbnail-updates/) |
| Related video (link Short → video dài) | Studio: Content → Short → *Related video* → chọn video của kênh → Save. Cần quyền *advanced features*. **API không có trường này** → làm tay | [CT] [14075157](https://support.google.com/youtube/answer/14075157), [videos resource](https://developers.google.com/youtube/v3/docs/videos) |
| "Edit into a Short" | Short tạo từ chính video dài của kênh trong Studio (≤ 60 s) **tự link về video gốc** | [CT] [12836917](https://support.google.com/youtube/answer/12836917) |
| Upload qua API | `videos.insert` như video thường; hẹn giờ bằng `status.publishAt` (khi `privacyStatus=private`); đặt `status.containsSyntheticMedia=true`, `status.selfDeclaredMadeForKids=false`. Quota: bucket riêng, mỗi lần gọi tốn 1 unit, mặc định 100 lần/ngày | [CT] [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert), [quota](https://developers.google.com/youtube/v3/determine_quota_cost) |
| **Cổng chặn API** | *"All videos uploaded via videos.insert from unverified API projects created after 28 July 2020 will be restricted to private viewing mode."* Phải qua **audit** của Google mới đăng công khai được | [CT] như trên (đã kiểm nguyên văn) |
| Remix | Short luôn cho người khác remix / "Use this sound", **không tắt được**. Video dài tắt được trong Studio | [CĐ] |
| Content ID | Từ **24/9/2026**, Short 1–3 phút có claim **không còn bị chặn tự động** (trước đây bị chặn) | [CT] 15424877 (đã kiểm nguyên văn) |

## 2. Thuật toán: cái gì làm Short được phân phối

- **Tín hiệu chính:** % người chọn xem thay vì lướt qua (*Viewed vs swiped away*, VVSA), thời lượng xem, % xem trung bình (APV), xem lại,
  like, khảo sát sau xem. Short được thử trên một nhóm nhỏ trước, rồi mới phát rộng nếu giữ được người xem. [CT] [11914225](https://support.google.com/youtube/answer/11914225),
  [blog 28/1/2025](https://blog.youtube/creator-and-artist-stories/youtube-shorts-deep-dive/)
- Người xem quyết định lướt hay ở trong khoảng **1 giây** (trưởng sản phẩm Shorts, 1/2025). → Giây đầu phải là giọng hát/hook, không intro. [CT]
- **Cách đếm view:** từ 31/3/2025 mỗi lần phát hoặc phát lại đều tính view. Số cũ đổi tên thành **engaged views**, dùng để chia tiền và
  xét YPP. → Loop làm view tăng; đánh giá bằng engaged views, VVSA, APV. [CT] [revision history](https://developers.google.com/youtube/v3/revision_history)
- Mốc tham khảo: VVSA 70–90 % là tốt, **< 60 % thì phân phối sụp**; Short giữ người xem > 50 s trung bình được nhiều view nhất (5.400 Short, 2023).
  [DL] [Paddy Galloway](https://x.com/PaddyG96/status/1646898356419981315). Thời lượng xem trung bình mỗi Short toàn nền tảng ~16 s (2026). [DL] [Metricool](https://metricool.com/youtube-shorts-algorithm/)
- Không có tuyên bố chính thức nào về xóa rồi đăng lại. Chính sách spam cấm đăng lại mà không thêm gì → **không làm**.

## 3. Shorts có kéo traffic sang video dài không

| Phía ủng hộ | Phía ngược |
|---|---|
| YouTube: *"Shorts performance doesn't negatively impact long form Video recommendations"*; hai định dạng đề xuất riêng [CT] [11914225](https://support.google.com/youtube/answer/11914225), [blog 6/5/2025](https://blog.youtube/creator-and-artist-stories/debunking-common-myths-about-youtube-shorts/) | 18.000 kênh (3/2025–3/2026): Shorts chiếm **25–40 %** số upload là tốt nhất; **> 55 % thì long-form yếu đi ở mọi ngách** [DL] [AIR Media-Tech](https://air.io/en/audience-growth/do-youtube-shorts-help-your-long-form-videos-grow-data-from-18000-channels) |
| Đề xuất video dài có tính kênh người xem đã xem trên Shorts (2022) [CT] | 250 creator: view long-form giảm sau khi bắt đầu làm Shorts, rõ nhất ở kênh lớn [DL] [arXiv 2402.18208](https://arxiv.org/html/2402.18208v2) |
| YouTube hướng dẫn Related video (7/2026): Short và video đích cùng ý định; CTA ở 5 s cuối; video đích trả đúng lời hứa trong 5–10 s đầu [CT] [blog 14/7/2026](https://blog.youtube/creator-and-artist-stories/youtube-related-videos-traffic-guide/) | Người làm nhạc: *"Shorts lead to channel subscribers but not long-form video views"* [CĐ] [MusicX 5/2025](https://musicx.substack.com/p/how-to-deal-with-youtube) |

**Kết luận:** kỳ vọng Shorts mang về **subscriber và độ nhận diện**; lượng người nhảy từ Short 30–60 s sang album 60–90 phút sẽ thấp.
Không có số chuyển đổi chính thức. Phải đo trên kênh của mình (§7).

## 4. Chính sách: điều có thể làm mất kênh hoặc mất kiếm tiền

| Mức | Rủi ro | Nội dung | Cách tránh |
|---|---|---|---|
| **Nghiêm trọng** | Spam: *Automated or synthetic mass-production* [CT] [2801973](https://support.google.com/youtube/answer/2801973) (đã kiểm nguyên văn) | Cấm *"Using automated tools or AI to churn out high volumes of similar content with minimal changes"*. Ví dụ vi phạm: *"Channels that use the exact same background music and repetitive AI generated imagery across many videos, with each video reading out an AI-generated script."* Có thể xóa kênh | Mỗi Short phải khác thật: **bài khác, lời khác, câu hook viết từ lời bài đó**, khung dọc dựng riêng, có lời bài chạy trên màn hình. Không cắt thô 16:9 + viền đen. Không 2 Short từ cùng một bài. Không đăng lại cùng một đoạn |
| **Nghiêm trọng** | YPP: *Inauthentic content* (đổi tên từ "repetitious" ngày 15/7/2025) [CT] [1311392](https://support.google.com/youtube/answer/1311392) | Không cho kiếm tiền: *"image slideshows… scrolling text with minimal or no narrative"*, *"AI-generated content made with generic or unoriginal templates giving the impression of mass production"*. Xét **theo cả kênh** (video mới nhất, nhiều view nhất, metadata, About). Bản làm rõ 7/2026 chia 3 loại, kênh có "quá nhiều" thì bị loại khỏi YPP [CĐ] [TechCrunch 20/7/2026](https://techcrunch.com/2026/07/20/youtube-clarifies-policies-around-ai-slop-and-upsetting-videos/) | Như trên. Shorts làm tăng số video "cùng khuôn" của kênh, nên biến thể giữa các Short (khung, chuyển động, câu mở, cách viết title) là bắt buộc, không phải trang trí |
| Cao | Khai báo AI [CT] [14328491](https://support.google.com/youtube/answer/14328491) | "AI generated music" thuộc nhóm phải khai báo. Không khai báo nhiều lần → gắn nhãn cưỡng chế hoặc tạm ngưng YPP | Mọi Short: AI use = **Yes** (Studio) hoặc `containsSyntheticMedia=true` (API) |
| Trung bình | Metadata, hashtag [CT] [6390658](https://support.google.com/youtube/answer/6390658) | > 60 hashtag → bỏ qua toàn bộ; hashtag không liên quan có thể bị gỡ; 3 hashtag đầu hiện trên title | 3–5 hashtag đúng chủ đề; title không hứa điều video không có |
| Trung bình | Made for kids [CT] [9528076](https://support.google.com/youtube/answer/9528076) | đặt sai → tắt comment và nhiều tính năng | nhạc cho người lớn: **No** |
| Thấp | Tần suất | không có giới hạn upload/ngày công bố; không có nhịp tối thiểu [CT] [11914225](https://support.google.com/youtube/answer/11914225) | 3 video/ngày nằm xa dưới mọi giới hạn đã biết |
| Thấp | Tôn giáo | không có chính sách riêng, chỉ luật chung | — |

## 5. Kiếm tiền từ Shorts

- Creator nhận **45 %** phần doanh thu quỹ Shorts được phân bổ, chia theo engaged views. Nhạc gốc của kênh **không bị trừ** phí bản quyền nhạc.
  [CT] [12504220](https://support.google.com/youtube/answer/12504220)
- Vào YPP: 1.000 sub + 4.000 giờ xem video dài, **hoặc** 1.000 sub + 10 triệu view Short hợp lệ / 90 ngày. Giờ xem Short **không** tính vào 4.000 giờ.
  [CT] [72851](https://support.google.com/youtube/answer/72851)
- **Từ 1/2/2027** [CT] [blog 10/8/2026](https://blog.youtube/news-and-events/youtube-partner-program-updates-2027-new-opportunities-earn/):
  - kênh mới xin vào YPP cần **8.000 giờ** hoặc **20 triệu view Short / 90 ngày**;
  - kênh đã trong YPP cần ≥ 10 triệu view Short / 90 ngày mới được chia tiền quỹ Shorts tháng đó.
- → Với kênh nhỏ, tiền từ Shorts gần như bằng 0. Giá trị của Shorts là **khám phá kênh + sub**.

## 6. Cách làm Short nhạc để tăng traffic

Quan sát các kênh cùng ngách (R&D: `research/trends/<ch>/shorts/`) và dữ liệu ở §2–3. Cách xưởng làm: skill `youtube-shorts`.

1. **Giây 0 là giọng hát trên hook/điệp khúc**, cắt sát trước từ đầu tiên, trên downbeat. Không mở bằng intro nhạc cụ.
2. **Độ dài là trục thử.** Kênh cùng ngách ăn nhất ở Short 70–180 s có câu cảm xúc, còn clip 9–20 s chỉ được 1–3K view. Dữ liệu chung nghiêng về
   giữ người xem > 50 s. Bắt đầu 45–60 s (một điệp khúc trọn), rồi thử 90–120 s.
3. **Loop liền:** điểm ra ở cuối câu hoặc cuối vòng 4/8 ô nhịp, crossfade ngắn về điểm vào để người xem nghe lại mà không thấy chỗ nối.
4. **Chữ trên màn hình:** lời bài chạy theo từng câu (tăng giá trị thêm vào, chống "inauthentic"). Câu hook 0–3 s viết từ lời bài
   (vd. "For the one who left the light on tonight"), đổi mỗi Short, không dùng câu mẫu. CTA 3–5 s cuối trỏ tới Related video.
5. **Title:** câu cảm xúc/khẳng định lấy từ lời + tên bài/thể loại, hoặc kiểu "Listen to Full Song 👇". Kênh cùng ngách: title cảm xúc và title có CTA
   đều ăn hơn title chỉ ghi tên bài. Đây là trục version.
6. **Description:** dòng 1 link video dài; 1–2 câu cảm xúc; câu mời comment viết theo lời bài; 3–5 hashtag.
7. **Related video khớp lời hứa.** Short cắt từ **title track** → album là khớp nhất, vì album mở đúng bằng bài đó ở 0:00 (đúng hướng dẫn
   "trả lời hứa trong 5–10 s đầu"). Short từ bài giữa album → single của bài đó (bài đó bắt đầu ngay), không phải album (người xem phải tua).
8. **Nhịp và giờ:** Shorts ăn nhất chiều tối, video dài ăn nhất buổi sáng; giờ tốt của hai loại gần như không trùng [DL] [Buffer 7/2026](https://buffer.com/resources/best-time-to-post-on-youtube/).
   Đăng video dài trước để Related video gắn được ngay. Mỗi Short thêm vào/tuần giảm nhẹ view trung bình mỗi Short nhưng tổng vẫn tăng [DL] [Metricool](https://metricool.com/youtube-shorts-algorithm/).
9. **Hình dọc làm mới cho từng Short** (CEO 2026-09-25): ChatGPT vẽ ảnh 9:16 mới, kiểu ảnh theo các Short được xem nhiều nhất trong
   ngách (`trend.py shorts`), không crop ảnh 16:9; video Short render riêng (layout dọc: logo, spectrum, chữ đều trong vùng an toàn §1).
   Làm vậy còn giảm rủi ro "mass-production" (§4): mỗi Short một hình khác thật.
10. **Remix:** để bật (Short thì bắt buộc). Nhạc chậm khó thành trend "use this sound", không kỳ vọng.

## 7. Đo sau ~7 ngày

| Chỉ số (Studio) | Mốc | Đọc thế nào |
|---|---|---|
| Viewed vs swiped away | ≥ 70 % tốt, < 60 % hỏng | giây đầu / điểm vào / câu hook |
| APV | ≥ 80 % (Short < 60 s); > 100 % là loop tốt | độ dài, điểm ra, loop |
| Engaged views | so trung vị lô 7–10 Short | đừng đọc "views" (tính cả replay) |
| Sub / 1.000 engaged views | so giữa các version | giá trị thật của Shorts |
| Click Related video; view video dài từ nguồn *Shorts feed* | — | Shorts có kéo traffic không |
| View / watch time album cùng kỳ | so trước/sau khi có Shorts | canh ngưỡng 55 % của AIR |

Mỗi lần đổi một trục (độ dài → câu hook chữ → mẫu title → đích Related video → nhịp đăng), so bằng trung vị, như luật đánh giá của xưởng (CLAUDE.md §0).
