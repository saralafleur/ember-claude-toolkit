# librarian config — `library-locations.json`

The registry that tells the librarian **where the library lives** and **which repos
are bound to which library**. The skill reads this on every run; if `libraries` is
empty it runs first-run setup (asks Sara where the library should live).

## Schema

```jsonc
{
  "version": 1,

  // One entry per physical library root. Many repos can share one root.
  "libraries": [
    {
      "id": "primary",                       // short stable id
      "root": "/abs/path/to/library",        // absolute path to the library folder
      "label": "Primary knowledge library",  // human label
      "createdAt": "2026-06-30"
    }
  ],

  // Which repo (by absolute path) defaults to which library id. Optional —
  // a repo with no binding is asked to pick an existing library or declare one.
  "repoBindings": [
    {
      "repoPath": "/abs/path/to/some/repo",
      "libraryId": "primary",
      "boundAt": "2026-06-30"
    }
  ]
}
```

## Rules
- `root` is **absolute**. The library is shared infrastructure, not repo-relative.
- Multiple `repoBindings` may point at the **same** `libraryId` — that is how
  several repos pool into one library.
- Only the `librarian-archivist` writes this file, and only after Sara approves a
  setup/binding change. Hand-editing is allowed but keep it valid JSON.

## Distribution note
This plugin ships with an **empty** `library-locations.json` (no libraries, no
bindings) so every fresh install goes through first-run setup rather than
inheriting someone else's library locations. Once you bind libraries locally,
keep that real data out of any copy of this repo you intend to publish or share
— treat it as local instance state, not shippable skill content.
