# Landing a redesign (or any doc change) in git

Use when the user names a target branch for the design work (often `main`) and the
working branch is ahead of it. Local refs are frequently stale — verify, never assume.

1. **One commit for the whole change** on the current branch — old artifacts deleted,
   new package added, superseded docs bannered, ADR added — so history reads as one
   decision.
2. **Check topology before landing:**
   - `git rev-list --left-right --count <target>...HEAD` (is target an ancestor of HEAD?)
   - `git rev-list --left-right --count <target>...origin/<target>` (is local target stale?)
   A non-zero left side means target has divergent commits and a plain fast-forward is
   impossible.
3. **Sync then merge:** `git checkout <target> && git merge --ff-only origin/<target>`,
   then merge the working branch, preferring `--ff-only` while topology allows. When a
   merge is non-ff (a PR merge commit landed on origin meanwhile), confirm it is
   **content-neutral**: `git rev-parse HEAD^{tree}` before and after the merge must be
   identical. Identical trees = safe to push. Never force-push a shared branch to fix
   topology.
4. **Push rejected** ("remote contains work that you do not have") → `git fetch`, inspect
   the new remote commits (`git log <target>..origin/<target>`), confirm content-
   neutrality the same way, merge, push again.
5. **Verify on the remote, not locally:** `git ls-remote origin refs/heads/<target>` must
   equal `git rev-parse <target>`; spot-check the pushed tree with `git ls-tree -r
   origin/<target>` (new files present, deleted artifacts gone).
6. **Deleting a directory that holds gitignored build output:** `git rm -r` only removes
   tracked files — ignored leftovers (`.gradle/`, `build/`) stay on disk, and once the
   directory's own tracked `.gitignore` is gone they can appear as untracked files.
   After the commit, check `git status`; if untracked leftovers appear, `rm -rf` them.
