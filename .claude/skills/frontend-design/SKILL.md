# frontend-design SKILL Overview

## Summary Table

| Property | Value |
|----------|-------|
| **Name** | frontend-design |
| **Description** | Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications. Generates creative, polished code that avoids generic AI aesthetics. |
| **License** | Complete terms in LICENSE.txt |

## Purpose

This skill guides the creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. It implements real working code with exceptional attention to aesthetic details and creative choices.

## Design Thinking Process

Before coding, understand context and commit to a **BOLD aesthetic direction**:

1. **Purpose**: What problem does this interface solve? Who uses it?
2. **Tone**: Pick an extreme aesthetic (brutally minimal, maximalist, retro-futuristic, organic, luxury, playful, editorial, brutalist, art deco, soft/pastel, industrial, etc.)
3. **Constraints**: Technical requirements (framework, performance, accessibility)
4. **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision.

## Frontend Aesthetics Guidelines

### Focus Areas

- **Typography**: Choose distinctive, characterful fonts. Avoid generics (Arial, Inter). Pair a distinctive display font with a refined body font.

- **Color & Theme**: Commit to cohesive aesthetics. Use CSS variables. Dominant colors with sharp accents outperform timid palettes.

- **Motion**: Use animations for high-impact moments (staggered page load reveals, scroll-triggering, hover surprises). Prefer CSS-only for HTML; use Motion library for React.

- **Spatial Composition**: Unexpected layouts, asymmetry, overlap, diagonal flow, grid-breaking elements, generous negative space or controlled density.

- **Backgrounds & Visual Details**: Create atmosphere with gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, grain overlays.

### What to AVOID

- Generic AI aesthetics (overused fonts, clichéd purple gradients, predictable layouts)
- Cookie-cutter design lacking context-specific character
- Convergence on common choices

### Key Principle

**Match implementation complexity to aesthetic vision**:
- Maximalist designs need elaborate code with extensive animations
- Minimalist/refined designs need restraint and precision in spacing, typography, and subtle details

The code should be:
- ✅ Production-grade and functional
- ✅ Visually striking and memorable
- ✅ Cohesive with clear aesthetic point-of-view
- ✅ Meticulously refined in every detail

## Activation Conditions

This skill should be activated when:
- ユーザーがWebコンポーネント、ページ、アプリケーションの構築を依頼した時
- フロントエンドのUIデザインを改善したい時
- デザイン性の高いインターフェースを作成する必要がある時
- 既存のWebページのデザインを洗練させたい時

## Implementation for Sagebase

Sagebaseプロジェクトでは、以下のフロントエンド要素にこのSKILLを適用します：

- Hugo静的サイト（`just website`でビルド）
- Streamlit BI Dashboard（`just bi-dashboard`で起動）
- その他のWeb UI要素

### Design Philosophy for Sagebase

政治活動追跡アプリケーションという性質上、以下の点を重視します：

- **信頼性と権威性**: 政治データを扱うため、プロフェッショナルで信頼できる印象
- **データの可読性**: 複雑な政治データを明確に伝えるタイポグラフィとレイアウト
- **日本語フォント最適化**: 日本語テキストの美しい表示
- **アクセシビリティ**: 幅広いユーザーがアクセス可能なデザイン

### 🎨 Political Neutrality & Monochrome Principle（政治的中立性とモノクローム原則）

**CRITICAL DESIGN PRINCIPLE（重要なデザイン原則）**:

Sagebaseは政治データを扱う中立的なプラットフォームであるため、**政治的メッセージ性を持たせないことが最優先**です。

#### モノクローム配色の採用理由

1. **政治的中立性の視覚的表現**
   - 特定の色（ブルー＝保守、レッド＝革新など）が政治的立場を連想させることを避ける
   - モノクローム（白・黒・グレーのグラデーション）により、完全な中立性を保つ
   - データそのものに焦点を当て、プラットフォーム側の意見を視覚的に示さない

2. **信頼性とプロフェッショナリズム**
   - 新聞・学術論文のような客観的で信頼できる印象
   - 感情的な訴求ではなく、事実とデータに基づく印象
   - 非営利法人としての公正性を視覚的に担保

3. **データの可視性向上**
   - 装飾的な色を排除することで、データ自体が際立つ
   - ユーザーの注意を重要な情報に集中させる
   - 視覚的なノイズを最小化

#### 許可される色の使用

- **ベースカラー**: 黒（#000000 ~ #1a1a1a）、白（#ffffff）、グレー（#333333 ~ #f5f5f5）のみ
- **アクセントカラー**: 原則として使用しない
- **例外**:
  - エラー表示など、ユーザビリティ上必要な場合のみ、最小限の色を使用可能
  - その場合も、政治的連想を避けるため、赤・青・緑などの鮮やかな色は避け、グレースケールに近い控えめな色調を選択

#### Aesthetic Direction（美学的方向性）

**Editorial / Journalistic Monochrome Aesthetic（編集・ジャーナリスティック・モノクローム美学）**

- **新聞・雑誌のような紙媒体の権威性**: タイポグラフィと余白による視覚階層
- **ミニマリスト哲学**: 装飾を排除し、本質（データ）に集中
- **テクスチャによる深み**: 色ではなく、微細なノイズテクスチャ、影、罫線で視覚的な豊かさを表現
- **タイポグラフィの洗練**: フォントの選択、サイズ、太さ、行間で表現力を最大化

#### Implementation Guidelines（実装ガイドライン）

✅ **推奨される表現手法**:
- タイポグラフィの階層（見出し・本文のコントラスト）
- 余白とスペーシング
- 罫線とボーダー
- グラデーション（グレースケールのみ）
- 影とレイヤー効果
- テクスチャ（紙質感、ノイズグレイン）
- アニメーション（控えめで洗練されたもの）

❌ **避けるべき表現**:
- 鮮やかな色の使用（ブルー、レッド、グリーン、パープルなど）
- 政治的シンボルや連想を生む色の組み合わせ
- 感情的・主観的な印象を与える配色
- 装飾過多なデザイン

#### Code Implementation Requirements（コード実装要件）

CSS変数で完全にモノクロームのカラーパレットを定義：

```css
:root {
  /* Monochrome Base Colors */
  --color-black: #000000;
  --color-dark: #1a1a1a;
  --color-gray-900: #171717;
  --color-gray-800: #262626;
  --color-gray-700: #404040;
  --color-gray-600: #525252;
  --color-gray-500: #737373;
  --color-gray-400: #a3a3a3;
  --color-gray-300: #d4d4d4;
  --color-gray-200: #e5e5e5;
  --color-gray-100: #f5f5f5;
  --color-white: #ffffff;
}
```

この原則に従い、すべてのUI要素をモノクロームで実装すること。
