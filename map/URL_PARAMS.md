# 網址（URL）參數說明 / 註解（Shareable Map URLs）

本專案的互動地圖會把「使用者點擊的狀態」寫進網址的 query string（`?key=value`），讓你可以：

- 分享連結：別人打開同一個網址，會還原相同的圖層/語言/面板內容
- SEO / 收錄：同一張地圖可用不同 URL 表達不同主題（但本專案目前是純前端頁面，是否能被完整索引仍取決於你的部署與爬蟲策略）

重要：**不會記錄地圖的縮放與拖曳視角**（不會產生 `lat/lng/z` 之類參數）。

---

## 1) 基本規則

- 網址由「路徑」＋「query 參數」組成，例如：`/index.html?base=terrain&contours=1`
- 參數使用 `history.replaceState` 寫入，不會重新整理頁面
- 使用瀏覽器上一頁/下一頁（`popstate`）會套用網址參數並更新地圖狀態
- 布林值（開/關）接受以下格式：
  - `1` / `0`
  - `true` / `false`
  - `?contours`（只有 key 沒有 value）視為 **開啟**

---

## 2) 參數一覽（你最常用的）

### A. 底圖（base layer）

用 `base=...` 表示「底圖樣式」（互斥，只會有一個為 true）。

- `base=baseDefault`（預設，不一定會出現在網址中）
- `base=terrain`
- `base=topo`
- `base=outline`

範例：

- `?base=terrain`

相容寫法（舊/方便寫法）：

- `?layer=terrain`（等同 `base=terrain`）
- `?terrain=1`（把 terrain 當成 base 的「快速開啟」寫法）

---

### B. 圖層開關（layers）

除 base 以外的圖層會以「圖層 id」作為 query key 記錄。

例：

- `?contours=1`（等高線）
- `?currents=1`（洋流）
- `?tectonicPlates=1`（板塊）
- `?worldpopDots=1`（人口點）
- `?graticule=1`（經緯網）
- `?names=0`（關閉國家名稱）
- `?oceans=0`（關閉海洋名稱）
- `?admin=1`（行政/首都標註）

相容別名（aliases）：

- `contour` → `contours`
- `plates` / `tectonic` → `tectonicPlates`
- `pop` / `population` / `populationdensity` / `worldpop` → `worldpopDots`

---

### C. 語言（language）

- `lang=zh`（預設）
- `lang=en`

範例：

- `?lang=en&base=terrain`

---

### D. 板塊點擊模式（tectonic click mode）

只有在板塊圖層啟用時才會持久寫入：

- `mode=plate`：板塊模式（可點板塊）
- `mode=country`：國家模式（板塊只當背景，點擊穿透到國家）

範例：

- `?tectonicPlates=1&mode=plate`
- `?tectonicPlates=1&mode=country`

---

### E. 資料顯示（資訊面板欄位，Data Display）

使用 `fields=` 記錄「資訊面板要顯示哪些欄位」。

- 格式：`fields=id1,id2,id3`
- 只有在「不是預設欄位組合」時才會出現在網址中（避免網址太長）

可用欄位 id（以程式內 `PANEL_FIELDS` 為準）常見包含：

- `capital`, `region`, `subregion`, `latlng`, `googleMaps`
- `pop`, `area`, `density`
- `languages`, `demonym`, `currency`, `timezone`
- `driveSide`, `idd`, `unMember`, `orgs`

範例：

- `?fields=capital,pop,currency,timezone`

---

## 3) 「點擊顯示資訊面板」也會記錄（國家/洋流/板塊）

當你點擊地圖，開啟資訊面板時，網址會多記錄「目前面板顯示的對象」。

注意：**三者同時只能有一種**（最後一次打開的面板會覆蓋前一個）。

### A. 國家面板

- `country=` 使用地圖 GeoJSON 的「canonical key」：`ADMIN/NAME/name`（通常是英文國名）
- 例：`country=Japan`

範例：

- `?country=Japan`
- `?base=terrain&contours=1&country=Japan`

### B. 洋流面板

- `current=` 使用洋流資料的 `nameEn`（英文名稱，完全比對）
- 例：`current=Kuroshio`

範例：

- `?currents=1&current=Kuroshio`

補充：如果網址帶 `current=...`，系統會**自動把 `currents` 圖層打開**，確保連結打開就能看到洋流脈絡。

### C. 板塊面板

- `plate=` 使用板塊 **代碼**（plate code），例如 `PA`、`NA` 等（實際代碼以資料集為準）

範例：

- `?tectonicPlates=1&mode=plate&plate=PA`

補充：如果網址帶 `plate=...`，系統會**自動把 `tectonicPlates` 圖層打開**。
由於板塊多邊形是非同步載入，開啟面板可能會稍等片刻才出現（程式會自動重試）。

---

## 4) 參數優先順序（建議你理解的行為）

1. 先以 `LAYER_DEFS` 的預設值初始化
2. 套用 URL 的 `lang`、`base/layer`、各圖層開關、`fields`、`mode`
3. 最後套用選取（`country` / `current` / `plate`）並打開面板

---

## 5) 常見分享範例

- 地形＋等高線：
  - `?base=terrain&contours=1`
- 洋流＋指定洋流面板（會自動確保 currents 開啟）：
  - `?current=Kuroshio`
  - 或明確一點：`?currents=1&current=Kuroshio`
- 板塊（板塊模式）＋指定板塊面板：
  - `?tectonicPlates=1&mode=plate&plate=PA`
- 英文介面＋人口點：
  - `?lang=en&worldpopDots=1`

---

## 6) URL 編碼注意事項

- `country` / `current` 可能包含空白或特殊字元時，瀏覽器會自動 URL encode。
  - 例如 `North Atlantic Drift` 會變成 `North%20Atlantic%20Drift`
- 你通常不用手動處理；複製瀏覽器網址列即可。
