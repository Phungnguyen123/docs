# studio/ — Brand motion-graphics pipeline (reusable)

Code lõi để dựng đồ hoạ video theo design-system của brand. Tách khỏi `videos/`
(vùng gitignore chứa media) để **commit và tái dùng** cho video sau.

## Cấu trúc

```
studio/
├── kit.py          # design-system 720p: màu brand, Poppins, helper (F, pill, add_shadow, over, tw, vbox)
├── kit1080.py      # bản 1080p — mọi kích thước/font tự nhân hệ số S (1.5). Đổi S=2 → 1440, S=3 → 4K
└── generators/     # thư viện kỹ thuật (render từng khung RGBA bằng PIL)
```

Font Poppins được resolve **tương đối** với gốc repo (`../.fonts/poppins`) nên chạy được sau khi clone.

## Generator canonical (kỹ thuật mới nhất, render native 1080)

| File | Dựng gì |
| --- | --- |
| `build_1080.py` | title/outro card, lower-third frosted, logo bug, "3 days" hero, checklist panel, close tag — toàn bộ ở 1080 |
| `build_fix.py`  | ví dụ chỉnh vị trí (hero sang phải, panel đẩy ra) — mẫu reposition |
| `build_lt_glass.py` | lower-third frosted glass (blur nền thật) — bản kỹ thuật độc lập |
| `build_counter.py`  | KPI counter đếm số + bubble-pop |
| `build_mockup.py`   | mockup giả-3D (perspective warp + float) |
| `build_typo.py`     | typography pop per-letter drop-in |
| `build_cards_anim.py` | title/outro keynote reveal (stagger) |

Các file còn lại (`build_static`, `build_sequences`, `build_stat2`…) là bản lặp/lịch sử — giữ để tham khảo.

## Cách dùng cho video mới

1. Tạo thư mục làm việc trong `videos/` (vd `videos/<project>/edit/brand/`).
2. Copy `kit*.py` + generator cần dùng vào đó (hoặc `sys.path` trỏ tới `studio/`).
3. Đổi **nội dung/brand token** (tên, màu, text) + **đường dẫn footage/output** trong generator
   (các script hiện hardcode path theo project cũ — chỉnh cho khớp project mới).
4. Render footage grade → sinh chuỗi overlay → composite bằng ffmpeg
   (`overlay=0:0` + `setpts=PTS-STARTPTS+OFFSET/TB` + `enable='between(t,a,b)'`).

> Xem `../STUDIO_GUIDE.md` cho catalog đầy đủ, nguyên lý animation, quy tắc đặt overlay và tuỳ chọn export.

## Lưu ý

- Generator hiện gắn path cụ thể của project cũ (`videos/edit/brand/...`) → **chỉnh path** khi tái dùng.
- `kit*.py` là phần lõi portable; generator là **mẫu kỹ thuật** để chỉnh, không phải lib đa dụng plug-and-play.
