# Human Evaluation Survey

Pairwise preference study: Phys-GRPO vs FramePack Base on physical plausibility and visual quality.

## Setup Steps

### 1. Add videos

Place your videos in:
```
videos/base/test_01.mp4 ... test_14.mp4      <- FramePack baseline
videos/physgrpo/test_01.mp4 ... test_14.mp4   <- Phys-GRPO (ours)
```

### 2. Host the survey page

The survey must be hosted on a public URL (videos play in-browser).

**Option A: GitHub Pages (free, easiest)**
```bash
# Create a separate repo or branch
git init human-eval-survey
cp -r human_eval/* human-eval-survey/
cd human-eval-survey
git add . && git commit -m "survey"
gh repo create your-username/physics-video-eval --public --source=.
git push -u origin main
# Enable Pages: Settings -> Pages -> Source: main branch
# URL: https://your-username.github.io/physics-video-eval/survey.html
```

**Option B: Netlify Drop (drag & drop)**
- Go to https://app.netlify.com/drop
- Drag the entire `human_eval/` folder
- Get a URL instantly

### 3. Set up data collection (Google Sheets)

1. Create a new Google Sheet
2. Go to **Extensions -> Apps Script**
3. Paste this code:

```javascript
function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);

  // One row per participant
  var row = [
    data.participant_id,
    data.timestamp,
    data.duration_seconds,
    data.demographics.physics_background,
    data.demographics.ai_video_experience,
    data.comments,
  ];

  // Add responses (3 columns per trial: physics, visual, confidence)
  data.responses.forEach(function(r) {
    row.push(r.physics_mapped, r.visual_mapped, r.confidence);
  });

  sheet.appendRow(row);
  return ContentService.createTextOutput("OK");
}
```

4. Click **Deploy -> New deployment -> Web app**
   - Execute as: **Me**
   - Who has access: **Anyone**
5. Copy the web app URL and paste it into `survey.html` as `SHEETS_WEBHOOK_URL`

---

## Recruitment Platform Options

### Option A: Wenjuanxing (问卷星) — Recommended for Chinese annotators

Cost: ~200 RMB (~$28 USD) for 30 participants.

#### Step-by-step setup:

1. **Create a 问卷星 survey** at https://www.wjx.cn
   - Add one question: "请点击以下链接完成视频评估 / Click the link below to start the video evaluation"
   - The question type can be "描述说明" (description) — no answer needed
   
2. **Set up the redirect chain:**
   - In 问卷星, go to **设置 -> 答题后跳转** (Post-completion redirect)
   - Set it to redirect to your hosted survey URL:
     ```
     https://your-site.github.io/survey.html?sojumpparm=${问卷星参数}
     ```
   - In `survey.html`, set `WENJUANXING_REDIRECT_URL` to your 问卷星 completion page:
     ```
     https://www.wjx.cn/vm/xxxxxxx.aspx
     ```

3. **Alternative (simpler): Direct link approach**
   - Don't create a real 问卷星 survey
   - Just use 问卷星's **样本服务** (sample service) to recruit participants
   - Give them the direct GitHub Pages URL
   - They complete the survey and get auto-redirected back

4. **Configure `survey.html`:**
   ```javascript
   const WENJUANXING_REDIRECT_URL = "https://www.wjx.cn/vm/xxxxxxx.aspx";
   const SHEETS_WEBHOOK_URL = "https://script.google.com/macros/s/xxx/exec";
   ```

5. **Quality controls already built in:**
   - Randomized A/B order per trial (eliminates position bias)
   - Randomized trial presentation order
   - Bilingual (English + Chinese) instructions and questions
   - Duration tracking (filter out submissions < 3 min)
   - Google Sheets auto-collection + localStorage backup

#### 问卷星 pricing reference:
| Item | Cost |
|------|------|
| 30 participants via 样本服务 | ~150-200 RMB |
| **Total** | **~200 RMB (~$28 USD)** |

### Option B: Prolific — For English-speaking annotators

1. Go to https://www.prolific.com -> New Study
2. **Study link**: paste your hosted survey URL
   - Add `?PROLIFIC_PID={{%PROLIFIC_PID%}}` to the URL
3. **Completion code**: set to match `PROLIFIC_COMPLETION_CODE` in survey.html (default: `C1X8K9PH`)
4. **Settings**:
   - Participants: 30
   - Estimated time: 20 minutes
   - Reward: GBP 2.50-3.00 per participant
   - Pre-screening: English fluency, approval rate > 95%

| Item | Cost |
|------|------|
| 30 participants x GBP 3.00 | GBP 90 |
| Prolific service fee (33%) | GBP 30 |
| **Total** | **~GBP 120 (~$150 USD)** |

---

### 4. Analyze results

Export from Google Sheets as JSON, or from browser console:
```javascript
// In browser console:
copy(localStorage.getItem("survey_results"))
// Paste into results.json
```

Then run:
```bash
python analyze_results.py results.json
```

This outputs:
- Win rates with binomial significance test
- Per-phenomenon breakdown
- Fleiss' kappa (inter-annotator agreement)
- Ready-to-paste LaTeX table

---

## Writing it up in the thesis

The human evaluation section (Section 5.8) in `main.tex` has TODO placeholders. After collecting data, run `analyze_results.py` and fill in:

- `N_TODO` / `N_VALID_TODO` -> participant counts
- `T_TODO` -> median completion time
- Table `tab:human_eval` -> win/loss/tie counts and p-values
- `KAPPA_PHYS_TODO` / `KAPPA_VIS_TODO` -> Fleiss' kappa values
- `INTERP_TODO` -> kappa interpretation (slight/fair/moderate/substantial)
- Interpretation paragraph
