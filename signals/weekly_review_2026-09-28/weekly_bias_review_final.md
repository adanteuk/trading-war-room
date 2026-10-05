📊 NAS100 週度偏向準確度檢討 — Week of 2026-09-28 (9/28–10/2)

**週準確率**: 4/4 方向性偏向命中 = 100%（9/30 中性訊號不計入方向性統計）
**平均信心**: 55.0%（方向性 4 日）；含中性為 52.0%

計分口徑：各日偏向於 ~18:30–19:00 HKT（紐約盤前）發出，針對當日剩餘時段 → 以「發出價 vs 當日收盤」計方向。

**Daily Breakdown:**
• Mon 9/28: 預測 bearish（信心 55%）→ 收盤低於發出價 28.0pt（30,338.3→30,310.3），TP1 30100.9 當日觸及（session low 30100.8，0.1pt 精確掃過）✅
• Tue 9/29: 預測 bullish（55%）→ 收盤高於發出價 43.9pt（30,360.2→30,404.1），TP1 30449.1 觸及（高 30472.3）✅
• Wed 9/30: 預測 neutral（40%）→ 雙向走勢（低 30262.6 / 高 30655.5），S&D 判讀合理 ➖（不計入）
• Thu 10/1: 預測 bearish（58%）→ 發出價 30,647 後 -119.9pt（-0.39%），BSL 30903.8 拒絕後 NY 分布至低 30285.4 ✅（註：日線 c2c 仍 +0.19% 收陽——以發出後口徑計命中）
• Fri 10/2: 預測 bullish（52%）→ BSL 30903.8 被掃（高 31038.0，+134.2pt 穿越），發出價 30,728 後 +80.3pt（+0.26%）收 30,808.3 ✅

**週度收盤（CFD，NY session dates）**: Mon 30,310.3 / Tue 30,404.1 / Wed 30,469.2 / Thu 30,527.1 / Fri 30,808.3
**c2c**: -1.11% / +0.31% / +0.21% / +0.19% / +0.92% | 週 +0.51%（9/25 收 30,650.5 → 10/2）

**Patterns Observed**:
① Draw-on-liquidity 3/3 精確：Mon SSL 掃 0.1pt、Thu BSL 拒絕、Fri BSL 穿越 +134pt
② SMT 訊號 2/2：Tue 看漲 SMT（US500 掃 Mon 低 7655.5<7668.4 且守 Sep-24 SSL 7650.3（5.2pt）而 NAS100 守住）；Thu 看跌 SMT（NAS100 掃 Sep-23 高 30903.8>30820.4 而 US500 ONH 7711.7 未過其 Sep-22 高 7785.0）
③ 週三中性（S&D）判讀與雙邊 raid 週一致

**Confidence Calibration**: 最高信心 Thu 58% 反而最「骯髒」（日線仍收陽，僅發出後口徑命中）；52–55% 的 Mon/Tue/Fri 命中質量更高。信心區間過窄（52–58），未有效區分確定性。

**Improvement Notes**:
① 午後發出的偏向應同時聲明「發出後」與「日線 c2c」兩種計分口徑（Thu 為例證）
② 信心應反映日線背景與日內偏向的衝突（Thu 應 ≤50）
③ Mon 型 setup（terminal-equal SSL + purge + close off low）最乾淨，值得在未來偏向加權

🧑‍💼 EDITOR VERDICT
- ✅ 5 份 walker_ta.json（bias/confidence/current_price）— verified via editor 獨立讀取訊號檔
- ✅ 5 日 session closes + c2c + 週 +0.51% — verified via Carson MT5 ZMQ bridge 獨立重抓（diff 0.0）
- ✅ 極值（Mon 低 30100.8 / Tue 高 30472.3 / Wed 30262.6–30655.5 / Thu ONH 30903.8、低 30285.4 / Fri 高 31038.0）— verified via re-fetch
- ✅ Swing levels（NAS100 28756.7 / 30820.4 / 30100.9 / 30788.3）— verified via re-fetch
- ✅ US500 SMT levels（7785.0 / 7725.2 / 7711.7 / 7650.3 / 7668.4 / 7655.5）+ 兩組 SMT 邏輯重算 — verified via re-fetch + recompute
- ✅ Fri 收盤定盤 30808.3（最後 M15 20:45Z、meta.last_price 一致）— verified via re-fetch
- ✅ Fri 方向 UP — verified via Yahoo NQ=F 10/2 +0.94%（方向與 CFD +0.92% 一致）
- ✅ Thu 收盤位置 39.1% of range — verified via recompute
- ✅ 時間範圍（9/28–10/2，無未來/錯標日期）與相關性 — verified
Final: 48 verified, 0 corrected, 0 uncertain

（分析教育用途，非投資建議）
