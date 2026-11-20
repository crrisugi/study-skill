# Changelog

All notable changes to `study-skill` will be documented in this file.

## [0.2.0] - 2026-11-20

### Added
- 新增百页长卷伴学总图与跨单元按需规程 `skills/study/workflows/long-corpus.md`，支持自适应深浅摸底、独立目录隔离与跨单元前提继承。
- 新增跨宿主低打扰更新探测与按来源分流升级脚本 `skills/study/scripts/check_update.py`（纯标准库，支持 `npx skills` / `git-clone` / 宿主插件 / 手动复制识别、`72h` 缓存与 `6h` 失败负缓存、GitHub Releases 302 探测）。
- 在 `plot_helper.py` 退出阶段挂载非阻塞更新提示旁路，并在 `study-feedback` 补入轻量版本提示入口与 `lint_study.py` 版本一致性和更新自检门禁。

### Changed
- 优化分卡伴学主干推演：`SKILL.md` 明确多物理量并列概览节按原序排卡并先立主线骨架、收紧 `k-A/k-B` 适用范围、原式首次出场逐一交代新符号下标与正斜体区分，以及降维算例先说明暂略层。

## [0.1.0] - 2026-11-18

### Added
- 初始发布 `study` 与 `study-feedback` 双技能、`10` 份正交草稿纸表征文件、`plot_helper.py` 科学矢量绘图底座及跨三端 `lint_study.py` 静态与冒烟 CI 门禁。
