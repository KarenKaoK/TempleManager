
## Env 

### 安裝指令
```
python3 -m venv temple_venv
source ./temple_venv/bin/activate

pip install --upgrade pip
pip install PyQt5==5.15.9 PyQt5-sip
pip install bcrypt


```

### 驗證安裝成功

- pyqt 安裝成功： 會有彈跳視窗
    ```
    python -c "from PyQt5.QtWidgets import QApplication, QLabel; app = QApplication([]); label = QLabel('PyQt5 安裝成功！'); label.show(); app.exec_()"
    ```
- qtdesigner
    - 官網下載 dmg 安裝(https://build-system.fman.io/qt-designer-download)
    - apple 安全性強制打開

- bcrypt
    ```
    python -c "import bcrypt; print('bcrypt 安裝成功！')"
    ```

## Dev logs

### 登入畫面

需求：
1. 應用程式啟動時，先彈出登入視窗
2. 使用者輸入帳號 & 密碼後驗證（儲存在 SQLite 資料庫）
3. 登入成功後，開啟主視窗
4. 如果登入失敗，顯示錯誤訊息
5. 加上權限四個角色：admin, accountant, committee, staff
