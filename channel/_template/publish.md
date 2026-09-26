# Đăng YouTube: <Channel Name>

Luật đóng gói YouTube riêng của kênh (skill `youtube-publish` là quy trình). `publish.py check` đọc hai khối ``` dưới
*Description YouTube mặc định* và *Tags YouTube mặc định* (giữ nguyên tên mục).

## Description YouTube mặc định

```
<đoạn giới thiệu kênh>

🎵 ABOUT THIS VIDEO
[Write 3–5 sentences here about the specific song or collection before publishing.]

TRACKLIST
[chapters, bắt đầu bằng 0:00]

<đoạn kết + hashtags>
```

## Tags YouTube mặc định

```
<Channel Name>, <tag>, <tag>
```

## Title

**Album:** `<Title Track> <1 emoji> <Genre phrase> for <Use-case> & <Feeling> | Full Album`

**Single:** `<Song Title> <1 emoji> <Genre phrase> for <Use-case> | <Channel Name>`

## ABOUT THIS VIDEO

- <những gì mẫu description đã nói, không lặp lại>

## Tags: các nhóm

| Nhóm | Ví dụ |
|---|---|
| album / title track name | |
| use-cases (2–3) | |
| album theme (1–2) | |
| subgenre | |
| lead instrument | |
| format (1–2) | |

## Pinned comment

Emoji của kênh: <bảng emoji>

## Shorts

<skill youtube-shorts đọc mục này>

**Title** (≤ 60 ký tự):

```
<công thức title Short, vd. <câu cảm xúc từ lời bài> | <Song Title> <emoji>>
```

**Description:**

```
<1 câu cho người nghe>
🎧 <Full album | Full song>: <related video URL>
💬 <1 câu mời comment gắn với lời bài>

<3 hashtag đúng chủ đề>
```

**Tags:** tags mặc định + tên bài + tên album. **Pinned comment:** <mẫu, có link video đích>.
**Chữ trên video:** `hook_text` <cách viết> · `cta_text` Short → album <…> / Short → single <…>.

## Giờ đăng

<giờ ET cho gói một album (CLAUDE.md §3): album → single → Short, không hai video cùng giờ; Shorts buổi chiều tối>

## Ghi chú kênh

- Playlists trong Studio: `<Channel Name> · Full Albums`, `<Channel Name> · Songs`.
