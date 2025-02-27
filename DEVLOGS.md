# DEVLOGS

## 2025 年 2 月 28 日

## 2025 年 2 月 27 日

### 🎯 **今日目標**:

1. 登入使用者角色歡迎詞
![alt text](/images/login_welcome.png)
2. 收入項目建檔作業
![alt text](/images/config_setting_income_1.png)
![alt text](/images/config_setting_income_2.png)
![alt text](/images/config_setting_income_3.png)

### ✅ 今日完成項目
1. 收入項目建檔作業

- 完成收入項目 **新增**、**修改**、**刪除** 功能
- **新增功能**
    - 使用者可以輸入「收入項目代號、名稱、捐助金額」，一次完成輸入
    - 金額輸入框改為 `QSpinBox`，確保僅輸入整數
    - 代號 `id` 由系統自動產生，避免使用者輸入重複 ID
- **修改功能**
    - 使用 `QDialog + QFormLayout`，讓使用者一次修改「名稱 & 金額」，減少彈跳視窗
    - `收入項目代號 (id)` 為固定值，**不可修改**
- **刪除功能**
    - **修正 SQL DELETE 問題**，確保 `id` 為整數 `(int)`
    - **修正 UI 按鈕無反應問題**，刪除後 UI 立即更新
    - **確認刪除視窗**，按鈕文字改為「是 / 否」，提升使用者體驗

2️. SQLite 資料庫調整

- 撈取 `income_items` 數據
    - 撰寫測試程式 `fetch_income_items()`，確認目前資料庫內的收入項目
- 修正 SQL 操作
    - `DELETE FROM income_items WHERE id = ?` **改為 tuple `(id,)`**
    - 先檢查 `income_items` 是否存在，避免刪除錯誤

3️. **優化 UI 操作體驗**

- 刪除確認視窗改為「是 / 否」，符合直覺操作
- 修改 & 新增操作都改為單一彈跳視窗，減少不必要的輸入步驟
- 刪除後 UI 立即更新，不需重新啟動應用程式

## 2025 年 2 月 26 日

### 🎯 **今日目標**：建立登入功能，並擴展使用者角色管理

### ✅ 今日完成項目

1. **環境安裝與設定**
    - 安裝 **PyQt5、Qt Designer、bcrypt、SQLite** 等必要套件
    - 解決 **PyQt5-tools 安裝問題**，確認 `Qt Designer` 正常運行
2. **開發登入功能**
    - 使用 **PyQt5** 設計 **登入 UI（login.ui）** 並轉換為 Python 代碼
    - 建立 **SQLite `users.db`** 資料庫
    - **加密儲存密碼**（使用 `bcrypt`）
    - **驗證帳號密碼**，登入成功後開啟主視窗
3. **擴展使用者角色管理**
    - **新增 3 個角色**：會計（accountant）、委員（committee）、工作人員（staff）
    - 更新 **`users` 表**，確保 `role` 欄位支援這些角色
    - **自動建立角色帳號（如不存在則創建）**
    - 確保登入時顯示對應的使用者角色
4. **程式結構調整**
    - 整合 **`setup_users.py`**，確保 **資料表建立 + 預設帳號初始化**
    - 修正 `login.py` 讓 **登入時顯示角色名稱**
    - 進一步規劃 **未來權限管理**（不同角色可存取不同功能）
