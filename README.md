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
- **状態に応じたトレイアイコン**：丸い背景を，現在の接続がBSSID固定中なら赤，自動ローミング中なら青，未接続ならグレーで表示します．SSIDには依存しません．実行時にPython標準ライブラリで画像を生成するため，Pillowは不要です．メニュー用PNGは従来の固定デザインです．

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

依存パッケージをインストールします．

```bash
sudo apt update
sudo apt install make python3-gi python3-dbus gir1.2-gtk-3.0 \
  gir1.2-ayatanaappindicator3-0.1 network-manager
```

GNOMEでトレイアイコンが表示されない場合は，AppIndicator拡張機能を確認してください．

```bash
sudo apt install gnome-shell-extension-appindicator
```

GitHubに公開後は，次のように取得してインストールできます．

```bash
git clone https://github.com/takago/WiFi-BSSID-Manager.git
cd WiFi-BSSID-Manager
sudo make install
```

`sudo make install`はスクリプトを`/usr/local/bin/wifi-bssid-manager`へ，アイコンを`/usr/local/share/icons/hicolor/64x64/apps/`へ，アプリケーションメニュー登録用`.desktop`を`/usr/local/share/applications/`へ配置します．これらはシステム共通の設定です．

GitHubリポジトリが未公開の場合は，配布ZIPを展開して同じコマンドを実行できます．

起動コマンド：

```bash
wifi-bssid-manager
```

### ログイン時に自動起動（個人設定）

インストール後，ログイン時の自動起動を有効化できます．

```bash
make autostart
```

自動起動を解除する場合：

```bash
make no-autostart
```

自動起動はオプションです．`sudo make install`だけでは有効になりません．**`make autostart`と`make no-autostart`にはsudoを付けないでください**．デスクトップログイン時に起動する仕組みであり，systemdのシステムサービスは追加しません．

### 更新・アンインストール

```bash
git pull
sudo make install
```

実行中の旧アプリは終了してから起動し直してください．

アンインストール：

```bash
sudo make uninstall
```

本体，メニュー登録，アイコンをシステムから削除します．個人用の自動起動設定は別管理なので，解除する場合は**一般ユーザー**として次を実行します．

```bash
make no-autostart
```

NetworkManagerの接続プロファイルは変更しません．

### 手動起動・インターフェース指定

リポジトリ内のソースを直接実行する場合：

```bash
/usr/bin/python3 wifi-bssid-manager.py
```

Wi-Fiインターフェースを指定する場合：

```bash
wifi-bssid-manager wlp6s0
```

## 使い方

システムトレイの専用アイコンをクリックして操作します．メニューには次の項目があります．

1. **全ての接続先プロファイルからBSSID設定を削除して，Wi-Fiを再接続する**
2. **現在の接続先（SSID）のBSSID（MACアドレス）を固定化して，Wi-Fiを再接続する**
3. **終了**

固定操作はWi-Fi接続中にのみ利用できます．すでにそのBSSIDに固定されている場合は「AP(SSID)は固定BSSID(MACアドレス)に接続しています」と表示し，その項目は選択できません．一括解除は未接続でも利用できますが，固定指定が一つもない場合は無効になります．

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

## ローミング・切断のログを監視する（参考）

Wi-Fiが不安定な場合は，別の端末で次のコマンドを実行すると，`wpa_supplicant`が出力する認証・接続・切断イベントをリアルタイムに確認できます．

```bash
sudo journalctl -fu wpa_supplicant | \
  grep --line-buffered -E 'Trying to (authenticate|associate)|CTRL-EVENT-CONNECTED|CTRL-EVENT-DISCONNECTED'
```

異なるBSSIDへの接続が連続して表示される場合は，AP間の切り替えが発生している可能性があります．切断時の`reason`や`locally_generated`も原因調査の参考になります．ただし，このログだけで切断原因やローミングの良否を断定することはできません．

現在接続しているAPのBSSIDを確認するには，次のコマンドも使用できます（インターフェース名は適宜置き換えてください）．

```bash
watch -n 1 'iw dev wlp6s0 link | head -n 3'
```

`journalctl`の監視は`Ctrl+C`で終了できます．環境によっては，`wpa_supplicant`ではなく`iwd`がWi-Fi認証を管理している場合があり，その場合は上記ログが出力されません．

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

### Makefileの権限分離

| コマンド | 権限 | 対象 |
| --- | --- | --- |
| `sudo make install` | 管理者 | 本体，アイコン，システム共通アプリケーションメニュー |
| `sudo make uninstall` | 管理者 | 上記のシステム共通ファイルを削除 |
| `make autostart` | 一般ユーザー | `~/.config/autostart/`に登録 |
| `make no-autostart` | 一般ユーザー | 自分の自動起動登録を解除 |

個人用自動起動は，実際にログインするユーザーで設定してください．`sudo make autostart`ではrootユーザーの設定先を変更してしまう場合があります．
