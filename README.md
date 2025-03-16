# Temple Manager 

## Introduction
Temple Manager 是一個專為寺廟社群設計的 **管理運營系統**，幫助寺廟進行信眾身份管理、收支記錄、安燈拜斗設定、法會活動與求神問事記錄等，協助寺廟進行信眾管理、捐獻記錄、光明燈、文昌燈等多項業務。

本系統旨在簡化 **寺廟運營、財務管理與收支紀錄**，適合用於中小型廟宇，提升管理效率。

## Features

## Tech Stack

## Environment

安裝指令

```
python3 -m venv temple_venv
source ./temple_venv/bin/activate

pip install --upgrade pip
pip install PyQt5==5.15.9 PyQt5-sip
pip install bcrypt

pip install pytest
```

驗證安裝成功
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


## Usage


## Git Flow

- 開發流程

    1. **feature**（功能開發）  
    - 針對單一功能開發，分出 `feature/xxx` 分支，例如 `feature/login`
    - 開發完成後，PR 合併到 `dev`
    
    2. **dev**（開發 & 測試）  
    - 所有 `feature` 會先合併到 `dev`
    - 進行基本測試（單元測試 & 整合測試）
    - 確認無誤後，推送到 `release` 做最後驗證

    3. **release**（預備上線）  
    - 這裡是 **穩定測試環境**，開發完成的功能在這裡做最後的測試
    - 測試通過後，即可合併到 `main`

    4. **main**（正式版）  
    - 確認 `release` 無誤後，合併到 `main`，並正式發布

    5. **hotfix**（緊急修正）  
    - 若 `main` 有重大 Bug，需要立即修正時：
        - **從 `main` 分出 `hotfix/xxx`**
        - 修正後 **直接合併回 `main`**，並同步回 `dev` 確保開發版本一致

- 開發分支流程圖

    ```
    (feature) ---> dev ---> release ---> main
                        \  
                        \-- hotfix (from main)
    ```
