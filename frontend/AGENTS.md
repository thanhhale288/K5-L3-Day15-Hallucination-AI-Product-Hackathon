# AGENTS.md (frontend)

Hướng dẫn cho coding agent khi sửa `frontend/`. Luật chung của repo ở `../AGENTS.md`.

- Stack: React 19 + Vite + Tailwind v4 (`@tailwindcss/vite`) + shadcn/ui (style `base-nova`, chạy trên Base UI) + Motion (`motion/react`) + NumberFlow.
- Component shadcn nằm ở `src/components/ui/`. Thêm component: `npx shadcn@latest add <tên>`.
- Màu theo nghĩa, khai trong `src/index.css`: `profit` (lãi), `fee` (phí bắt buộc), `switch` (công tắc), `alert` (lệch / không khớp luật), `ink`, và màu từng sàn. Dùng các class như `bg-profit` hay `text-alert`, không viết mã màu trực tiếp trong component.
- Frontend **không tự tính số hiển thị**. Mọi số tiền trên màn lấy nguyên từ JSON H4 hoặc từ kết quả what-if của bridge. Cộng dồn trong `Waterfall.tsx` chỉ để đặt vị trí thanh, không hiện thành số.
- Không đụng lớp agent khi chỉ sửa giao diện: `src/agent/*` (AG-UI) và `agui/server.py`.
- Animation tôn trọng `prefers-reduced-motion`: `MotionConfig reducedMotion="user"` ở `main.tsx`, và CSS `shimmer` / `beam` tắt theo media query.
