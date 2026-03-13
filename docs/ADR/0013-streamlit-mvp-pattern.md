# ADR 0013: Streamlit対応MVPパターンとUI構成規約

## Status

Accepted (2026-03-13)

## Context

### 背景

SagebaseのWebインターフェースにはStreamlitを採用しています（ADR 0001のInterface層）。Streamlitには以下の制約があります：

- **同期的実行モデル**: Streamlitのランタイムは基本的に同期的で、`async`/`await`を直接サポートしない
- **全画面リラン**: ユーザー操作のたびにスクリプト全体が再実行される
- **状態管理の特殊性**: `st.session_state`による独自の状態管理

一方、SagebaseのDomain層・Application層は完全に`async`/`await`ベースで実装されています（ADR 0003）。この非同期コードをStreamlitの同期的環境で安全に実行する方法が必要でした。

### 課題

#### 1. async/await の非互換

```python
# ❌ Streamlitから直接asyncメソッドを呼べない
result = await use_case.execute(input_dto)  # RuntimeError
```

#### 2. UIの肥大化

初期実装では、ビジネスロジックとUI表示が混在し、単一のStreamlitスクリプトが数千行に膨らんでいました。

#### 3. 多機能画面の構成

政治家管理、会派管理、議事録処理など、各機能が複数のサブ機能（一覧表示、新規作成、編集、抽出結果確認）を持ち、画面構成の統一ルールが必要でした。

### 検討した代替案

#### 1. FastAPI + React SPA

**利点**: 非同期処理のネイティブサポート、リッチなUI
**欠点**: 開発コストが大幅増。少人数チームで政治データ分析に集中すべきフェーズでは過剰

#### 2. Streamlit + asyncio.run()

```python
# △ 毎回新しいイベントループを作成
result = asyncio.run(use_case.execute(input_dto))
```

**問題点**: Streamlitが既にイベントループを持っている場合に競合する

#### 3. Streamlit + nest_asyncio + MVPパターン（選択）

`nest_asyncio`でイベントループのネストを許可し、`_run_async()`ヘルパーで統一的に非同期コードを実行する方式。

## Decision

**Streamlit環境にMVP（Model-View-Presenter）パターンを適用し、非同期変換とUI構成の規約を定める。**

### 1. 非同期→同期変換: `_run_async()` パターン

```python
import nest_asyncio
nest_asyncio.apply()

def _run_async(coro):
    """非同期コルーチンをStreamlitの同期環境で実行"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)
```

すべての非同期ユースケース呼び出しはこのヘルパーを経由する。

### 2. MVP（Model-View-Presenter）パターン

```
View（Streamlit UI）→ Presenter → UseCase → Domain
```

- **View（`.py`ファイル in `views/`）**: Streamlitウィジェットの配置のみ。ビジネスロジックなし
- **Presenter（`.py`ファイル in `presenters/`）**: Domainエンティティ/DTOをUI表示用データに変換。Streamlit依存なし
- **Model**: Domain層のエンティティとApplication層のDTO

#### Presenterの実装例

```python
class PoliticianPresenter:
    """政治家情報をUI表示用に変換"""

    @staticmethod
    def to_dataframe(politicians: list[Politician]) -> pd.DataFrame:
        """政治家リストをDataFrameに変換"""
        return pd.DataFrame([
            {"ID": p.id, "名前": p.name, "政党": p.party_name}
            for p in politicians
        ])
```

### 3. ページ→タブ→サブタブの3段階構成

複雑な機能画面を以下の3段階で構成する：

```
src/interfaces/web/streamlit/views/
├── politicians_view.py           # ページ（シンプルな機能）
├── parliamentary_groups/          # ページ（複雑な機能）
│   ├── page.py                   # ページエントリーポイント
│   ├── tabs/                     # タブ
│   │   ├── list.py               # 一覧タブ
│   │   ├── new.py                # 新規作成タブ
│   │   ├── edit_delete.py        # 編集・削除タブ
│   │   ├── member_extraction.py  # メンバー抽出タブ
│   │   └── member_review.py      # レビュータブ
│   └── subtabs/                  # サブタブ（タブ内のさらなる分割）
│       ├── review.py
│       ├── create_memberships.py
│       └── statistics.py
```

#### 分割基準

| レベル | 分割基準 | 例 |
|-------|---------|-----|
| **ページ** | ドメインエンティティ単位 | 政治家、会派、議事録 |
| **タブ** | CRUD操作 or 主要機能単位 | 一覧、新規作成、編集、抽出 |
| **サブタブ** | タブ内のワークフローステップ | レビュー、確定、統計 |

### 4. セッション状態の最小化

`st.session_state`には最小限のデータのみ保持する：

- 選択中のエンティティID
- フィルター条件
- フォーム入力値（一時的）

**禁止**: エンティティのリストや処理結果をセッション状態に長期保持しない。必要な都度、リポジトリから取得する。

### 採用理由

1. **非同期の安全な変換**: `nest_asyncio` + `_run_async()`で確実にasyncコードを実行
2. **関心の分離**: Presenterがドメイン知識とUI表示の変換を担当し、Viewをシンプルに保つ
3. **スケーラビリティ**: 3段階構成で機能追加時もファイル肥大化を防止
4. **保守性**: 各タブ/サブタブが独立したファイルで、変更の影響範囲が限定される

## Consequences

### Positive

- ✅ 非同期バックエンドとの統合が統一的なパターンで実現
- ✅ 新しい画面の追加がページ/タブ/サブタブの構造に従って系統的に行える
- ✅ Presenterのテストがユニットテストで可能（Streamlit不要）
- ✅ 画面ごとの責務が明確で、コードレビューが容易

### Negative

- ⚠️ `nest_asyncio`はイベントループのモンキーパッチであり、公式にサポートされた手法ではない
- ⚠️ Streamlitの全画面リランモデルにより、大量データの取得が毎回発生する
- **対策**: `@st.cache_data`や`@st.fragment`で部分的にキャッシュ/部分リランを活用
- ⚠️ ファイル数が多くなる（views/配下に20以上のファイル）

### Risks

- **Streamlitのバージョンアップ**: Streamlit自体がasync対応する可能性 → `_run_async()`を段階的に除去可能
- **パフォーマンス**: 全画面リランによる応答遅延 → `@st.fragment`で軽減

## References

- [ADR 0001: Clean Architecture採用](0001-clean-architecture-adoption.md)
- `src/interfaces/web/streamlit/views/` - ページ/タブ構成の実装
- `src/interfaces/web/streamlit/presenters/` - Presenter実装
- `.claude/skills/streamlit-patterns/` - Streamlit実装パターンSKILL
