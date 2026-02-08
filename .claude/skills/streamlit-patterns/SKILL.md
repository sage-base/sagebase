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

## 実装パターンまとめ

| 状況 | 解決策 |
|------|--------|
| Presenter/View層からasync UseCaseを呼ぶ | `nest_asyncio` + `loop.run_until_complete()` |
| カスケードセレクター（親→子の連動） | 依存ウィジェットを`st.form`外に配置 |
| フォーム外ウィジェット変更でタブリセット | `@st.fragment`でラップ |
| フラグメント↔フォーム間の値受け渡し | `st.session_state`を使用 |
| Presenter/View新規作成 | DI Container登録確認 + 依存の最小化 |

---

## リファレンス

- [streamlit-verification](../streamlit-verification/): Streamlit動作確認手順
- `src/infrastructure/persistence/repository_adapter.py`: `nest_asyncio`パターンの参考実装
- `src/interfaces/web/streamlit/views/conferences/widgets.py`: `@st.fragment`の実装例
