---
name: streamlit-patterns
description: Streamlit UI実装の落とし穴とパターンを提供します。asyncio/nest_asyncio、st.formの制約、st.fragmentによる部分リランなど、Streamlit固有の実装パターンをカバー。Streamlit UIコンポーネントを実装・修正する時にアクティベートします。
---

# Streamlit Patterns（Streamlit実装パターン）

## 目的
Streamlit UIを実装する際に陥りやすい落とし穴と、正しい実装パターンを提供します。
特にSagebaseプロジェクト固有の非同期処理やフォーム設計に関するガイダンスを含みます。

## いつアクティベートするか
- Streamlit UIコンポーネントを新規作成・修正する時
- Streamlit内で非同期処理（async/await）を呼び出す時
- `st.form`内でウィジェットの依存関係がある時
- ウィジェット変更でページ全体リランが問題になる時

## クイックチェックリスト

### 非同期処理
- [ ] Streamlit環境で`asyncio.run()`を使っていない（`nest_asyncio`パターンを使用）
- [ ] `RepositoryAdapter._run_async()`のパターンに合わせている

### フォーム設計
- [ ] `st.form`内に依存ウィジェット（カスケードセレクター等）を配置していない
- [ ] 依存ウィジェットはフォーム外に配置し、`st.session_state`で値を受け渡している

### 部分リラン
- [ ] フォーム外のウィジェットが全ページリランを引き起こす場合、`@st.fragment`でラップしている

### パフォーマンス
- [ ] ループ内で同一引数のAPI/UseCase呼び出しを繰り返していない（ループ外でキャッシュして渡す）
- [ ] ビューで`get_all()`を呼んでいない（ページネーションまたはフィルタ必須）
- [ ] 1行あたりのStreamlit要素数が多すぎない（目安: 5個以下。`st.markdown`統合で削減）

### パフォーマンス問題の調査
- [ ] UIパフォーマンス問題の調査時、報告されたタブだけでなく**全タブ・全フラグメント**を確認した
- [ ] `@st.fragment`でも初回ロード時は全タブが描画されることを考慮した

### Presenter/View新規作成
- [ ] DI Container（`src/infrastructure/di/providers.py`）にRepository/UseCaseが登録済みか確認した
- [ ] Presenterのコンストラクタで注入する依存は、実際にメソッドで使うものだけに絞っている
- [ ] 「念のため」の未使用依存を注入していない

---

## パターン1: Streamlitでの非同期処理

### 問題
Streamlitは内部でイベントループを常時稼働させています。
`asyncio.run()`は新しいイベントループを作ろうとするため、`RuntimeError: This event loop is already running`が発生します。

### ❌ 悪い例: `asyncio.run()`を使用
```python
def get_data(self, id: int) -> list[SomeDto]:
    coro = self.use_case.list_items(id)
    return asyncio.run(coro)  # RuntimeError!
```

### ✅ 良い例: `nest_asyncio` + `loop.run_until_complete()`
```python
def get_data(self, id: int) -> list[SomeDto]:
    try:
        import asyncio
        import nest_asyncio
        nest_asyncio.apply()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        coro = self.use_case.list_items(id)
        return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"Failed: {e}")
        return []
```

### 参考実装
`RepositoryAdapter._run_async()`が同じパターンを使用しています。
Presenter層で非同期UseCaseを呼ぶ場合は、このパターンに統一してください。

**ファイル**: `src/infrastructure/persistence/repository_adapter.py`

---

## パターン2: `st.form`内の依存ウィジェット

### 問題
`st.form`内のウィジェットは、フォーム送信まで値が確定しません。
そのため、あるウィジェットの値に依存する別のウィジェット（カスケードセレクター）は、
フォーム内では正しく連動しません。

### ❌ 悪い例: 依存ウィジェットをフォーム内に配置
```python
with st.form("my_form"):
    # 親セレクター
    selected_parent = st.selectbox("親カテゴリ", options=parent_options)
    parent_id = parent_map[selected_parent]

    # 子セレクター（親に依存）→ フォーム送信まで parent_id が更新されない！
    children = get_children(parent_id)  # 常にデフォルト値の子が返る
    selected_child = st.selectbox("子カテゴリ", options=children)
```

### ✅ 良い例: 依存ウィジェットをフォーム外に配置
```python
# フォーム外: 選択変更で即座にリラン
selected_parent = st.selectbox("親カテゴリ", options=parent_options)
parent_id = parent_map[selected_parent]

children = get_children(parent_id)  # 選択に応じた子が返る
selected_child = st.selectbox("子カテゴリ", options=children)

# フォーム内: 入力フィールドと送信ボタンのみ
with st.form("my_form"):
    name = st.text_input("名前")
    submitted = st.form_submit_button("登録")
    if submitted:
        handle_submit(name, parent_id, selected_child)
```

---

## パターン3: `@st.fragment`による部分リラン

### 問題
フォーム外のウィジェットを変更すると、ページ全体がリランされます。
`st.tabs`内のタブにいる場合、リランでタブ選択がリセットされることがあります。

### ❌ 悪い例: フォーム外のselectboxがそのまま配置
```python
# タブ内でselectbox変更 → ページ全体リラン → タブリセット
selected = st.selectbox("選択", options=options)
dependent_data = fetch_data(selected)
```

### ✅ 良い例: `@st.fragment`でラップ
```python
gb_key = f"{prefix}_selected_id"
child_key = f"{prefix}_child_id"

@st.fragment
def _selector_fragment() -> None:
    selected = st.selectbox("選択", options=options, key=f"{prefix}_select")
    st.session_state[gb_key] = option_map[selected]

    child = fetch_data(st.session_state[gb_key])
    st.session_state[child_key] = child

_selector_fragment()

# フォームでは session_state 経由で値を取得
selected_id = st.session_state.get(gb_key)
child_id = st.session_state.get(child_key)
```

### `@st.fragment`の特徴
- Streamlit 1.33+で利用可能（Sagebaseでは1.46.1を使用）
- フラグメント内のウィジェット変更は、フラグメント部分だけを再描画
- ページ全体のリランが発生しないため、タブ状態やスクロール位置が保持される
- フラグメント内からフラグメント外への値の受け渡しは`st.session_state`を使用

---

## パターン4: Presenter/View新規作成時のDI確認

### 問題
新しいPresenter/Viewを作成する際、対応するRepository/UseCaseがDI Container（`providers.py`）に
登録されていないことがあります。また、「後で使うかもしれない」と不要な依存を注入してしまうことがあります。

### チェック手順

1. **DI Container登録の確認**: `src/infrastructure/di/providers.py`を開き、使用するRepository/UseCaseが
   `RepositoryContainer`/`UseCaseContainer`に登録されているか確認する
2. **未登録の場合**: RepositoryImpl/UseCaseの`Factory`登録を追加する
3. **依存の最小化**: Presenterのコンストラクタでは、メソッドで実際に呼び出す依存だけを注入する

### ❌ 悪い例: 未使用の依存を注入
```python
class MyPresenter(BasePresenter[list[SomeOutputItem]]):
    def __init__(self, container: Container | None = None):
        super().__init__(container)
        self.use_case = self.container.use_cases.manage_something_usecase()
        self.other_repo = self.container.repositories.other_repository()  # どのメソッドでも使わない！
```

### ✅ 良い例: 必要な依存だけを注入
```python
class MyPresenter(BasePresenter[list[SomeOutputItem]]):
    def __init__(self, container: Container | None = None):
        super().__init__(container)
        self.use_case = self.container.use_cases.manage_something_usecase()
        # other_repo は使わないので注入しない
```

---

## パターン5: ループ内の冗長なAPI呼び出し

### 問題
メンバー詳細のように複数アイテムをループ表示する際、各アイテムの描画関数内で同一引数のAPI/UseCase呼び出しを繰り返すと、表示件数分のクエリが発生する。

### ❌ 悪い例: ループ内で毎回呼び出し
```python
for member in display_members:
    _render_member_detail(member, usecase)

def _render_member_detail(member, usecase):
    # 同じconference_idに対して毎回呼ばれる → N回のDB問い合わせ
    candidates = _run_async(
        usecase.get_election_candidates(
            GetElectionCandidatesInputDTO(conference_id=member.conference_id)
        )
    )
```

### ✅ 良い例: ループ外でキャッシュして渡す
```python
# conference_idごとに1回だけ取得
cache: dict[int, SearchPoliticiansOutputDTO] = {}
for member in display_members:
    cid = member.conference_id
    if cid not in cache:
        cache[cid] = _run_async(
            usecase.get_election_candidates(
                GetElectionCandidatesInputDTO(conference_id=cid)
            )
        )

for member in display_members:
    _render_member_detail(member, usecase, cache.get(member.conference_id))
```

---

## パターン6: ビューでの`get_all()`禁止とWebSocket過負荷

### 問題
Streamlitでは各UI要素（`st.markdown`, `st.button`, `st.columns`等）がWebSocketメッセージを生成する。
ビューで`get_all()`を使って大量レコードを取得し、各行を複数のStreamlit要素でレンダリングすると、
WebSocketメッセージが数万〜数十万件に達し、`tornado.websocket.WebSocketClosedError`でクラッシュする。

### ❌ 悪い例: `get_all()`で全件取得して全行表示
```python
# judges テーブルに数万件 × 各行10要素 = 数十万WebSocketメッセージ → クラッシュ
judges = presenter.load_extracted_judges(proposal_id=None)  # get_all()
for judge in judges:
    col1, col2, col3 = st.columns(3)      # 要素1
    with col1:
        st.markdown(f"**{judge.name}**")   # 要素2
    with col2:
        st.markdown(judge.status)          # 要素3
    with col3:
        st.button("編集", key=f"edit_{judge.id}")  # 要素4
```

### ✅ 良い例: フィルタ/ページネーション必須 + 要素統合
```python
# 必ずフィルタまたはページネーションで件数を制限
judges = presenter.load_extracted_judges(proposal_id=proposal_id)  # フィルタ済み

for judge in judges:
    # 複数のst.markdownを1つに統合してWebSocketメッセージを削減
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"**{judge.name}** | {judge.status}")  # 1要素に統合
    with col2:
        st.button("編集", key=f"edit_{judge.id}")
```

### 目安
- 1行あたりのStreamlit要素数: **5個以下**
- 1ページの表示件数: **10〜20件**（ページネーション必須）
- `get_all()`は**ビューから直接呼ばない**（フィルタ条件またはID指定を必須にする）

### 参考実装
`src/interfaces/web/streamlit/views/proposals_view.py`: `render_proposal_display()`が要素統合の実装例

---

## パターン7: `@st.fragment`と初回ロードの落とし穴

### 問題
`@st.fragment`はウィジェット変更時の**部分リラン**には有効だが、
**ページ初回ロード時は全フラグメントが描画される**。
そのため、`@st.fragment`で囲んだタブ内に重いデータ取得（`get_all()`等）があると、
そのタブが表示されていなくても初回ロードで実行されてしまう。

### ❌ 悪い例: fragmentで囲んでいるから安全、と思い込む
```python
tab1, tab2, tab3 = st.tabs(["一覧", "抽出結果", "確定結果"])

with tab2:
    @st.fragment
    def render_tab2():
        # ユーザーがTab2を選択していなくても、ページ初回ロードで実行される！
        all_judges = presenter.load_all_judges()  # 数万件取得
        for judge in all_judges:
            render_judge_row(judge)  # 数万行 × 10要素 = WebSocketクラッシュ
    render_tab2()
```

### ✅ 良い例: 重いタブは必ずフィルタ条件を要求する
```python
with tab2:
    @st.fragment
    def render_tab2():
        # フィルタ条件を必須にし、初回ロードでは全件取得しない
        proposal_id = st.number_input("議案ID", min_value=1, value=1)
        judges = presenter.load_judges(proposal_id=proposal_id)  # 数件〜数十件
        for judge in judges:
            render_judge_row(judge)
    render_tab2()
```

### 調査のポイント
UIパフォーマンス問題（WebSocketClosedError等）を調査する際は、**報告されたタブだけでなく全タブ・全フラグメントを確認する**こと。
問題のあるタブが表示されていなくても、初回ロード時に描画が走っている可能性がある。

---

## 実装パターンまとめ

| 状況 | 解決策 |
|------|--------|
| Presenter/View層からasync UseCaseを呼ぶ | `nest_asyncio` + `loop.run_until_complete()` |
| カスケードセレクター（親→子の連動） | 依存ウィジェットを`st.form`外に配置 |
| フォーム外ウィジェット変更でタブリセット | `@st.fragment`でラップ |
| フラグメント↔フォーム間の値受け渡し | `st.session_state`を使用 |
| Presenter/View新規作成 | DI Container登録確認 + 依存の最小化 |
| ループ内で同一引数のAPI呼び出し | ループ外でキャッシュ（dict）して各アイテムに渡す |
| ビューで大量レコードを表示 | `get_all()`禁止、フィルタ/ページネーション必須、要素統合 |
| `@st.fragment`タブで重いデータ取得 | 初回ロードで全タブ描画されるため、フィルタ条件を必須にする |

---

## リファレンス

- [streamlit-verification](../streamlit-verification/): Streamlit動作確認手順
- `src/infrastructure/persistence/repository_adapter.py`: `nest_asyncio`パターンの参考実装
- `src/interfaces/web/streamlit/views/conferences/widgets.py`: `@st.fragment`の実装例
