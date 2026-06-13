# Video Studio — Guideline tổng hợp

Tài liệu này đúc kết **mọi thứ có thể làm** với studio dựng video hội thoại này, dựa trên pipeline
thực tế đã xây (brand BBCIncorp / testimonial). Dùng làm sổ tay để tái sử dụng cho các video sau.

---

## 1. Studio này là gì

Ba lớp năng lực chồng lên nhau:

| Lớp | Công cụ | Vai trò |
| --- | --- | --- |
| **Biên tập** | `video-use` (skill) | Phiên âm → cắt → bỏ filler/dead-air → grade màu → burn phụ đề |
| **Motion graphics (HTML)** | `hyperframes` + adapters (GSAP, three, lottie, typegpu, waapi, anime, css, tailwind) | Title card, lower-third, kinetic caption, overlay… render xác định từ HTML/CSS/JS |
| **Motion graphics (code, brand kit)** | `kit.py` / `kit1080.py` + bộ generator PIL/ffmpeg (đã xây trong repo) | Đồ hoạ theo design-system của brand, render từng khung bằng Python rồi composite bằng ffmpeg |
| **Sinh / nguồn asset (AI & cloud)** | MCP: `higgsfield`, `Canva`, `Google Drive` | Tạo ảnh/video/audio AI, upscale, reframe, xoá nền, lấy logo/asset từ Drive/Canva |

> Quy ước vàng: **Nguồn không bao giờ bị sửa.** Mọi thứ đổ vào thư mục `edit/`. File media không commit vào git.

---

## 2. Pipeline chuẩn

```
raw footage
   ├─ inventory + transcribe        (ffprobe + ElevenLabs Scribe / Whisper local)
   ├─ xác nhận PLAN (plain English) ── ask → confirm → execute → iterate → persist
   ├─ cut + bỏ filler/dead-air      (trên ranh giới từ, fade audio 30ms)
   ├─ color grade                   (per-segment)
   ├─ motion graphics               (overlay tracks: title, lower-third, counter, mockup, typo…)
   ├─ subtitles                     (burn sau cùng)
   └─ self-evaluate + render        → edit/final.mp4
```

---

## 3. Catalog đồ hoạ có thể dựng (đã có generator sẵn)

Mỗi mục là một "asset type" tái dùng được, chỉ cần đổi nội dung/brand:

| Asset | Mô tả | Animation đặc trưng |
| --- | --- | --- |
| **Color grade** | Look màu (vd Apple cool: +exposure, lift shadow, desat nhẹ, light-leak, vignette; hoặc warm testimonial) | tĩnh, áp per-segment |
| **Title / End card** | Card trắng bo góc + pill + tiêu đề + gạch accent + footer tracked | **Keynote reveal**: phần tử trồi 14px + fade lệch nhịp (stagger), Expo-Out |
| **Lower-third frosted glass** | Name tag: logo monogram + kẻ gradient (xanh→amber) + tên đậm + chức danh | **Backdrop blur thật** (lấy nền từ chính khung) + tint trắng 65% + scale-pop + bar draw-on + text slide-in |
| **Kinetic counter (KPI)** | Thẻ số liệu: icon + số lớn + mô tả | **Count-up** 0→target (ease-out-cubic) + bubble-pop từ góc dưới-trái |
| **Status / checklist panel** | Panel "Singapore Pte Ltd" với các dòng tick dần + footer chip | Slide-in từ phải + float sin + **tick stagger** (gray ring → check xanh) |
| **Product / dashboard mockup** | Khung app/dashboard giả-3D | **Perspective warp** (xoay trục Y 10–15°→0) + slide-in + float lơ lửng + shadow |
| **Typography pop / kinetic word** | Từ khoá lớn (vd "FAST", "3 days") chữ accent + viền trắng + shadow | **Per-letter drop-in** (ease-out-back) hoặc scale-flash |
| **Logo bug** | Logo persistent góc (pill nền mờ + mark + wordmark) | fade-in, giữ suốt clip |
| **Close / CTA tag** | Pill bo tròn ở đáy: ✓ + thông điệp | rise + fade-in |
| **Transitions** | Nối cảnh | `xfade` (fade/wipe…) + `acrossfade` audio |
| **Subtitles** | Phụ đề styled burn-in | qua `video-use`, key theo ranh giới từ |

`video-use` còn lo: transcribe, cắt câu, **bỏ filler/dead-air**, fade audio ở mọi cut, EDL (`edl.json`).

---

## 4. Design system (nhất quán brand)

Định nghĩa 1 lần trong `kit.py` — mọi generator import từ đó:

- **Màu**: accent `#007eff`, amber `#ffab00`, text `#333333`, dark `#002a66`, muted `#898989`,
  nền `#f4f9ff` / `#e4f2ff` / `#eaf1ff`.
- **Font**: Poppins (400/500/600/700), bundled trong `.fonts/poppins`.
- **Token hình**: bo góc 12–16px, shadow mềm (blur + offset + opacity ~0.3), pill bo tròn,
  gradient xanh→amber cho điểm nhấn.
- **Helper**: `F()` (font), `pill()`, `add_shadow()`, `over()` (alpha-composite), `tw/vbox` (đo chữ).

---

## 5. Nguyên lý animation (đã dùng)

- **Easing**: Expo-Out `1−2^(−10t)` (vào mượt), **ease-out-back** (overshoot/bounce cho pop),
  ease-out-cubic (đếm số), **stagger** (delay theo index).
- **Patterns**: scale-from-anchor (bong bóng), draw-on (kẻ chạy), slide+fade, float `sin(2πt/T)`,
  perspective warp (giả-3D), per-letter reveal.
- **Cut**: fade 0.5s giữa các cảnh; out luôn nhanh hơn in (~0.25–0.3s).

---

## 6. Kỹ thuật compositing (cốt lõi)

1. **PIL render từng khung** → mỗi overlay là chuỗi PNG **RGBA full-canvas** (vị trí/scale/alpha bake sẵn).
2. **ffmpeg ghép**: `overlay=0:0` với `setpts=PTS-STARTPTS+OFFSET/TB` (đặt thời điểm) và
   `enable='between(t,a,b)'` (cửa sổ hiện). Nhiều overlay nối chuỗi trong **một** filter_complex → 1 lần encode.
3. **Frosted glass thật**: trích khung footage đã grade ở đúng vùng → `GaussianBlur` → clip bằng mask rounded-rect → tint trắng → đặt nội dung lên. Blur là nền THẬT, không giả.
4. **Native resolution**: dùng hệ số `S` trong `kit1080.py` (S=1.5 → 1080; có thể S=3 → 4K) — **mọi
   kích thước/font tự nhân S**, đồ hoạ render gốc ở target res (không upscale → chữ sắc tuyệt đối).
5. ⚠️ **Tránh `zoompan` trên ảnh tĩnh** — làm tròn pixel từng khung gây **rung lắc**. Thay bằng
   reveal render-sẵn bằng PIL.

---

## 7. Quy tắc đặt overlay (đọc footage trước khi đặt)

- **Luôn trích vài khung tại đúng thời điểm overlay** để xem chủ thể/tay ở đâu → đặt vào **vùng trống chắc chắn**.
- Chủ thể center/center-left, tay/đạo cụ ở dưới-giữa → **bên phải (cửa kính) thường trống** = chỗ đặt text/panel an toàn.
- Mặt ở center-upper → **không đặt chữ lớn ở giữa** (chủ thể cử động sẽ đè mặt).
- Logo: góc phải-trên. Lower-third: góc trái-dưới. Không để 2 element to cùng vùng, cùng lúc.
- Sắp xếp theo **beat/VO**: thoại nói gì → overlay minh hoạ đúng cái đó (đừng nhồi số liệu lạc đề).

---

## 8. Export — chất lượng & định dạng

| Mục đích | Cấu hình |
| --- | --- |
| Giao hàng đẹp nhất | **1080p, H.264 High, CRF 14**, (tuỳ chọn 10-bit `yuv420p10le`), faststart |
| Mượt gradient | **10-bit** (đỡ banding) — lưu ý: H.264 High10 không phát trên vài máy cũ/Safari |
| Master biên tập/lưu trữ | **ProRes 422 HQ** (visually lossless, file lớn) |
| Nhẹ hơn ~40% | **H.265 / HEVC** cùng chất lượng |
| Tương thích tối đa | **8-bit `yuv420p`** H.264 |
| Social | **1:1 (1080×1080)** hoặc **9:16 (1080×1920)** — reframe giữ chủ thể |

> Trần chi tiết = độ phân giải **footage gốc** (upscale không tạo chi tiết thật). Nhưng đồ hoạ render
> native ở target res nên **luôn sắc** — đáng để xuất 1080p kể cả khi nguồn 720p.

---

## 9. Asset cần từ bạn (và cách gửi)

- **Footage thô** (thả vào folder bất kỳ).
- **Logo**: **đính kèm dưới dạng FILE** (PNG nền trong / SVG). ⚠️ Ảnh **dán trong chat KHÔNG lưu thành file** → render không đọc được.
- **Số liệu + mốc giây** cho counter; **từ khoá + mốc giây** cho typo pop (vì không tự biết ai nói gì ở giây nào nếu chưa transcribe).
- **Screenshot/recording** sản phẩm cho mockup.
- **Script / beat map / brand colors / font** nếu có → khớp câu chuyện, đỡ "giả định".

---

## 10. Năng lực mở rộng qua skill/MCP

- **HyperFrames**: dựng overlay/animation bằng HTML/CSS + GSAP/three.js/lottie/WebGPU… render xác định;
  `website-to-hyperframes` (URL → video), port Remotion, registry blocks, TTS/transcribe/remove-bg.
- **higgsfield (MCP)**: sinh **ảnh/video/audio AI**, upscale, reframe, xoá nền, **virality predictor**.
- **Canva (MCP)**: tạo/sửa design, brand template, export.
- **Google Drive (MCP)**: lấy logo/asset/script từ Drive.

---

## 11. Cách ra lệnh (ví dụ)

- "Cắt thành video 60s gọn, bỏ hết ‘ừm’, thêm title card và name tag."
- "Grade tone Apple, thêm lower-third frosted ‘Tên · Chức danh’."
- "Thêm counter 40% / 3000 users ở giây 0:08, và mockup dashboard bay vào từ phải."
- "Highlight chữ ‘3 days’ ở payoff; close tag ‘100% Remote’ ở cuối."
- "Xuất 1080p 10-bit; thêm bản 9:16 cho IG."

---

## 12. Tổ chức file (pipeline brand đã xây)

```
videos/edit/brand/
├── kit.py / kit1080.py        # design-system + helper (1080 auto-scale ×S)
├── build_*.py                 # generator: title/outro, lower-third, counter, mockup, typo, panel, closetag
├── leak*.png                  # light-leak cho grade
├── footage_graded*.mp4        # footage sau grade (nền cho mọi overlay)
├── <asset>/%04d.png           # chuỗi khung RGBA của từng overlay
├── title.mp4 / outro.mp4 / footage_fx.mp4
videos/edit/
└── final.mp4 / *_1080p10_native.mp4   # bản giao
```

---

## 13. Giới hạn (nói thẳng)

- Chi tiết footage giới hạn ở res gốc; mockup là **giả-3D** (perspective warp), không phải engine 3D thật.
- Không transcribe ⇒ mốc giây phải do bạn cấp hoặc mình tự canh (rồi bạn duyệt).
- Ảnh dán chat ≠ file → cần upload file để dùng pixel thật.
- `zoompan` gây rung → luôn dùng reveal render-sẵn.
