# WiFi-BSSID-Manager

A lightweight Linux system tray utility for managing Wi-Fi BSSID pinning through NetworkManager D-Bus.

**WiFi-BSSID-Manager** は，LinuxのNetworkManagerでWi-Fi接続先のBSSID固定を操作する小さなシステムトレイアプリです．大学や企業など，同じSSIDを持つアクセスポイント（AP）が多数存在し，ローミング時に接続が不安定になる環境を想定しています．

接続中のAPにBSSIDを固定するか，保存済みの全Wi-Fi接続プロファイルからBSSID指定を解除できます．**Wi-Fiに接続できない状態でも一括解除が可能**です．

## 主な機能

- **現在のBSSIDを固定**：現在のSSID・BSSIDを表示し，接続中のWi-Fiプロファイルへ保存して再接続します．
- **すべてのBSSID固定を解除**：NetworkManagerに保存された全Wi-Fi接続プロファイルからBSSID指定のみを削除します．接続中のプロファイルが変更された場合は再接続します．
- **未接続でも復旧可能**：固定先APの圏外に移動しても，保存済みのBSSID制限を解除できます．
- **Wi-Fiインターフェース自動検出**：通常はコマンドライン引数が不要です．
- **D-Bus APIを使用**：`nmcli`や`iw`の定期実行に依存しません．
- **独自のトレイアイコン**：実行時にPython標準ライブラリで画像を生成します．Pillowは不要です．アプリケーションメニュー用には同じデザインのPNGを同梱しています．

## 動作のイメージ

| 操作 | 設定変更 | 接続への影響 |
| --- | --- | --- |
| 現在の接続先のBSSIDを固定化 | 現在のWi-FiプロファイルのBSSIDに，接続中APのアドレスを設定 | 対象Wi-Fi接続を再接続 |
| すべての接続先プロファイルからBSSID設定を削除 | 保存済みWi-FiプロファイルのBSSID指定を一括削除 | 現在の接続プロファイルを変更した場合だけ再接続 |

**注意：** BSSID固定中は，固定したAPが届かない場所に移動すると，同じSSIDの別APが利用可能でも接続できない場合があります．その場合はトレイメニューの一括解除を実行してください．SSID，パスワード，接続プロファイルそのものは削除しません．

## 動作環境

- Linux（NetworkManagerでWi-Fiを管理している環境）
- Python 3，PyGObject（GTK 3），`dbus-python`
- Ayatana AppIndicatorが表示できるデスクトップ環境

Ubuntu Desktopでの利用を想定しています．その他のディストリビューションやデスクトップ環境では，必要なパッケージやトレイの対応状況が異なる場合があります．

## インストール（Ubuntu）

```bash
sudo apt update
sudo apt install python3-gi python3-dbus gir1.2-gtk-3.0 \
  gir1.2-ayatanaappindicator3-0.1 network-manager
```

GNOMEでトレイアイコンが表示されない場合は，AppIndicator対応のシェル拡張機能を確認してください．Ubuntuでは，必要に応じて次を導入します．

```bash
sudo apt install gnome-shell-extension-appindicator
```

リポジトリを取得して起動します．

```bash
git clone https://github.com/takago/WiFi-BSSID-Manager.git
cd WiFi-BSSID-Manager
/usr/bin/python3 wifi-bssid-manager.py
```

上記GitHub URLは**公開予定のリポジトリ名**を前提としています．リポジトリを作成した後に利用してください．

### `/usr/local/bin`へインストールする場合

リポジトリのディレクトリで実行権限を付与し，コマンド名`wifi-bssid-manager`で配置できます．

```bash
chmod +x wifi-bssid-manager.py
sudo install -m 755 wifi-bssid-manager.py /usr/local/bin/wifi-bssid-manager
```

これ以降は作業ディレクトリに関係なく，次のコマンドで起動できます．Wi-Fiインターフェースは自動検出されます．

```bash
wifi-bssid-manager
```

`/usr/local/bin`への配置後も，Python関連の依存パッケージは上記の手順でインストールする必要があります．このアプリ自体は管理者権限で起動しないでください．NetworkManagerへの設定変更は，ログインユーザーのD-Busセッションと権限で実行します．

最新版に更新するときは，リポジトリで`git pull`を実行してから，再度`sudo install -m 755 ...`を実行してください．実行中の旧アプリは終了してから起動し直します．

```bash
git pull
sudo install -m 755 wifi-bssid-manager.py /usr/local/bin/wifi-bssid-manager
```

本体をアンインストールする場合は，以下のコマンドを実行します．アプリケーションメニューと自動起動の登録も上記の手順で削除してください．NetworkManagerに保存されたBSSID固定設定は変更されません．

```bash
sudo rm /usr/local/bin/wifi-bssid-manager
```

### アプリケーションメニューに登録する（Ubuntu Desktop）

本体を`/usr/local/bin/wifi-bssid-manager`へインストールした後，専用アイコンと`.desktop`ファイルを配置します．

```bash
sudo install -D -m 644 wifi-bssid-manager.png \
  /usr/local/share/icons/hicolor/64x64/apps/wifi-bssid-manager.png
mkdir -p ~/.local/share/applications
install -m 644 wifi-bssid-manager.desktop \
  ~/.local/share/applications/wifi-bssid-manager.desktop
```

これでGNOMEの「アプリを表示」などから**WiFi BSSID Manager**を検索して起動できます．アプリを開くとトレイに常駐します．メニューへの登録自体は自動起動を有効にしません．

メニュー登録を削除する場合は，次を実行します．

```bash
rm ~/.local/share/applications/wifi-bssid-manager.desktop
```

専用アイコンも使わなくなった場合に限り，次のコマンドで削除できます．自動起動用`.desktop`ファイルも同じアイコンを参照しているため，継続利用する場合は削除しないでください．

```bash
sudo rm /usr/local/share/icons/hicolor/64x64/apps/wifi-bssid-manager.png
```

### ログイン時に自動起動する（Ubuntu Desktop）

`/usr/local/bin/wifi-bssid-manager`へのインストール後，ユーザーごとの自動起動設定を登録できます．専用アイコンは上記のメニュー登録手順で配置してください．リポジトリに同梱した`wifi-bssid-manager.desktop`を使用します．

```bash
mkdir -p ~/.config/autostart
install -m 644 wifi-bssid-manager.desktop ~/.config/autostart/
```

次回の**デスクトップへのログイン時**から，システムトレイに自動起動します．登録直後に試す場合は，現在のトレイアプリが起動していないことを確認してから次を実行してください．

```bash
wifi-bssid-manager
```

自動起動を無効化する場合は，次のファイルを削除します．

```bash
rm ~/.config/autostart/wifi-bssid-manager.desktop
```

この設定はユーザー単位です．`sudo`を使って`~/.config/autostart/`に配置しないでください．また，`.desktop`内の`Exec`は`/usr/local/bin/wifi-bssid-manager`を指定しているため，**先に上記のコマンドで本体をインストール**してください．これはGUIログイン時の自動起動であり，OS起動時にバックグラウンドサービスとして動作するものではありません．GNOMEではAppIndicator拡張機能が必要な場合があります．

Wi-Fiインターフェースを明示する場合は，次のように指定できます．

```bash
/usr/bin/python3 wifi-bssid-manager.py wlp6s0
```

## 使い方

システムトレイの専用アイコンをクリックして操作します．メニューには次の項目があります．

1. **全ての接続先プロファイルからBSSID設定を削除して，Wi-Fiを再接続する**
2. **現在の接続先（SSID）のBSSID（MACアドレス）を固定化して，Wi-Fiを再接続する**
3. **終了**

固定操作はWi-Fi接続中にのみ利用できます．すでにそのBSSIDに固定されている場合は選択できません．一括解除は未接続でも利用できますが，固定指定が一つもない場合は無効になります．

操作時に確認ダイアログは出ません．対象Wi-Fi接続の再接続によって，通信が一時的に途切れます．NetworkManagerサービス自体を再起動するわけではありません．

## コマンドラインで設定を確認

保存済みプロファイルのBSSID固定状態：

```bash
nmcli -g 802-11-wireless.bssid connection show "KIT-WLAP2"
```

MACアドレスが表示されれば固定設定が保存されています．空欄なら固定指定はありません．現在接続しているAPは以下で確認できます．

```bash
iw dev wlp6s0 link
```

## 設計上の注意点

- 設定はNetworkManagerのD-Bus API（`ListConnections()`，`GetSettings()`，`Update2()`）で読み書きします．
- 接続中のプロファイルを変更した場合，`DeactivateConnection()`と`ActivateConnection()`で対象接続を再接続します．`Reapply()`はBSSID変更に対応しない環境があるため利用しません．
- 保存済みプロファイルのBSSID解除は，Wi-Fi未接続でも可能です．解除後の接続成功は，電波状況・認証設定・自動接続設定によります．
- 一括解除中に更新が失敗したプロファイルがあればエラーを表示します．その時点までに成功した変更はロールバックしません．
- ほかのWi-Fi設定は保持するよう，既存プロファイルを読み取ってBSSID項目のみを書き換えます．ただし，認証情報の保存方式などによって動作が異なる場合があるため，重要な接続プロファイルはバックアップしてから使用してください．
- このツールはローミング障害の根本原因（APの設定，認証処理やドライバの不具合）を修正するものではありません．BSSID固定による回避手段です．

## 開発・検証状況

本ツールはUbuntu系のNetworkManager環境での利用を想定して開発しています．BSSID固定設定の保存と解除は実環境で確認されています．ただし，公開対象の最新コードについて，全ディストリビューションでの動作や，Wi-Fi未接続時を含む全操作の検証が完了しているわけではありません．

## ライセンス

ライセンスは公開時に決定してください．オープンソースとして配布する場合は，MIT Licenseなどを候補にできます．
