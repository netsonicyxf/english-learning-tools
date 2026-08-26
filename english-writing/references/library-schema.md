# 个人库 schema（library.json）

路径：`~/Documents/english-writing/library.json`

## 结构
```json
{
  "version": 1,
  "updated_at": "2026-08-23T10:00:00",
  "groups": [
    {
      "id": "important-1",
      "meaning_zh": "重要的",
      "items": [
        {
          "term": "crucial",
          "pos": "adj",
          "translation": "至关重要的",
          "example": "Education is crucial to social mobility.",
          "source": "<范文标题>",
          "added_at": "2026-08-23T10:00:00"
        },
        {
          "term": "play a pivotal role",
          "pos": "phrase",
          "translation": "起关键作用",
          "example": "Technology plays a pivotal role in ...",
          "source": "<范文标题>",
          "added_at": "2026-08-23T10:00:00"
        }
      ]
    }
  ],
  "ungrouped": []
}
```

## 字段说明
- `groups[].id`：语义组唯一 id（如 `important-1`），首次建组由脚本生成（基于 meaning_zh 的 slug + 计数）。
- `groups[].meaning_zh`：该同义组的汉语释义，聚类的主键。同名组合并。
- `groups[].items[]`：组内同义 term。
  - `term`：单词或词组（原文形态，建议小写原形；词组保留原样）。
  - `pos`：`adj|verb|noun|adv|phrase|other`。
  - `translation`：中文释义。
  - `example`：来源例句（尽量取自范文原句）。
  - `source`：来源范文标题。
  - `added_at`：收录时间（ISO）。
- `ungrouped`：暂未归组的项（正常流程应尽量避免，agent 聚类时尽量都进组）。

## 合并规则（manage_library.py）
1. `group_meaning_zh` 相同（精确匹配或归一化去空格/标点后匹配）的并入同一组；无则新建组并生成 `id`。
2. 同组内 `term`（小写归一化）已存在则跳过（不覆盖原有 example/source，除非原为空）。
3. `ungrouped` 仅用于 agent 未提供 `group_meaning_zh` 的情况。
